import os
import json
from openai import OpenAI
import re
import random
from z3 import *
import z3.z3util

from chatbot import ChatBotDummy
from str_to_z3_parser import Z3Builder, parse_z3
from prompt_loader import PromptLoader

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
**Past Declarations**
{past_declarations}
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

def get_relation_params(relation_str: str) -> list:
    match = re.search(r'\(([^()]*)\)', relation_str)
    if match:
        params = match.group(1).split(",")
        params = [param.strip() for param in params]
        return params
    else:
        return []

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
        self.objects = {}
        self.relations = {}
        self.timeline = {}
        self.logs = []
        self.z3_builder = Z3Builder(self.get_z3_function)
        
        self.prompt_loader = PromptLoader("prompts/")
        
    
    def get_all_declarations_str(self) -> str:
        out_str = ""
        for name, meaning in self.objects.items():
            out_str += f"{name}: {meaning}\n"
        for name, info in self.relations.items():
            out_str += f"{name}({", ".join(info["params"])}): {info["meaning"]}\n"
        return out_str
    
    def get_keyed_declarations_str(self, obj_keys: list, rel_keys: list) -> str:
        obj_str = ""
        for key in obj_keys:
            if key in self.objects:
                obj_str += f"{key}: {self.objects[key]}\n"
            else:
                print(f"Warning: {key} not found in declarations.")
        rel_str = ""
        for key in rel_keys:
            if key in self.relations:
                info = self.relations[key]
                rel_str += f"{key}({", ".join(info["params"])}): {info["meaning"]}\n"
            else:
                print(f"Warning: {key} not found in declarations.")
        return obj_str, rel_str
    
    def get_timeline_str(self) -> str:
        out_str = ""
        for name, meaning in self.timeline.items():
            out_str += f"{name}: {meaning}\n"
        return out_str
    
    def get_z3_function(self, name: str) -> Function:
        if name in self.relations:
            return self.relations[name]["function"]
        else:
            raise ValueError(f"Relation {name} not found in declarations.")
    
    def parse_internal_formula(self, definitions_text: str) -> list:
        formulas = []
        new_definition_text = ""
        for definition_line in definitions_text.splitlines():
            if "[exclusive_arg]" in definition_line:
                rel_just_name = definition_line.split("(")[0]
                edited_params = get_relation_params(definition_line)
                original_params = self.relations[rel_just_name]["params"]
                rel_z3_func = self.relations[rel_just_name]["function"]
                
                scope_params = []
                ref_l = []
                ref_r = []
                constrain_pairs = []
                for param_l, param_r in zip(original_params, edited_params):
                    if param_r == "[exclusive_arg]" or param_r == "[free_arg]":
                        replace1 = param_l + "1"
                        replace2 = param_l + "2"
                        scope_params.append(replace1)
                        ref_l.append(replace1)
                        scope_params.append(replace2)
                        ref_r.append(replace2)
                        if param_r == "[exclusive_arg]":
                            constrain_pairs.append(Int(replace1) == Int(replace2))
                    else:
                        scope_params.append(param_l)
                        ref_l.append(param_l)
                        ref_r.append(param_l)
                lhs_func = rel_z3_func(*[Int(param) for param in ref_l])
                rhs_func = rel_z3_func(*[Int(param) for param in ref_r])
                constraint_expr = constrain_pairs[0] if len(constrain_pairs) == 1 else And(*constrain_pairs)
                explicit_formula = ForAll([Int(param) for param in scope_params], Implies(And(lhs_func, rhs_func), constraint_expr))
                formulas.append(explicit_formula)
            else:
                new_definition_text += definition_line + "\n"
        return formulas, new_definition_text
    
    def handle_timeline_maker(self, lastest_conversation: str) -> str:
        
        sys_prompt = [{"role": "system", "content": self.prompt_loader.load_sys_prompts("timeline_maker")}]
        if self.rp_history:
            sys_prompt.append({"role": "user", "content": "\n".join(self.rp_history)})
            sys_prompt.append({"role": "assistant", "content": "-- **Reasoning**\n[Hidden]\n-- **Timeline Definitions**\n" + self.get_timeline_str()})
        bot = ChatBotDummy(self.client, self.model, sys_prompt)
        
        message = instruction_templates["timeline_maker"].format(story=lastest_conversation)
        
        complete_response = bot.send_message(message, record=False, temperature=0.2)
        print("Timeline Maker Response:")
        print(complete_response)
        
        reasoning_text, timeline_text = divide_response_parts(complete_response)
        
        # Parse the timeline
        for definition_line in timeline_text.splitlines():
            if ":" in definition_line:
                time_point_name, time_point_meaning = definition_line.split(":", 1)
                time_point_name = time_point_name.strip()
                time_point_meaning = time_point_meaning.strip()
                if time_point_name in self.timeline:
                    print(f"Warning: {time_point_name} already exists in timeline.")
                self.timeline[time_point_name] = time_point_meaning
        
        return timeline_text
    
    def handle_declaration_maker(self, lastest_conversation: str) -> tuple[list, list]:
        
        sys_prompt = [{"role": "system", "content": self.prompt_loader.load_sys_prompts("declaration_maker")}]
        bot = ChatBotDummy(self.client, self.model, sys_prompt)
        
        declarations_str = self.get_all_declarations_str()
        message = instruction_templates["declaration_maker"].format(story=lastest_conversation, reference=declarations_str)
        
        complete_response = bot.send_message(message, record=False, temperature=0.2)
        print("Declaration Maker Response:")
        print(complete_response)
        
        objects_text, relations_text, replenishment_text = divide_response_parts(complete_response)
        
        objects_text += "\n" + replenishment_text
        
        # Parse the object declarations
        obj_keys = []
        for definition_line in objects_text.splitlines():
            if ":" in definition_line:
                obj_name, obj_meaning = definition_line.split(":", 1)
                obj_name = obj_name.strip()
                obj_meaning = obj_meaning.strip()
                if obj_name in self.objects:
                    print(f"Warning: {obj_name} already exists in declarations.")
                self.objects[obj_name] = obj_meaning
                obj_keys.append(obj_name)
        
        # Parse the relation declarations
        rel_keys = []
        for definition_line in relations_text.splitlines():
            if ":" in definition_line:
                rel_name, rel_meaning = definition_line.split(":")[:2]
                rel_name = rel_name.strip()
                rel_meaning = rel_meaning.strip()
                rel_just_name = rel_name.split("(")[0]
                rel_params = get_relation_params(rel_name)
                rel_z3_func = Function(rel_just_name, *[IntSort() for param in rel_params], BoolSort())
                if rel_just_name in self.relations:
                    print(f"Warning: {rel_just_name} already exists in declarations.")
                self.relations[rel_just_name] = {"params": rel_params, "meaning": rel_meaning, "function": rel_z3_func}
                
                
                rel_keys.append(rel_just_name)
        
        return obj_keys, rel_keys, declarations_str

    def handle_semantic_definer(self, lastest_conversation: str, obj_keys: list, rel_keys: list, old_declarations: str) -> tuple[list, list, str, str]:
        
        sys_prompt = [{"role": "system", "content": self.prompt_loader.load_sys_prompts("semantic_definer")}]
        bot = ChatBotDummy(self.client, self.model, sys_prompt)
        
        obj_str, rel_str = self.get_keyed_declarations_str(obj_keys, rel_keys)
        current_declarations = obj_str + "\n" + rel_str
                
        message = instruction_templates["semantic_definer"].format(declarations=current_declarations, past_declarations=old_declarations)
        
        complete_response = bot.send_message(message, record=False, temperature=0.1)
        print("Semantic Definer Response:")
        print(complete_response)
        
        reasoning_text, definitions_text = divide_response_parts(complete_response)
        
        # Incase there are some re-defined time-sensitive relations, we need to add them to the declarations
        explicit_formulas, new_definition_text = self.parse_internal_formula(definitions_text)
        
        return obj_keys, rel_keys, new_definition_text, explicit_formulas
    
    def handle_formula_maker(self, lastest_conversation: str, obj_keys: list, rel_keys: list, predefined_text: str) -> AstVector:
        
        sys_prompt = [{"role": "system", "content": self.prompt_loader.load_sys_prompts("formula_maker")}]
        bot = ChatBotDummy(self.client, self.model, sys_prompt)
        
        # Make up the prompt from data
        obj_str, rel_str = self.get_keyed_declarations_str(obj_keys, rel_keys)
        
        timeline_str = self.get_timeline_str()
        
        message = instruction_templates["formula_maker"].format(story=lastest_conversation, objects=obj_str, relations=rel_str, predefined_properties=predefined_text, existing_timelines=timeline_str)
        
        
        complete_response = bot.send_message(message, record=True, temperature=0)
        print("Formula Maker Response:")
        print(complete_response)
        
        reasoning_text, plan_text, formula_text = divide_response_parts(complete_response)

        current_formula = []
        if formula_text != "None":
            for formula in formula_text.splitlines():
                parsed_formula = parse_z3(self.z3_builder, formula)
                current_formula.append(parsed_formula)
        
        return current_formula
        

    def append_conversation(self, lastest_conversation: str) -> None:
        
        self.handle_timeline_maker(lastest_conversation)
        obj_keys, rel_keys, old_declarations = self.handle_declaration_maker(lastest_conversation)
        obj_keys, rel_keys, definition_text, semantic_defined_formulas = self.handle_semantic_definer(lastest_conversation, obj_keys, rel_keys, old_declarations)
        current_formula = self.handle_formula_maker(lastest_conversation, obj_keys, rel_keys, definition_text)
        self.rp_history.append(lastest_conversation)
        
        complete_current_formula = semantic_defined_formulas + current_formula
        combined_past_formula = sum(self.formulas, [])
        combined_past_formula += semantic_defined_formulas
        
        result = self.solve_combined_formulas(combined_past_formula)
            
        self.formulas.append(complete_current_formula)
        
        pretty_formula = "\n".join([str(formula) for formula in complete_current_formula])
        
        obj_str, rel_str = self.get_keyed_declarations_str(obj_keys, rel_keys)
        current_declarations = obj_str + "\n" + rel_str
        
        new_log = {
            "conversation": lastest_conversation,
            "new_declarations": current_declarations,
            "pseudo_predefinitions": definition_text,
            "formula": pretty_formula,
            "result": result,
        }
        self.logs.append(new_log)
    
    def solve_combined_formulas(self, formulas: list) -> None:
        # Add the formulas to the solver
        var_list = set()
        solver = Solver()
        for i, formula in enumerate(formulas):
            solver.assert_and_track(formula, str(formula) + str(i))
            var_list.update(z3util.get_vars(formula))
        
        solver.add(Distinct(*var_list))
        
        # Check if the formulas are satisfiable
        result = solver.check()
        
        print(solver.assertions())
        print("Solver result:", result)
        
        if result == sat:
            return 0
        elif result == unsat:
            return len(solver.unsat_core())
        else:
            return -1
    
    def export_logs(self, file_path: str) -> None:
        # Add the global data to the log
        new_log = {
            "full_conversation": "\n".join(self.rp_history),
            "full_formulas": "\n".join([str(formula) for formula in self.formulas]),
            "full_declarations": self.get_all_declarations_str(),
            "full_timeline": self.get_timeline_str(),
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.logs + [new_log], f, indent=2)

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
        
    session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))