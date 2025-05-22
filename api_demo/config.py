from chatbot import ChatBot, ChatBotDeepSeekSimple, ChatBotGeminiSimple

_PRINT_CONTENT = False
_ERROR_RETRIES = 10



def print_warning_message(message):
    global _PRINT_CONTENT
    if _PRINT_CONTENT:
        print(message)

_model_info = {
    "deepseek-chat": {
        "model": "deepseek-chat",
        "chatbot": ChatBotDeepSeekSimple,
        "output_format": "text"
    },
    
    "gemini-chat": {
        "model": "gemini-2.0-flash",
        "chatbot": ChatBotGeminiSimple,
        "output_format": "text"
    },
    
    "gemini-lite": {
        "model": "gemini-2.0-flash-lite",
        "chatbot": ChatBotGeminiSimple,
        "output_format": "text"
    }
}

class ModelInfo:
    def __init__(self, model_name: str):
        self.model_info = _model_info.get(model_name)
        if not self.model_info:
            raise ValueError(f"Model {model_name} not available.")
    
    def model(self) -> str:
        return self.model_info["model"]
    
    def chatbot(self) -> ChatBot:
        return self.model_info["chatbot"]
    
    def output_format(self) -> str:
        return self.model_info["output_format"]