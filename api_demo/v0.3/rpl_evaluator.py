import os
import json
from openai import OpenAI
import re
import random
from z3 import *

from chatbot import ChatBotSimple
from prompts_definition import *

instruction_templates = {
    "timeline_maker": """
**Story**
{story}
""",
    "declaration_maker": """
**Story**
{story}
**Reference**
{reference}
""",
    "semantic_definer": """
**Declarerations**
{declarations}
""",
    "formula_maker": """
**Story**
{story}
**Objects**
{objects}
**Relations**
{relations}
**Pre-defined properties**
{predefined_properties}
**Existing Timeline**
{existing_timelines}
""",
    "error_correction": """
Your provided SMT-LIB has returned some error while being passed to Z3 parser. Please check the syntax and fix it. The error message is:
{error_message}

Please respond with the fixed SMT-LIB code only (The part after **SAT definition**), in the same format as before. There should no natural language explanation, comments, or informal syntax. Be sure that all the brackets are closed and all used constants are declared.
"""
}


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
        self.rp_history = history if history is not None else []
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
    
    def handle_timeline_maker(self, lastest_conversation: str) -> str:
        
        sys_prompt = [{"role": "system", "content": sys_prompts["timeline_maker"]}]
        if self.rp_history:
            sys_prompt.append({"role": "user", "content": "\n".join(self.rp_history)})
            sys_prompt.append({"role": "assistant", "content": "-- **Reasoning**\n[Hidden]\n-- **Timeline Definitions**\n" + self.get_timeline_str()})
        bot = ChatBotSimple(self.client, self.model, sys_prompt)
        
        message = instruction_templates["timeline_maker"].format(story=lastest_conversation)
        
        complete_response = bot.send_message(message, record=False, temperature=0.2)
        print("Timeline Maker Response:")
        print(complete_response)
        
        reasoning_text, timeline_text = divide_response_parts(complete_response)
        
        # Parse the timeline
        for declare_line in timeline_text.split("\n"):
            if ":" in declare_line:
                time_point_name, time_point_meaning = declare_line.split(":", 1)
                time_point_name = time_point_name.strip()
                time_point_meaning = time_point_meaning.strip()
                if time_point_name in self.timeline:
                    print(f"Warning: {time_point_name} already exists in timeline.")
                self.timeline[time_point_name] = time_point_meaning
        
        return timeline_text
    
    def handle_declaration_maker(self, lastest_conversation: str) -> tuple[list, list]:
        
        sys_prompt = [{"role": "system", "content": sys_prompts["declaration_maker"]}]
        bot = ChatBotSimple(self.client, self.model, sys_prompt)
        
        declarations_str = self.get_declarations_str()
        message = instruction_templates["declaration_maker"].format(story=lastest_conversation, reference=declarations_str)
        
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
        bot = ChatBotSimple(self.client, self.model, sys_prompt)
        
        current_declarations = ""
        for key in obj_keys + rel_keys:
            if key in self.declarations:
                current_declarations += f"{key}: {self.declarations[key]}\n"
            else:
                print(f"Warning: {key} not found in declarations.")
        message = instruction_templates["semantic_definer"].format(declarations=current_declarations)
        
        complete_response = bot.send_message(message, record=False, temperature=0.1)
        print("Semantic Definer Response:")
        print(complete_response)
        
        reasoning_text, definitions_text = divide_response_parts(complete_response)
        
        # Incase there are some re-defined time-sensitive relations, we need to add them to the declarations
        # new_definition_text = ""
        # for declare_line in definitions_text.split("\n"):
        #     if "time_exclusive" in declare_line:
        #         key, new_definition = declare_line.split("time_exclusive", 1)
        #         new_name, new_meaning = new_definition.split(":", 1)
        #         key = key.strip()
        #         new_name = new_name.strip()
        #         new_meaning = new_meaning.strip()
        #         if key in self.declarations:
        #             self.declarations.pop(key)
        #         else:
        #             print(f"Warning: {key} not found in declarations.")
        #         if key in rel_keys:
        #             replace_index = rel_keys.index(key)
        #             rel_keys[replace_index] = new_name
        #         else:
        #             print(f"Warning: {key} not found in rel_keys.")
        #         self.declarations[new_name] = new_meaning
        #     else:
        #         new_definition_text += declare_line + "\n"
        
        return obj_keys, rel_keys, definitions_text.strip()
    
    def handle_formula_maker(self, lastest_conversation: str, obj_keys: list, rel_keys: list, predefined_text: str) -> AstVector:
        
        sys_prompt = [{"role": "system", "content": sys_prompts["formula_maker"]}]
        bot = ChatBotSimple(self.client, self.model, sys_prompt)
        
        # Make up the prompt from data
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
        
        message = instruction_templates["formula_maker"].format(story=lastest_conversation, objects=objects_str, relations=relations_str, predefined_properties=predefined_text, existing_timelines=timeline_str)
        
        
        complete_response = bot.send_message(message, record=True, temperature=0)
        print("Formula Maker Response:")
        print(complete_response)
        
        reasoning_text, plan_text, formula_text = divide_response_parts(complete_response)

        current_formula = None
        parsed_success = False
        while not parsed_success:
            try:
                current_formula = parse_smt2_string(formula_text)
                parsed_success = True
            except Z3Exception  as e:
                print(f"Returns error when parsed as SMT-LIB: {e}")
                formula_text = bot.send_message(instruction_templates["error_correction"].format(error_message=str(e)), record=True, temperature=0.1)
                print("Retrying with corrected SMT-LIB:")
                print(formula_text)
        
        return current_formula
        

    def append_conversation(self, lastest_conversation: str) -> None:
        
        self.handle_timeline_maker(lastest_conversation)
        obj_keys, rel_keys = self.handle_declaration_maker(lastest_conversation)
        obj_keys, rel_keys, new_definition_text = self.handle_semantic_definer(lastest_conversation, obj_keys, rel_keys)
        current_formula = self.handle_formula_maker(lastest_conversation, obj_keys, rel_keys, new_definition_text)
        self.rp_history.append(lastest_conversation)
        
        result = None
        if self.formulas:
            all_formulas = []
            for formula in self.formulas:
                all_formulas += list(formula)
            all_formulas += list(current_formula)
            
            self.solver = Solver()
            for i, formula in enumerate(all_formulas):
                self.solver.assert_and_track(formula, formula.sexpr() + str(i))
            solved_success = False
            countdown = 10
            while not solved_success:
                try:
                    result = str(self.solver.check())
                    solved_success = True
                except OSError as e:
                    print(f"Returns error when solving: {e}")
                    with open("smt2_error.smt2", "w") as f:
                        f.write(self.solver.to_smt2())
                    self.solver = Solver()
                    for i, formula in enumerate(all_formulas):
                        self.solver.assert_and_track(formula, formula.sexpr() + str(i))
                    countdown -= 1
                    if countdown <= 0:
                        print("Error: Timeout when solving.")
                        exit(1)
            if result == "unsat":
                result += str(self.solver.unsat_core())
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
        with open(file_path, "w", encoding="utf-8") as f:
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
    with open(os.path.join(cur_dir, "sample_rp.json"), "r", encoding="utf-8") as f:
        sample_conversations = json.load(f)
        sample_conversation = sample_conversations[0]
        
    for section in sample_conversation:
        session.append_conversation(section)
        session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))
        
    session.finalise_log()
    session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))