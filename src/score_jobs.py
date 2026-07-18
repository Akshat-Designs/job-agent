import json
import time
from pathlib import Path
from groq import Groq
from database import connect

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

def load_source_material():
    with open(FACTS_PATH, "r", encoding="utf-8") as f:
        facts = f.read()
    with open(MASTER_RESUME_PATH, "r", encoding="utf-8") as f:
        resume = f.read()
    return facts, resume

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
Title: {job['title']}
Company: {job['company']}
Description: {job['description']}
"""
    
    max_retries = len(API_KEYS)
    attempts = 0
    
    while attempts < max_retries:
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile", # Change to "llama-3.1-8b-instant" if you prefer Option 1
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
            # If we hit the rate limit, trigger the automatic key rotation
            if "429" in error_msg or "rate limit" in error_msg:
                print(f"\n⚠️ Account {current_key_index + 1} exhausted its free tokens.")
                current_key_index += 1
                
                if current_key_index < len(API_KEYS):
                    print(f"🔄 Switching to Account {current_key_index + 1}...")
                    client = Groq(api_key=API_KEYS[current_key_index])
                    attempts += 1
                    time.sleep(2)
                    continue # Retry the exact same job with the new key
                else:
                    print("❌ All provided API keys have been exhausted for today!")
                    return None
            else:
                print(f"Failed to score job {job['id']} due to error: {e}")
                return None

def main():
    facts_json, master_resume = load_source_material()
    connection = connect()
    
    # 2. Increased the batch limit to 100 jobs per run
    cursor = connection.execute("SELECT * FROM jobs WHERE status = 'ready_for_scoring' LIMIT 100")
    jobs_to_score = cursor.fetchall()
    
    print(f"Found {len(jobs_to_score)} jobs. Starting batch processing...")
    
    for job in jobs_to_score:
        job_dict = dict(job)
        print(f"Scoring: {job_dict['title']} at {job_dict['company']}...")
        
        result = score_job_with_ai(job_dict, facts_json, master_resume)
        
        # 3. Added a pacing delay so you don't overwhelm the Groq servers
        time.sleep(2.5) 
        
        if result:
            connection.execute(
                """
                UPDATE jobs 
                SET status = ?, score = ?, notes = ? 
                WHERE id = ?
                """,
                (
                    result.get("decision", "review"),
                    result.get("score", 0),
                    json.dumps(result, ensure_ascii=False),
                    job_dict['id']
                )
            )
    
    connection.commit()
    connection.close()
    print("AI scoring loop finished.")

if __name__ == "__main__":
    main()