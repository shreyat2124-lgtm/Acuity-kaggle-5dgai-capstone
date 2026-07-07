import os
import sys
import json
from dotenv import load_dotenv
from google import genai

# Add parent directory to path so we can import agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import TriageAgents

def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    triage_system = TriageAgents(client)
    
    vignettes_path = os.path.join(os.path.dirname(__file__), "vignettes.json")
    results_path = os.path.join(os.path.dirname(__file__), "results.txt")
    
    with open(vignettes_path, "r") as f:
        vignettes = json.load(f)
        
    total = len(vignettes)
    correct = 0
    dangerous_misses = 0
    
    tier_levels = {"NORMAL": 1, "URGENT": 2, "EMERGENCY": 3}
    
    results_output = []
    
    import time
    for i, v in enumerate(vignettes):
        print(f"Evaluating vignette {i+1}/{total}...")
        text = v["text"]
        expected = v["correct_tier"]
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = triage_system.run_pipeline(text)
                predicted = result.priority
                
                is_correct = (predicted == expected)
                is_dangerous_miss = tier_levels.get(predicted, 0) < tier_levels.get(expected, 0)
                
                if is_correct:
                    correct += 1
                if is_dangerous_miss:
                    dangerous_misses += 1
                    
                res_str = (f"Vignette {i+1} ({v['type']}):\n"
                           f"Text: {text}\n"
                           f"Expected: {expected} | Predicted: {predicted}\n"
                           f"Reasoning: {result.reasoning}\n"
                           f"Counterfactual: {result.counterfactual}\n"
                           f"Correct: {is_correct} | Dangerous Miss: {is_dangerous_miss}\n"
                           f"-"*40)
                results_output.append(res_str)
                time.sleep(4) # Slight delay to avoid base limits
                break # Success
            except Exception as e:
                err_msg = str(e)
                if '429' in err_msg and attempt < max_retries - 1:
                    print(f"Rate limit hit. Waiting 15 seconds before retry...")
                    time.sleep(15)
                else:
                    err_str = f"Vignette {i+1} failed: {e}"
                    print(err_str)
                    results_output.append(err_str)
                    break
            
    accuracy = correct / total
    dangerous_miss_rate = dangerous_misses / total
    
    summary = (f"\n=== EVALUATION SUMMARY ===\n"
               f"Total Vignettes: {total}\n"
               f"Overall Accuracy: {accuracy:.1%}\n"
               f"Dangerous Miss Rate: {dangerous_miss_rate:.1%}\n"
               f"==========================\n")
               
    results_output.append(summary)
    
    print(summary)
    
    with open(results_path, "w") as f:
        f.write("\n".join(results_output))
        
    print(f"Full results written to {results_path}")

if __name__ == "__main__":
    main()
