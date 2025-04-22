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
You are a helpful AI assistant that creates a first-order logical formula based on a given role-playing scenario happened between a user and an AI in order to maintain its logical consistency.
The input will be given in the format \"AI:[content] User:[content] AI:[content] ...\"
Your output will be in the format:
\"
**Reasoning**
[reasoning]
**SAT definition**
[formula]
\"
Where [reasoning] is your explanation and chain of thought about what you are planning to do, and [formula] is the first-order logical formula definition you created based on the input and your previous thoughts. The definition should be given in plain text of SMT-LIB format that can be parsed directly to a Z3 solver. So there should not be any beginning and ending \"```\" and \"smtlib\" notion. All comments should follow a prefix \";;\"
**Guidelines of Creating Formula**
Most of objects that appeared in the story should be defined as contants that has type of \"Object\". The type of \"Object\" is defined as a set of all objects that appeared in the story. And in order to state further facts about story, you can define functions as the relation between declared objects. No other sort need to be declared except for Object.
Be note tha relation function can only exist between already-declared constants!
Functions can come in serveral basic categories:
- Simple relation: \"foo (Object, Object) Bool\", which simply states the existence of a relation, the input field can be more than 2. Example: \"is_friend (Alice, Bob)\" means Alice and Bob are friends.
- Exclusive relation: \"foo (Object, Object) Bool\", which states that the unidirectional relation from the first object A to the second object B is exclusive, and cannot happen between A and C or any other object. Example: \"is_race (Alice, Human)\" means Alice is a human, and Alice cannot be any other type of object, in this case \"is_race (Alice, Human) and is_race (Alice, Dog)\" should be false, since Alice cannot be human and dog at the same time. In this case the definition should also include something like \"(assert (implies (is_race a b) (forall ((x Object)) (implies (not (= x b)) (not (is_race a x))))))\" as a part of CNF.
- Time contrained exclusive relation: \"foo (Object, Object, Int) Bool\", which states that the unidirectional relation from the first object A to the second object B is exclusive in a certain time period. Example: \"locates_in (Alice, London, T)\" means Alice is in London at time T (integer type) and Alice cannot be in any other place at the same time, but can be in other places if the time is different. so \"locates_in (Alice, London, T) and \"locates_in (Alice, Paris, T)\" is false since Alice cannot be in two different cities at the same time, but \"locates_in (Alice, London, T) and \"locates_in (Alice, Paris, T+1)\" is acceptable, since it means that Alice has moved from London to Paris at since time T. And extra formula should be added to the root CNF to make such logic valid, like \"(assert (implies (locates_in a b c) (forall ((x Object)) (implies (not (= x b)) (not (locates_in a x c))))))\". Time expression can be just an abstruct representation like Tminus, T0, T1, Tplus -- where Tminus means past, T0 means present at beginning of the story section, T1 means the new present at the end of story section and Tplus means future. All of these time expressions should be declared as a constant of type Int.
"""
        }
    ]
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

def check_brackets(smtlib_str):
    open_count = smtlib_str.count('(')
    close_count = smtlib_str.count(')')
    difference = open_count - close_count
    if difference > 0:
        print(f"[!] Mismatch: {open_count} '(' vs {close_count} ')'. Adding {difference} closing ')'s.")
        return smtlib_str + (')' * (difference))
    return smtlib_str
    
class RPEvaluationSession():
    def __init__(self, client: OpenAI, model: str, history: list = None) -> None:
        self.rp_history = history if history is not None else ""
        self.client = client
        self.model = model
        self.formulas = []
        self.logs = []

    def append_conversation(self, lastest_conversation: str) -> None:
        
        complete_messages = eval_prompts["formula_maker"].copy()
        
        if is_in_openai_form(lastest_conversation):
            lastest_conversation = openai_form_to_str(lastest_conversation)
        message = lastest_conversation
        
        user_message = {"role": "user", "content": message}
        complete_messages.append(user_message)
        
        response = self.client.chat.completions.create(messages=complete_messages, model=self.model, temperature=0)
        complete_response = response.choices[0].message
        complete_messages.append(complete_response)
        
        reasoning_text, formula_text = complete_response.content.split("**SAT definition**")
        reasoning_text = reasoning_text.split("**Reasoning**")[1].strip()
        print(reasoning_text)
        print(formula_text)
        
        self.rp_history += lastest_conversation + "\n"
        
        formula_text = check_brackets(formula_text)
        current_formula = parse_smt2_string(formula_text)
        result = None
        
        if self.formulas:
            last_formula = self.formulas[-1]
            satisfiable = Implies(And(*last_formula), And(*current_formula))
            
            solver = Solver()
            solver.add(satisfiable)
            result = str(solver.check())
            
        self.formulas.append(parse_smt2_string(formula_text.replace("T0", "Tminus").replace("T1", "T0")))
        
        pretty_formula = current_formula.sexpr()
        
        new_log = {
            "conversation": lastest_conversation,
            "reasoning": reasoning_text,
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
    with open(os.path.join(cur_dir, "sample_rp.json"), "r") as f:
        sample_conversation = json.load(f)
    
    for section in sample_conversation:
        session.append_conversation(section)
        session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))
