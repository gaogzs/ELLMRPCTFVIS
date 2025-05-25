import os
import json
import re
from z3 import *
from collections import defaultdict

from parser.str_to_z3_parser import Z3Builder, parse_z3, FOLParsingError
from utils.loaders import PromptLoader, SchemaLoader, InputTemplateLoader
from utils.regex import divide_response_parts, get_relation_params
from utils.utils import *
from config import print_warning_message, print_dev_message, ModelInfo, _ERROR_RETRIES


# def fix_by_lines(smtlib_str):
#     if smtlib_str.startswith("; "):
#         return ""
#     return smtlib_str

class Relation:
    def __init__(self, name: str, params: list, meaning: str, function: Function) -> None:
        self.name = name
        self.params = params
        self.meaning = meaning
        self.function = function
    
    def __str__(self):
        params_str = ", ".join(self.params)
        return f"{self.name}({params_str}): {self.meaning}"

class FOLEvaluationSession():
    def __init__(self, model_info: ModelInfo, history: list = None, prompt_dir: str = "../prompts/", schema_dir: str = "../schemas/", input_template_dir: str = "../input_templates/") -> None:
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
        
        self.prompt_loader = PromptLoader(prompt_dir)
        self.schema_loader = SchemaLoader(schema_dir)
        self.input_template_loader = InputTemplateLoader(input_template_dir)
        
    def get_timeline_str(self) -> str:
        return dict_pretty_str(self.timeline)
    
    def get_all_declarations_str(self) -> str:
        out_str = "Objects:\n"
        for name, meaning in self.objects.items():
            out_str += f"{name}: {meaning}\n"
        out_str += "Relations:\n"
        for name, info in self.relations.items():
            out_str += str(info) + "\n"
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
                rel_str += str(info) + "\n"
            else:
                print_warning_message(f"Warning: {key} not found in declarations.")
        return obj_str, rel_str
    
    def get_scopes_str(self) -> str:
        return dict_pretty_str(self.scopes)
    
    def scoped_formula_to_str(self, formula: dict) -> str:
        out_str = ""
        for scope, formulas in formula.items():
            out_str += f"Scope: {scope}\n"
            for f in formulas:
                out_str += str(f) + "\n"
        return out_str
    
    def get_z3_function(self, name: str) -> Function:
        if name in self.relations:
            return self.relations[name].function
        else:
            return None
    
    def handle_declaration_builder(self, lastest_conversation: str) -> tuple[list, list]:
        
        
        declarations_str = self.get_all_declarations_str()
        message = self.input_template_loader.load("declaration_builder").format(story=lastest_conversation, reference=declarations_str)
        
        processed_success = False
        tries_count = _ERROR_RETRIES
        
        
        if self.model_info.output_format() == "json":
            sys_prompt = self.prompt_loader.load_sys_prompts("declaration_builder")
            bot = self.chatbot(self.model_info.model(), sys_prompt)
            output_schema = self.schema_loader.load_output_schema("declaration_builder")
            text_response, json_response = bot.get_structured_response(message, output_schema, record=True, temperature=0.2)
            print_dev_message("Declaration Maker Response:")
            print_dev_message(text_response)
            while not processed_success:
                try:
                    new_objects, new_relations = self.parse_obj_rel_declarations_json(json_response)
                    obj_keys = new_objects.keys()
                    rel_keys = new_relations.keys()
                    self.objects.update(new_objects)
                    self.relations.update(new_relations)
                    processed_success = True
                except Exception as e:
                    error_message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                    
                    print_dev_message("Error in response division:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        print_dev_message("Error: Too many failing responses.")
                        exit(1)
                        
                    text_response, json_response = bot.get_structured_response(error_message, output_schema, record=True, temperature=0.2)
                    print_dev_message("Retry with:\n")
                    print_dev_message(text_response)
        else:
            sys_prompt = self.prompt_loader.load_sys_prompts("declaration_builder")
            bot = self.chatbot(self.model_info.model(), sys_prompt)
            complete_response = bot.send_message(message, record=True, temperature=0.2)
            print_dev_message("Declaration Maker Response:")
            print_dev_message(complete_response)
            while not processed_success:
                try:
                    objects_text, relations_text, replenishment_text = divide_response_parts(complete_response)
                    
                    # Parse the object declarations
                    objects_text += "\n" + replenishment_text 
                    new_objects = self.parse_object_declarations(objects_text)
                    obj_keys = new_objects.keys()
                    
                    # Parse the relation declarations
                    new_relations = self.parse_relation_declarations(relations_text)
                    rel_keys = new_relations.keys()
                    
                    self.objects.update(new_objects)
                    self.relations.update(new_relations)
                            
                    processed_success = True
                            
                except Exception as e:
                    error_message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                    
                    print_dev_message("Error in response division:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        print_dev_message("Error: Too many failing responses.")
                        exit(1)
                        
                    complete_response = bot.send_message(error_message, record=True, temperature=0.2)
                    print_dev_message("Retry with:\n")
                    print_dev_message(complete_response)
        
        
        return obj_keys, rel_keys

    def handle_semantic_analyser(self, lastest_conversation: str, obj_keys: list, rel_keys: list) -> tuple[list, list, list, str]:
        
        
        obj_str, rel_str = self.get_keyed_declarations_str(obj_keys, rel_keys)
        current_declarations = "Objects:\n" + obj_str + "\n" + "Relaions:\n" + rel_str
        
        old_declarations = ""
        for name, meaning in self.objects.items():
            if name not in obj_keys:
                old_declarations += f"{name}: {meaning}\n"
        for name, info in self.relations.items():
            if name not in rel_keys:
                old_declarations += str(info) + "\n"
                
        message = self.input_template_loader.load("semantic_analyser").format(declarations=current_declarations, past_declarations=old_declarations)
        
        processed_success = False
        tries_count = _ERROR_RETRIES
        
        if self.model_info.output_format() == "json":
            sys_prompt = self.prompt_loader.load_sys_prompts("semantic_analyser")
            bot = self.chatbot(self.model_info.model(), sys_prompt)
            output_schema = self.schema_loader.load_output_schema("semantic_analyser")
            text_response, json_response = bot.get_structured_response(message, output_schema, record=True, temperature=0.2)
            print_dev_message("Semantic Definer Response:")
            print_dev_message(text_response)
            
            while not processed_success:
                try:
                    returning_formulas = self.parse_semantic_analyser_json(json_response)
                    pseudo_definitions = str(json_response["exclusiveness_definitions"] + json_response["formulas"])
                    processed_success = True
                except Exception as e:
                    error_message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                    print_dev_message("Error in response division:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        print_dev_message("Error: Too many failing responses.")
                        exit(1)
                        
                    text_response, json_response = bot.get_structured_response(error_message, output_schema, record=True, temperature=0.2)
                    print_dev_message("Retry with:\n")
                    print_dev_message(text_response)
        else:
            sys_prompt = self.prompt_loader.load_sys_prompts("semantic_analyser")
            bot = self.chatbot(self.model_info.model(), sys_prompt)
            complete_response = bot.send_message(message, record=True, temperature=0)
            print_dev_message("Semantic Definer Response:")
            print_dev_message(complete_response)
            
            while not processed_success:
                try:
                    reasoning_text, exclusive_definitions_text, formula_definitions_text = divide_response_parts(complete_response)
                    processed_success = True
                except Exception as e:
                    error_message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                    print_dev_message("Error in response division:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        print_dev_message("Error: Too many failing responses.")
                        exit(1)
                        
                    complete_response = bot.send_message(error_message, record=True, temperature=0.2)
                    print_dev_message("Retry with:\n")
                    print_dev_message(complete_response)
            
            explicit_formulas = []
            if exclusive_definitions_text != "None":
                parsed_success = False
                tries_count = _ERROR_RETRIES
                while not parsed_success:
                    try:
                        explicit_formulas = self.parse_exclusive_args(exclusive_definitions_text)
                        parsed_success = True
                    except FOLParsingError as e:
                        error_message = self.input_template_loader.load("exclusive_error_correction").format(error_message=str(e))
                        print_dev_message("Error in formula parsing:", e)
                        tries_count -= 1
                        if tries_count <= 0:
                            print_dev_message("Error: Too many failing responses.")
                            exit(1)
                            
                        exclusive_definitions_text = bot.send_message(error_message, record=True, temperature=0.1)
                        print_dev_message("Retry with:\n")
                        print_dev_message(exclusive_definitions_text)
            
            parsed_formulas = []
            if formula_definitions_text != "None":
                parsed_success = False
                tries_count = _ERROR_RETRIES
                while not parsed_success:
                    try:
                        parsed_formulas += self.parse_formulas(formula_definitions_text)
                        parsed_success = True
                    except FOLParsingError as e:
                        error_message = self.input_template_loader.load("formula_error_correction").format(error_message=str(e))
                        print_dev_message("Error in formula parsing:", e)
                        tries_count -= 1
                        if tries_count <= 0:
                            print_dev_message("Error: Too many failing responses.")
                            exit(1)
                            
                        formula_definitions_text = bot.send_message(error_message, record=True, temperature=0.1)
                        print_dev_message("Retry with:\n")
                        print_dev_message(formula_definitions_text)
            
            returning_formulas = explicit_formulas + parsed_formulas
            pseudo_definitions = exclusive_definitions_text + "\n" + formula_definitions_text
        
        return returning_formulas, pseudo_definitions
    
    def handle_formula_maker(self, lastest_conversation: str, obj_keys: list, rel_keys: list) -> dict:
        
        
        # Make up the prompt from data
        obj_str, rel_str = self.get_keyed_declarations_str(obj_keys, rel_keys)
        
        timeline_str = self.get_timeline_str()
        scopes_str = self.get_scopes_str()
        
        message = self.input_template_loader.load("formula_maker").format(story=lastest_conversation, objects=obj_str, relations=rel_str, existing_timelines=timeline_str, existing_scopes=scopes_str)
        
        scopes_backup = self.scopes.copy()
        processed_success = False
        tries_count = _ERROR_RETRIES
        
        if self.model_info.output_format() == "json":
            sys_prompt = self.prompt_loader.load_sys_prompts("formula_maker")
            bot = self.chatbot(self.model_info.model(), sys_prompt)
            output_schema = self.schema_loader.load_output_schema("formula_maker")
            text_response, json_response = bot.get_structured_response(message, output_schema, record=True, temperature=0)
            print_dev_message("Formula Maker Response:")
            print_dev_message(text_response)
            
            while not processed_success:
                try:
                    current_formula = self.parse_formula_maker_json(json_response)
                    processed_success = True
                except Exception as e:
                    error_message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                    self.scopes = scopes_backup.copy()
                    print_dev_message("Error in response division:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        print_dev_message("Error: Too many failing responses.")
                        exit(1)
                        
                    text_response, json_response = bot.get_structured_response(error_message, output_schema, record=True, temperature=0.2)
                    print_dev_message("Retry with:\n")
                    print_dev_message(text_response)
        else:
            sys_prompt = self.prompt_loader.load_sys_prompts("formula_maker")
            bot = self.chatbot(self.model_info.model(), sys_prompt)
            complete_response = bot.send_message(message, record=True, temperature=0)
            print_dev_message("Formula Maker Response:")
            print_dev_message(complete_response)
            
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
                    error_message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                    self.scopes = scopes_backup.copy()
                    print_dev_message("Error in response division:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        print_dev_message("Error: Too many failing responses.")
                        exit(1)
                        
                    complete_response = bot.send_message(error_message, record=True, temperature=0.2)
                    print_dev_message("Retry with:\n")
                    print_dev_message(complete_response)
            

            current_formula = []
            if formula_text != "None":
                parsed_success = False
                tries_count = _ERROR_RETRIES
                while not parsed_success:
                    try:
                        current_formula = self.parse_scoped_formulas(formula_text)
                        parsed_success = True
                    except FOLParsingError as e:
                        error_message = self.input_template_loader.load("formula_error_correction").format(error_message=str(e))
                        print_dev_message("Error returned when parsing:", e)
                        tries_count -= 1
                        if tries_count <= 0:
                            print_dev_message("Error: Too many failing responses.")
                            exit(1)
                            
                        formula_text = bot.send_message(error_message, record=True, temperature=0.1)
                        print_dev_message("Retry with:\n")
                        print_dev_message(formula_text)
        
        return current_formula
        

    def append_conversation(self, lastest_conversation: str, new_timeline: dict) -> None:
        
        self.timeline = new_timeline.copy()
        timeline_definitions = dict_pretty_str(self.timeline)
        obj_keys, rel_keys = self.handle_declaration_builder(lastest_conversation)
        semantic_defined_formulas, definitions_text = self.handle_semantic_analyser(lastest_conversation, obj_keys, rel_keys)
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
            "new_timeline": timeline_definitions,
            "new_declarations": current_declarations,
            "pseudo_predefinitions": definitions_text,
            "formula": pretty_formula,
            "result": unsat_score,
        }
        self.logs.append(new_log)
    
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
                if "'" in rel_cases or '"' in rel_cases:
                    raise FOLParsingError(f"Invalid relation declaration: relation should not take strings. Please remove relevent relation: {definition_line}")
                if rel_cases.count(",") % rel_name.count(",") != 0:
                    raise FOLParsingError(f"Invalid relation declaration: declared relation has ambiguous number of parameters. Please correct the definition: {definition_line}")
                
                rel_z3_func = Function(rel_just_name, *[IntSort() for param in rel_params], BoolSort())
                if rel_just_name in self.relations:
                    print_warning_message(f"Warning: {rel_just_name} already exists in declarations.")
                new_relations[rel_just_name] = Relation(rel_just_name, rel_params, rel_meaning, rel_z3_func)
        
        return new_relations
    
    def parse_formulas(self, formulas_text: str) -> list:
        formulas = []
        for formula_line in formulas_text.splitlines():
            parsing_formula = formula_line.strip()
            if  "```" in parsing_formula:
                continue
            if parsing_formula:
                parsed_formula = parse_z3(self.z3_builder, parsing_formula)
                formulas.append(parsed_formula)
        return formulas
    
    def parse_scoped_formulas(self, formulas_text: str) -> dict:
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
                        if scope in self.objects:
                            self.scopes[scope] = self.objects[scope]
                        else:
                            raise FOLParsingError(f"Scope {scope} not found in scope table. Please remove any related usage of this scope for now.")
                parsed_formula = parse_z3(self.z3_builder, parsing_formula)
                formulas[scope].append(parsed_formula)
        return formulas
    
    def parse_exclusive_args(self, definitions_text: str):
        formulas = []
        for definition_line in definitions_text.splitlines():
            if  "```" in definition_line:
                continue
            rel_just_name = definition_line.split("(")[0]
            if rel_just_name not in self.relations:
                raise FOLParsingError(f"Relation {rel_just_name} not found in function table.")
            edited_params = get_relation_params(definition_line)
            original_params = self.relations[rel_just_name].params
            rel_z3_func = self.relations[rel_just_name].function
            if len(edited_params) != len(original_params):
                raise FOLParsingError(f"Invalid exclusive relation declaration: relation has ambiguous number of parameters. Please correct the definition: {definition_line}")
            
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
        return formulas
    
    def parse_obj_rel_declarations_json(self, declarations_json: dict) -> tuple[dict, dict]:
        new_objects = {}
        for definition_line in declarations_json["objects"]:
            obj_name = definition_line["object_name"]
            obj_meaning = definition_line["object_description"]
            if obj_name in self.objects:
                print_warning_message(f"Warning: {obj_name} already exists in declarations.")
            new_objects[obj_name] = obj_meaning
        
        new_relations = {}
        for definition_line in declarations_json["relations"]:
            rel_name = definition_line["relation_name"]
            rel_meaning = definition_line["relation_description"]
            rel_cases = definition_line["relation_cases"]
            rel_just_name = rel_name.split("(")[0]
            rel_params = get_relation_params(rel_name)
            if len(rel_cases) == 0:
                raise FOLParsingError(f"Invalid relation declaration: declared relation has no usage case. Please check the syntax: {definition_line}")
            for rel_case in rel_cases:
                if "'" in rel_case or '"' in rel_case:
                    raise FOLParsingError(f"Invalid relation declaration: relation should not take strings. Please remove relevent relation: {definition_line}")
                if rel_case.count(",") != rel_name.count(","):
                    raise FOLParsingError(f"Invalid relation declaration: declared relation has ambiguous number of parameters. Please correct the definition: {definition_line}")
            
            rel_z3_func = Function(rel_just_name, *[IntSort() for param in rel_params], BoolSort())
            if rel_just_name in self.relations:
                print_warning_message(f"Warning: {rel_just_name} already exists in declarations.")
            new_relations[rel_just_name] = Relation(rel_just_name, rel_params, rel_meaning, rel_z3_func)
        
        return new_objects, new_relations
    
    def parse_semantic_analyser_json(self, definitions_json: dict) -> list:
        formulas = []
        for definition_line in definitions_json["exclusiveness_definitions"]:
            rel_just_name = definition_line.split("(")[0]
            if rel_just_name not in self.relations:
                raise FOLParsingError(f"Relation {rel_just_name} not found in function table.")
            edited_params = get_relation_params(definition_line)
            original_params = self.relations[rel_just_name].params
            rel_z3_func = self.relations[rel_just_name].function
            if len(edited_params) != len(original_params):
                raise FOLParsingError(f"Invalid exclusive relation declaration: relation has ambiguous number of parameters. Please correct the definition: {definition_line}")
            
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
            
        for formula_line in definitions_json["formulas"]:
            parsing_formula = formula_line.strip()
            if parsing_formula:
                parsed_formula = parse_z3(self.z3_builder, parsing_formula)
                formulas.append(parsed_formula)
        
        return formulas
    
    def parse_formula_maker_json(self, formulas_json: dict) -> dict:
        
        for scope_line in formulas_json["scopes"]:
            scope_name = scope_line["scope_name"]
            scope_meaning = scope_line["scope_description"]
            if scope_name in self.scopes:
                print_warning_message(f"Warning: {scope_name} already exists in scopes.")
            self.scopes[scope_name] = scope_meaning
        
        formulas = defaultdict(list)
        formulas["global"] = []
        for formula_line in formulas_json["formulas"]:
            if "scope" in formula_line:
                scope = formula_line["scope"]
                if scope not in self.scopes:
                    if scope in self.objects:
                        self.scopes[scope] = self.objects[scope]
                    else:
                        raise FOLParsingError(f"Scope {scope} not found in scope table. Please remove any related usage of this scope for now.")
            else:
                scope = "global"
                
            parsing_formula = formula_line["formula"]
            parsed_formula = parse_z3(self.z3_builder, parsing_formula)
            formulas[scope].append(parsed_formula)
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
        
        print_dev_message(solver.assertions())
        print_dev_message("Solver result:", results, unsat_score)
        
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

# No longer usable independently
# if __name__ == "__main__":
#     # Example usage
#     cur_dir = os.path.dirname(os.path.realpath(__file__))
#     MODEL_NAME = "gemini-structured"
#     model_info = ModelInfo(MODEL_NAME)
#     session = FOLEvaluationSession(model_info)
    
#     sample_conversation = []
#     with open(os.path.join(cur_dir, "sample_rp.json"), "r", encoding="utf-8") as f:
#         sample_conversations = json.load(f)
#         sample_conversation = sample_conversations[-1]
        
#     for section in sample_conversation:
#         session.append_conversation(section)
#         session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))
        
#     session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))