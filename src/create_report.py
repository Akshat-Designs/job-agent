import datetime
from pathlib import Path
import json
from database import connect

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
TAILORED_DIR = ROOT / "tailored"

def main():
    connection = connect()
    # Fetch jobs that were scored highly or have drafted documents
    cursor = connection.execute(
        "SELECT * FROM jobs WHERE status IN ('apply', 'documents_drafted', 'review') ORDER BY score DESC"
    )
    jobs = cursor.fetchall()
    
    if not jobs:
        print("No high-priority jobs to report today.")
        return
        
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"{date_str}-job-review.md"
    
    lines = [f"# Daily Job Agent Report — {date_str}\n"]
    
    for job in jobs:
        job_dict = dict(job)
        notes = {}
        if job_dict.get('notes'):
            try:
                notes = json.loads(job_dict['notes'])
            except:
                pass
                
        lines.append(f"## {job_dict['title']} @ {job_dict['company']}")
        lines.append(f"- **Score:** {job_dict['score']}/100")
        lines.append(f"- **Status:** {job_dict['status'].upper()}")
        lines.append(f"- **URL:** [Link]({job_dict['url']})")
        
        if notes.get('rationale'):
            lines.append(f"- **AI Rationale:** {notes['rationale']}")
            
        if notes.get('missing_requirements'):
            lines.append(f"- **Missing:** {', '.join(notes['missing_requirements'])}")
            
        # Check if drafts exist
        safe_company = "".join(x for x in job_dict['company'] if x.isalnum())
        safe_title = "".join(x for x in job_dict['title'] if x.isalnum())[:20]
        cv_name = f"{date_str}_{safe_company}_{safe_title}_CV.md"
        
        if (TAILORED_DIR / cv_name).exists():
            lines.append(f"- **Draft Available:** `tailored/{cv_name}`")
            
        lines.append("\n---\n")
        
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated daily review report at: {report_path}")
    connection.close()

if __name__ == "__main__":
    main()