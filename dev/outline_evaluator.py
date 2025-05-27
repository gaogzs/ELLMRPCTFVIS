import os
import json

from config import print_warning_message, print_dev_message, ModelInfo, _ERROR_RETRIES
from utils.loaders import PromptLoader, SchemaLoader, InputTemplateLoader
from api_wrapper.sentence_similarity_lm import SentenceSimilarityWorker

SIMILARITY_MODEL = "all-MiniLM-L6-v2"
EVALUATOR_MODEL = "gemini-structured"

SIMILARITY_LOG_BASE = 0.95

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
            result += subsection.to_str(indent_base + indent_add, indent_add)
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
    def __init__(self, model_info: ModelInfo, prompt_dir: str, schema_dir: str, input_template_dir: str) -> None:
        self.model_info = model_info
        self.prompt_loader = PromptLoader(prompt_dir)
        self.schema_loader = SchemaLoader(schema_dir)
        self.input_template_loader = InputTemplateLoader(input_template_dir)

        self.chatbot = self.model_info.chatbot()
        self.outline = Outline()
        self.predictions = []
        self.logs = []

    def get_outline(self) -> Outline:
        return self.outline

    def append_conversation(self, lastest_conversation: str) -> None:
        new_chapter, new_section, predicted_sections = self.handle_outline_builder(lastest_conversation)
        similarity_results, prediction_options = self.handle_similarity_worker(new_section, predicted_sections)
        multichoice_result = self.handle_outline_multichoice_examinee(new_section, new_chapter, prediction_options)
        
        new_log = {
            "conversation": lastest_conversation,
            "new_chapter": new_chapter,
            "new_section": new_section,
            "similarity_results": similarity_results,
            "multichoice_result": multichoice_result
        }
        self.logs.append(new_log)
        
    def export_logs(self, file_path: str) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.logs, f, ensure_ascii=False, indent=4)