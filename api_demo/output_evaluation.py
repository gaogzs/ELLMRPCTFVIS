import os
import json
from matplotlib import pyplot as plt

cur_dir = os.path.dirname(__file__)

visual_dir_rel = "visualisations"
visual_dir = os.path.join(cur_dir, visual_dir_rel)

summarising_metrics = ["average", "total", "final"]

def single_value_scoring_by_prompts(dir, score_keyword, store_keyword=""):
    filename = dir.split(".")[0]
    output_log = []
    prompts_dir = os.path.join(cur_dir, dir)
    eval_hists = []
    with open(prompts_dir, "r") as f:
        eval_hists = json.load(f)
    
    # Iterate through the evaluation history
    score_hists = []
    i = 0
    for eval_hist in eval_hists:
        score_hists.append([])
        for eval_item in eval_hist:
            score_hists[i].append(eval_item[score_keyword])
        i += 1
    
    # Plot the scores in a line graph
    for prompt_index, scores in zip(range(len(score_hists)), score_hists):
        plt.plot(scores, label=prompt_index)
    plt.legend()
    
    if store_keyword == "":
        plt.savefig(os.path.join(visual_dir, f"{filename}_{score_keyword}_line_graph.png"))
    else:
        plt.savefig(os.path.join(visual_dir, f"{filename}_{store_keyword}_{score_keyword}_line_graph.png"))

def multi_value_scoring(dir, score_keyword, metrics_used=["average"], store_keyword=""):
    filename = dir.split(".")[0]
    output_log = []
    prompts_dir = os.path.join(cur_dir, dir)
    eval_hists = []
    with open(prompts_dir, "r") as f:
        eval_hists = json.load(f)
    
    i = 0
    for eval_hist in eval_hists:
        plt.figure()
        if metrics_used is None:
            metrics_used = [metric for metric in eval_hist[0][score_keyword].keys() if isinstance(eval_hist[0][score_keyword][metric], (int, float))]
        # Iterate through the evaluation history
        score_hists = {}
        for metric in metrics_used:
            score_hists[metric] = []
            for eval_item in eval_hist:
                score_hists[metric].append(eval_item[score_keyword][metric])

        # Plot the scores in a line graph
        for metric in metrics_used:
            if metric  in summarising_metrics:
                plt.plot(score_hists[metric], label=metric, linewidth=3)
            else:
                plt.plot(score_hists[metric], label=metric, linewidth=1)
        plt.legend(fontsize='small', framealpha=0.5)
        
        if len(eval_hists) > 1:
            store_filename = f"{filename}_{i}"
        
        if store_keyword == "":
            plt.savefig(os.path.join(visual_dir, f"{store_filename}_{score_keyword}_line_graph.png"))
        else:
            plt.savefig(os.path.join(visual_dir, f"{store_filename}_{store_keyword}_{score_keyword}_line_graph.png"))
            
        i += 1
    

if __name__ == "__main__":
    multi_value_scoring(dir="output_subjective-identifying_1_shot.json", score_keyword="chat_evaluation", metrics_used=None)