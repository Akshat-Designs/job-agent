import json
import datetime
from pathlib import Path
import ollama
from database import connect

ROOT = Path(__file__).resolve().parents[1]
MASTER_RESUME_PATH = ROOT / "resume" / "master.md"
COVER_TEMPLATE_PATH = ROOT / "resume" / "cover_letter_template.md"
TAILORED_DIR = ROOT / "tailored"

def load_templates():
    with open(MASTER_RESUME_PATH, "r", encoding="utf-8") as f:
        resume = f.read()
    with open(COVER_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        cover = f.read()
    return resume, cover

def generate_tailored_resume(job, master_resume):
    prompt = f"""Create a targeted resume in Markdown using only the supplied master resume.

Allowed actions:
- Reorder existing skills and bullets.
- Rewrite wording while preserving exact factual meaning.
- Select the most relevant existing projects and experience.
- Use job-description terminology only when it accurately describes a verified fact.

Forbidden actions:
- Add any employer, title, date, metric, certification, degree, project, tool, responsibility, or skill that is not supported by the source material.
- Claim proficiency where no evidence exists.
- Omit a required factual qualification merely to make the match look stronger.
- DO NOT invent or alter metrics or numbers.

MASTER RESUME:
{master_resume}

JOB DESCRIPTION:
Title: {job['title']}
Company: {job['company']}
Description: {job['description']}
"""
    response = ollama.chat(
        model='qwen3:8b',
        messages=[{'role': 'user', 'content': prompt}],
        options={'temperature': 0.2}
    )
    return response['message']['content']

def generate_tailored_cover_letter(job, cover_template):
    prompt = f"""You are a precise corporate writing assistant. Your task is to fill in the placeholders of a cover letter template.

You must only change two elements:
1. Replace standard variables: [Date], [Hiring Team / Recruiter Name], [Company Name], and [Program / Role Title].
2. Replace the [INSERT_FIRM_CONNECTION_LINE] placeholder with exactly ONE flowing, formal sentence connecting the target firm's public operations/mandate to the applicant's background. 

Do not add any details about the applicant's experience, skills, metrics, or education that are not already present in the baseline template. Keep the tone identical.

COVER LETTER TEMPLATE:
{cover_template}

JOB DETAILS:
Title: {job['title']}
Company: {job['company']}
Description: {job['description']}
"""
    response = ollama.chat(
        model='qwen3:8b',
        messages=[{'role': 'user', 'content': prompt}],
        options={'temperature': 0.1}
    )
    return response['message']['content']

def main():
    resume_tmpl, cover_tmpl = load_templates()
    connection = connect()
    
    cursor = connection.execute("SELECT * FROM jobs WHERE status = 'apply'")
    approved_jobs = cursor.fetchall()
    
    print(f"Generating documents for {len(approved_jobs)} applications...")
    
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    for job in approved_jobs:
        job_dict = dict(job)
        safe_company = "".join(x for x in job_dict['company'] if x.isalnum())
        safe_title = "".join(x for x in job_dict['title'] if x.isalnum())[:20]
        
        print(f"Drafting tailoring package for {job_dict['title']} at {job_dict['company']}...")
        
        # 1. Custom Resume
        tailored_cv = generate_tailored_resume(job_dict, resume_tmpl)
        cv_path = TAILORED_DIR / f"{date_str}_{safe_company}_{safe_title}_CV.md"
        cv_path.write_text(tailored_cv, encoding="utf-8")
        
        # 2. Custom Cover Letter
        tailored_cl = generate_tailored_cover_letter(job_dict, cover_tmpl)
        cl_path = TAILORED_DIR / f"{date_str}_{safe_company}_{safe_title}_CL.md"
        cl_path.write_text(tailored_cl, encoding="utf-8")
        
        # Update state to avoid rebuilding on subsequent runs
        connection.execute("UPDATE jobs SET status = 'documents_drafted' WHERE id = ?", (job_dict['id'],))
        
    connection.commit()
    connection.close()
    print("Asset execution complete.")

if __name__ == "__main__":
    main()