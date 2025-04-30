import os
import json
from openai import OpenAI
import re
import random
from z3 import *

from chatbot import ChatBotDummy

do_it_command = "move on to function calls"

eval_prompts = {
    "formula_maker": [
        {
            "role": "system",
            "content": f"""
You are a helpful AI assistant that creates a first-order logical formula based on a given role-playing scenario happened between a user and an AI, which can then be used to check the logical consistency of the story.
The input will be given in the format \"AI:[content] User:[content] AI:[content] ...\"
Your output will be in the format:
\"
**Reasoning**
[reasoning]
**Plan**
[plan]
**SAT definition**
[formula]
\"
Where [reasoning] is your explanation and chain of thought about what you are planning to do. And then in [plan] you should state, based on the previous reasonning, the list of objects and relations you are going to add each line should be composed by the object/function name to be declared, followed by a one sentence description. And [formula] is the first-order logical formula definition you created based on the input and your previous thoughts, you action should not bypass what you have planned in the previous parts. The definition should be given in plain text of SMT-LIB format that can be parsed directly to a Z3 solver. So there should not be any beginning and ending \"```\" and \"smtlib\" notion. All comments should follow a prefix \";;\"
**Guidelines of Creating Formula**
Most of objects that appeared in the story should be defined as contants that has type of \"Object\". The type of \"Object\" is defined as a set of all objects that appeared in the story, including characters, locations, items, events, mentioned concept, and anything else that you think matters in the story. Objects should be declared as EnumSort, for example \"(declare-datatypes () ((Object obj1, obj2, obj3 ...)))\"
All sorts should be considered as declared already and there should not be any new sort delcarations.
And in order to state further facts about story, you can define functions as the relation between declared objects, they should be specific relation, and should not be general terms like \"relate_with()\" or \"interact_with()\". Be note tha relation function can only exist between already-declared constants! All constant names are upper/lowercase sensitive.
Functions can come in serveral basic categories:
- Simple relation: \"foo (Object, Object) Bool\", which simply states the existence of a relation, the input field can be more than 2. Example: \"is_friend (Alice, Bob)\" means Alice and Bob are friends.
- Exclusive relation: \"foo (Object, Object) Bool\", which states that the unidirectional relation from the first object A to the second object B is exclusive, and cannot happen between A and C or any other object. Example: \"is_animal (Alice, Human)\" means Alice is a human, and Alice cannot be any other type of object, in this case \"is_animal (Alice, Human) and is_animal (Alice, Dog)\" should be false, since Alice cannot be human and dog at the same time. In this case the definition should also include something like \"(assert (forall ((a Object) (b Object) (c Object)) (=> (and (is_animal a b) (is_animal a c)) (= b c))))\" as a part of CNF.
- Time contrained exclusive relation: \"foo (Object, Object, Int) Bool\", which states that the unidirectional relation from the first object A to the second object B is exclusive in a certain time period. Example: \"locates_in (Alice, London, T)\" means Alice is in London at time T (integer type) and Alice cannot be in any other place at the same time, but can be in other places if the time is different. so \"locates_in (Alice, London, T) and \"locates_in (Alice, Paris, T)\" is false since Alice cannot be in two different cities at the same time, but \"locates_in (Alice, London, T) and \"locates_in (Alice, Paris, T+1)\" is acceptable, since it means that Alice has moved from London to Paris at since time T. And extra formula should be added to the root CNF to make such logic valid, like \"(assert (forall ((a Object) (b Object) (c Object) (t Int)) (=> (and (locates_in a b t) (locates_in a c t)) (= b c))))\". Time expression should be just an abstruct relative representation like T0, T1, T2.
- Beware that exclusive relation should not be used too often, it should only be used at very specific relation that are stricly exclusive.

**SMT-LIB Syntax Regularisation Guide**

1. General Structure:

Fully parenthesised Lisp-style syntax.

Each expression starts and ends with ( and ).

Every declare or assert must be closed properly.

2. Constant Declarations:

Constants must specify the sort:

(declare-const T0 Int)

All constants must be declared before use.

3. EnumSort Declarations:

EnumSorts, in this case for Objects, are declared as:

(declare-datatypes () ((Object Aleph Bet Charlie ...)))

All constants must be declared before use.
4. Function & Relation Declarations:

Functions follow this syntax:

(declare-fun function_name (ArgType1 ArgType2 ...) ReturnType)
Example:

(declare-fun locates_in (Object Object Int) Bool)

All args appear in a function must be declared before use.

5. Assertions:

An assertion is always wrapped in (assert ...).

Nested logical operators must obey parentheses strictly:

(assert (and (P x) (Q x)))
(assert (implies A B))

All assert command has to be written in a single line, does not matter how long it is, the code needs no beautification.
6. Quantifiers:

forall and exists define variable lists once in this form:

(forall ((x Sort) (y Sort)) expression)
Never nest a forall or exists inside the variable list!
Nested quantifiers should appear in the body only.

7. Time / Numeric Ordering:

Numeric operations assume Int or Real types.

You can write:

(assert (> T1 T0))
Only if T1 and T0 are declared as Int or Real.

8. Naming Rules:

Avoid special characters in names like +, -, /, * unless you escape them with |name-with-symbols|.

Stick to alphanumeric or underscores: my_constant, Paris, locates_in.

9. Comments:

Start with ;; for single-line comments.

;; This is a comment

**Hint**
While making up the code, be sure to check for regular syntax errors, like undeclared constants and unclosed parentheses. Your code will be passed to a Z3 parser so no error should be allowed.
"""
        }
    ]
}

instruction_templates = {
    "formula_maker": """
**Inheritance**
Here is a list of objects relations that have appeared in other parts of the story for your reference only. You should declare them again in the same way if themselves, or similar things appear again in the current part of the story. Beware that these cannot be treated as real declaration, you will have to declare them yourself again if you want to use any yourself!
[inherited_declaration]
**Story**
[story]
""",
    "error_correction": """
Your provided SMT-LIB has returned some error while being passed to Z3 parser. Please check the syntax and fix it. The error message is:
[error_message]

Please respond with the fixed SMT-LIB code only (The part after **SAT definition**), in the same format as before. There should not be any other resoning or explanation unless they are entered as comments in the code.
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

def fix_by_lines(smtlib_str):
    if smtlib_str.startswith("; "):
        return ""
    return smtlib_str

def close_brackets(smtlib_str):
    open_count = smtlib_str.count('(')
    close_count = smtlib_str.count(')')
    difference = open_count - close_count
    if difference > 0:
        return smtlib_str + (')' * (difference))
    return smtlib_str

def add_definition(smtlib_str, new_def):
    if new_def not in smtlib_str:
        smtlib_str = new_def + "\n" + smtlib_str
    return smtlib_str
    
class RPEvaluationSession():
    def __init__(self, client: OpenAI, model: str, history: list = None) -> None:
        self.rp_history = history if history is not None else ""
        self.client = client
        self.model = model
        self.formulas = []
        self.plans = []
        self.logs = []
        
        self.solver = Solver()

    def append_conversation(self, lastest_conversation: str) -> None:
        
        complete_messages = eval_prompts["formula_maker"].copy()
        bot = ChatBotDummy(self.client, self.model, complete_messages)
        
        if is_in_openai_form(lastest_conversation):
            lastest_conversation = openai_form_to_str(lastest_conversation)
        message = instruction_templates["formula_maker"].replace("[story]", lastest_conversation)
        
        if self.plans == []:
            message = message.replace("[inherited_declaration]", "Empty")
        else:
            message = message.replace("[inherited_declaration]", self.plans[-1])
        
        
        complete_response = bot.send_message(message, record=True, temperature=0.1)
        
        sections = re.split(r"\*\*[a-zA-Z ]+\*\*", complete_response)
        reasoning_text, plan_text, formula_text = sections[1], sections[2], sections[3]
        
        self.plans.append(plan_text)
        self.rp_history += lastest_conversation + "\n"
        
        # cleaned_formula_text = "\n".join(map(fix_by_lines, formula_text.split("\n")))
        # closed_formula_text = "\n".join(map(close_brackets, cleaned_formula_text.split("\n")))
        # closed_formula_text = add_definition(closed_formula_text, "(declare-sort Object 0)")
        
        print(complete_response)
        
        parsed_success = False
        while not parsed_success:
            try:
                current_formula = parse_smt2_string(formula_text)
                parsed_success = True
            except Z3Exception  as e:
                print(f"Error parsing SMT-LIB: {e}")
                formula_text = bot.send_message(instruction_templates["error_correction"].replace("[error_message]", str(e)), record=True, temperature=0)
                print(f"Retrying with corrected formula: {formula_text}\n")
            
        result = None
        
        if self.formulas:
            last_formula = self.formulas[-1]
            
            self.solver.reset()
            satisfiable = And(list(last_formula) + list(current_formula))
            self.solver.add(satisfiable)
            result = str(self.solver.check())
            print(self.solver.assertions())
            print(result)
            
        self.formulas.append(current_formula)
        
        pretty_formula = current_formula.sexpr()
        
        new_log = {
            "conversation": lastest_conversation,
            "reasoning": reasoning_text,
            "plan": plan_text,
            "formula": pretty_formula,
            "result": result,
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
        sample_conversation = json.load(f)
    
    for section in sample_conversation:
        session.append_conversation(section)
        session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))