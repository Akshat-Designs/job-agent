import json
from pathlib import Path
from database import insert_job, connect

ROOT = Path(__file__).resolve().parents[1]
RAW_GREENHOUSE = ROOT / "data" / "greenhouse_jobs.json"

def main():
    if not RAW_GREENHOUSE.exists():
        print("No greenhouse_jobs.json file found to import.")
        return

    with open(RAW_GREENHOUSE, "r", encoding="utf-8") as file:
        try:
            jobs = json.load(file)
        except json.JSONDecodeError:
            print("Error reading the JSON file.")
            return

    connection = connect()
    count_before = connection.execute("SELECT count(*) FROM jobs").fetchone()[0]
    connection.close()

    for job in jobs:
        insert_job(job)

    connection = connect()
    count_after = connection.execute("SELECT count(*) FROM jobs").fetchone()[0]
    connection.close()
    
    print(f"Processed {len(jobs)} jobs from collectors.")
    print(f"Imported {count_after - count_before} new unique jobs into the database.")

if __name__ == "__main__":
    main()