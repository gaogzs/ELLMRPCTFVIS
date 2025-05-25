
from config import print_warning_message, print_dev_message, ModelInfo, _ERROR_RETRIES
from utils.loaders import PromptLoader, SchemaLoader, InputTemplateLoader
from utils.regex import divide_response_parts
from utils.utils import *

class TimelineMakerSession:
    def __init__(self, model_info: ModelInfo, prompt_dir: str, schema_dir: str, input_template_dir: str) -> None:
        prompt_loader = PromptLoader(prompt_dir)
        schema_loader = SchemaLoader(schema_dir)
        input_template_loader = InputTemplateLoader(input_template_dir)
        
        
        self.model_info = model_info
        self.prompt_loader = prompt_loader
        self.output_schema = schema_loader.load_output_schema("timeline_maker")
        self.input_template_loader = input_template_loader
        
        self.chatbot = self.model_info.chatbot()
        self.timeline = {}
        self.rp_history = []
        self.logs = []
    
    def get_timeline(self) -> dict:
        return self.timeline.copy()
    
    def get_timeline_str(self) -> str:
        return dict_pretty_str(self.timeline)
    
    def get_timeline_schema_form(self) -> dict:
        out_dict = [{"time_point_name": time_point_name, "time_point_description": time_point_description} for time_point_name, time_point_description in self.timeline.items()]
        return out_dict
    
    def append_conversation(self, lastest_conversation: str) -> None:
        new_timeline, timeline_text = self.handle_new_section(lastest_conversation)
        
        self.rp_history.append(lastest_conversation)
        self.timeline.update(new_timeline)
        self.logs.append({"conversation": lastest_conversation, "timeline": new_timeline})
        
    def handle_new_section(self, lastest_conversation: str) -> tuple[dict, str]:
        
            
        message = self.input_template_loader.load("timeline_maker").format(story=lastest_conversation)
        
        processed_success = False
        tries_count = _ERROR_RETRIES
        
        if self.model_info.output_format() == "json":
            sys_prompt = self.prompt_loader.load_sys_prompts("timeline_maker_json")
            bot = self.chatbot(self.model_info.model(), sys_prompt)
            if self.rp_history:
                bot.add_fake_user_message("\n".join(self.rp_history))
                fake_json_message = {
                    "reasoning": "[Hidden]",
                    "timeline_definition": self.get_timeline_schema_form()
                }
                bot.add_fake_model_message(str(fake_json_message))
            text_response, json_response = bot.get_structured_response(message, self.output_schema, record=True, temperature=0.2)
            print_dev_message("Timeline Maker Response:")
            print_dev_message(text_response)
            
            while not processed_success:
                try:
                    new_timeline = self.parse_timeline_declarations_json(json_response)
                    timeline_text = str(json_response["timeline_definition"])
                    processed_success = True
                except Exception as e:
                    error_message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                    print_dev_message("Error in response division:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        print_dev_message("Error: Too many failing responses.")
                        exit(1)
                        
                    text_response, json_response = bot.get_structured_response(error_message, self.output_schema, record=True, temperature=0.2)
                    print_dev_message("Retry with:\n")
                    print_dev_message(text_response)
        else:
            sys_prompt = self.prompt_loader.load_sys_prompts("timeline_maker_json")
            bot = self.chatbot(self.model_info.model(), sys_prompt)
            if self.rp_history:
                bot.add_fake_user_message("\n".join(self.rp_history))
                bot.add_fake_model_message("-- **Reasoning**\n[Hidden]\n-- **Timeline Definitions**\n" + self.get_timeline_str())
            complete_response = bot.send_message(message, record=True, temperature=0.2)
            print_dev_message("Timeline Maker Response:")
            print_dev_message(complete_response)
            
            while not processed_success:
                try:
                    reasoning_text, timeline_text = divide_response_parts(complete_response)
                    processed_success = True
                    # Parse the timeline
                    new_timeline = self.parse_timeline_declarations(timeline_text)
                except Exception as e:
                    error_message = self.input_template_loader.load("complete_error_correction").format(error_message=str(e))
                    print_dev_message("Error in response division:", e)
                    tries_count -= 1
                    if tries_count <= 0:
                        print_dev_message("Error: Too many failing responses.")
                        exit(1)
                        
                    complete_response = bot.send_message(error_message, record=True, temperature=0.2)
                    print_dev_message("Retry with:\n")
                    print_dev_message(complete_response)
        
        
        return new_timeline, timeline_text
        
    def parse_timeline_declarations(self, timeline_text: str) -> dict:
        new_timeline = {}
        for definition_line in timeline_text.splitlines():
            if ":" in definition_line:
                time_point_name, time_point_description = definition_line.split(":", 1)
                time_point_name = time_point_name.strip()
                time_point_description = time_point_description.strip()
                if time_point_name in self.timeline:
                    print_warning_message(f"Warning: {time_point_name} already exists in timeline.")
                new_timeline[time_point_name] = time_point_description

        return new_timeline
    
    def parse_timeline_declarations_json(self, timeline_json: dict) -> dict:
        new_timeline = {}
        for definition_line in timeline_json["timeline_definition"]:
            time_point_name = definition_line["time_point_name"]
            time_point_description = definition_line["time_point_description"]
            if time_point_name in self.timeline:
                print_warning_message(f"Warning: {time_point_name} already exists in timeline.")
            new_timeline[time_point_name] = time_point_description

        return new_timeline