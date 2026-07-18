import time
import json
import requests
from bs4 import BeautifulSoup
from langdetect import detect, LangDetectException
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

class JobValidator:
    def __init__(self):
        self.title_blacklist = [
            "software engineer", "developer", "customer support", "sales representative", 
            "call center", "tutor", "bpo", "graphic designer", "video editor", "social media manager"
        ]
        self.allowed_locations = ["remote", "india", "delhi", "mumbai", "bengaluru", "bangalore", "united states", "usa", "uk", "united kingdom", "canada"]
        self.exclusion_phrases = ["us citizens only", "no c2c", "must reside in", "sponsorship not available"]

    def is_valid(self, title, location, description):
        # 1. Anti-Trash Title Check
        if any(bad_word in title.lower() for bad_word in self.title_blacklist):
            return False

        # 2. Location Verification
        location_lower = location.lower()
        desc_lower = description.lower()
        
        is_allowed_location = any(loc in location_lower or loc in desc_lower for loc in self.allowed_locations)
        has_exclusion = any(phrase in desc_lower for phrase in self.exclusion_phrases)
        
        if not is_allowed_location or has_exclusion:
            return False

        # 3. Strict Language Policing
        try:
            if detect(description) != 'en':
                return False
        except LangDetectException:
            return False 

        return True

class JobScraperPipeline:
    def __init__(self, apify_token="YOUR_APIFY_TOKEN"):
        self.validator = JobValidator()
        self.apify_token = apify_token
        self.saved_jobs = []
        
        # Broadened target roles to increase search yield
        self.target_roles = [
            "Investment Banking Intern", "Corporate Finance Intern", "Finance Intern",
            "Growth Marketing Intern", "Demand Generation Intern", "Marketing Intern",
            "Management Consulting Intern", "Corporate Strategy Intern", "Strategy Analyst"
        ]

    def process_and_save(self, title, company, location, description, url, source):
        if self.validator.is_valid(title, location, description):
            clean_job = {
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "source": source
            }
            if clean_job not in self.saved_jobs:
                self.saved_jobs.append(clean_job)
                print(f"[PASSED] {title} at {company} ({source})")
        else:
            print(f"[DROPPED] {title} at {company} did not meet criteria.")

    def export_to_json(self, filename="jobs.json"):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.saved_jobs, f, indent=4, ensure_ascii=False)
        print(f"\n[EXPORTED] Saved {len(self.saved_jobs)} pristine roles directly into {filename}")

    # ==================== PLATFORM 1: Y COMBINATOR (API Tier) ====================
    def scrape_ycombinator_api(self):
        print("\n--- Ingesting Y Combinator via Apify API ---")
        url = f"https://api.apify.com/v2/acts/automation-lab~ycombinator-jobs-scraper/run-sync-get-dataset-items?token={self.apify_token}"
        for role in self.target_roles:
            # Setting remoteOnly to False to capture hybrid/in-person opportunities
            payload = {"maxItems": 15, "query": role, "remoteOnly": False, "jobType": "Internship"}
            try:
                res = requests.post(url, json=payload, timeout=30)
                if res.status_code in [200, 201]:
                    for job in res.json():
                        desc = f"{job.get('title', '')} {job.get('skills', '')} {job.get('description', '')}"
                        self.process_and_save(job.get("title", "N/A"), job.get("companyName", "N/A"), job.get("location", "Remote"), desc, job.get("url", ""), "Y Combinator")
                else:
                    print(f"⚠️ YC API Error for {role}: HTTP {res.status_code} - {res.text[:100]}")
            except Exception as e:
                print(f"YC API Exception for {role}: {e}")

    # ==================== PLATFORM 2: LINKEDIN (API Tier) ====================
    def scrape_linkedin_api(self):
        print("\n--- Ingesting LinkedIn via Apify API ---")
        url = f"https://api.apify.com/v2/acts/rockstars~linkedin-jobs-scraper/run-sync-get-dataset-items?token={self.apify_token}"
        for role in self.target_roles:
            # Removed explicit "Remote" lock to pull in region-wide roles
            payload = {"queries": f'"{role}"', "location": "India", "rows": 10, "publishedAt": "pastWeek"}
            try:
                res = requests.post(url, json=payload, timeout=30)
                if res.status_code in [200, 201]:
                    for job in res.json():
                        self.process_and_save(job.get("position", "N/A"), job.get("companyName", "N/A"), job.get("location", "India"), job.get("description", ""), job.get("jobUrl", ""), "LinkedIn")
                else:
                    print(f"⚠️ LinkedIn API Error for {role}: HTTP {res.status_code} - {res.text[:100]}")
            except Exception as e:
                print(f"LinkedIn API Exception for {role}: {e}")

    # ==================== PLATFORM 3: INDEED & NAUKRI (API Tier Combo) ====================
    def scrape_enterprise_aggregators_api(self):
        print("\n--- Ingesting Indeed & Naukri via Apify Hub ---")
        for platform, actor in [("Indeed", "apify~indeed-scraper"), ("Naukri", "vrozs~naukri-scraper")]:
            url = f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items?token={self.apify_token}"
            for role in self.target_roles:
                payload = {"searchQuery": f"{role}", "maxItems": 10}
                try:
                    res = requests.post(url, json=payload, timeout=30)
                    if res.status_code in [200, 201]:
                        for job in res.json():
                            self.process_and_save(job.get("title", "N/A"), job.get("company", "N/A"), job.get("location", "India"), job.get("description", ""), job.get("url", ""), platform)
                    else:
                        print(f"⚠️ {platform} API Error for {role}: HTTP {res.status_code} - {res.text[:100]}")
                except Exception as e:
                    print(f"{platform} API Exception for {role}: {e}")

    # ==================== LOCAL PLAYWRIGHT STEALTH ENGINE ====================
    def run_stealth_browser_pipeline(self):
        print("\n--- Launching Local Headless Stealth Engine (Wellfound, Shine, Jobaaj) ---")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            Stealth().apply_stealth_sync(context)
            page = context.new_page()

            for role in self.target_roles:
                query = role.replace(' ', '%20')
                
                # PLATFORM 4: Wellfound Loop
                try:
                    page.goto(f"https://wellfound.com/role/intern?keyword={query}", timeout=20000)
                    time.sleep(4)
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    for card in soup.find_all('div', class_='styles_component__2kU1Z'):
                        title = card.find('h2').text if card.find('h2') else "N/A"
                        company = card.find('h4').text if card.find('h4') else "N/A"
                        self.process_and_save(title, company, "Remote", card.text, "https://wellfound.com", "Wellfound")
                except Exception as e:
                    print(f"Wellfound local parsing skipped for {role}")

                # PLATFORM 5: Shine Custom Loop
                try:
                    page.goto(f"https://www.shine.com/job-search/{query}-jobs", timeout=20000)
                    time.sleep(3)
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    for item in soup.find_all('div', class_='jobCard'):
                        title = item.find('h2').text.strip() if item.find('h2') else "N/A"
                        company = item.find('span', class_='compName').text.strip() if item.find('span', class_='compName') else "N/A"
                        link = item.find('a')['href'] if item.find('a') else ""
                        self.process_and_save(title, company, "India", item.text, f"https://www.shine.com{link}", "Shine")
                except Exception as e:
                    print(f"Shine parsing skipped for {role}")

                # PLATFORM 6: Jobaaj Niche Finance/Growth Loop
                try:
                    page.goto(f"https://www.jobaaj.com/jobs-search?keyword={query}", timeout=20000)
                    time.sleep(3)
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    for row in soup.find_all('div', class_='job-box'):
                        title = row.find('h3').text.strip() if row.find('h3') else "N/A"
                        company = row.find('p', class_='company-name').text.strip() if row.find('p', class_='company-name') else "N/A"
                        self.process_and_save(title, company, "India", row.text, "https://www.jobaaj.com", "Jobaaj")
                except Exception as e:
                    print(f"Jobaaj parsing skipped for {role}")

            browser.close()

if __name__ == "__main__":
    PIPELINE_TOKEN = "YOUR_APIFY_TOKEN_HERE"
    
    pipeline = JobScraperPipeline(apify_token=PIPELINE_TOKEN)
    
    # 1. API Extraction Sequence
    pipeline.scrape_ycombinator_api()
    pipeline.scrape_linkedin_api()
    pipeline.scrape_enterprise_aggregators_api()
    
    # 2. Local Stealth Extraction Sequence
    pipeline.run_stealth_browser_pipeline()
    
    # 3. Persistent Storage Engine Call
    pipeline.export_to_json("jobs.json")