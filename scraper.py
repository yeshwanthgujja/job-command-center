import os, csv, requests, pandas as pd
from datetime import datetime
from jobspy import scrape_jobs
from hirehunt import scrape_jobs as hirehunt_scrape
from config import ROLE_GROUPS, LOCATION, RESULTS_PER_QUERY, JOA_QUERIES

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
JOA_API_KEY = os.environ["JOA_API_KEY"]

FIELDS = ["company", "title", "location", "url", "source", "role_group", "date_found", "snippet"]

def normalize(title, company, location, url, source, role_group, snippet=""):
    return dict(
        company=company or "", title=title or "", location=location or "",
        url=url or "", source=source or "", role_group=role_group,
        date_found=datetime.utcnow().strftime("%Y-%m-%d"), snippet=snippet[:300],
    )

# 1) JobSpy — broad board scraping
def scrape_jobspy():
    out = []
    for group, terms in ROLE_GROUPS.items():
        for term in terms[:2]:
            try:
                df = scrape_jobs(
                    site_name=["linkedin", "indeed", "naukri"],
                    search_term=term,
                    location=LOCATION,
                    results_wanted=RESULTS_PER_QUERY,
                    country_indeed="India",
                    linkedin_fetch_description=False,
                    verbose=0,
                )
                for _, row in df.iterrows():
                    out.append(normalize(
                        row.get("title"), row.get("company"), row.get("location"),
                        row.get("job_url"), row.get("site"), group,
                    ))
            except Exception as e:
                print(f"jobspy failed for {term}: {e}")
    return out

# 2) HireHunt — India-focused boards
def scrape_hirehunt():
    out = []
    for group in ["swe_junior", "ai_genai", "data_engineering", "devops_cloud", "internships"]:
        term = ROLE_GROUPS[group][0]
        try:
            result = hirehunt_scrape(
                search_term=term,
                sources=["internshala", "naukri", "shine", "unstop"],
                country="India",
                results_wanted=RESULTS_PER_QUERY,
                job_kind="internship" if group == "internships" else "job",
            )
            for j in result.jobs:
                out.append(normalize(
                    j.title, j.company, j.city or j.location,
                    j.job_url, j.source, group, j.description or "",
                ))
        except Exception as e:
            print(f"hirehunt failed for {term}: {e}")
    return out

# 3) JOA — corrected endpoint, parameter, and response key
def scrape_joa():
    if not JOA_API_KEY:
        return []
    headers = {"Authorization": f"Bearer {JOA_API_KEY}"}
    out = []
    priority_groups = [
        "swe_junior", "ai_genai", "backend", "fullstack",
        "frontend", "data_engineering", "devops_cloud", "internships",
    ]
    for group in priority_groups[:JOA_QUERIES]:
        term = ROLE_GROUPS[group][0]
        try:
            resp = requests.get(
                "https://api.jobopportunitiesapi.org/v1/jobs",
                headers=headers,
                params={"title": term, "country": "IN", "limit": 5},
                timeout=30,
            )
            if resp.status_code == 401:
                print("JOA: invalid key")
                break
            if resp.status_code == 402:
                print("JOA: monthly record limit reached")
                break
            resp.raise_for_status()
            for job in resp.json().get("data", []):
                out.append(normalize(
                    job.get("title"), job.get("company"), job.get("location"),
                    job.get("apply_url") or job.get("url"), "joa", group,
                    job.get("description", "")[:300],
                ))
        except Exception as e:
            print(f"JOA failed for {group}: {e}")
    return out

def dedupe(jobs, existing_urls):
    seen = set(existing_urls)
    fresh = []
    for j in jobs:
        if j["url"] and j["url"] not in seen:
            seen.add(j["url"])
            fresh.append(j)
    return fresh

def save(fresh):
    path = "data/jobs.csv"
    write_header = not os.path.exists(path)
    os.makedirs("data", exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(fresh)

    day = datetime.utcnow().strftime("%Y-%m-%d")
    os.makedirs(f"inbox/{day}", exist_ok=True)
    for j in fresh[:20]:
        safe = f"{j['company']}_{j['title']}".replace("/", "_")[:80]
        with open(f"inbox/{day}/{safe}.md", "w", encoding="utf-8") as f:
            f.write(f"# {j['title']} @ {j['company']}\n\n"
                    f"- URL: {j['url']}\n- Source: {j['source']}\n"
                    f"- Role group: {j['role_group']}\n- Location: {j['location']}\n\n"
                    f"{j['snippet']}\n")

def telegram(fresh):
    if not fresh:
        return
    lines = [f"*{len(fresh)} new roles found*"]
    for j in fresh[:12]:
        lines.append(f"• [{j['title']} @ {j['company']}]({j['url']}) — {j['role_group']}")
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": "\n".join(lines),
              "parse_mode": "Markdown", "disable_web_page_preview": True},
        timeout=20,
    )

def main():
    existing = pd.read_csv("data/jobs.csv")["url"].dropna().tolist() if os.path.exists("data/jobs.csv") else []
    jobs = scrape_jobspy() + scrape_hirehunt() + scrape_joa()
    fresh = dedupe(jobs, existing)
    save(fresh)
    telegram(fresh)
    print(f"Saved {len(fresh)} new jobs")

if __name__ == "__main__":
    main()
