import os
import json

from chatbot import ChatBotSimple
from openai import OpenAI

user_command = "Now generate 5 conversation history each of length 20-30 lines, with a initial system message defines the nature of the assistant to perform a specific task and set certain guidelines for the assistant while. For the beginning four conversations, the assistant assistant should follow the guideline and perform the task as expected. In the last conversation, the assistant should gradually start to break the guideline and respond to the user in a way that is not expected as the conversation proceeds."

cur_dir = os.path.dirname(os.path.abspath(__file__))
key_dir = os.path.join(cur_dir, "deepseek_api_key")
with open(key_dir, "r") as f:
    api_key = f.read().strip()
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

prompt_dir = os.path.join(cur_dir, "content_generator_prompt.json")
with open(prompt_dir, "r", encoding='utf-8') as f:
    system_prompt = json.load(f)

chatbot = ChatBotSimple(client=client, model="deepseek-chat", history=system_prompt)
result = chatbot.send_message(user_command, record=False, temperature=1.0)

output_dir = os.path.join(cur_dir, "content_generator_output.json")
with open(output_dir, "w", encoding="utf-8") as f:
    f.write(result)