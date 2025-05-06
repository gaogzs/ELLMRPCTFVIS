import os
import json
from openai import OpenAI
import re
import random
from z3 import *

from chatbot import ChatBotDummy

do_it_command = "move on to function calls"

unused = """
- inheritance implication: When certain objects in a relation can directly imply another combination of objects in a relation, for example if you are provided with relation \"is_animal(a, b)\" and \"is_type_of(b, c)\", you should write them as \"forall(a b c) (is_type_of(b, c) and is_animal(a, b)) => is_animal(a, c)\". To make it like something
"""

eval_prompts = {
    "declaration_maker": f"""
You are a helpful AI assistant who will be in charge of extracting some key elements from a given role-playing scenario happened between a user and an AI。
Your input will be given in the format \**Story**[story]"**Reference**[reference]\" and [story] will be given in the format \"AI:[content] User:[content] AI:[content] ...\". In your output you should extract 3 elements in 3 stages, give in the format:
\"
**Objects**
[objects]
**Relations**
[relations]
**Replenishment**
[replenishment]
\"
Where [objects] is a list of objects that appeared in the story, including characters, locations, items, events, mentioned concept. You should list out one object perline, each line consists of a non-repetitive variable name in python case together with a brief translation (not a complete description) of what the variable name represents, separated by \":\". For example, if the story mentions \"Aleph is a brown dog living in Mount Everest with a leopard cat.\" You may give output like:
\"
aleph: Aleph, a name of a character
dog: dog, a type of animal
mount_everest: Mount Everest, a name of a location
leopard_cat: leopard cat, a type of animal
...
\"
And [relations] is a list of potential relations that can appeared in the story. Relation may represents any type of relation between two and more objects, or may be used to additionally describe the properties and facts of an object. You should list out one relation perline, each line consists of a non-repetitive relation declaration whose name in python case, a brief explanation of the nature of the relation, and the cases you want to apply it to, all separated by \":\". For example, in the same story \"Aleph is a brown dog living in Mount Everest with a leopard cat.\" You may give output like:
\"
is_animal(a, b): a is an animal of type b: is_animal(aleph, dog)
is_colour(a, b): a shows a colour of b: is_colour(aleph, brown)
live_in_location(a, b): a lives in location b: live_in_location(aleph, mount_everest)
...
\"
Every element should be decomposed in such a fundamental level. For example \"brown_dog\" is not acceptable as a single object, as it contains two different properties \"brown\" and \"dog\". \"is_dog\" is not acceptable as a single relation, as additional properties can only be applied in a general and flexible relation like \"is_animal\", and there should be no relation that takes in only one argument.
In the second stage, if any object that was not declared in the [objects] part appeared in any of the relations, you should replenish it in the following [replenishment] part. The format will be just the same as the [objects] part, where each line consists of a non-repetitive variable name in python case together with a brief translation of what the variable name represents, separated by \":\". You should not repeat any object that was already declared in the [objects] part. For example, in the examples given above, \"is_colour(aleph, brown)\" contains a new object \"brown\" that was not declared in the [objects] part, so you should add it in the [replenishment] part:
\"
brown: brown
...
\"
The [reference] part of the input may contain a list of objects and relation declarations that have existed elseware for your to maintain consistencty in syntax, and if the story contains any object or relation that means exactly the same as one in the [reference] list, you should declare it the same way. For example, if the [reference] part contains \"is_animal(a, b): a is a creature of type b: is_animal(aleph, dog)\" and the story contains \"Aleph is a brown dog living in Mount Everest with a leopard cat.\" You should declare it as \"is_animal(aleph, dog)\" in the [relations] part. But if the [reference] part contains \"is_colour(a, b): a shows a colour of b\", you should no longer declare something like \"is_color(a, b)\" or \"is_of_colour(a, b)\" which is just different in name but exactly in meaning. However, if you onnly find a similar match, like \"live_in_location(a, b)\" and \"stay_in_location(a, b)\", they should not be merged, and you should declare them separately. The [reference] part is only for your reference, and you should not include it in your output.
""",
    "semantic_definer": f"""
You are a helpful AI assistant who will be in charge of analysing the definition of some logical symbols for logical analysis. The input will consist of a list of declaration, where each line contains a single declaration. The declarations will come in two types, objects and relations. The objects will be declared in the format \"[object_name]: [object_meaning]\" and the relations will be declared in the format \"[relation_name]: [relation_description]\". Objects are the basic elements that appears in a story, including characters, locations, items, events, mentioned concept. Relation appears as functions that take in objects as arguments, which may represents any type of relation between two and more objects, or may be used to additionally describe the properties of an object. You should analyse the logical nature of those concepts, and give your output with one spotted nature per line. Here are some types of nature you may find:
- equity: You find that two objects means exactly the same thing whereever they are used, for example if both \"earphone\" and \"headphone\" are declared as \"an audio device\", you should write them as \"earphone = headphone\".
- exclusive relation: When a relation of objects declared in some way that will make other usage of the same relation impossible, for example for \"is_animal(a, b): a is an animal of type b\" clearly a cannot be a dog and a cat at the same time, so you should write \"forall(a b c) is_animal(a, b) exclusive_with is_animal(a, c)\". Beware that exclusive relation should not be used too often, it should only be used at very specific relation that are stricly exclusive.
- time contrained exclusive relation: When a relation of objects declared in some way that will make other usage of the same relation impossible only at the same time, for example for \"locates_in(a, b): a is in location b\" clearly a cannot be in two different locations at the same time, so you should write two definitions \"locates_in(a, b) time_exclusive locates_in(a, b, t)\" where you change its definition by adding a new time argument t at the end of it, and \"forall(a b c t) locates_in(a, b, t) exclusive_with locates_in(a, c, t)\" to indicate that a cannot be in two different locations b and c at the same time t. From this on, if appears in later part of your definitions, this relation will always appear as \"locates_in(a, b, t)\" instead of \"locates_in(a, b)\".
- relation implication: When an object having a relation can directly imply another specific relation, for example if both \"live_in_location(a, b)\" and \"stay_in_location(a, b)\" are declared, you should write them as \"forall(a b) live_in_location(a, b) => stay_in_location(a, b)\". But you may not have "forall(a b) live_in_location(a, b) => locates_in(a, b)\" since someone lives in a location does not necessarily mean that they are in that location at the same time. Some implication can be bidirectional, so you should also check again in another way.
- relation contradiction: When an object having a relation is directly the opposite of another specific relation, for example if both \"is_animal(a, b)\" and \"is_plant(a, c)\" are declared, you should write them as \"forall(a b c) is_animal(a, b) => not(is_plant(a, c))\", since a cannot be both an animal and a plant at the same time, doesn't matter what type of animal or plant it is.
- relation contradiction limited: Similar to relation contradiction, but only contradicts for the same combination of input. For definitions like \"stay_in_location(a, b)\" and \"leave_location(a, b)\" you should write \"forall(a b) stay_in_location(a, b) => not(leave_location(a, b))\", since the contradiction happens for a to stay and leave the same location.

Your output should be in the format:
\"
**Reasoning**
[reasoning]
**Definitions**
[definitions]
\"
Where [reasoning] is your explanation and chain of thought about what you are planning to do. And then in [definitions] is, based on the previous reasonning, the main body of your definition output.
""",
    "formula_maker": f"""
You are a helpful AI assistant that creates a first-order logical formula based on a given role-playing scenario happened between a user and an AI, which can then be used to check the logical consistency of the story.
The input will be given in the format:
\"
**Story**
[story]
**Objects**
[objects]
**Relations**
[relations]
**Pre-defined properties**
[predefined_properties]
\"
Where [story] is the content of the story you will be analysing, given in the format \"AI:[content] User:[content] AI:[content] ...\".
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
Most of objects that appeared in the story should be defined as contants that has type of \"Object\". The type of \"Object\" is defined as a set of all objects that appeared in the story, all available objects are supplied in the [objects] part of the input. Objects should be declared as EnumSort, for example \"(declare-datatypes () ((Object obj1, obj2, obj3 ...)))\"
All sorts should be considered as declared already and there should not be any new sort delcarations.
And in order to state further facts about story, you have been supplied with a list of available relations in the [relations] part of the input. You should declare them as functions, for example \"(declare-fun foo (Object Object) Bool)\". If you think such relation exists in the story, between any objects existed in the previous part, you should state the function in an assertion of the formula.
In [predefined_properties] part, there are some existing logical properties written in pseudo code, you should convert them into SMT-LIB format and add them to the formula. There are some special types of properties you should be aware of:
- Exclusive relation: \"forall(...) foo(...) exclusive_with foo(...)\", which states that the unidirectional relation defined as foo is exclusive, and cannot happen in another usage of foo. Example: \"forall(a b c) is_animal(a, b) exclusive_with is_animal(a, c)\" means that a can only be one animal and a cannot be multiple animals at the same time. In this case if the same a is defined in is_animal more than once for different second argument, the formula shoudl return false. In this case the definition should also include something like \"(assert (forall ((a Object) (b Object) (c Object)) (=> (and (is_animal a b) (is_animal a c)) (= b c))))\" as a part of CNF. Watch the for which argument is the exclusive one in two sides of the exclusiveness definition, as it can be in any position.

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
        
        sys_prompt = {"role": "system", "content": eval_prompts["formula_maker"].copy()}
        bot = ChatBotDummy(self.client, self.model, sys_prompt)
        
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