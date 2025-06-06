import os
import pandas as pd

from config import ModelInfo
from utils.loaders import PromptLoader, SchemaLoader, InputTemplateLoader

def baseline_evaluator(model_info, input_narrative, input_template_dir, schema_dir):
    input_template = input_template_loader.load("consistency_evaluator_baseline")
    message = input_template.format(target_story=input_narrative)
    
    if model_info.output_format() == "json":
        bot = model_info.chatbot()(model_info.model(), "", schema_loader)
        text_response, json_response = bot.get_structured_response(message, schema_key="consistency_evaluator_baseline", record=False, temperature=0)
        consistency_score = json_response["consistency"]
    else:
        raise ValueError(f"Unsupported output format: {model_info.output_format()}")

    return consistency_score