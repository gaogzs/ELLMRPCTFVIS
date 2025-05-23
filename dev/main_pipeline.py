import os
import json

from config import ModelInfo
from fol_evaluator import RPEvaluationSession

cur_dir = os.path.dirname(os.path.abspath(__file__))
prompt_dir = os.path.join(cur_dir, "prompts")
schema_dir = os.path.join(cur_dir, "schemas")

fol_model_info = ModelInfo("gemini-structured")
fol_session = RPEvaluationSession(fol_model_info, prompt_dir=prompt_dir, schema_dir=schema_dir)

sample_conversation = []
with open(os.path.join(cur_dir, "sample_rp.json"), "r", encoding="utf-8") as f:
    sample_conversations = json.load(f)
    sample_conversation = sample_conversations[-1]
    
for section in sample_conversation:
    fol_session.append_conversation(section)
    fol_session.export_logs(os.path.join(cur_dir, "sample_rp_log.json"))
    