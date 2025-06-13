import os
import json
from openai import OpenAI
import re

from chatbot import ChatBotOpenAISimple
from sentence_transformers import SentenceTransformer, util

 
cur_dir = os.path.dirname(__file__)

eval_prompts_dir = os.path.join(cur_dir, "evaluation_prompts.json")
with open(eval_prompts_dir, "r") as f:
    eval_prompts = json.load(f)

metric_desc_dir = os.path.join(cur_dir, "metric_descs.json")
with open(metric_desc_dir, "r") as f:
    metric_descs = json.load(f)

def metric_to_string(wanted_metric):
    out_string = "\n"
    for key, values in wanted_metric.items():
        new_line = f"{key}: {values["name"]}. {values["description"]}\n"
        out_string += new_line
    
    return out_string

# Replace the placeholders in the eval_prompts with the actual metric descriptions
for eval_type, sub_prompt in eval_prompts.items():
    for sub_type, content in sub_prompt.items():
        if "[[metric_desc]]" in content[0]["content"]:
            new_content = content[0]["content"]
            metric_desc = metric_descs[eval_type]
            new_content = new_content.replace(f"[[metric_desc]]", metric_to_string(metric_desc))
            sub_prompt[sub_type][0]["content"] = new_content
            
            if "[[output_form]]" in content[0]["content"]:
                new_content = content[0]["content"]
                output_format = "{"
                for key in metric_desc.keys():
                    output_format += f"{key}: [score], "
                output_format = output_format[:-2] + "}"
                new_content = new_content.replace(f"[[output_form]]", output_format)
                sub_prompt[sub_type][0]["content"] = new_content

chatter_prompts_dir = os.path.join(cur_dir, "chatter_prompts.json")
with open(chatter_prompts_dir, "r") as f:
    chatter_prompts = json.load(f)

samples_dir = os.path.join(cur_dir, "sample_conversations.json")
with open(samples_dir, "r", encoding="utf-8") as f:
    samples = json.load(f)

# Replace the placeholders in the samples with the actual systemp prompts
for sample in samples:
    sample_system_prompt_content = sample["messages"][0]["content"]
    placeholder_re = re.compile(r"\[\[prompt_(.+)\]\]")
    matches = placeholder_re.search(sample_system_prompt_content)
    if matches:
        placeholder = matches.group(0)
        prompt_type = matches.group(1)
        new_content = sample_system_prompt_content.replace(placeholder, chatter_prompts[prompt_type])
        sample["messages"][0]["content"] = new_content

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

def llm_evaluation(messages, eval_type="single-scoring", model="deepseek-chat", shots=0, history=None):
    if eval_type == "single-scoring":
        temperature = 0
        if shots is not None:
            eval_prompt = eval_prompts[eval_type]["evaluator"][:shots * 2 + 1].copy()
        else:
            eval_prompt = eval_prompts[eval_type]["evaluator"].copy()
        
        user_input = {"role": "user", "content": str(messages)}
        eval_prompt.append(user_input)
    
        response = client.chat.completions.create(
            model=model,
            messages=eval_prompt,
            temperature=temperature,
            stream=False
        )
        
        response_content = str(response.choices[0].message.content)
        eval_score = float(response_content.split(" ")[0])
        
        print(eval_score)
        
        eval_reason = None
        if model == "deepseek-reasoner":
            eval_reason = response.choices[0].message.reasoning_content
            # print(eval_reason)
            
        return (eval_score, eval_reason)
    
    elif "multiple-scoring" in eval_type:
        temperature = 0
        if shots is not None:
            eval_prompt = eval_prompts[eval_type]["evaluator"][:shots * 2 + 1].copy()
        else:
            eval_prompt = eval_prompts[eval_type]["evaluator"].copy()
        
        user_input = {"role": "user", "content": str(messages)}
        eval_prompt.append(user_input)
    
        response = client.chat.completions.create(
            model=model,
            messages=eval_prompt,
            temperature=temperature,
            stream=False
        )
        
        response_content = str(response.choices[0].message.content)
        
        response_content = response_content.replace("\n", "")
        match = re.search(r'\{.*\}', response_content)
        if match:
            response_content = match.group(0)
        else:
            print("No valid JSON object found in response_content")
            
        try:
            eval_score = json.loads(response_content)
        except:
            print("Unable to decode:")
            print(response_content)
            exit()
        average_score = 0
        for key in eval_score.keys():
            if key != "average":
                average_score += eval_score[key]
        eval_score["average"] = round(average_score / len(eval_score.keys()), 3)
        
        print(eval_score)
        
        eval_reason = None
        if model == "deepseek-reasoner":
            eval_reason = response.choices[0].message.reasoning_content
            # print(eval_reason)
            
        return (eval_score, eval_reason)
    
    elif eval_type == "subjective-summarising":
        temperature = 0
        if shots is not None:
            identifier_prompt = eval_prompts[eval_type]["identifier"][:shots * 2 + 1].copy()
            comparer_prompt = eval_prompts[eval_type]["comparer"][:shots * 2 + 1].copy()
        else:
            identifier_prompt = eval_prompts[eval_type]["identifier"].copy()
            comparer_prompt = eval_prompts[eval_type]["comparer"].copy()
        
        user_input = {"role": "user", "content": str(messages[1:])}
        identifier_prompt.append(user_input)
    
        response = client.chat.completions.create(
            model=model,
            messages=identifier_prompt,
            temperature=temperature,
            stream=False
        )
        
        identifier_reponse = str(response.choices[0].message.content)
        print(identifier_reponse)
        
        # Comparing with the ground truth
        ground_truth = messages[0]["content"]
        user_input = {"role": "user", "content": f"Guideline: {ground_truth}\nSummary: {identifier_reponse}"}
        response = client.chat.completions.create(
            model=model,
            messages=comparer_prompt + [user_input],
            temperature=temperature,
            stream=False
        )
        truth_score = float(response.choices[0].message.content.split(" ")[0])
        print(truth_score)
        eval_reason = None
        
        if model == "deepseek-reasoner":
            eval_reason = response.choices[0].message.reasoning_content
            print(eval_reason)
        
        # Comparing the current summary with the previous one
        relative_score = 1
        history_score = 1
        similarity_model = "sentence-transformers"
        if history:
            hist_identifier_reponse = []
            for entry in history:
                hist_identifier_reponse.append(entry["chat_evaluation"]["identification"])
            if similarity_model == "deepseek":
                user_input = {"role": "user", "content": f"Summary 1: {hist_identifier_reponse[-1]}\nSummary 2: {identifier_reponse}"}
                response = client.chat.completions.create(
                    model=model,
                    messages=comparer_prompt + [user_input],
                    temperature=temperature,
                    stream=False
                )
                relative_score = float(response.choices[0].message.content.split(" ")[0])
                print(relative_score)
                user_input = {"role": "user", "content": f"Summary 1: {hist_identifier_reponse}\nSummary 2: {identifier_reponse}"}
                response = client.chat.completions.create(
                    model=model,
                    messages=comparer_prompt + [user_input],
                    temperature=temperature,
                    stream=False
                )
                history_score = float(response.choices[0].message.content.split(" ")[0])
                print(history_score)
            elif similarity_model == "sentence-transformers":
                model = SentenceTransformer("all-MiniLM-L6-v2")
                last_embeddings = model.encode(hist_identifier_reponse[-1], convert_to_tensor=True)
                current_embedding = model.encode(identifier_reponse, convert_to_tensor=True)
                
                relative_score = util.pytorch_cos_sim(last_embeddings, current_embedding).item()
                print(relative_score)
                
                history_embeddings = model.encode(str(hist_identifier_reponse), convert_to_tensor=True)
                history_score = util.pytorch_cos_sim(history_embeddings, current_embedding).item()
                print(history_score)
            else:
                raise ValueError(f"Unknown similarity model: {similarity_model}")
        
        
        eval_score = {"identification": identifier_reponse, "truth_score": truth_score, "relative_score": relative_score, "history_score": history_score}
        return (eval_score, eval_reason)
    elif eval_type == "continuous-summarising":
        temperature = 0
        if shots is not None:
            identifier_prompt = eval_prompts[eval_type]["identifier"][:shots * 2 + 1].copy()
            provider_prompt = eval_prompts[eval_type]["provider"][:shots * 2 + 1].copy()
        else:
            identifier_prompt = eval_prompts[eval_type]["evaluator"].copy()
            provider_prompt = eval_prompts[eval_type]["provider"].copy()
        
        chatbot = ChatBotOpenAISimple(client=client, model=model, history=identifier_prompt)
        
        summaries = []
        for i in range(3, len(messages), 2):
            sliced_messages = messages[i - 2:i]
            new_providing = provider_prompt.copy()[0]["content"]
            new_providing = new_providing.replace("[[messages]]", str(sliced_messages))
            
            response = chatbot.send_message(new_providing, record=True, temperature=temperature)
            summaries.append(response)
            print(response)
        
        eval_score = {"summaries": summaries}
            
        eval_reason = None
        return (eval_score, eval_reason)
    else:
        print(f"Evaluation type {eval_type} not recognised!")
        return None

def test_evaluation(sample_messages, eval_type, model, shots, slicing=True):
    
    histories = []
    last_eval = None
    if slicing:
        for i in range(3, len(sample_messages), 2):
            new_entry = {}
            
            sliced_messages = sample_messages[:i]
            new_entry["messages"] = sliced_messages
            new_entry["type"] = eval_type
            
            evaluation = llm_evaluation(sliced_messages, eval_type=eval_type, model="deepseek-chat", shots=shots, history=histories)[0]
            new_entry["chat_evaluation"] = evaluation
            last_eval = evaluation
            
            # evaluation, reason = llm_evaluation(sliced_messages, eval_type=eval_type, model="deepseek-reasoner", shots=shots, history=histories)
            # new_entry["reasoner_evaluation"] = evaluation
            # new_entry["reason_reasoning"] = reason
            
            histories.append(new_entry)
    else:
        new_entry = {}
        
        new_entry["messages"] = sample_messages
        new_entry["type"] = eval_type
        
        evaluation = llm_evaluation(sample_messages, eval_type=eval_type, model="deepseek-chat", shots=shots, history=histories)[0]
        new_entry["chat_evaluation"] = evaluation
        last_eval = evaluation
        
        evaluation, reason = llm_evaluation(sample_messages, eval_type=eval_type, model="deepseek-reasoner", shots=shots)
        new_entry["reasoner_evaluation"] = evaluation
        new_entry["reason_reasoning"] = reason
        
        histories.append(new_entry)
        
    return histories

if __name__ == "__main__":
    eval_type = "subjective-summarising"
    eval_model = "deepseek-chat"
    prompt_shots = 1
    
    output_dir = os.path.join(cur_dir, f"output_{eval_type}_{prompt_shots}_shot.json")
    
    
    test_histories = []
    for test_sample in samples[:1]:
        sample_messages = test_sample["messages"]
        
        test_history = test_evaluation(sample_messages, eval_type=eval_type, model=eval_model, shots=prompt_shots, slicing=True)
        test_histories.append(test_history)
        
        with open(output_dir, "w", encoding="utf-8") as f:
            json.dump(test_histories, f, indent=2, ensure_ascii=False)
    