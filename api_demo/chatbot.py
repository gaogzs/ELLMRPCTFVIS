from openai import OpenAI

class ChatBot():

    def send_message(self, message: str, record: bool = True) -> str:
        raise NotImplementedError("send_message method must be implemented by subclasses")

    def get_history(self) -> str:
        raise NotImplementedError("get_history method must be implemented by subclasses")

    def set_history(self, history: list) -> None:
        raise NotImplementedError("set_history method must be implemented by subclasses")


class ChatBotDummy(ChatBot):
    """
    Dummy chatbot that does not send messages to any API.
    It is used for testing purposes only.
    """

    def __init__(self, client: OpenAI, history: list = None):
        self.history = []
        self.client = client

    def send_message(self, message: str, record: bool = True) -> str:
        new_message = {"role": "user", "content": message}
        if record:
            self.history.append(new_message)
        response = self.client.chat.completions.create(messages=self.history + [new_message])
        response_message = response.choices[0].message
        if record:
            self.history.append(response_message)
        return response_message.content

    def get_history(self) -> list:
        return self.history
    
    def set_history(self, history: list) -> None:
        self.history = history