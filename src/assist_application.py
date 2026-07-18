import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from database import connect

ROOT = Path(__file__).resolve().parents[1]
TAILORED_DIR = ROOT / "tailored"

def assist_with_application():
    connection = connect()
    # Find one job that has its documents drafted but hasn't been applied to yet
    cursor = connection.execute(
        "SELECT * FROM jobs WHERE status = 'documents_drafted' LIMIT 1"
    )
    job = cursor.fetchone()
    
    if not job:
        print("No drafted jobs found awaiting application.")
        connection.close()
        return

    job_dict = dict(job)
    print(f"\n{'='*50}")
    print(f"🚀 PREPARING APPLICATION: {job_dict['title']} at {job_dict['company']}")
    print(f"{'='*50}")
    
    # Locate the tailored CV for easy reference
    safe_company = "".join(x for x in job_dict['company'] if x.isalnum())
    safe_title = "".join(x for x in job_dict['title'] if x.isalnum())[:20]
    
    # Check the directory for the specific CV (ignoring the date prefix for the search)
    drafts = list(TAILORED_DIR.glob(f"*_{safe_company}_{safe_title}_CV.pdf"))
    cv_path = drafts[0] if drafts else "No PDF found. Did you run Pandoc?"
    
    print(f"\nTarget URL: {job_dict['url']}")
    print(f"Tailored CV Path: {cv_path}")
    print("\nLaunching browser... Please complete the CAPTCHAs, upload your CV, and click Submit manually.")
    print("Press Ctrl+C in this terminal when you are finished to close the browser and update the database.")

    with sync_playwright() as p:
        # headless=False ensures you can actually see the browser and interact with it
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            page.goto(job_dict['url'])
            
            # Keep the script running so the browser stays open
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nClosing browser...")
            browser.close()
            
            # Mark as applied
            connection.execute(
                "UPDATE jobs SET status = 'applied' WHERE id = ?", 
                (job_dict['id'],)
            )
            connection.commit()
            print(f"✅ Marked '{job_dict['title']}' as applied in the database.")
            
    connection.close()

if __name__ == "__main__":
    assist_with_application()