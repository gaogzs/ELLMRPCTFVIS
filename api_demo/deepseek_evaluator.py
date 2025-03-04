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
    if eval_type == "single-scoring":
        temperature=0.1
        eval_prompt = prompts[eval_type].copy()
        
        user_input = {"role": "user", "content": str(messages)}
        eval_prompt.append(user_input)
    
        response = client.chat.completions.create(
            model=model,
            messages=eval_prompt,
            temperature=temperature,
            stream=False
        )
        
        response_content = str(response.choices[0].message.content)
        eval_score = int(response_content.split(" ")[0])
        
        print(eval_score)
        
        eval_reason = None
        if model == "deepseek-reasoner":
            eval_reason = response.choices[0].message.reasoning_content
            # print(eval_reason)
            
        return (eval_score, eval_reason)
    else:
        print(f"Evaluation type {eval_type} not recognised!")
        return None

def test_slicing(sample_messages, eval_type, model):
    
    histories = []
    
    for i in range(3, len(sample_messages), 2):
        new_entry = {}
        
        sliced_messages = sample_messages[:i]
        new_entry["messages"] = sliced_messages
        new_entry["type"] = eval_type
        
        evaluation = llm_evaluation(sliced_messages, eval_type=eval_type, model="deepseek-chat")[0]
        new_entry["chat_evaluation"] = evaluation
        
        evaluation, reason = llm_evaluation(sliced_messages, eval_type=eval_type, model="deepseek-reasoner")
        new_entry["reasoner_evaluation"] = evaluation
        new_entry["reason_reasoning"] = reason
        
        histories.append(new_entry)
        
    return histories

if __name__ == "__main__":
    eval_type = "single-scoring"
    eval_model = "deepseek-chat"
    test_histories = []
    i = 0
    
    for test_sample in samples:
        for preset_prompts in test_sample["system_prompt"]:
            sample_messages = [preset_prompts] + test_sample["messages"]
            test_history = test_slicing(sample_messages, eval_type=eval_type, model=eval_model)
            test_histories.append(test_history)
            
            with open(output_dir, "w") as f:
                json.dump(test_histories, f, indent=2, ensure_ascii=False)
    