import os
import json
import jsonschema

from openai import OpenAI

from google import genai

schema_draft = "http://json-schema.org/draft-07/schema#"
class ChatBot():

    def send_message(self, message: str, record: bool = True, temperature: float = 0.7) -> str:
        raise NotImplementedError("send_message method must be implemented by subclasses")

    def get_structured_response(self, message: str, schema: dict, record: bool = True, temperature: float = 0.7):
        raise NotImplementedError("get_structured_response method must be implemented by subclasses")
    
    def append_history(self, conversation: dict) -> None:
        raise NotImplementedError("send_message method must be implemented by subclasses")

    def get_history(self) -> str:
        raise NotImplementedError("get_history method must be implemented by subclasses")

    def set_history(self, history: list) -> None:
        raise NotImplementedError("set_history method must be implemented by subclasses")
    
    def reset_history(self) -> None:
        raise NotImplementedError("reset_history method must be implemented by subclasses")
    
    def add_fake_user_message(self, message: str) -> None:
        raise NotImplementedError("add_fake_user_message method must be implemented by subclasses")
    
    def add_fake_model_message(self, message: str) -> None:
        raise NotImplementedError("add_fake_model_message method must be implemented by subclasses")
    
    def is_structured(self) -> bool:
        return False

cur_dir = os.path.dirname(os.path.realpath(__file__))
api_key_dir = os.path.join(cur_dir, "api_keys")

deepseek_key_dir = os.path.join(api_key_dir, "deepseek_api_key")
with open(deepseek_key_dir, "r") as f:
    deepseek_api_key = f.read().strip()
class ChatBotDeepSeekSimple(ChatBot):

    def __init__(self, model: str, sys_prompt: str = None) -> None:
        self.history = [{"role": "system", "content": sys_prompt}]
        self.init_history = self.history.copy()
        self.client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
        self.model = model

    def send_message(self, message: str, record: bool = True, temperature: float = 0.7) -> str:
        new_message = {"role": "user", "content": message}
        response = self.client.chat.completions.create(messages=self.history + [new_message], model=self.model, temperature=temperature)
        response_message = response.choices[0].message.content
        if record:
            self.history.append(new_message)
            new_response_message = {"role": "assistant", "content": response_message}
            self.history.append(new_response_message)
        return response_message
    
    # def get_structured_response(self, message: str, schema: dict, record: bool = True, temperature: float = 0.7) -> dict:
    #     new_message = {"role": "user", "content": message}
    #     response_format = {
    #         "type": "json_schema",
    #         "json_schema": {
    #             "name": "output_schema",
    #             "strict": True,
    #             "schema": schema
    #         }
    #     }
    #     response = self.client.chat.completions.create(messages=self.history + [new_message], model=self.model, temperature=temperature, response_format=response_format)
    #     response_message = response.choices[0].message.content
    #     response_parsed = json.loads(response_message)
    #     if record:
    #         self.history.append(new_message)
    #         new_response_message = {"role": "assistant", "content": response_message}
    #         self.history.append(new_response_message)
    #     return json.dumps(response_parsed, indent=2).encode().decode('unicode_escape'), response_parsed
    
    def append_history(self, conversation: dict) -> None:
        self.history.append(conversation)

    def get_history(self) -> list:
        return self.history
    
    def set_history(self, history: list) -> None:
        self.history = history
    
    def reset_history(self) -> None:
        self.history = self.init_history.copy()
    
    def add_fake_user_message(self, message: str) -> None:
        fake_user_message = {"role": "user", "content": message}
        self.history.append(fake_user_message)
    
    def add_fake_model_message(self, message: str) -> None:
        fake_assistant_message = {"role": "assistant", "content": message}
        self.history.append(fake_assistant_message)

gpt_key_dir = os.path.join(api_key_dir, "gpt_api_key")
with open(gpt_key_dir, "r") as f:
    gpt_api_key = f.read().strip()
class ChatBotGPTSimple(ChatBot):

    def __init__(self, model: str, sys_prompt: str = None) -> None:
        self.history = [{"role": "system", "content": sys_prompt}]
        self.init_history = self.history.copy()
        self.client = OpenAI(api_key=deepseek_api_key, base_url="https://api.openai.com")
        self.model = model

    def send_message(self, message: str, record: bool = True, temperature: float = 0.7) -> str:
        new_message = {"role": "user", "content": message}
        response = self.client.chat.completions.create(messages=self.history + [new_message], model=self.model, temperature=temperature)
        response_message = response.choices[0].message.content
        if record:
            self.history.append(new_message)
            new_response_message = {"role": "assistant", "content": response_message}
            self.history.append(new_response_message)
        return response_message
    
    def get_structured_response(self, message: str, schema: dict, record: bool = True, temperature: float = 0.7) -> dict:
        new_message = {"role": "user", "content": message}
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "output_schema",
                "strict": True,
                "schema": schema
            }
        }
        response = self.client.chat.completions.create(messages=self.history + [new_message], model=self.model, temperature=temperature, response_format=response_format)
        response_message = response.choices[0].message.content
        response_parsed = json.loads(response_message)
        if record:
            self.history.append(new_message)
            new_response_message = {"role": "assistant", "content": response_message}
            self.history.append(new_response_message)
        return json.dumps(response_parsed, indent=2).encode().decode('unicode_escape'), response_parsed
    
    def append_history(self, conversation: dict) -> None:
        self.history.append(conversation)

    def get_history(self) -> list:
        return self.history
    
    def set_history(self, history: list) -> None:
        self.history = history
    
    def reset_history(self) -> None:
        self.history = self.init_history.copy()
    
    def add_fake_user_message(self, message: str) -> None:
        fake_user_message = {"role": "user", "content": message}
        self.history.append(fake_user_message)
    
    def add_fake_model_message(self, message: str) -> None:
        fake_assistant_message = {"role": "assistant", "content": message}
        self.history.append(fake_assistant_message)


gemini_key_dir = os.path.join(api_key_dir, "gemini_api_key")
with open(gemini_key_dir, "r") as f:
    gemini_api_key = f.read().strip()
    
class ChatBotGeminiSimple(ChatBot):

    def __init__(self, model: str, sys_prompt: str = None) -> None:
        self.sys_prompt = sys_prompt
        self.history = []
        self.init_history = self.history.copy()
        self.client = genai.Client(api_key=gemini_api_key)
        self.model = model
    
    def send_message(self, message: str, record: bool = True, temperature: float = 0.7) -> str:
        new_message = {"role": "user", "parts": [{"text": message}]}
        message_config = {
            "temperature": temperature,
            "system_instruction": self.sys_prompt
        }
        response = self.client.models.generate_content(contents=self.history + [new_message], model=self.model, config=message_config)
        response_message = response.text
        if record:
            self.history.append(new_message)
            new_response_message = {"role": "model", "parts": [{"text": response_message}]}
            self.history.append(new_response_message)
        return response_message
    
    def get_structured_response(self, message: str, schema: dict, record: bool = True, temperature: float = 0.7) -> dict:
        new_message = {"role": "user", "parts": [{"text": message}]}
        message_config = {
            "temperature": temperature,
            "system_instruction": self.sys_prompt,
            "response_mime_type": "application/json",
            "response_schema": schema
        }
        response = self.client.models.generate_content(contents=self.history + [new_message], model=self.model, config=message_config)
        response_message = response.text
        response_parsed = response.parsed
        if record:
            self.history.append(new_message)
            new_response_message = {"role": "model", "parts": [{"text": response_message}]}
            self.history.append(new_response_message)
        return json.dumps(response_message, indent=2).encode().decode('unicode_escape'), response_parsed
    
    def append_history(self, conversation: dict) -> None:
        self.history.append(conversation)
    
    def get_history(self) -> list:
        return self.history

    def set_history(self, history: list) -> None:
        self.history = history
        
    def reset_history(self) -> None:
        self.history = self.init_history.copy()
        
    def add_fake_user_message(self, message: str) -> None:
        fake_user_message = {"role": "user", "parts": [{"text": message}]}
        self.history.append(fake_user_message)
        
    def add_fake_model_message(self, message: str) -> None:
        fake_model_message = {"role": "model", "parts": [{"text": message}]}
        self.history.append(fake_model_message)
    
    def is_structured(self) -> bool:
        return True
