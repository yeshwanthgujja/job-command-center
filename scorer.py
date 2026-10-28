# scorer.py
import os
import json
import google.generativeai as genai

STRONG_GROUPS = {"swe_junior", "frontend", "backend", "fullstack", "ai_genai", "internships"}
MODERATE_GROUPS = {"ml_data_science", "data_engineering", "devops_cloud"}

RESUME_KEYWORDS = [
    "python", "typescript", "javascript", "sql", "react", "next.js", "node", "fastapi", 
    "postgresql", "mongodb", "redis", "pgvector", "pytorch", "machine learning", "nlp", 
    "llm", "rag", "langgraph", "aws", "docker", "kubernetes", "ci/cd", "playwright", "git"
]

def rule_based_score(job):
    score = 0
    reasons = []
    
    group = job.get("role_group", "")
    if group in STRONG_GROUPS:
        score += 4; reasons.append(f"strong role ({group})")
    elif group in MODERATE_GROUPS:
        score += 2; reasons.append(f"moderate role ({group})")
    else:
        score += 1

    text = f"{job.get('title','')} {job.get('snippet','')}".lower()
    hits = sum(1 for kw in RESUME_KEYWORDS if kw in text)
    if hits >= 5: score += 3; reasons.append(f"{hits} skill matches")
    elif hits >= 3: score += 2; reasons.append(f"{hits} skill matches")
    elif hits >= 1: score += 1

    loc = (job.get("location") or "").lower()
    if "hyderabad" in loc or "remote" in loc:
        score += 3; reasons.append("Hyd/Remote")
    elif "india" in loc:
        score += 1
        
    return min(10, max(1, score)), "; ".join(reasons) if reasons else "No strong signals"

def get_gemini_model():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

def llm_enhance(job):
    model = get_gemini_model()
    if not model: return job["fit_reason"], "GEMINI_API_KEY missing."
    
    prompt = f"""
    Analyze this job for a B.Tech CSE student (graduating 2027) with skills in Python, React, FastAPI, AI/ML, and Cloud.
    Job Title: {job['title']}
    Company: {job['company']}
    Snippet: {job['snippet']}
    
    Return ONLY valid JSON: {{"explanation": "1 sentence why it fits", "gaps": "1 sentence on gaps"}}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(text)
        return data.get("explanation", job["fit_reason"]), data.get("gaps", "")
    except Exception as e:
        return job["fit_reason"], "LLM Error"

def compute_fit(job):
    return rule_based_score(job)