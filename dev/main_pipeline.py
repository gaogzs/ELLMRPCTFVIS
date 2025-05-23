import os
import json

from config import ModelInfo
from fol_evaluator import FOLEvaluationSession
from timeline_maker import TimelineMakerSession

cur_dir = os.path.dirname(os.path.abspath(__file__))
prompt_dir = os.path.join(cur_dir, "prompts")
schema_dir = os.path.join(cur_dir, "schemas")
input_template_dir = os.path.join(cur_dir, "input_templates")

timeline_model_info = ModelInfo("gemini-structured")
timeline_session = TimelineMakerSession(timeline_model_info, prompt_dir=prompt_dir, schema_dir=schema_dir, input_template_dir=input_template_dir)

fol_model_info = ModelInfo("gemini-structured")
fol_session = FOLEvaluationSession(fol_model_info, prompt_dir=prompt_dir, schema_dir=schema_dir, input_template_dir=input_template_dir)

sample_conversation = []
with open(os.path.join(cur_dir, "sample_rp.json"), "r", encoding="utf-8") as f:
    sample_conversations = json.load(f)
    sample_conversation = sample_conversations[-1]
    
for section in sample_conversation:
    timeline_session.append_conversation(section)
    new_timeline = timeline_session.get_timeline()
    fol_session.append_conversation(section, new_timeline=new_timeline)
    fol_session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))
    