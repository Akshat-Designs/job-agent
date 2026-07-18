import re
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
TAILORED_DIR = ROOT / "tailored"
MASTER_RESUME = ROOT / "resume" / "master.md"

def main():
    if not TAILORED_DIR.exists():
        print("Tailored directory not found.")
        return
        
    master_text = MASTER_RESUME.read_text(encoding="utf-8")
    drafts = list(TAILORED_DIR.glob("*.md"))
    
    print(f"Found {len(drafts)} drafts to validate.")
    
    for draft in drafts:
        text = draft.read_text(encoding="utf-8")
        flags = []
        
        # Safety Check: Compare years (e.g., 2024, 2025) in draft vs master
        years_in_draft = set(re.findall(r'\b20\d{2}\b', text))
        years_in_master = set(re.findall(r'\b20\d{2}\b', master_text))
        
        unsupported_years = years_in_draft - years_in_master
        if unsupported_years:
            flags.append(f"Contains unsupported years: {unsupported_years}")
            
        if flags:
            print(f"⚠️ WARNING - {draft.name} requires human review:")
            for flag in flags:
                print(f"  - {flag}")
        else:
            print(f"✅ {draft.name} passed programmatic validation.")

if __name__ == "__main__":
    main()