import json
from pathlib import Path
from database import connect

ROOT = Path(__file__).resolve().parents[1]
FACTS_PATH = ROOT / "resume" / "facts.json"

def load_preferences():
    with open(FACTS_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)
        return data.get("preferences", {})

def basic_decision(job, preferences):
    # Combine title and description for a fast keyword search
    text = f"{job['title']} {job['description']}".lower()
    
    # Check if the job title matches any of our targets
    targets = [x.lower() for x in preferences.get('target_titles', [])]
    if not any(target in job['title'].lower() for target in targets):
        return "rejected_title"
        
    # Check for excluded red-flag keywords
    excluded = preferences.get('excluded_keywords', [])
    if any(word.lower() in text for word in excluded):
        return "rejected_keyword"
        
    # If it passes the fast filters, it goes to the AI
    return "ready_for_scoring"

def main():
    preferences = load_preferences()
    connection = connect()
    
    # Get all jobs that haven't been filtered yet
    cursor = connection.execute("SELECT * FROM jobs WHERE status = 'new'")
    new_jobs = cursor.fetchall()
    
    processed_count = 0
    for job in new_jobs:
        # Convert sqlite3.Row to a standard dictionary
        job_dict = dict(job)
        decision = basic_decision(job_dict, preferences)
        
        # Update the database with the new status
        connection.execute(
            "UPDATE jobs SET status = ? WHERE id = ?", 
            (decision, job['id'])
        )
        processed_count += 1
        
    connection.commit()
    connection.close()
    
    print(f"Applied basic filters to {processed_count} new jobs.")

if __name__ == "__main__":
    main()