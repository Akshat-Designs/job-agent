import json
from pathlib import Path

# Setup paths
ROOT = Path(__file__).resolve().parents[1]
SCORED_JOBS_PATH = ROOT / "data" / "scored_jobs.json"
TO_APPLY_PATH = ROOT / "data" / "to_apply.json"

def main():
    if not SCORED_JOBS_PATH.exists():
        print(f"⚠️ Error: {SCORED_JOBS_PATH} not found. Please run score_jobs.py first.")
        return

    with open(SCORED_JOBS_PATH, "r", encoding="utf-8") as file:
        scored_jobs = json.load(file)
    
    print(f"Found {len(scored_jobs)} scored jobs. Applying strict >= 75 filter and checking redundancies...")

    top_tier_jobs = []
    seen_urls = set()

    for job in scored_jobs:
        # Safely extract the score from the ai_analysis block
        ai_analysis = job.get("ai_analysis", {})
        
        try:
            score = int(ai_analysis.get("score", 0))
        except (ValueError, TypeError):
            score = 0
            
        url = job.get("url", "")

        # Strict filter: Must be 75 or higher, and must not be a duplicate URL
        if score >= 75 and url not in seen_urls:
            top_tier_jobs.append(job)
            seen_urls.add(url)
            
    # Sort the final list by score descending (so the 95s and 90s are at the top)
    top_tier_jobs.sort(key=lambda x: int(x.get("ai_analysis", {}).get("score", 0)), reverse=True)

    # Save the polished shortlist
    TO_APPLY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TO_APPLY_PATH, "w", encoding="utf-8") as file:
        json.dump(top_tier_jobs, file, indent=4, ensure_ascii=False)

    print(f"✅ Filtering complete! Eliminated {len(scored_jobs) - len(top_tier_jobs)} low-match or duplicate roles.")
    print(f"🎯 Secured {len(top_tier_jobs)} highly qualified jobs (Score 75+).")
    print(f"📁 Shortlist saved to {TO_APPLY_PATH}")

if __name__ == "__main__":
    main()