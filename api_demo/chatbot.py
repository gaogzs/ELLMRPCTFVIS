from openai import OpenAI

class ChatBot():

    def send_message(self, message: str, record: bool = True) -> str:
        raise NotImplementedError("send_message method must be implemented by subclasses")

    def get_history(self) -> str:
        raise NotImplementedError("get_history method must be implemented by subclasses")

    def set_history(self, history: list) -> None:
        raise NotImplementedError("set_history method must be implemented by subclasses")


class ChatBotDummy(ChatBot):

    def __init__(self, client: OpenAI, model: str, history: list = None) -> None:
        self.history = history
        self.client = client
        self.model = model

    def send_message(self, message: str, record: bool = True, temperature: float = 0.7) -> str:
        new_message = {"role": "user", "content": message}
        response = self.client.chat.completions.create(messages=self.history + [new_message], model=self.model, temperature=temperature)
        if record:
            self.history.append(new_message)
        response_message = response.choices[0].message
        if record:
            self.history.append(response_message)
        return response_message.content

    def get_history(self) -> list:
        return self.history
    
    def set_history(self, history: list) -> None:
        self.history = history