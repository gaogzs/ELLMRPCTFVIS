import os
import json

from config import ModelInfo
from fol_evaluator import FOLEvaluationSession
from timeline_maker import TimelineMakerSession
from outline_evaluator import OutlineEvaluatorSession

cur_dir = os.path.dirname(os.path.abspath(__file__))
def do_one_run_fol(target_narrative: list[str], model: str) -> None:
    prompt_dir = os.path.join(cur_dir, "prompts")
    schema_dir = os.path.join(cur_dir, "schemas")
    input_template_dir = os.path.join(cur_dir, "input_templates")

    using_model_info = ModelInfo(model)

    timeline_session = TimelineMakerSession(using_model_info, prompt_dir=prompt_dir, schema_dir=schema_dir, input_template_dir=input_template_dir)
    fol_session = FOLEvaluationSession(using_model_info, prompt_dir=prompt_dir, schema_dir=schema_dir, input_template_dir=input_template_dir)
    
    for section in target_narrative:
        timeline_session.append_conversation(section)
        new_timeline = timeline_session.get_timeline()
        fol_session.append_conversation(section, new_timeline=new_timeline)
        fol_session.export_logs(os.path.join(cur_dir, "sample_fol_log2.json"))

def do_one_run_outline(target_narrative: list[str], model: str, similarity_model: str) -> None:
    prompt_dir = os.path.join(cur_dir, "prompts")
    schema_dir = os.path.join(cur_dir, "schemas")
    input_template_dir = os.path.join(cur_dir, "input_templates")

    using_model_info = ModelInfo(model)

    outline_session = OutlineEvaluatorSession(using_model_info, similarity_model, prompt_dir=prompt_dir, schema_dir=schema_dir, input_template_dir=input_template_dir)
    
    for section in target_narrative:
        outline_session.append_conversation(section)
        outline_session.export_logs(os.path.join(cur_dir, "sample_outline_log.json"))

if __name__ == "__main__":
    sample_conversation = []
    with open(os.path.join(cur_dir, "sample_rp.json"), "r", encoding="utf-8") as f:
        sample_conversations = json.load(f)
        sample_conversation = sample_conversations[-1]
    
    using_model = "gemini-structured"
    similarity_model = "all-MiniLM-L6-v2"
    
    do_one_run_fol(sample_conversation, using_model)
    #do_one_run_outline(sample_conversation, using_model, similarity_model)
    print("Pipeline run completed.")
    
    