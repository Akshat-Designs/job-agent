import csv
import json
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
COMPANIES = ROOT / "data" / "companies.csv"
RAW = ROOT / "data" / "greenhouse_jobs.json"


def get_greenhouse_jobs(token: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    jobs = []
    for job in response.json().get("jobs", []):
        jobs.append({
            "source": "greenhouse",
            "external_id": str(job["id"]),
            "title": job.get("title", ""),
            "company": token,
            "location": (job.get("location") or {}).get("name", ""),
            "description": job.get("content", ""),
            "url": job.get("absolute_url", ""),
            "posted_date": job.get("updated_at", "")
        })
    return jobs


def main():
    collected = []
    with COMPANIES.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if row.get("ats_type", "").lower() != "greenhouse":
                continue
            try:
                collected.extend(get_greenhouse_jobs(row["board_token"]))
            except requests.RequestException as error:
                print(f"Could not collect {row['company']}: {error}")
    RAW.write_text(json.dumps(collected, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(collected)} Greenhouse jobs to {RAW}")


if __name__ == "__main__":
    main()