import os
import json
from openai import OpenAI

cur_dir = os.path.dirname(__file__)

prompts_dir = os.path.join(cur_dir, "evaluation_prompts.json")
with open(prompts_dir, "r") as f:
    prompts = json.load(f)

samples_dir = os.path.join(cur_dir, "sample_conversations.json")
with open(samples_dir, "r") as f:
    samples = json.load(f)
    
output_dir = os.path.join(cur_dir, "output.json")

key_dir = os.path.join(cur_dir, "deepseek_api_key")
with open(key_dir, "r") as f:
    api_key = f.read().strip()
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

def get_response(messages, temperature=1.3):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=temperature,
        stream=False
    )

    print(response.choices[0].message.content)
    return response.choices[0].message

def llm_evaluation(messages, eval_type="single-scoring", model="deepseek-chat"):
    temperature=0.1
    if eval_type == "single-scoring":
        eval_prompt = prompts[eval_type]
        
        user_input = {"role": "user", "content": str(messages)}
        
        eval_prompt.append(user_input)
        
        response = client.chat.completions.create(
            model=model,
            messages=eval_prompt,
            temperature=temperature,
            stream=False
        )
        print(eval_prompt)
        print(response.choices[0].message.content)
        return response.choices[0].message
    else:
        print(f"Evaluation type {eval_type} not recognised!")
        return None

def test_slicing(sample_messages, eval_type):
    
    sample_messages
    
    histories = []
    
    for i in range(3, len(sample_messages), 2):
        new_entry = {}
        
        sliced_messages = sample_messages[:i]
        new_entry["messages"] = sliced_messages
        new_entry["type"] = eval_type
        
        evaluation = llm_evaluation(sliced_messages, eval_type=eval_type)
        new_entry["evaluation"] = evaluation
        
        histories.append(new_entry)
        
    return histories

if __name__ == "__main__":
    test_sample = samples[0]
    eval_type = "single-scoring"
    
    test_history = test_slicing(test_sample, eval_type=eval_type)
    
    with open(output_dir, "w") as f:
        json.dump(test_history, f)
    
