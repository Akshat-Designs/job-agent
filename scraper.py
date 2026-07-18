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
        if any(bad_word in title.lower() for bad_word in self.title_blacklist):
            return False

        location_lower = location.lower()
        desc_lower = description.lower()
        
        is_allowed_location = any(loc in location_lower or loc in desc_lower for loc in self.allowed_locations)
        has_exclusion = any(phrase in desc_lower for phrase in self.exclusion_phrases)
        
        if not is_allowed_location or has_exclusion:
            return False

        try:
            if detect(description) != 'en':
                return False
        except LangDetectException:
            return False 

        return True

class JobScraperPipeline:
    def __init__(self, apify_token):
        self.validator = JobValidator()
        self.apify_token = apify_token
        self.saved_jobs = []
        
        # Optimized for high-value commerce and strategy tracks
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
            pass # Silently drop invalid roles to keep terminal output clean

    def export_to_json(self, filename="jobs.json"):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.saved_jobs, f, indent=4, ensure_ascii=False)
        print(f"\n[EXPORTED] Pipeline secured {len(self.saved_jobs)} roles into {filename}")

    # ==================== API TIER ====================
    def scrape_apify_endpoints(self):
        print("\n--- Initiating Apify API Extraction ---")
        
        # 1. Y Combinator
        yc_url = f"https://api.apify.com/v2/acts/automation-lab~ycombinator-jobs-scraper/run-sync-get-dataset-items?token={self.apify_token}"
        for role in self.target_roles:
            try:
                res = requests.post(yc_url, json={"maxItems": 15, "query": role, "remoteOnly": False, "jobType": "Internship"}, timeout=30)
                if res.status_code in [200, 201]:
                    for job in res.json():
                        desc = f"{job.get('title', '')} {job.get('skills', '')} {job.get('description', '')}"
                        self.process_and_save(job.get("title", "N/A"), job.get("companyName", "N/A"), job.get("location", "Remote"), desc, job.get("url", ""), "Y Combinator")
            except Exception as e:
                print(f"YC API Exception: {e}")

        # 2. LinkedIn (Verified Endpoint)
        li_url = f"https://api.apify.com/v2/acts/automation-lab~linkedin-jobs-scraper/run-sync-get-dataset-items?token={self.apify_token}"
        for role in self.target_roles:
            try:
                res = requests.post(li_url, json={"searchQuery": role, "location": "India", "maxJobs": 10, "experienceLevel": "1", "datePosted": "r604800"}, timeout=30)
                if res.status_code in [200, 201]:
                    for job in res.json():
                        self.process_and_save(job.get("title", "N/A"), job.get("companyName", "N/A"), job.get("location", "India"), job.get("descriptionText", ""), job.get("url", ""), "LinkedIn")
            except Exception as e:
                print(f"LinkedIn API Exception: {e}")

        # 3. Indeed (Verified Endpoint)
        indeed_url = f"https://api.apify.com/v2/acts/curious_coder~indeed-scraper/run-sync-get-dataset-items?token={self.apify_token}"
        for role in self.target_roles:
            try:
                res = requests.post(indeed_url, json={"country": "in", "position": role, "location": "India", "max_pages": 1}, timeout=30)
                if res.status_code in [200, 201]:
                    for job in res.json():
                        self.process_and_save(job.get("title", "N/A"), job.get("company", "N/A"), job.get("location", "India"), job.get("description", ""), job.get("url", ""), "Indeed")
            except Exception as e:
                print(f"Indeed API Exception: {e}")

# ==================== LOCAL STEALTH ENGINE (CDP HIJACK) ====================
    def run_stealth_browser_pipeline(self):
        print("\n--- Hooking into Existing Native Chrome Session ---")
        with sync_playwright() as p:
            try:
                # Attach to the manual Chrome window running on port 9222
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0] 
                page = context.new_page()
            except Exception as e:
                print(f"⚠️ CDP Error: Make sure you launched Chrome with --remote-debugging-port=9222. Details: {e}")
                return

            for role in self.target_roles:
                query = role.replace(' ', '%20')
                
                # PLATFORM 4: Wellfound Bypass Loop
                try:
                    page.goto(f"https://wellfound.com/role/intern?keyword={query}", timeout=20000)
                    time.sleep(4)
                    html_content = page.content()
                    print(f"[WELLFOUND DIAGNOSTIC] Role: '{role}' - HTML Length caught: {len(html_content)}")
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    processed_titles = set()
                    for card in soup.find_all('div'):
                        title_elem = card.find('h2')
                        company_elem = card.find('h4')
                        
                        if title_elem and company_elem:
                            title = title_elem.text.strip()
                            company = company_elem.text.strip()
                            
                            if title not in processed_titles:
                                processed_titles.add(title)
                                self.process_and_save(title, company, "Remote", card.text, "https://wellfound.com", "Wellfound")
                except Exception as e:
                    print(f"Wellfound local parsing skipped for {role}: {e}")

                # PLATFORM 5: Shine Custom Loop
                try:
                    page.goto(f"https://www.shine.com/job-search/{query}-jobs", timeout=20000)
                    time.sleep(3)
                    html_content = page.content()
                    print(f"[SHINE DIAGNOSTIC] Role: '{role}' - HTML Length caught: {len(html_content)}")
                    soup = BeautifulSoup(html_content, 'html.parser')
                    for item in soup.find_all(['div', 'li'], class_=lambda c: c and 'jobCard' in c):
                        title_elem = item.find(['h2', 'h3'])
                        title = title_elem.text.strip() if title_elem else "N/A"
                        company_elem = item.find('span', class_=lambda c: c and 'compName' in c)
                        company = company_elem.text.strip() if company_elem else "N/A"
                        link_elem = item.find('a')
                        link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ""
                        self.process_and_save(title, company, "India", item.text, f"https://www.shine.com{link}", "Shine")
                except Exception as e:
                    print(f"Shine parsing skipped for {role}: {e}")

                # PLATFORM 6: Jobaaj Niche Loop
                try:
                    page.goto(f"https://www.jobaaj.com/jobs-search?keyword={query}", timeout=20000)
                    time.sleep(3)
                    html_content = page.content()
                    print(f"[JOBAAJ DIAGNOSTIC] Role: '{role}' - HTML Length caught: {len(html_content)}")
                    soup = BeautifulSoup(html_content, 'html.parser')
                    for row in soup.find_all('div', class_=lambda c: c and 'job-box' in c):
                        title_elem = row.find('h3')
                        title = title_elem.text.strip() if title_elem else "N/A"
                        company_elem = row.find('p', class_=lambda c: c and 'company-name' in c)
                        company = company_elem.text.strip() if company_elem else "N/A"
                        self.process_and_save(title, company, "India", row.text, "https://www.jobaaj.com", "Jobaaj")
                except Exception as e:
                    print(f"Jobaaj parsing skipped for {role}: {e}")

            # Close just the tab we created, leave the main debug browser open for future runs
            page.close()

            browser.close()
if __name__ == "__main__":
    PIPELINE_TOKEN = "apify_api_jKRPayUWhCDhbBfC4inZvL9QcO40gz3Gqs51"
    
    pipeline = JobScraperPipeline(apify_token=PIPELINE_TOKEN)
    pipeline.scrape_apify_endpoints()
    pipeline.run_stealth_browser_pipeline()
    pipeline.export_to_json("jobs.json")