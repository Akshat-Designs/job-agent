import json
import time
from pathlib import Path
from groq import Groq

# 1. Paste the keys from your different Groq accounts here
API_KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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", 
]

# Set up the initial client
current_key_index = 0
client = Groq(api_key=API_KEYS[current_key_index])

ROOT = Path(__file__).resolve().parents[1]
FACTS_PATH = ROOT / "resume" / "facts.json"
MASTER_RESUME_PATH = ROOT / "resume" / "master.md"
JOBS_JSON_PATH = ROOT / "jobs.json"
OUTPUT_PATH = ROOT / "data" / "scored_jobs.json"

def load_source_material():
    with open(FACTS_PATH, "r", encoding="utf-8") as f:
        facts = f.read()
    with open(MASTER_RESUME_PATH, "r", encoding="utf-8") as f:
        resume = f.read()
    return facts, resume

def load_scraped_jobs():
    if not JOBS_JSON_PATH.exists():
        print(f"⚠️ Error: {JOBS_JSON_PATH} not found. Run scraper.py first!")
        return []
    with open(JOBS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def score_job_with_ai(job, facts_json, master_resume):
    global current_key_index, client
    
    prompt = f"""You are a careful job-match analyst.

Use only the candidate facts and master resume provided. Do not infer unlisted experience.

Return valid JSON only, with exactly these keys:
score (integer 0-100), decision (apply|review|skip), matched_skills (array), missing_requirements (array), concerns (array), rationale (string).

Scoring guide:
- 80-100: strong evidence of fit.
- 65-79: plausible but needs human review.
- Below 65: usually skip.
- A required skill absent from the candidate facts must be listed as missing.

CANDIDATE FACTS:
{facts_json}

MASTER RESUME:
{master_resume}

JOB:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Description: {job.get('description', 'N/A')}
"""
    
    max_retries = len(API_KEYS)
    attempts = 0
    
    while attempts < max_retries:
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.1
            )
            output = chat_completion.choices[0].message.content.strip()
            
            if output.startswith("```json"):
                output = output[7:]
            if output.endswith("```"):
                output = output[:-3]
                
            return json.loads(output.strip())
            
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "rate limit" in error_msg:
                print(f"\n⚠️ Account {current_key_index + 1} exhausted its free tokens.")
                current_key_index += 1
                
                if current_key_index < len(API_KEYS):
                    print(f"🔄 Switching to Account {current_key_index + 1}...")
                    client = Groq(api_key=API_KEYS[current_key_index])
                    attempts += 1
                    time.sleep(2)
                    continue 
                else:
                    print("❌ All provided API keys have been exhausted for today!")
                    return "RATE_LIMIT_EXHAUSTED"
            else:
                job_title = job.get('title', 'Unknown Job')
                print(f"Failed to score job '{job_title}' due to error: {e}")
                return None

def main():
    facts, resume = load_source_material()
    all_scraped_jobs = load_scraped_jobs()
    
    if not all_scraped_jobs:
        return
        
    # 1. Load previously scored jobs to build a memory of what's already done
    existing_scored_jobs = []
    scored_urls = set()
    
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            try:
                existing_scored_jobs = json.load(f)
                scored_urls = {job.get("url") for job in existing_scored_jobs if job.get("url")}
            except json.JSONDecodeError:
                pass # File is empty or corrupted, start fresh

    # 2. Filter the raw scrape list to ONLY include jobs we haven't scored yet
    unscored_jobs = [job for job in all_scraped_jobs if job.get("url") not in scored_urls]
    
    if not unscored_jobs:
        print("✅ All scraped jobs have already been scored. Run your scraper to find more!")
        return
        
    # 3. Apply the Batch Limit (120 Jobs)
    BATCH_LIMIT = 120
    jobs_to_score = unscored_jobs[:BATCH_LIMIT]
    
    print(f"📊 Found {len(unscored_jobs)} unscored jobs in queue.")
    print(f"🚀 Processing a batch of {len(jobs_to_score)} to protect API rate limits...")
    
    newly_scored_results = []
    for index, job in enumerate(jobs_to_score):
        print(f"[{index + 1}/{len(jobs_to_score)}] Scoring: {job.get('title')} at {job.get('company')}...")
        
        if 'description' not in job:
            job['description'] = f"{job.get('title')} position at {job.get('company')}. Location: {job.get('location')}."
            
        try:
            ai_score = score_job_with_ai(job, facts, resume)
            
            if ai_score == "RATE_LIMIT_EXHAUSTED":
                print("\n🛑 Halting batch processing to save progress before keys reset.")
                break
                
            if ai_score:
                job['ai_analysis'] = ai_score
                newly_scored_results.append(job)
            
            time.sleep(2.5) 
        except Exception as e:
            print(f"Skipping role due to critical processing error: {e}")
            continue

    # 4. Append the new results to the existing ones and save
    existing_scored_jobs.extend(newly_scored_results)
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(existing_scored_jobs, f, indent=4, ensure_ascii=False)
        
    print(f"\n🎉 Successfully processed {len(newly_scored_results)} roles! Saved output to {OUTPUT_PATH}")
    if len(unscored_jobs) > BATCH_LIMIT:
        remaining = len(unscored_jobs) - len(newly_scored_results)
        print(f"⏳ {remaining} jobs remain in the queue. Run this script again tomorrow (or when your keys reset) to continue.")

if __name__ == "__main__":
    main()