import os
import json
from openai import OpenAI
import re
import random
from z3 import *
import z3.z3util
import lark
from collections import defaultdict

from chatbot import ChatBot, ChatBotDeepSeekSimple
from str_to_z3_parser import Z3Builder, parse_z3, FOLParsingError
from prompt_loader import PromptLoader
from config import print_warning_message, get_model_info, ModelInfo, _ERROR_RETRIES


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
**Existing Timeline**
{existing_timelines}
**Existing Scopes**
{existing_scopes}
""",
    "semantic_error_correction": """
Your provided formulas has returned some error while being parsed as FOL formula. Please check the syntax and fix it. The error message is:
{error_message}

Please respond with the corrected complete formulas only (No header, no reasoning and anything other than the formula definitions), in the same format as before. There should no natural language explanation, comments, or informal syntax. Be sure that all the brackets are closed and all used constants are declared. There should not be any beginning and ending "```" or other extra notions.
""",
    "formula_maker_error_correction": """
Your provided formulas has returned some error while being parsed as FOL formula. Please check the syntax and fix it. The error message is:
{error_message}

Please respond with the corrected complete formulas only (No header, no reasoning and anything other than the formula definitions), in the same format as before. There should no natural language explanation, comments, or informal syntax. Be sure that all the brackets are closed and all used constants are declared. There should not be any beginning and ending "```" or other extra notions.
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

class RPEvaluationSession():
    def __init__(self, model_info: ModelInfo, history: list = None) -> None:
        self.rp_history = history if history is not None else []
        self.model_info = model_info
        self.chatbot = self.model_info.chatbot()
        self.formulas = []
        self.objects = {}
        self.relations = {}
        self.timeline = {}
        self.scopes = {}
        self.logs = []
        self.z3_builder = Z3Builder(self.get_z3_function)
        
        self.prompt_loader = PromptLoader("prompts/")
        
    def relation_to_str(self, name: str, info: dict) -> str:
        params_str = ", ".join(info["params"])
        return f"{name}({params_str}): {info['meaning']}"
    
    def get_all_declarations_str(self) -> str:
        out_str = ""
        for name, meaning in self.objects.items():
            out_str += f"{name}: {meaning}\n"
        for name, info in self.relations.items():
            out_str += self.relation_to_str(name, info) + "\n"
        return out_str
    
    def get_keyed_declarations_str(self, obj_keys: list, rel_keys: list) -> str:
        obj_str = ""
        for key in obj_keys:
            if key in self.objects:
                obj_str += f"{key}: {self.objects[key]}\n"
            else:
                print_warning_message(f"Warning: {key} not found in declarations.")
        rel_str = ""
        for key in rel_keys:
            if key in self.relations:
                info = self.relations[key]
                rel_str += self.relation_to_str(key, info) + "\n"
            else:
                print_warning_message(f"Warning: {key} not found in declarations.")
        return obj_str, rel_str
    
    def get_timeline_str(self) -> str:
        out_str = ""
        for name, meaning in self.timeline.items():
            out_str += f"{name}: {meaning}\n"
        return out_str
    
    def get_scopes_str(self) -> str:
        out_str = ""
        for name, meaning in self.scopes.items():
            out_str += f"{name}: {meaning}\n"
        return out_str
    
    def scoped_formula_to_str(self, formula: dict) -> str:
        out_str = ""
        for scope, formulas in formula.items():
            out_str += f"Scope:\n"
            for f in formulas:
                out_str += str(f) + "\n"
        return out_str
    
    def get_z3_function(self, name: str) -> Function:
        if name in self.relations:
            return self.relations[name]["function"]
        else:
            return None
    
    def handle_timeline_maker(self, lastest_conversation: str) -> str:
        
        sys_prompt = self.prompt_loader.load_sys_prompts("timeline_maker")
        bot = self.chatbot(self.model_info.model(), sys_prompt)
        if self.rp_history:
            bot.add_fake_user_message("\n".join(self.rp_history))
            bot.add_fake_model_message("-- **Reasoning**\n[Hidden]\n-- **Timeline Definitions**\n" + self.get_timeline_str())
        
        message = instruction_templates["timeline_maker"].format(story=lastest_conversation)
        
        complete_response = bot.send_message(message, record=True, temperature=0.2)
        print("Timeline Maker Response:")
        print(complete_response)
        
        timeline_backup = self.timeline.copy()
        processed_success = False
        tries_count = _ERROR_RETRIES
        while not processed_success:
            try:
                reasoning_text, timeline_text = divide_response_parts(complete_response)
                processed_success = True
                # Parse the timeline
                new_timeline = self.parse_timeline_declarations(timeline_text)
                self.timeline.update(new_timeline)
            except Exception as e:
                tries_count -= 1
                if tries_count <= 0:
                    print("Error: Too many failing responses.")
                    exit(1)
                    
                self.timeline = timeline_backup.copy()
                print("Error in response division:", e)
                bot.reset_history()
                complete_response = bot.send_message(message, record=True, temperature=0.2)
                print("Retry with:\n")
                print(complete_response)
        
        
        return timeline_text
    
    def handle_declaration_maker(self, lastest_conversation: str) -> tuple[list, list]:
        
        sys_prompt = self.prompt_loader.load_sys_prompts("declaration_maker")
        bot = self.chatbot(self.model_info.model(), sys_prompt)
        
        declarations_str = self.get_all_declarations_str()
        message = instruction_templates["declaration_maker"].format(story=lastest_conversation, reference=declarations_str)
        
        complete_response = bot.send_message(message, record=True, temperature=0.2)
        print("Declaration Maker Response:")
        print(complete_response)
        
        objects_backup = self.objects.copy()
        relations_backup = self.relations.copy()
        processed_success = False
        tries_count = _ERROR_RETRIES
        while not processed_success:
            try:
                objects_text, relations_text, replenishment_text = divide_response_parts(complete_response)
                
                # Parse the object declarations
                new_objects = self.parse_object_declarations(objects_text)
                obj_keys = new_objects.keys()
                
                # Parse the relation declarations
                new_relations = self.parse_relation_declarations(relations_text)
                rel_keys = new_relations.keys()
                
                self.objects.update(new_objects)
                self.relations.update(new_relations)
                        
                processed_success = True
                        
            except Exception as e:
                tries_count -= 1
                if tries_count <= 0:
                    print("Error: Too many failing responses.")
                    exit(1)
                    
                self.objects = objects_backup.copy()
                self.relations = relations_backup.copy()
                
                print("Error in response division:", e)
                bot.reset_history()
                complete_response = bot.send_message(message, record=True, temperature=0.2)
                print("Retry with:\n")
                print(complete_response)
        
        objects_text += "\n" + replenishment_text
        
        return obj_keys, rel_keys

    def handle_semantic_definer(self, lastest_conversation: str, obj_keys: list, rel_keys: list) -> tuple[list, list, list, str]:
        
        sys_prompt = self.prompt_loader.load_sys_prompts("semantic_definer")
        bot = self.chatbot(self.model_info.model(), sys_prompt)
        
        obj_str, rel_str = self.get_keyed_declarations_str(obj_keys, rel_keys)
        current_declarations = obj_str + "\n" + rel_str
        
        old_declarations = ""
        for name, meaning in self.objects.items():
            if name not in obj_keys:
                old_declarations += f"{name}: {meaning}\n"
        for name, info in self.relations.items():
            if name not in rel_keys:
                old_declarations += self.relation_to_str(name, info) + "\n"
                
        message = instruction_templates["semantic_definer"].format(declarations=current_declarations, past_declarations=old_declarations)
        
        complete_response = bot.send_message(message, record=True, temperature=0)
        print("Semantic Definer Response:")
        print(complete_response)
        
        processed_success = False
        tries_count = _ERROR_RETRIES
        while not processed_success:
            try:
                reasoning_text, definitions_text = divide_response_parts(complete_response)
                processed_success = True
            except Exception as e:
                tries_count -= 1
                if tries_count <= 0:
                    print("Error: Too many failing responses.")
                    exit(1)
                    
                print("Error in response division:", e)
                bot.reset_history()
                complete_response = bot.send_message(message, record=True, temperature=0.2)
                print("Retry with:\n")
                print(complete_response)
        
        explicit_formulas = []
        if definitions_text != "None":
            parsed_success = False
            tries_count = _ERROR_RETRIES
            while not parsed_success:
                try:
                    explicit_formulas = self.parse_internal_definitions(definitions_text)
                    parsed_success = True
                except FOLParsingError as e:
                    tries_count -= 1
                    if tries_count <= 0:
                        print("Error: Too many failing responses.")
                        exit(1)
                        
                    error_message = instruction_templates["semantic_error_correction"].format(error_message=str(e))
                    print("Error in formula parsing:", e)
                    definitions_text = bot.send_message(error_message, record=True, temperature=0.1)
                    print("Retry with:\n")
                    print(definitions_text)
            
        
        return obj_keys, rel_keys, explicit_formulas, definitions_text
    
    def handle_formula_maker(self, lastest_conversation: str, obj_keys: list, rel_keys: list) -> dict:
        
        sys_prompt = self.prompt_loader.load_sys_prompts("formula_maker")
        bot = self.chatbot(self.model_info.model(), sys_prompt)
        
        # Make up the prompt from data
        obj_str, rel_str = self.get_keyed_declarations_str(obj_keys, rel_keys)
        
        timeline_str = self.get_timeline_str()
        scopes_str = self.get_scopes_str()
        
        message = instruction_templates["formula_maker"].format(story=lastest_conversation, objects=obj_str, relations=rel_str, existing_timelines=timeline_str, existing_scopes=scopes_str)
        
        
        complete_response = bot.send_message(message, record=True, temperature=0)
        print("Formula Maker Response:")
        print(complete_response)
        
        scopes_backup = self.scopes.copy()
        processed_success = False
        tries_count = _ERROR_RETRIES
        while not processed_success:
            try:
                reasoning_text, plan_text, scopes_text, formula_text  = divide_response_parts(complete_response)
                for scope_line in scopes_text.splitlines():
                    if ":" in scope_line:
                        scope_name, scope_meaning = scope_line.split(":", 1)
                        scope_name = scope_name.strip()
                        scope_meaning = scope_meaning.strip()
                        if scope_name in self.scopes:
                            print_warning_message(f"Warning: {scope_name} already exists in scopes.")
                        self.scopes[scope_name] = scope_meaning
                processed_success = True
            except Exception as e:
                tries_count -= 1
                if tries_count <= 0:
                    print("Error: Too many failing responses.")
                    exit(1)
                    
                self.scopes = scopes_backup.copy()
                print("Error in response division:", e)
                bot.reset_history()
                complete_response = bot.send_message(message, record=True, temperature=0.2)
                print("Retry with:\n")
                print(complete_response)
        

        current_formula = []
        if formula_text != "None":
            parsed_success = False
            tries_count = _ERROR_RETRIES
            while not parsed_success:
                try:
                    current_formula = self.parse_formulas(formula_text)
                    parsed_success = True
                except FOLParsingError as e:
                    tries_count -= 1
                    if tries_count <= 0:
                        print("Error: Too many failing responses.")
                        exit(1)
                        
                    error_message = instruction_templates["formula_maker_error_correction"].format(error_message=str(e))
                    print("Error returned when parsing:", e)
                    formula_text = bot.send_message(error_message, record=True, temperature=0.1)
                    print("Retry with:\n")
                    print(formula_text)
        
        return current_formula
        

    def append_conversation(self, lastest_conversation: str) -> None:
        
        timeline_definitions = self.handle_timeline_maker(lastest_conversation)
        obj_keys, rel_keys = self.handle_declaration_maker(lastest_conversation)
        obj_keys, rel_keys, semantic_defined_formulas, definitions_text = self.handle_semantic_definer(lastest_conversation, obj_keys, rel_keys)
        current_formula = self.handle_formula_maker(lastest_conversation, obj_keys, rel_keys)
        self.rp_history.append(lastest_conversation)
        
        complete_current_formula = current_formula.copy()
        complete_current_formula["global"] = semantic_defined_formulas + complete_current_formula["global"]
        
        combined_past_formula = defaultdict(list)
        combined_past_formula["global"] = []
        for scope, formulas in complete_current_formula.items():
            for history_formula in self.formulas:
                if scope in history_formula:
                    combined_past_formula[scope] += history_formula[scope]
            combined_past_formula[scope] += formulas
        
        results, unsat_score = self.solve_combined_formulas(combined_past_formula)
            
        self.formulas.append(complete_current_formula)
        
        pretty_formula = self.scoped_formula_to_str(complete_current_formula)
        
        obj_str, rel_str = self.get_keyed_declarations_str(obj_keys, rel_keys)
        current_declarations = obj_str + "\n" + rel_str
        
        new_log = {
            "conversation": lastest_conversation,
            "new_declarations": current_declarations,
            "pseudo_predefinitions": definitions_text,
            "formula": pretty_formula,
            "result": unsat_score,
        }
        self.logs.append(new_log)
        
    def parse_timeline_declarations(self, timeline_text: str) -> dict:
        new_timeline = {}
        for definition_line in timeline_text.splitlines():
            if ":" in definition_line:
                time_point_name, time_point_meaning = definition_line.split(":", 1)
                time_point_name = time_point_name.strip()
                time_point_meaning = time_point_meaning.strip()
                if time_point_name in self.timeline:
                    print_warning_message(f"Warning: {time_point_name} already exists in timeline.")
                new_timeline[time_point_name] = time_point_meaning

        return new_timeline
    
    def parse_object_declarations(self, objects_text: str) -> dict:
        new_objects = {}
        for definition_line in objects_text.splitlines():
            if ":" in definition_line:
                obj_name, obj_meaning = definition_line.split(":", 1)
                obj_name = obj_name.strip()
                obj_meaning = obj_meaning.strip()
                if obj_name in self.objects:
                    print_warning_message(f"Warning: {obj_name} already exists in declarations.")
                new_objects[obj_name] = obj_meaning
        
        return new_objects

    def parse_relation_declarations(self, relations_text: str) -> dict:
        new_relations = {}
        for definition_line in relations_text.splitlines():
            if ":" in definition_line:
                rel_name, rel_def = definition_line.split(":", 1)
                try:
                    rel_meaning, rel_cases = rel_def.split("|", 1)
                except ValueError:
                    raise FOLParsingError(f"Invalid relation declaration: declared relation has no usage case. Please check the syntax: {definition_line}")
                
                rel_name = rel_name.strip()
                rel_meaning = rel_meaning.strip()
                rel_just_name = rel_name.split("(")[0]
                rel_params = get_relation_params(rel_name)
                rel_cases
                if rel_cases.count(",") % rel_name.count(",") != 0:
                    raise FOLParsingError(f"Invalid relation declaration: declared relation has ambiguous number of parameters. Please check the syntax: {definition_line}")
                
                rel_z3_func = Function(rel_just_name, *[IntSort() for param in rel_params], BoolSort())
                if rel_just_name in self.relations:
                    print_warning_message(f"Warning: {rel_just_name} already exists in declarations.")
                new_relations[rel_just_name] = {"params": rel_params, "meaning": rel_meaning, "function": rel_z3_func}
        
        return new_relations
    
    def parse_formulas(self, formulas_text: str) -> dict:
        formulas = defaultdict(list)
        formulas["global"] = []
        for formula_line in formulas_text.splitlines():
            parsing_formula = formula_line.strip()
            if  "```" in parsing_formula:
                continue
            if parsing_formula:
                scope = "global"
                if "|:" in parsing_formula:
                    try:
                        scope, parsing_formula = parsing_formula.split("|:")
                    except ValueError:
                        raise FOLParsingError(f"Invalid scope usage. Please check the syntax: {parsing_formula}")
                    scope = scope.strip()
                    parsing_formula = parsing_formula.strip()
                    if scope not in self.scopes:
                        raise FOLParsingError(f"Scope {scope} not found in scope table. Please remove any related usage of this scope for now.")
                parsed_formula = parse_z3(self.z3_builder, parsing_formula)
                formulas[scope].append(parsed_formula)
        return dict(formulas)
    
    def parse_exclusive_args(self, definition_line: str):
        rel_just_name = definition_line.split("(")[0]
        if rel_just_name not in self.relations:
            raise FOLParsingError(f"Relation {rel_just_name} not found in function table.")
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
        return explicit_formula
        
    def parse_internal_definitions(self, definitions_text: str) -> list:
        formulas = []
        for definition_line in definitions_text.splitlines():
            if  "```" in definition_line:
                continue
            if "[exclusive_arg]" in definition_line or "[free_arg]" in definition_line:
                explicit_formula = self.parse_exclusive_args(definition_line)
                formulas.append(explicit_formula)
            else:
                parsing_formula = definition_line.strip()
                parsed_formula = parse_z3(self.z3_builder, parsing_formula)
                formulas.append(parsed_formula)
        return formulas
    
    def solve_combined_formulas(self, combined_formulas: dict) -> tuple[list, int]:
        solver = Solver()
        # Get a list of all variables in the formulas
        var_list = set()
        for formulas in combined_formulas.values():
            for formula in formulas:
                var_list.update(z3util.get_vars(formula))
        if var_list:
            solver.add(Distinct(*var_list))
            
        # First, add the global formulas
        global_formulas = combined_formulas["global"]
        for i, formula in enumerate(global_formulas):
            solver.assert_and_track(formula, f"global_assertion_{i}")
            
        # Check the satisfiability of global formulas
        results = [str(solver.check())]
        unsat_score = len(solver.unsat_core())
        global_unsat_score = len(solver.unsat_core())
        
        # Check formulas by scope
        for scope, formulas in combined_formulas.items():
            if scope != "global":
                solver.push()
                for i, formula in enumerate(formulas):
                    solver.assert_and_track(formula, f"{scope}_assertion_{i}")
                scope_result = solver.check()
                results.append(str(scope_result))
                unsat_score += len(solver.unsat_core()) - global_unsat_score
                solver.pop()
        
        print(solver.assertions())
        print("Solver result:", results, unsat_score)
        
        return results, unsat_score
    
    def export_logs(self, file_path: str) -> None:
        # Add the global data to the log
        new_log = {
            "full_conversation": "\n".join(self.rp_history),
            "full_formulas": "\n".join([str(formula) for formula in self.formulas]),
            "full_declarations": self.get_all_declarations_str(),
            "full_timeline": self.get_timeline_str(),
            "full_scopes": self.get_scopes_str(),
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.logs + [new_log], f, indent=2)

cur_dir = os.path.dirname(os.path.realpath(__file__))


if __name__ == "__main__":
    # Example usage
    model_info = get_model_info()
    session = RPEvaluationSession(model_info)
    
    sample_conversation = []
    with open(os.path.join(cur_dir, "sample_rp.json"), "r", encoding="utf-8") as f:
        sample_conversations = json.load(f)
        sample_conversation = sample_conversations[-1]
        
    for section in sample_conversation:
        session.append_conversation(section)
        session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))
        
    session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))