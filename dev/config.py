from api_wrapper.chatbot import ChatBot, ChatBotDeepSeekSimple, ChatBotGeminiSimple, ChatBotGPTSimple, ChatBotClaudeSimple

_PRINT_WARNING = False
_PRINT_DEV_MESSAGE = True
_ERROR_RETRIES = 10



def print_warning_message(message):
    global _PRINT_WARNING
    if _PRINT_WARNING:
        print(message)

def print_dev_message(*args, **kwargs):
    global _PRINT_DEV_MESSAGE
    if _PRINT_DEV_MESSAGE:
        print(*args, **kwargs)

_model_info = {
    "deepseek-chat": {
        "model": "deepseek-chat",
        "chatbot": ChatBotDeepSeekSimple,
        "output_format": "text"
    },
    
    "deepseek-structured": {
        "model": "deepseek-chat",
        "chatbot": ChatBotDeepSeekSimple,
        "output_format": "json"
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
    },
    
    "gemini-structured": {
        "model": "gemini-2.0-flash",
        "chatbot": ChatBotGeminiSimple,
        "output_format": "json"
    },
    
    "gemini-lite-structured": {
        "model": "gemini-2.0-flash-lite",
        "chatbot": ChatBotGeminiSimple,
        "output_format": "json"
    },
    
    "gpt-structured": {
        "model": "gpt-4.1",
        "chatbot": ChatBotGPTSimple,
        "output_format": "json"
    },
    
    "gpt-mini-structured": {
        "model": "gpt-4.1-mini",
        "chatbot": ChatBotGPTSimple,
        "output_format": "json"
    },
    
    "claude-sonnet-structured": {
        "model": "claude-sonnet-4-20250514",
        "chatbot": ChatBotClaudeSimple,
        "output_format": "json"
    },
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