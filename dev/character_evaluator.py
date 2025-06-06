import os
import json

from config import print_warning_message, print_dev_message, ModelInfo, _ERROR_RETRIES
from utils.loaders import PromptLoader, SchemaLoader, InputTemplateLoader

class CharacterProcessingError(Exception):
    pass

class CharacterInfo:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.traits = []
    
    def add_trait(self, trait):
        self.traits.append(trait)
    
    def update_description(self, new_description):
        if new_description:
            self.description = new_description
        else:
            print_warning_message(f"Empty description provided for character '{self.name}'. Keeping the old description.")
    
    def to_str_simple(self):
        return f"{self.name}: {self.description}"
    
    def to_str_full(self):
        traits_str = '\n'.join(self.traits) if self.traits else 'No traits so far'
        return f"character_name: {self.name}\ncharacter_description: {self.description}\ncharacter_traits:\n{traits_str}"

    def to_dict(self):
        return {
            "character_name": self.name,
            "character_description": self.description,
            "character_traits": self.traits
        }

class CharacterEvaluatorSession:
    def __init__(self, model_info: ModelInfo, prompt_dir: str, schema_dir: str, input_template_dir: str):
        self.model_info = model_info
        self.prompt_loader = PromptLoader(prompt_dir)
        self.schema_loader = SchemaLoader(schema_dir)
        self.input_template_loader = InputTemplateLoader(input_template_dir)
        
        self.chatbot = self.model_info.chatbot()
        self.character_records = {}
        self.logs = []
    
    def get_simple_strs(self, character_names) -> list[CharacterInfo]:
        out_str = ""
        if character_names == "all":
            for name, info in self.character_records.items():
                out_str += info.to_str_simple() + "\n"
        else:
            for name in character_names:
                if name in self.character_records:
                    out_str += self.character_records[name].to_str_simple() + "\n"
                else:
                    raise CharacterProcessingError(f"Character '{name}' not found in records.")
        return out_str

    def get_full_strs(self, character_names) -> list[CharacterInfo]:
        out_str = ""
        if character_names == "all":
            for name, info in self.character_records.items():
                out_str += info.to_str_full() + "\n\n"
        else:
            for name in character_names:
                if name in self.character_records:
                    out_str += self.character_records[name].to_str_full() + "\n\n"
                else:
                    raise CharacterProcessingError(f"Character '{name}' not found in records.")
        return out_str
    
    def append_conversation(self, lastest_conversation: str) -> dict:
        appeared_characters, actions = self.handle_character_extractor(lastest_conversation)
        integrity_scores = self.handle_integrity_evaluator(actions)
        self.handle_trait_extractor(lastest_conversation, appeared_characters)
        
        new_log = {
            "conversation": lastest_conversation,
            "integrity_scores": integrity_scores,
            "characters": [char.to_dict() for char in self.character_records.values()]
        }
        self.logs.append(new_log)
        
        return integrity_scores
    
    def handle_character_extractor(self, lastest_conversation: str) -> tuple[list[str], dict]:
        processed_success = False
        tries_count = _ERROR_RETRIES
        
        if self.model_info.output_format() == "json":
            sys_prompt = self.prompt_loader.load_sys_prompts("character_extractor", subtype="json")
            input_template = self.input_template_loader.load("character_extractor")
            message = input_template.format(story=lastest_conversation,  existing_characters=self.get_simple_strs("all"))
            bot = self.chatbot(self.model_info.model(), sys_prompt, self.schema_loader)
            while not processed_success:
                try:
                    text_response, json_response = bot.get_structured_response(message, schema_key="character_extractor", record=True, temperature=0.2)
                    print_dev_message(f"Character extractor response:")
                    print_dev_message(text_response)
                    appeared_characters = []
                    actions = {}
                    for character in json_response["characters"]:
                        appeared_characters.append(character["character_name"])
                        if character["character_name"] not in self.character_records:
                            self.character_records[character["character_name"]] = CharacterInfo(character["character_name"], character["character_description"])
                        actions[character["character_name"]] = character["character_behaviours"]
                    processed_success = True
                except Exception as e:
                    message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                    print_dev_message("Error in response division:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        raise e
        else:
            raise NotImplementedError("Only JSON output format is supported for character extraction.")
    
        return appeared_characters, actions
    
    def handle_integrity_evaluator(self, actions: dict) -> dict:
        processed_success = False
        tries_count = _ERROR_RETRIES
        
        integrity_scores = {}
        
        if self.model_info.output_format() == "json":
            sys_prompt = self.prompt_loader.load_sys_prompts("character_integrity", subtype="json")
            for name, char_actions in actions.items():
                if name not in self.character_records:
                    raise CharacterProcessingError(f"Character '{name}' not found in records.")
                
                input_template_1 = self.input_template_loader.load("character_integrity_self")
                message = input_template_1.format(character_information=self.character_records[name].to_str_full())
                bot = self.chatbot(self.model_info.model(), sys_prompt, self.schema_loader)
                integrity_scores[name] = {}
                while not processed_success:
                    try:
                        text_response, json_response = bot.get_structured_response(message, schema_key="character_integrity_self", record=True, temperature=0.2)
                        print_dev_message(f"Integrity self evaluation: {text_response}")
                        integrity_scores[name]["self_integrity"] = json_response["integrity_score"]
                        processed_success = True
                    except Exception as e:
                        message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                        print_dev_message("Error in integrity evaluation:", e)
                        tries_count -= 1
                        if tries_count <= 0:
                            raise e
                        
                input_template_2 = self.input_template_loader.load("character_integrity_cross")
                action_str = name + ":\n" +  "\n".join(char_actions)
                message = input_template_2.format(character_actions=action_str)
                processed_success = False
                while not processed_success:
                    try:
                        text_response, json_response = bot.get_structured_response(message, schema_key="character_integrity_cross", record=True, temperature=0.2)
                        print_dev_message(f"Integrity cross evaluation: {text_response}")
                        integrity_scores[name]["action_integrity"] = json_response["action_score"]
                        processed_success = True
                    except Exception as e:
                        message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                        print_dev_message("Error in integrity evaluation:", e)
                        tries_count -= 1
                        if tries_count <= 0:
                            raise e
        else:
            raise NotImplementedError("Only JSON output format is supported for integrity evaluation.")
        
        return integrity_scores
    
    def handle_trait_extractor(self, lastest_conversation:str, appeared_characters: list[str]) -> None:
        processed_success = False
        tries_count = _ERROR_RETRIES
        
        if self.model_info.output_format() == "json":
            sys_prompt = self.prompt_loader.load_sys_prompts("character_trait_extractor", subtype="json")
            input_template = self.input_template_loader.load("character_trait_extractor")
            message = input_template.format(story=lastest_conversation, character_information=self.get_simple_strs(appeared_characters))
            bot = self.chatbot(self.model_info.model(), sys_prompt, self.schema_loader)
            while not processed_success:
                try:
                    text_response, json_response = bot.get_structured_response(message, schema_key="character_trait_extractor", record=True, temperature=0.2)
                    print_dev_message(f"Trait extractor response:")
                    print_dev_message(text_response)
                    for character in json_response["characters"]:
                        if character["character_name"] in appeared_characters:
                            if character["character_name"] not in self.character_records:
                                raise CharacterProcessingError(f"Character '{character['character_name']}' not found in records.")
                            self.character_records[character["character_name"]].update_description(character["character_description"])
                            for trait in character["character_traits"]:
                                self.character_records[character["character_name"]].add_trait(trait)
                    processed_success = True
                except Exception as e:
                    message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                    print_dev_message("Error in trait extraction:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        raise e
        else:
            raise NotImplementedError("Only JSON output format is supported for trait extraction.")

    def export_logs(self, file_path: str) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.logs, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    
    model = "gemini-structured"
    
    sample_narrative = []
    with open(os.path.join(cur_dir, "sample_rp.json"), "r", encoding="utf-8") as f:
        sample_narratives = json.load(f)
        sample_narrative = sample_narratives[-1]
    
    prompt_dir = os.path.join(cur_dir, "prompts")
    schema_dir = os.path.join(cur_dir, "schemas")
    input_template_dir = os.path.join(cur_dir, "input_templates")

    using_model_info = ModelInfo(model)

    character_session = CharacterEvaluatorSession(using_model_info, prompt_dir=prompt_dir, schema_dir=schema_dir, input_template_dir=input_template_dir)
    
    for section in sample_narrative:
        character_session.append_conversation(section)
        character_session.export_logs(os.path.join(cur_dir, "sample_character_log.json"))