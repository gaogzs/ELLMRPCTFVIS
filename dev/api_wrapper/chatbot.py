import os
import json
import jsonschema

from openai import OpenAI
from google import genai
from anthropic import Anthropic

from utils.loaders import SchemaLoader

schema_draft = "http://json-schema.org/draft-07/schema#"
class ChatBot():
    
    def __init__(self, model: str, sys_prompt: str, schema_loader: SchemaLoader) -> None:
        raise NotImplementedError("ChatBot is an abstract class and cannot be instantiated directly.")

    def send_message(self, message: str, record: bool = True, temperature: float = 0.7) -> str:
        raise NotImplementedError("send_message method must be implemented by subclasses")

    def get_structured_response(self, message: str, schema_key: str, record: bool = True, temperature: float = 0.7):
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

class ChatBotDeepSeekSimple(ChatBot):

    def __init__(self, model: str, sys_prompt: str = None, schema_loader: SchemaLoader = None) -> None:
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        api_key_dir = os.path.join(cur_dir, "api_keys")
        deepseek_key_dir = os.path.join(api_key_dir, "deepseek_api_key")
        with open(deepseek_key_dir, "r") as f:
            deepseek_api_key = f.read().strip()
            
        self.history = [{"role": "system", "content": sys_prompt}]
        self.init_history = self.history.copy()
        self.client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
        self.model = model
        self.schema_loader = schema_loader

    def send_message(self, message: str, record: bool = True, temperature: float = 0.7) -> str:
        new_message = {"role": "user", "content": message}
        response = self.client.chat.completions.create(
            messages=self.history + [new_message],
            model=self.model,
            temperature=temperature
        )
        response_message = response.choices[0].message.content
        if record:
            self.history.append(new_message)
            new_response_message = {"role": "assistant", "content": response_message}
            self.history.append(new_response_message)
        return response_message
    
    def get_structured_response(self, message: str, schema_key: dict, record: bool = True, temperature: float = 0.7) -> dict:
        if not self.schema_loader:
            raise ValueError("Schema loader must be provided for structured responses.")
        schema = self.schema_loader.load_output_schema(schema_key)
        new_message = {"role": "user", "content": message}
        validating_schema = schema.copy()
        validating_schema["$schema"] = schema_draft
        response_format = {
            "type": "json_object"
        }
        response = self.client.chat.completions.create(
            messages=self.history + [new_message],
            model=self.model,
            temperature=temperature,
            response_format=response_format
        )
        response_message = response.choices[0].message.content
        response_parsed = json.loads(response_message)
        jsonschema.validate(instance=response_parsed, schema=validating_schema)
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
        
    def is_structured(self) -> bool:
        return True

class ChatBotGPTSimple(ChatBot):

    def __init__(self, model: str, sys_prompt: str = None, schema_loader: SchemaLoader = None) -> None:
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        api_key_dir = os.path.join(cur_dir, "api_keys")
        gpt_key_dir = os.path.join(api_key_dir, "gpt_api_key")
        with open(gpt_key_dir, "r") as f:
            gpt_api_key = f.read().strip()
            
        self.history = [{"role": "system", "content": sys_prompt}]
        self.init_history = self.history.copy()
        self.client = OpenAI(api_key=gpt_api_key)
        self.model = model
        self.schema_loader = schema_loader

    def send_message(self, message: str, record: bool = True, temperature: float = 0.7) -> str:
        new_message = {"role": "user", "content": message}
        response = self.client.chat.completions.create(
            messages=self.history + [new_message],
            model=self.model,
            temperature=temperature
        )
        response_message = response.choices[0].message.content
        if record:
            self.history.append(new_message)
            new_response_message = {"role": "assistant", "content": response_message}
            self.history.append(new_response_message)
        return response_message
    
    def get_structured_response(self, message: str, schema_key: str, record: bool = True, temperature: float = 0.7) -> dict:
        if not self.schema_loader:
            raise ValueError("Schema loader must be provided for structured responses.")
        schema = self.schema_loader.load_output_schema(schema_key, "strict")
        new_message = {"role": "user", "content": message}
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "output_schema",
                "strict": True,
                "schema": schema
            }
        }
        response = self.client.chat.completions.create(
            messages=self.history + [new_message],
            model=self.model,
            temperature=temperature,
            response_format=response_format
        )
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
        
    def is_structured(self) -> bool:
        return True
    
class ChatBotGeminiSimple(ChatBot):

    def __init__(self, model: str, sys_prompt: str = None, schema_loader: SchemaLoader = None) -> None:
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        api_key_dir = os.path.join(cur_dir, "api_keys")
        gemini_key_dir = os.path.join(api_key_dir, "gemini_api_key")
        with open(gemini_key_dir, "r") as f:
            gemini_api_key = f.read().strip()
            
        self.sys_prompt = sys_prompt
        self.history = []
        self.init_history = self.history.copy()
        self.client = genai.Client(api_key=gemini_api_key)
        self.model = model
        self.schema_loader = schema_loader
    
    def send_message(self, message: str, record: bool = True, temperature: float = 0.7) -> str:
        new_message = {"role": "user", "parts": [{"text": message}]}
        message_config = {
            "temperature": temperature,
            "system_instruction": self.sys_prompt
        }
        response = self.client.models.generate_content(
            contents=self.history + [new_message],
            model=self.model,
            config=message_config
        )
        response_message = response.text
        if record:
            self.history.append(new_message)
            new_response_message = {"role": "model", "parts": [{"text": response_message}]}
            self.history.append(new_response_message)
        return response_message
    
    def get_structured_response(self, message: str, schema_key: str, record: bool = True, temperature: float = 0.7) -> dict:
        if not self.schema_loader:
            raise ValueError("Schema loader must be provided for structured responses.")
        schema = self.schema_loader.load_output_schema(schema_key)
        new_message = {"role": "user", "parts": [{"text": message}]}
        message_config = {
            "temperature": temperature,
            "system_instruction": self.sys_prompt,
            "response_mime_type": "application/json",
            "response_schema": schema
        }
        response = self.client.models.generate_content(
            contents=self.history + [new_message],
            model=self.model,
            config=message_config
        )
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

class ChatBotClaudeSimple(ChatBot):

    def __init__(self, model: str, sys_prompt: str = None, schema_loader: SchemaLoader = None) -> None:
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        api_key_dir = os.path.join(cur_dir, "api_keys")
        claude_key_dir = os.path.join(api_key_dir, "claude_api_key")
        with open(claude_key_dir, "r") as f:
            claude_api_key = f.read()
        
        self.sys_prompt = sys_prompt
        self.history = []
        self.init_history = self.history.copy()
        self.client = Anthropic(api_key=claude_api_key)
        self.model = model
        self.schema_loader = schema_loader
    
    def send_message(self, message: str, record: bool = True, temperature: float = 0.7) -> str:
        new_message = {"role": "user", "content": message}
        response = self.client.messages.create(
            messages=self.history + [new_message],
            model=self.model,
            temperature=temperature
        )
        response_message = ""
        for content_block in response.content:
            if content_block.type == "text":
                response_message += content_block.text
        if record:
            self.history.append(new_message)
            new_response_message = {"role": "assistant", "content": response_message}
            self.history.append(new_response_message)
        return response_message

    def get_structured_response(self, message: str, schema_key: str, record: bool = True, temperature: float = 0.7) -> dict:
        if not self.schema_loader:
            raise ValueError("Schema loader must be provided for structured responses.")
        schema = self.schema_loader.load_output_schema(schema_key, "strict")
        new_message = {"role": "user", "content": message}
        tools = [
            {
                "name": "structured_output",
                "description": "Your response must be in the form of a single json according to this provided schema.",
                "input_schema": schema
            }
        ]
        tool_choice = {
            "type": "tool",
            "name": "structured_output"
        }
        response = self.client.messages.create(
            messages=self.history + [new_message],
            model=self.model,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=1000
        )
        # if response.stop_reason != "tool_use":
        #     print(response.content)
        #     raise ValueError("Claude did not use the structured output tool as expected.")
        for content_block in response.content:
            if content_block.type == "tool_use" and content_block.name == "structured_output":
                response_parsed = content_block.input
                response_message = str(response_parsed)
                if record:
                    self.history.append(new_message)
                    new_response_message = {"role": "assistant", "content": response_message}
                    self.history.append(new_response_message)
                return json.dumps(response_parsed, indent=2).encode().decode('unicode_escape'), response_parsed
        raise ValueError("Structured output invalid in Claude's response.")
    
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
        fake_model_message = {"role": "assistant", "content": message}
        self.history.append(fake_model_message)
    
    def is_structured(self) -> bool:
        return True