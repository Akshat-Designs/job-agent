import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"

def run_script(script_name):
    print(f"\n{'='*50}")
    print(f"🚀 RUNNING: {script_name}")
    print(f"{'='*50}")
    
    script_path = SRC_DIR / script_name
    
    try:
        # Run the script and stream the output to the console
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ERROR: {script_name} failed with exit code {e.returncode}.")
        print("Stopping daily run to prevent cascading errors.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR running {script_name}: {e}")
        sys.exit(1)

def main():
    print("Starting Job Agent Daily Run...")
    
    # 1. Collect public jobs
    run_script("collect_greenhouse.py")
    
    # 2. Import to SQLite and deduplicate
    run_script("import_jobs.py")
    
    # 3. Apply deterministic filters
    run_script("filter_jobs.py")
    
    # 4. Score new jobs locally
    run_script("score_jobs.py")
    
    # 5. Create tailored drafts
    run_script("tailor_applications.py")
    
    # 6. Validate every draft
    run_script("validate_resume.py")
    
    # 7. Create daily review report
    run_script("create_report.py")
    
    print(f"\n{'='*50}")
    print("✅ DAILY RUN COMPLETE. Check the 'reports' folder for your review dashboard.")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()