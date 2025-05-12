import os
import json
from openai import OpenAI
import re
import random
from z3 import *

from chatbot import ChatBotDummy
from prompts_definition import *

instruction_templates = {
    "declaration_maker": """
**Story**
[story]
**Reference**
[Reference]
""",
    "semantic_definer": """
**Declarerations**
[declarations]
""",
    "formula_maker": """
**Story**
[story]
**Objects**
[objects]
**Relations**
[relations]
**Pre-defined properties**
[predefined_properties]
**Existing Timeline**
[existing_timelines]
""",
    "error_correction": """
Your provided SMT-LIB has returned some error while being passed to Z3 parser. Please check the syntax and fix it. The error message is:
[error_message]

Please respond with the fixed SMT-LIB code only (The part after **SAT definition**), in the same format as before. There should no natural language explanation, comments, or informal syntax.
"""
}

def is_in_openai_form(message: str) -> bool:
    
    if message.startswith("{") and message.endswith("}"):
        try:
            message_json = json.loads(message)
            if type(message_json) == list and "role" in message_json[0] and "content" in message_json[0]:
                return True
        except json.JSONDecodeError:
            return False
    return False

def openai_form_to_str(message: str) -> str:
    role_convert_table = {
        "user": "User",
        "assistant": "AI",
        "system": "System"
    }
    message_json = json.loads(message)
    message_str = ""
    for message in message_json:
        role = message["role"]
        if role in role_convert_table:
            role = role_convert_table[role]
            message_str += f"{role}: {message['content']}\n"
    return message_str

def divide_response_parts(response_txt: str) -> list:
    sections = re.split(r"-- \*\*.+\n", response_txt)
    # print([section.strip() for section in sections if section.strip()])
    return [section.strip() for section in sections if section.strip()]


def add_definition(smtlib_str, new_def):
    if new_def not in smtlib_str:
        smtlib_str = new_def + "\n" + smtlib_str
    return smtlib_str

# def fix_by_lines(smtlib_str):
#     if smtlib_str.startswith("; "):
#         return ""
#     return smtlib_str

# def close_brackets(smtlib_str):
#     open_count = smtlib_str.count('(')
#     close_count = smtlib_str.count(')')
#     difference = open_count - close_count
#     if difference > 0:
#         return smtlib_str + (')' * (difference))
#     return smtlib_str

class RPEvaluationSession():
    def __init__(self, client: OpenAI, model: str, history: list = None) -> None:
        self.rp_history = history if history is not None else ""
        self.client = client
        self.model = model
        self.formulas = []
        self.declarations = {}
        self.timeline = {}
        self.logs = []
        
        self.solver = Solver()
    
    def get_declarations_str(self) -> str:
        out_str = ""
        for name, meaning in self.declarations.items():
            out_str += f"{name}: {meaning}\n"
        return out_str
    
    def get_timeline_str(self) -> str:
        out_str = ""
        for name, meaning in self.timeline.items():
            out_str += f"{name}: {meaning}\n"
        return out_str
    
    def handle_declaration_maker(self, lastest_conversation: str) -> tuple[list, list]:
        
        sys_prompt = [{"role": "system", "content": sys_prompts["declaration_maker"]}]
        bot = ChatBotDummy(self.client, self.model, sys_prompt)
        
        message = instruction_templates["declaration_maker"].replace("[story]", lastest_conversation)
        declarations_str = self.get_declarations_str()
        message = message.replace("[Reference]", declarations_str)
        
        complete_response = bot.send_message(message, record=False, temperature=0.2)
        print("Declaration Maker Response:")
        print(complete_response)
        
        objects_text, relations_text, replenishment_text = divide_response_parts(complete_response)
        
        objects_text += "\n" + replenishment_text
        
        # Parse the object declarations
        obj_keys = []
        for declare_line in objects_text.split("\n"):
            if ":" in declare_line:
                obj_name, obj_meaning = declare_line.split(":", 1)
                obj_name = obj_name.strip()
                obj_meaning = obj_meaning.strip()
                if obj_name in self.declarations:
                    print(f"Warning: {obj_name} already exists in declarations.")
                self.declarations[obj_name] = obj_meaning
                obj_keys.append(obj_name)
        
        # Parse the relation declarations
        rel_keys = []
        for declare_line in relations_text.split("\n"):
            if ":" in declare_line:
                rel_name, rel_meaning = declare_line.split(":")[:2]
                rel_name = rel_name.strip()
                rel_meaning = rel_meaning.strip()
                if rel_name in self.declarations:
                    print(f"Warning: {rel_name} already exists in declarations.")
                self.declarations[rel_name] = rel_meaning
                rel_keys.append(rel_name)
        
        return obj_keys, rel_keys

    def handle_semantic_definer(self, lastest_conversation: str, obj_keys: list, rel_keys: list) -> tuple[list, list, str, str]:
        
        sys_prompt = [{"role": "system", "content": sys_prompts["semantic_definer"]}]
        bot = ChatBotDummy(self.client, self.model, sys_prompt)
        
        message = instruction_templates["semantic_definer"]
        current_declarations = ""
        for key in obj_keys + rel_keys:
            if key in self.declarations:
                current_declarations += f"{key}: {self.declarations[key]}\n"
            else:
                print(f"Warning: {key} not found in declarations.")
        message = message.replace("[declarations]", current_declarations)
        
        complete_response = bot.send_message(message, record=False, temperature=0.1)
        print("Semantic Definer Response:")
        print(complete_response)
        
        reasoning_text, definitions_text = divide_response_parts(complete_response)
        
        # Incase there are some re-defined time-sensitive relations, we need to add them to the declarations
        new_definition_text = ""
        for declare_line in definitions_text.split("\n"):
            if "time_exclusive" in declare_line:
                key, new_definition = declare_line.split("time_exclusive", 1)
                new_name, new_meaning = new_definition.split(":", 1)
                key = key.strip()
                new_name = new_name.strip()
                new_meaning = new_meaning.strip()
                if key in self.declarations:
                    self.declarations.pop(key)
                else:
                    print(f"Warning: {key} not found in declarations.")
                if key in rel_keys:
                    replace_index = rel_keys.index(key)
                    rel_keys[replace_index] = new_name
                else:
                    print(f"Warning: {key} not found in rel_keys.")
                self.declarations[new_name] = new_meaning
            else:
                new_definition_text += declare_line + "\n"
        
        return obj_keys, rel_keys, new_definition_text.strip()
    
    def handle_formula_maker(self, lastest_conversation: str, obj_keys: list, rel_keys: list, predefined_text: str) -> AstVector:
        
        sys_prompt = [{"role": "system", "content": sys_prompts["formula_maker"]}]
        bot = ChatBotDummy(self.client, self.model, sys_prompt)
        
        # Make up the prompt from data
        message = instruction_templates["formula_maker"].replace("[story]", lastest_conversation)
        objects_str = ""
        for key in obj_keys:
            if key in self.declarations:
                objects_str += f"{key}: {self.declarations[key]}\n"
            else:
                print(f"Warning: {key} not found in declarations.")

        relations_str = ""
        for key in rel_keys:
            if key in self.declarations:
                relations_str += f"{key}: {self.declarations[key]}\n"
            else:
                print(f"Warning: {key} not found in declarations.")
        
        timeline_str = self.get_timeline_str()
        
        message = message.replace("[objects]", objects_str)
        message = message.replace("[relations]", relations_str)
        message = message.replace("[predefined_properties]", predefined_text)
        message = message.replace("[existing_timelines]", timeline_str)
        
        
        complete_response = bot.send_message(message, record=True, temperature=0)
        print("Formula Maker Response:")
        print(complete_response)
        
        reasoning_text, plan_text, time_point_definitions_text, formula_text = divide_response_parts(complete_response)
        
        # Parse the time point definitions
        for time_point_line in time_point_definitions_text.split("\n"):
            if ":" in time_point_line:
                time_point_name, time_point_meaning = time_point_line.split(":", 1)
                time_point_name = time_point_name.strip()
                time_point_meaning = time_point_meaning.strip()
                if time_point_name in self.timeline:
                    print(f"Warning: {time_point_name} already exists in timeline.")
                self.timeline[time_point_name] = time_point_meaning

        current_formula = None
        parsed_success = False
        while not parsed_success:
            try:
                current_formula = parse_smt2_string(formula_text)
                parsed_success = True
            except Z3Exception  as e:
                print(f"\"formula_text\"\n Returns error when parsed as SMT-LIB: {e}")
                formula_text = bot.send_message(instruction_templates["error_correction"].replace("[error_message]", str(e)), record=True, temperature=0.1)
                print("Retrying with corrected SMT-LIB:")
                print(formula_text)
        
        return current_formula
        

    def append_conversation(self, lastest_conversation: str) -> None:
        
        if is_in_openai_form(lastest_conversation):
            lastest_conversation = openai_form_to_str(lastest_conversation)
        message = instruction_templates["formula_maker"].replace("[story]", lastest_conversation)
        
        if is_in_openai_form(lastest_conversation):
            lastest_conversation = openai_form_to_str(lastest_conversation)
        message = instruction_templates["formula_maker"].replace("[story]", lastest_conversation)
        
        self.rp_history += lastest_conversation + "\n"
        obj_keys, rel_keys = self.handle_declaration_maker(lastest_conversation)
        obj_keys, rel_keys, new_definition_text = self.handle_semantic_definer(lastest_conversation, obj_keys, rel_keys)
        current_formula = self.handle_formula_maker(lastest_conversation, obj_keys, rel_keys, new_definition_text)
        
        result = None
        if self.formulas:
            last_formula = self.formulas[-1]
            
            self.solver.reset()
            satisfiable = And(list(last_formula) + list(current_formula))
            self.solver.add(satisfiable)
            try:
                result = str(self.solver.check())
            except OSError as e:
                print(satisfiable)
                result = str(self.solver.check())
            print(self.solver.assertions())
            print(result)
            
        self.formulas.append(current_formula)
        
        pretty_formula = current_formula.sexpr()
        
        current_declarations = ""
        for key in obj_keys + rel_keys:
            if key in self.declarations:
                current_declarations += f"{key}: {self.declarations[key]}\n"
            else:
                print(f"Warning: {key} not found in declarations.")
        
        new_log = {
            "conversation": lastest_conversation,
            "new_declarations": current_declarations,
            "pseudo_predefinitions": new_definition_text,
            "formula": pretty_formula,
            "result": result,
        }
        self.logs.append(new_log)
        
    def finalise_log(self) -> None:
        # Add the global data to the log
        
        new_log = {
            "full_conversation": self.rp_history,
            "full_declarations": self.get_declarations_str(),
            "full_timeline": self.get_timeline_str(),
        }
        
        self.logs.append(new_log)
        
    
    def export_logs(self, file_path: str) -> None:
        with open(file_path, "w") as f:
            json.dump(self.logs, f, indent=2)

cur_dir = os.path.dirname(os.path.realpath(__file__))

key_dir = os.path.join(cur_dir, "deepseek_api_key")
with open(key_dir, "r") as f:
    api_key = f.read().strip()
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

if __name__ == "__main__":
    # Example usage
    model = "deepseek-chat"
    
    session = RPEvaluationSession(client, model)
    
    sample_conversation = []
    with open(os.path.join(cur_dir, "sample_rp_false.json"), "r") as f:
        sample_conversations = json.load(f)
        sample_conversation = sample_conversations[0]
        
    for section in sample_conversation:
        session.append_conversation(section)
        session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))
        
    session.finalise_log()
    session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))