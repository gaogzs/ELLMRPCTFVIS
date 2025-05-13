import json


def is_in_openai_form(message: str) -> bool:
    
    if message.startswith("{") and message.endswith("}"):
        try:
            message_json = json.loads(message)
            if type(message_json) == list and "role" in message_json[0] and "content" in message_json[0]:
                return True
        except json.JSONDecodeError:
            return False
    return False
  

def openai_form_to_str(message: str) -> str:
    message_json = json.loads(message)
    message_str = ""
    for message in message_json:
        role = message["role"]
        if role == "assistant":
            message_str += message['content'] + "\n"
        elif role == "user":
            message_str += "(User: " + message['content'] + ")"
    return message_str