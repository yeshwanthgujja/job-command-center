import os, csv, requests, pandas as pd
from datetime import datetime
from jobspy import scrape_jobs
from hirehunt import scrape_jobs as hirehunt_scrape
from scoring import compute_fit
from config import (
    ROLE_GROUPS, PRIORITY_GROUPS_JOBSPY, LOCATION, RESULTS_PER_QUERY,
    JOA_QUERIES, MIN_SCORE_MARKDOWN, MIN_SCORE_TELEGRAM,
    MAX_TELEGRAM_JOBS, MAX_MARKDOWN_PER_RUN, MAX_CSV_ROWS,
)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
JOA_API_KEY = os.environ["JOA_API_KEY"]

DATA_DIR = "job_data"
CSV_PATH = os.path.join(DATA_DIR, "jobs.csv")
INBOX_DIR = os.path.join(DATA_DIR, "inbox")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")

FIELDS = ["company", "title", "location", "url", "source", "role_group",
          "date_found", "snippet", "fit_score", "fit_reason"]


def normalize(title, company, location, url, source, role_group, snippet=""):
    return dict(company=company or "", title=title or "", location=location or "",
                url=url or "", source=source or "", role_group=role_group,
                date_found=datetime.utcnow().strftime("%Y-%m-%d"),
                snippet=snippet[:300])


def rotate_csv_if_needed():
    if not os.path.exists(CSV_PATH):
        return
    try:
        df = pd.read_csv(CSV_PATH)
    except Exception:
        return
    legacy = "fit_score" not in df.columns
    too_big = len(df) >= MAX_CSV_ROWS
    if not (legacy or too_big):
        return
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y-%m")
    reason = "legacy_schema" if legacy else "size"
    path = os.path.join(ARCHIVE_DIR, f"jobs_{stamp}_{reason}.csv")
    os.rename(CSV_PATH, path)
    print(f"Rotated CSV → {path} (reason: {reason})")


def scrape_jobspy():
    out = []
    for group in PRIORITY_GROUPS_JOBSPY:
        term = ROLE_GROUPS[group][0]
        try:
            df = scrape_jobs(
                site_name=["linkedin", "indeed", "naukri"],
                search_term=term, location=LOCATION,
                results_wanted=RESULTS_PER_QUERY,
                country_indeed="India",
                linkedin_fetch_description=False, verbose=0,
            )
            for _, row in df.iterrows():
                out.append(normalize(row.get("title"), row.get("company"),
                                     row.get("location"), row.get("job_url"),
                                     row.get("site"), group))
        except Exception as e:
            print(f"jobspy failed for {term}: {e}")
    return out


def scrape_hirehunt():
    out = []
    for group in ["swe_junior", "ai_genai", "data_engineering", "devops_cloud", "internships"]:
        term = ROLE_GROUPS[group][0]
        try:
            result = hirehunt_scrape(
                search_term=term,
                sources=["internshala", "naukri", "shine", "unstop"],
                country="India", results_wanted=RESULTS_PER_QUERY,
                job_kind="internship" if group == "internships" else "job",
            )
            for j in result.jobs:
                out.append(normalize(j.title, j.company, j.city or j.location,
                                     j.job_url, j.source, group, j.description or ""))
        except Exception as e:
            print(f"hirehunt failed for {term}: {e}")
    return out


def scrape_joa():
    if not JOA_API_KEY:
        return []
    headers = {"Authorization": f"Bearer {JOA_API_KEY}"}
    out = []
    priority = ["swe_junior", "ai_genai", "backend", "fullstack",
                "frontend", "data_engineering", "devops_cloud", "internships"]
    for group in priority[:JOA_QUERIES]:
        term = ROLE_GROUPS[group][0]
        try:
            resp = requests.get("https://api.jobopportunitiesapi.org/v1/jobs",
                                headers=headers,
                                params={"title": term, "country": "IN", "limit": 5},
                                timeout=30)
            if resp.status_code == 401:
                print("JOA: invalid key"); break
            if resp.status_code == 402:
                print("JOA: monthly limit"); break
            resp.raise_for_status()
            for job in resp.json().get("data", []):
                out.append(normalize(job.get("title"), job.get("company"),
                                     job.get("location"),
                                     job.get("apply_url") or job.get("url"),
                                     "joa", group,
                                     job.get("description", "")[:300]))
        except Exception as e:
            print(f"JOA failed for {group}: {e}")
    return out


def dedupe(jobs, existing_urls):
    seen = set(existing_urls); fresh = []
    for j in jobs:
        if j["url"] and j["url"] not in seen:
            seen.add(j["url"]); fresh.append(j)
    return fresh


def save(fresh):
    for j in fresh:
        j["fit_score"], j["fit_reason"] = compute_fit(j)

    os.makedirs(DATA_DIR, exist_ok=True)
    write_header = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        w.writerows(fresh)

    good = [j for j in fresh if j["fit_score"] >= MIN_SCORE_MARKDOWN]
    good = sorted(good, key=lambda x: x["fit_score"], reverse=True)[:MAX_MARKDOWN_PER_RUN]

    day = datetime.utcnow().strftime("%Y-%m-%d")
    day_dir = os.path.join(INBOX_DIR, day)
    os.makedirs(day_dir, exist_ok=True)
    for j in good:
        safe = f"{j['company']}_{j['title']}".replace("/", "_")[:80]
        with open(os.path.join(day_dir, f"{safe}.md"), "w", encoding="utf-8") as f:
            f.write(f"# {j['title']} @ {j['company']}\n\n"
                    f"- **Fit score:** {j['fit_score']}/10\n"
                    f"- **Why:** {j['fit_reason']}\n"
                    f"- URL: {j['url']}\n- Source: {j['source']}\n"
                    f"- Role group: {j['role_group']}\n- Location: {j['location']}\n\n"
                    f"{j['snippet']}\n")


def telegram(fresh):
    good = [j for j in fresh if j["fit_score"] >= MIN_SCORE_TELEGRAM]
    if not good:
        return
    good = sorted(good, key=lambda x: x["fit_score"], reverse=True)[:MAX_TELEGRAM_JOBS]
    lines = [f"*{len(good)} top-fit roles*"]
    for i, j in enumerate(good):
        prefix = "⭐" if i < 5 else "•"
        lines.append(f"{prefix} [{j['fit_score']}/10] [{j['title']} @ {j['company']}]({j['url']}) — _{j['role_group']}_")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": "\n".join(lines),
                        "parse_mode": "Markdown", "disable_web_page_preview": True},
                  timeout=20)


def main():
    rotate_csv_if_needed()
    existing = pd.read_csv(CSV_PATH)["url"].dropna().tolist() if os.path.exists(CSV_PATH) else []
    jobs = scrape_jobspy() + scrape_hirehunt() + scrape_joa()
    fresh = dedupe(jobs, existing)
    save(fresh)
    telegram(fresh)
    print(f"Scraped {len(jobs)} → fresh {len(fresh)} → saved")


if __name__ == "__main__":
    main()
