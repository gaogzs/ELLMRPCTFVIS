import os
import json
from matplotlib import pyplot as plt

cur_dir = os.path.dirname(__file__)

visual_dir_rel = "visualisations"
visual_dir = os.path.join(cur_dir, visual_dir_rel)

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
    

if __name__ == "__main__":
    single_value_scoring_by_prompts(dir="output_hundred.json", score_keyword="reasoner_evaluation")