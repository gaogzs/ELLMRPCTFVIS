import os
import json
from openai import OpenAI
import re
import random

import fact_graph
from fact_graph import FactGraph
from chatbot import ChatBotDummy

do_it_command = "move on to function calls"

eval_prompts = {
    "graph_maker": [
        {
            "role": "system",
            "content": f"""
You are a helpful AI assistant that creates a graph of given format based on a given role-playing scenario happened between a user and an AI.
The input will be given in the format \"**Current Graph**[graph_content] **Historical Conversation**[conversation] **Latest Conversation**[conversation]\". Historical Conversation represents the history of the role-play scenario that was used to make the Current Graph, it can be empty. Your task is to edit the Current Graph based on the content of how content of Latest Conversation impact Historical Conversation. Example: If the Historical Conversation includes \"John is living in London\" and Current Graph includes an edge \"John ->([source_node] live in [target_node]) London\" and the Latest Conversation includes \"John moved to Paris\", then you should remove the edge \"John -> London ([source_node] live in [target_node])\" and add the edge \"John -> Paris ([source_node] live in [target_node])\". You can also add new nodes or edges if needed. You should not change the content of the Historical Conversation, but you can add new nodes or edges to the Current Graph based on the Latest Conversation. 
Your output should be in two steps: When the user first sends the input, you should reply with pure text with a brief reasoning about what you are planning to do and why, then after the user says \"{do_it_command}\", you will conduct the edit to the graph using the provided functions.
The graph you make will be a general summary of the role-playing scenario, like a mind map or a reading note. It should not be too detailed, but should include all the important information.
***Graph Explained***
{fact_graph.desc_fact_graph}
{fact_graph.desc_fact_node}
{fact_graph.desc_node_types}
{fact_graph.desc_info_types}
{fact_graph.desc_edge_content}
"""
        }
    ],
    "question_asker": [
        {
            "role": "system",
            "content": f"""
You are a helpful assistant specialised at analysing a role-playing scenario happened between a user and an AI. Later you will be presented with a convertsation history and being asked a question.
The input will be in the format:\"**Content**[content]**Question**[question]\", where Content is the role-playing scenario and Question is the yes/no question you need to answer.
In the question there may exist special objects in the token format of  \"[name](info_type=[info_type])\", these special objects will be the point of interest in your evaluation, and you need to evaluate them in the criteria of their repective info_type.
{fact_graph.desc_info_types}
Your output should be in the format:
\"**Reasoning**
[reasoning]
**Answer**
[answer]\", where you should first give a brief step-by-step reasoning in the [reasoning] about how you come to the answer, and then give the final answer in [answer]. The [reasoning] part should be concise and generally no more than 100 words, and the [answer] should be either \"True\", \"False\" or "Unkown". In some cases where the content is not implicitly irrelevent with the question, but you think it should be(Example:"John is ice-skating" and "Is John currently in a grassland?"), still answer in only \"True\" or \"False\", otherwise(Example:"John is ice-skating", "Is the apple red?") answer \"Unkown\".
"""
        }
    ]
}

input_templates = {
    "graph_maker": "**Current Graph**\n[current_graph]\n**Historical Conversation**\n[hist_conversation]\n**Latest Conversation**\n[latest_conversation]",
    "question_asker": "**Content**\n[conversation]\n**Question**\n[question]"
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

def ask_question(conversations: str, fact_graph: FactGraph, client: OpenAI, model: str, question_num: int=-1, question_type: int=-1):
    if fact_graph.graph_empty():
        return []
    if question_type == -1:
        question_type = 1
    question_texts = []
    if question_type == 0:
        sampled_nodes = fact_graph.sample_nodes(question_num)
        for node_name, node_data in sampled_nodes:
            question_text = f"Does the role-playing content respect the fact that object {node_name}(info_type={node_data["info_type"]}) exist as a {node_data["node_type"]} in the story as a background?"
            question_texts.append(question_text)
    elif question_type == 1:
        sampled_edges = fact_graph.sample_edges(question_num)
        for source_node, target_node, edge_data in sampled_edges:
            source_data = fact_graph.get_node_data(source_node)
            target_data = fact_graph.get_node_data(target_node)
            content = edge_data["content"]
            content = content.replace("[source_node]", f"{source_node}(info_type={source_data["info_type"]})")
            content = content.replace("[target_node]", f"{target_node}(info_type={target_data["info_type"]})")
            question_text = f"Does the role-playing content respect the fact \"{content}\" in the story as a background?"
            question_texts.append(question_text)
    else:
        raise ValueError("question_type not recognized")
    
    input_message = input_templates["question_asker"]
    input_message = input_message.replace("[conversation]", conversations)
    
    logs = []
    for question_text in question_texts:
        input_message_i = input_message.replace("[question]", question_text)
        user_message = {"role": "user", "content": input_message_i}
        response = client.chat.completions.create(messages=eval_prompts["question_asker"] + [user_message], model=model, temperature=0)
        response_message = response.choices[0].message.content
        logs.append({"question": question_text, "response": response_message})

    return logs
    
        
class RPEvaluationSession():
    def __init__(self, client: OpenAI, model: str, history: list = None) -> None:
        self.rp_history = history if history is not None else ""
        self.client = client
        self.model = model
        self.fact_graph = FactGraph()
        self.logs = []

    def append_conversation(self, lastest_conversation: str) -> None:
        
        complete_messages = eval_prompts["graph_maker"].copy()
        
        if is_in_openai_form(lastest_conversation):
            lastest_conversation = openai_form_to_str(lastest_conversation)
        beginning_graph = self.fact_graph.print_graph()
        message = input_templates["graph_maker"]
        message = message.replace("[current_graph]", beginning_graph)
        message = message.replace("[hist_conversation]", self.rp_history)
        message = message.replace("[latest_conversation]", lastest_conversation)
        
        user_message = {"role": "user", "content": message}
        complete_messages.append(user_message)
        
        response = self.client.chat.completions.create(messages=complete_messages, model=self.model, temperature=0.7)
        reasoning_response = response.choices[0].message
        complete_messages.append(reasoning_response)
        
        reasoning_text = reasoning_response.content
        print(reasoning_text)
        user_message = {"role": "user", "content": do_it_command}
        complete_messages.append(user_message)
        response = self.client.chat.completions.create(messages=complete_messages, model=self.model, tools=fact_graph.tool_api, temperature=0)
        tool_call_response = response.choices[0].message
        complete_messages.append(tool_call_response)
        
        qa_logs = self.ask_question(lastest_conversation)

        function_call_logs = []
        for tool_call in tool_call_response.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            self.fact_graph.exec_function(function_name, arguments)
            
            function_call_logs.append({
                "function_name": function_name,
                "arguments": arguments
            })
        
        self.rp_history += lastest_conversation + "\n"
        
        
        new_log = {
            "beginning_graph": beginning_graph,
            "conversation": lastest_conversation,
            "qa_logs": qa_logs,
            "reasoning": reasoning_text,
            "function_calls": function_call_logs,
            "ending_graph": self.fact_graph.print_graph()
        }
        self.logs.append(new_log)
    
    def ask_question(self, conversation: str, question_num: int=-1, question_type: int=-1) -> None:
       return ask_question(conversation, self.fact_graph, self.client, self.model, question_num, question_type)
        
    
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
