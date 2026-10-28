# scraper.py
import os, csv, requests, pandas as pd
from datetime import datetime
from jobspy import scrape_jobs
from hirehunt import scrape_jobs as hirehunt_scrape
from config import *
from scorer import compute_fit, llm_enhance
from tailor import generate_application_packet

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
JOA_API_KEY = os.environ["JOA_API_KEY"]

DATA_DIR = "job_data"
CSV_PATH = os.path.join(DATA_DIR, "jobs.csv")
INBOX_DIR = os.path.join(DATA_DIR, "inbox")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")

FIELDS = ["company", "title", "location", "url", "source", "role_group", "date_found", "snippet", "fit_score", "fit_reason", "llm_explanation", "llm_gaps"]

def normalize(title, company, location, url, source, role_group, snippet=""):
    return dict(company=company or "", title=title or "", location=location or "",
                url=url or "", source=source or "", role_group=role_group,
                date_found=datetime.utcnow().strftime("%Y-%m-%d"), snippet=snippet[:300])

def scrape_jobspy():
    out = []
    for group in PRIORITY_GROUPS_JOBSPY:
        term = ROLE_GROUPS[group][0]
        try:
            df = scrape_jobs(site_name=["linkedin", "indeed", "naukri"], search_term=term,
                             location=LOCATION, results_wanted=RESULTS_PER_QUERY,
                             country_indeed="India", verbose=0)
            for _, row in df.iterrows():
                out.append(normalize(row.get("title"), row.get("company"), row.get("location"), row.get("job_url"), row.get("site"), group))
        except Exception as e: print(f"jobspy failed: {e}")
    return out

def scrape_hirehunt():
    out = []
    for group in ["swe_junior", "ai_genai", "internships"]:
        term = ROLE_GROUPS[group][0]
        try:
            result = hirehunt_scrape(search_term=term, sources=["internshala", "naukri", "unstop"],
                                     country="India", results_wanted=RESULTS_PER_QUERY,
                                     job_kind="internship" if group == "internships" else "job")
            for j in result.jobs:
                out.append(normalize(j.title, j.company, j.city or j.location, j.job_url, j.source, group, j.description or ""))
        except Exception as e: print(f"hirehunt failed: {e}")
    return out

def scrape_joa():
    if not JOA_API_KEY: return []
    headers = {"Authorization": f"Bearer {JOA_API_KEY}"}
    out = []
    for group in PRIORITY_GROUPS_JOBSPY[:JOA_QUERIES]:
        term = ROLE_GROUPS[group][0]
        try:
            resp = requests.get("https://api.jobopportunitiesapi.org/v1/jobs", headers=headers,
                                params={"title": term, "country": "IN", "limit": 5}, timeout=30)
            if resp.status_code in [401, 402]: break
            for job in resp.json().get("data", []):
                out.append(normalize(job.get("title"), job.get("company"), job.get("location"), job.get("apply_url"), "joa", group, job.get("description", "")[:300]))
        except Exception as e: print(f"JOA failed: {e}")
    return out

def main():
    existing = pd.read_csv(CSV_PATH)["url"].dropna().tolist() if os.path.exists(CSV_PATH) else []
    
    jobs = scrape_jobspy() + scrape_hirehunt() + scrape_joa()
    
    # Dedupe
    seen = set(existing)
    fresh = [j for j in jobs if j["url"] and j["url"] not in seen]
    
    for j in fresh:
        j["fit_score"], j["fit_reason"] = compute_fit(j)
        j["llm_explanation"], j["llm_gaps"] = "", ""
        
    # LLM + Tailoring for top jobs
    top_jobs = sorted([j for j in fresh if j["fit_score"] >= MIN_SCORE_TELEGRAM], key=lambda x: x["fit_score"], reverse=True)[:5]
    for j in top_jobs:
        j["llm_explanation"], j["llm_gaps"] = llm_enhance(j)
        generate_application_packet(j) # Create PDF

    # Save CSV
    os.makedirs(DATA_DIR, exist_ok=True)
    write_header = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header: w.writeheader()
        w.writerows(fresh)

    # Markdown + Telegram
    good = sorted([j for j in fresh if j["fit_score"] >= MIN_SCORE_MARKDOWN], key=lambda x: x["fit_score"], reverse=True)[:MAX_TELEGRAM_JOBS]
    if good:
        day_dir = os.path.join(INBOX_DIR, datetime.utcnow().strftime("%Y-%m-%d"))
        os.makedirs(day_dir, exist_ok=True)
        lines = [f"*🔥 {len(good)} High-Fit Roles Found*"]
        
        for j in good:
            safe = f"{j['company']}_{j['title']}".replace("/", "_")[:80]
            with open(os.path.join(day_dir, f"{safe}.md"), "w", encoding="utf-8") as f:
                f.write(f"# {j['title']} @ {j['company']}\n\n**Score:** {j['fit_score']}/10\n**Why:** {j['llm_explanation']}\n**Gaps:** {j['llm_gaps']}\n**URL:** {j['url']}")
            lines.append(f"⭐ [{j['fit_score']}/10] [{j['title']} @ {j['company']}]({j['url']})\n_{j['llm_explanation']}_")

        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "\n\n".join(lines), "parse_mode": "Markdown"}, timeout=20)

if __name__ == "__main__":
    main()