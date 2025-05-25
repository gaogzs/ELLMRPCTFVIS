import os
import json


class InputTemplateLoader:
    def __init__(self, input_template_dir):
        self.cur_dir = os.path.dirname(os.path.realpath(__file__))
        self.input_template_dir = input_template_dir

    def load(self, filename):
        sys_prompt_filename = f"{filename}.txt"
        full_input_template_dir = os.path.join(self.cur_dir, self.input_template_dir, sys_prompt_filename)
        read_text = ""
        with open(full_input_template_dir, 'r', encoding="utf-8") as f:
            read_text = f.read()
        return read_text
    
class PromptLoader:
    def __init__(self, prompt_dir):
        self.cur_dir = os.path.dirname(os.path.realpath(__file__))
        self.prompt_dir = prompt_dir

    def load_sys_prompts(self, filename, subtype="text"):
        sys_prompt_filename = f"sys_prompt_{filename}_{subtype}.txt"
        full_prompt_dir = os.path.join(self.cur_dir, self.prompt_dir, sys_prompt_filename)
        read_text = ""
        with open(full_prompt_dir, 'r', encoding="utf-8") as f:
            read_text = f.read()
        return read_text
    
class SchemaLoader:
    def __init__(self, schema_dir: str) -> None:
        self.cur_dir = os.path.dirname(os.path.realpath(__file__))
        self.schema_dir = schema_dir
    
    def load_output_schema(self, filename: str) -> dict:
        schema_filename = f"{filename}_output.json"
        full_schema_dir = os.path.join(self.cur_dir, self.schema_dir, schema_filename)
        with open(full_schema_dir, 'r', encoding="utf-8") as f:
            schema = json.load(f)
        return schema