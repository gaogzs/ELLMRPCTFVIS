import os
import json
import math

from config import print_warning_message, print_dev_message, ModelInfo, _ERROR_RETRIES
from utils.loaders import PromptLoader, SchemaLoader, InputTemplateLoader
from api_wrapper.sentence_similarity_lm import SentenceSimilarityWorker

SIMILARITY_BASE_VALUE = 0.7

class OutlineProcessingError(Exception):
    pass

class Section:
    def __init__(self, content: str):
        self.content = content
        self.subsections = []

    def add_subsection(self, content: str):
        new_subsection = Section(content)
        self.subsections.append(new_subsection)
    
    def get_latest_subsection(self):
        if self.subsections:
            return self.subsections[-1]
        return None
    
    def self_to_str(self) -> str:
        return self.content
    
    def recur_to_str(self,  indent_base = 0, indent_add = 2) -> str:
        indent_str = " " * indent_base
        result = indent_str + self.self_to_str() + "\n"
        for subsection in self.subsections:
            result += subsection.recur_to_str(indent_base + indent_add, indent_add)
        return result

class Outline:
    def __init__(self):
        self.chapters = []
    
    def add_chapter(self, content: str):
        new_chapter = Section(content)
        self.chapters.append(new_chapter)
    
    def add_section(self, content: str):
        self.chapters[-1].add_subsection(content)
    
    def get_latest_section(self):
        if self.chapters:
            if self.chapters[-1].subsections:
                return self.chapters[-1].subsections[-1].self_to_str()
            else:
                return self.chapters[-1].self_to_str()
        return None
    
    def to_str(self) -> str:
        if not self.chapters:
            return "Empty"
        result = ""
        for chapter in self.chapters:
            result += chapter.recur_to_str()
        return result
    
class OutlineEvaluatorSession:
    def __init__(self, model_info: ModelInfo, similarity_model: str, prompt_dir: str, schema_dir: str, input_template_dir: str) -> None:
        self.model_info = model_info
        self.prompt_loader = PromptLoader(prompt_dir)
        self.schema_loader = SchemaLoader(schema_dir)
        self.input_template_loader = InputTemplateLoader(input_template_dir)
        self.similarity_model = similarity_model
        self.similarity_model_info = ModelInfo(similarity_model)

        self.chatbot = self.model_info.chatbot()
        self.outline = Outline()
        self.predictions = []
        self.rp_history = []
        self.logs = []

    def get_outline(self) -> Outline:
        return self.outline
    
    def get_previous_story(self) -> str:
        if self.rp_history:
            return self.rp_history[-1]
        return "Empty"

    def append_conversation(self, lastest_conversation: str) -> None:
        previous_outline = self.outline.to_str()
        previous_story = self.get_previous_story()
        new_chapter, new_sections, predicted_sections = self.handle_outline_builder(lastest_conversation, previous_outline, previous_story)
        first_section = new_sections[0]
        
        single_likelihood_result = None
        multi_likelihood_result = None
        similarity_results = None
        last_prediction = None
        if self.predictions:
            last_prediction = self.predictions[-1]
            similarity_results, prediction_options = self.handle_similarity_worker(first_section, last_prediction)
            multi_likelihood_result = self.handle_outline_multi_likelihood(first_section, new_chapter, prediction_options, previous_outline, previous_story)
            single_likelihood_result = self.handle_outline_single_likelihood(first_section, new_chapter, prediction_options, previous_outline, previous_story)
        
        self.predictions.append(predicted_sections)
        self.rp_history.append(lastest_conversation)
        
        new_log = {
            "conversation": lastest_conversation,
            "new_chapter": new_chapter,
            "new_sections": new_sections,
            "similarity_results": similarity_results,
            "multi_likelihood_result": multi_likelihood_result,
            "single_likelihood_result": single_likelihood_result,
        }
        self.logs.append(new_log)
        
        # Return predicability and abruptness
    
    def handle_outline_builder(self, lastest_conversation: str, existing_outline: str, previous_story: str) -> tuple[str, str, list[str]]:
        message = self.input_template_loader.load("outline_builder").format(existing_outline=existing_outline, previous_story=previous_story, new_story=lastest_conversation)
        
        processed_success = False
        tries_count = _ERROR_RETRIES
        
        if self.model_info.output_format() == "json":
            sys_prompt = self.prompt_loader.load_sys_prompts("outline_builder", subtype="json")
            bot = self.chatbot(self.model_info.model(), sys_prompt, self.schema_loader)
            
            while not processed_success:
                try:
                    text_response, json_response = bot.get_structured_response(message, schema_key="outline_builder", record=True, temperature=0.2)
                    print_dev_message("Outline Builder Response:")
                    print_dev_message(text_response)
                    
                    new_chapter = None
                    if json_response["new_chapter"]["create"]:
                        new_chapter = json_response["new_chapter"]["content"]
                        self.outline.add_chapter(new_chapter)
                    
                    new_sections = json_response["new_sections"]
                    for section in new_sections:
                        self.outline.add_section(section)
                    
                    predicted_sections = json_response["predicted_sections"]
                    if not predicted_sections:
                        raise OutlineProcessingError("No predicted sections found in the response.")
                        
                    processed_success = True
                except Exception as e:
                    message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                    print_dev_message("Error in response division:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        raise e
        else:
            raise NotImplementedError("Output format not supported for this method.")
    
        return new_chapter, new_sections, predicted_sections
    
    def handle_similarity_worker(self, new_section: str, predicted_sections: list[str]) -> tuple[list[float], list[str]]:
        similarities = []
        if not self.similarity_model_info.is_valid():
            similarity_worker = SentenceSimilarityWorker(self.similarity_model)
            similarities = [similarity_worker.cosine_similarity(new_section, section) for section in predicted_sections]
        else:
            message = self.input_template_loader.load("outline_similarity").format(predictions=predicted_sections, real_section=new_section)
            if self.model_info.output_format() == "json":
                sys_prompt = self.prompt_loader.load_sys_prompts("outline_similarity", subtype="json")
                bot = self.chatbot(self.similarity_model_info.model(), sys_prompt, self.schema_loader)
                
                text_response, json_response = bot.get_structured_response(message, schema_key="outline_similarity", record=False, temperature=0.2)
                print(message)
                print(text_response)
                similarities = json_response["similarities"]
            else:
                raise NotImplementedError("Output format not supported for this method.")
        
        print_dev_message(f"New Real Section: {new_section}")
        for prediction, result in zip(predicted_sections, similarities):
            print_dev_message(f"  '{prediction}': {result:.4f}")
        
        best_similarity = max(similarities)
        best_prediction_index = similarities.index(best_similarity)
        print_dev_message(f"Best prediction: '{predicted_sections[best_prediction_index]}' with similarity {best_similarity:.4f}")
        
        similarity_base = SIMILARITY_BASE_VALUE
        prediction_options = predicted_sections[:best_prediction_index] + predicted_sections[best_prediction_index + 1:]
        
        corresponding_similarities = {prediction: similarity for prediction, similarity in zip(predicted_sections, similarities)}
        
        similarity_results = {
            "similarities": corresponding_similarities,
            "best_similarity": best_similarity,
            "best_similarity_score": 1 / math.log(best_similarity, SIMILARITY_BASE_VALUE),
        }
        
        return similarity_results, prediction_options
    
    def handle_outline_multi_likelihood(self, new_section: str, new_chapter: str, prediction_options: list[str], existing_outline: str, previous_story: str) -> dict:
        options = prediction_options + [new_section]
        options_text = "\n".join([f"{i + 1}. {option}" for i, option in enumerate(options)])
        correct_answer_index = options.index(new_section)
        message = self.input_template_loader.load("outline_multi_likelihood").format(existing_outline=existing_outline, latest_story=previous_story, options=options_text)
        
        processed_success = False
        tries_count = _ERROR_RETRIES
        
        if self.model_info.output_format() == "json":
            sys_prompt = self.prompt_loader.load_sys_prompts("outline_multi_likelihood", subtype="json")
            bot = self.chatbot(self.model_info.model(), sys_prompt, self.schema_loader)
            
            while not processed_success:
                try:
                    text_response, json_response = bot.get_structured_response(message, schema_key="outline_multi_likelihood", record=True, temperature=0.2)
                    print_dev_message("Outline Multi Likelihood Response:")
                    print_dev_message(text_response)
                    
                    corresponding_prediction_results = {option: result for option, result in zip(options, json_response["option_likelihoods"])}
                    
                    final_score = json_response["option_likelihoods"][correct_answer_index] * len(options) - 1
                    multichoice_result = {
                        "new_chapter_probability": json_response["new_chapter_probability"],
                        "new_chapter_truth": 0 if new_chapter is None else 1,
                        "option_likelihoods": corresponding_prediction_results,
                        "correct_option_score": final_score
                    }
                    print_dev_message(multichoice_result)
                    
                    processed_success = True
                except Exception as e:
                    message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                    print_dev_message("Error in response division:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        raise e
        else:
            raise NotImplementedError("Output format not supported for this method.")
        
        return multichoice_result
    
    def handle_outline_single_likelihood(self, new_section: str, new_chapter: str, prediction_options: list[str], existing_outline: str, previous_story: str) -> dict:
        
        processed_success = False
        tries_count = _ERROR_RETRIES
        
        if self.model_info.output_format() == "json":
            sys_prompt = self.prompt_loader.load_sys_prompts("outline_single_likelihood", subtype="json")
            bot = self.chatbot(self.model_info.model(), sys_prompt, self.schema_loader)
            
            while not processed_success:
                try:
                    corresponding_prediction_results = {}
                    for prediction in prediction_options:
                        message = self.input_template_loader.load("outline_single_likelihood").format(existing_outline=existing_outline, latest_story=previous_story, prediction=prediction)
                        text_response, json_response = bot.get_structured_response(message, schema_key="outline_single_likelihood", record=False, temperature=0)
                        corresponding_prediction_results[prediction] = json_response["likelihood"]
                    score_sum = sum(corresponding_prediction_results.values())
                    
                    message = self.input_template_loader.load("outline_single_likelihood").format(existing_outline=existing_outline, latest_story=previous_story, prediction=new_section)
                    corresponding_prediction_results[new_section] = json_response["likelihood"]
                    
                    final_score = json_response["likelihood"] / (score_sum + json_response["likelihood"]) * len(corresponding_prediction_results) - 1
                    multichoice_result = {
                        "new_chapter_probability": json_response["new_chapter_probability"],
                        "new_chapter_truth": 0 if new_chapter is None else 1,
                        "option_likelihoods": corresponding_prediction_results,
                        "correct_option_score": final_score
                    }
                    print_dev_message(multichoice_result)
                    
                    processed_success = True
                except Exception as e:
                    print_dev_message("Error in response division:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        raise e
        else:
            raise NotImplementedError("Output format not supported for this method.")
        
        return multichoice_result
        
    def export_logs(self, file_path: str) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.logs, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    
    model = "gemini-structured"
    similarity_model = "gemini-structured"
    
    sample_narrative = []
    with open(os.path.join(cur_dir, "sample_rp.json"), "r", encoding="utf-8") as f:
        sample_narratives = json.load(f)
        sample_narrative = sample_narratives[-1]
    
    prompt_dir = os.path.join(cur_dir, "prompts")
    schema_dir = os.path.join(cur_dir, "schemas")
    input_template_dir = os.path.join(cur_dir, "input_templates")

    using_model_info = ModelInfo(model)

    outline_session = OutlineEvaluatorSession(using_model_info, similarity_model, prompt_dir=prompt_dir, schema_dir=schema_dir, input_template_dir=input_template_dir)
    
    for section in sample_narrative:
        outline_session.append_conversation(section)
        outline_session.export_logs(os.path.join(cur_dir, "sample_outline_log.json"))