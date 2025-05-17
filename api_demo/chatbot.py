import os
from openai import OpenAI

class ChatBot():

    def send_message(self, message: str, record: bool = True) -> str:
        raise NotImplementedError("send_message method must be implemented by subclasses")
    
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
    
    def add_fake_assistant_message(self, message: str) -> None:
        raise NotImplementedError("add_fake_assistant_message method must be implemented by subclasses")

cur_dir = os.path.dirname(os.path.realpath(__file__))

key_dir = os.path.join(cur_dir, "deepseek_api_key")
with open(key_dir, "r") as f:
    api_key = f.read().strip()
class ChatBotDeepSeekSimple(ChatBot):

    def __init__(self, model: str, sys_prompt: str = None) -> None:
        self.history = [{"role": "system", "content": sys_prompt}]
        self.init_history = self.history.copy()
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
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
    
    def add_fake_assistant_message(self, message: str) -> None:
        fake_assistant_message = {"role": "assistant", "content": message}
        self.history.append(fake_assistant_message)