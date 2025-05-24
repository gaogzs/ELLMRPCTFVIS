import os
import json

from config import print_warning_message, print_dev_message, ModelInfo, _ERROR_RETRIES
from utils.loaders import PromptLoader, SchemaLoader, InputTemplateLoader

SIMILARITY_MODEL = "all-MiniLM-L6-v2"
EVALUATOR_MODEL = "gemini-structured"

SIMILARITY_LOG_BASE = 0.95

class Section:
    def __init__(self, title: str, description: str):
        self.title = title
        self.description = description
        self.subsections = []

    def add_subsection(self, title: str, description: str):
        new_subsection = Section(title, description)
        self.subsections.append(new_subsection)
    
    def get_latest_subsection(self):
        if self.subsections:
            return self.subsections[-1]
        return None

class Outline:
    def __init__(self):
        self.chapters = []
    
    def add_chapter(self, title: str, description: str):
        new_chapter = Section(title, description)
        self.chapters.append(new_chapter)
    
    def add_section(self, title: str, description: str):
        self.chapters[-1].add_subsection(title, description)
    
    def get_latest_section(self):
        if self.chapters:
            return self.chapters[-1].get_latest_subsection()
        return None