from datasets import load_dataset
import json
import os

def build_knowledge():
    print("Fetching financial data from Hugging Face FinanceBench...")
    
    # 1. Load FinanceBench - Best for 10-K factual data
    #    Streaming=True: avoid downloading the whole huge dataset at once
    dataset = load_dataset("PatronusAI/financebench", split='train', streaming=True)

    knowledge_base = {
        "industry_benchmarks": {
            "SaaS": {"target_gross_margin": 0.75, "target_rule_of_40": 0.40},
            "Retail": {"target_inventory_turnover": 6.0, "target_operating_margin": 0.10}
        },
        "peer_examples": []
    }

    # 2. Extract real peer data points
    count = 0
    for entry in dataset:
        if count >= 1000: break
        
        # We extract the company and the verified answer to a financial question
        knowledge_base["peer_examples"].append({
            "company": entry.get("company", "N/A"),
            "context": entry.get("question", ""),
            "fact": entry.get("answer", "")
        })
        count += 1

    # 3. Save to the project root so main.py can find it
    output_path = 'knowledge.json'
    with open(output_path, 'w') as f:
        json.dump(knowledge_base, f, indent=4)
    
    print(f"Success! {output_path} created with real-world financial benchmarks.")

if __name__ == "__main__":
    build_knowledge()