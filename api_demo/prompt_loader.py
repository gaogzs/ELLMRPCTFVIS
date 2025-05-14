import os


class PromptLoader:
    def __init__(self, prompt_dir):
        self.cur_dir = os.path.dirname(os.path.realpath(__file__))
        self.prompt_dir = prompt_dir

    def load_sys_prompts(self, filename):
        sys_prompt_filename = f"sys_prompt_{filename}.txt"
        full_prompt_dir = os.path.join(self.cur_dir, self.prompt_dir, sys_prompt_filename)
        read_text = ""
        with open(full_prompt_dir, 'r', encoding="utf-8") as f:
            read_text = f.read()
        return read_text