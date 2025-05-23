import os


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