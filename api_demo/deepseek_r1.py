import os
import json
from openai import OpenAI

cur_dir = os.path.dirname(__file__)

prompts_dir = os.path.join(cur_dir, "prompts.json")
with open(prompts_dir, "r") as f:
    prompts = json.load(f)

key_dir = os.path.join(cur_dir, "deepseek_api_key")
with open(key_dir, "r") as f:
    api_key = f.read().strip()
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=prompts[0],
    stream=False
)

print(response.choices[0].message.content)