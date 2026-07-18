import json
import datetime
from pathlib import Path
import ollama
import markdown
from playwright.sync_api import sync_playwright

# Set up paths
ROOT = Path(__file__).resolve().parents[1]
MASTER_RESUME_PATH = ROOT / "resume" / "master.md"
COVER_TEMPLATE_PATH = ROOT / "resume" / "cover_letter_template.md"
TO_APPLY_PATH = ROOT / "data" / "to_apply.json"
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
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Description: {job.get('description', 'N/A')}
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
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Description: {job.get('description', 'N/A')}
"""
    response = ollama.chat(
        model='qwen3:8b',
        messages=[{'role': 'user', 'content': prompt}],
        options={'temperature': 0.1}
    )
    return response['message']['content']

def convert_md_to_pdf(md_text, pdf_path):
    # Convert Markdown to HTML
    html_body = markdown.markdown(md_text)
    
    # Inject professional CSS styling for the PDF
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Arial', sans-serif; line-height: 1.5; color: #000; font-size: 11pt; }}
            h1 {{ font-size: 18pt; text-align: center; border-bottom: 2px solid #000; padding-bottom: 5px; margin-bottom: 15px; }}
            h2 {{ font-size: 14pt; border-bottom: 1px solid #666; margin-top: 15px; padding-bottom: 3px; }}
            h3 {{ font-size: 12pt; margin-bottom: 5px; }}
            ul {{ margin-top: 5px; padding-left: 20px; }}
            li {{ margin-bottom: 4px; }}
            p {{ margin: 8px 0; }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """
    
    # Use Playwright to render the HTML into a PDF
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(full_html)
        page.pdf(
            path=str(pdf_path), 
            format="A4", 
            margin={"top": "0.8in", "bottom": "0.8in", "left": "0.8in", "right": "0.8in"}
        )
        browser.close()

def main():
    if not TO_APPLY_PATH.exists():
        print(f"⚠️ Error: {TO_APPLY_PATH} not found. Run filter_jobs.py first.")
        return

    resume_tmpl, cover_tmpl = load_templates()
    TAILORED_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(TO_APPLY_PATH, "r", encoding="utf-8") as f:
        approved_jobs = json.load(f)
        
    jobs_to_process = [j for j in approved_jobs if not j.get("documents_drafted")]
    
    if not jobs_to_process:
        print("No new jobs to tailor. All approved jobs already have drafted documents.")
        return

    print(f"Generating documents for {len(jobs_to_process)} applications via local Qwen3:8b...")
    
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    for job in jobs_to_process:
        safe_company = "".join(x for x in job.get('company', 'Unknown') if x.isalnum())
        safe_title = "".join(x for x in job.get('title', 'Role') if x.isalnum())[:20]
        
        print(f"\nDrafting tailoring package for {job.get('title')} at {job.get('company')}...")
        
        # 1. Custom Resume (MD & PDF)
        print("  -> Generating Resume...")
        tailored_cv = generate_tailored_resume(job, resume_tmpl)
        cv_md_path = TAILORED_DIR / f"{date_str}_{safe_company}_{safe_title}_CV.md"
        cv_pdf_path = TAILORED_DIR / f"{date_str}_{safe_company}_{safe_title}_CV.pdf"
        
        cv_md_path.write_text(tailored_cv, encoding="utf-8")
        convert_md_to_pdf(tailored_cv, cv_pdf_path)
        
        # 2. Custom Cover Letter (MD & PDF)
        print("  -> Generating Cover Letter...")
        tailored_cl = generate_tailored_cover_letter(job, cover_tmpl)
        cl_md_path = TAILORED_DIR / f"{date_str}_{safe_company}_{safe_title}_CL.md"
        cl_pdf_path = TAILORED_DIR / f"{date_str}_{safe_company}_{safe_title}_CL.pdf"
        
        cl_md_path.write_text(tailored_cl, encoding="utf-8")
        convert_md_to_pdf(tailored_cl, cl_pdf_path)
        
        # Update state
        job['documents_drafted'] = True
        job['cv_path'] = str(cv_pdf_path) # Now pointing directly to the PDF
        job['cl_path'] = str(cl_pdf_path) # Now pointing directly to the PDF
        
    with open(TO_APPLY_PATH, "w", encoding="utf-8") as f:
        json.dump(approved_jobs, f, indent=4, ensure_ascii=False)
        
    print("\n✅ Asset execution complete. Markdown and PDF documents are ready in the 'tailored' directory.")

if __name__ == "__main__":
    main()