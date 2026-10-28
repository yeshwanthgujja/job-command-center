# scorer.py
import os
import json
import google.generativeai as genai

STRONG_GROUPS = {"swe_junior", "frontend", "backend", "fullstack", "ai_genai", "internships"}
MODERATE_GROUPS = {"ml_data_science", "data_engineering", "devops_cloud", "qa_sdet", "product_ba", "automation_rpa", "campus_mass"}

RESUME_KEYWORDS = [
    "python", "typescript", "javascript", "sql", "react", "next.js", "tailwind", 
    "node", "express", "fastapi", "django", "rest", "websocket", "postgresql", 
    "mongodb", "redis", "pgvector", "pytorch", "numpy", "pandas", "scikit", 
    "machine learning", "deep learning", "nlp", "llm", "rag", "embedding", 
    "prompt", "agent", "langgraph", "aws", "docker", "kubernetes", "ci/cd", 
    "playwright", "git", "github", "dsa", "oop", "dbms"
]

PREFERRED_CITIES_HIGH = ["hyderabad", "remote", "work from home", "anywhere"]

def rule_based_score(job):
    score = 0
    reasons = []
    
    # 1. Role Group (Max 4)
    group = job.get("role_group", "")
    if group in STRONG_GROUPS:
        score += 4
        reasons.append(f"strong role ({group})")
    elif group in MODERATE_GROUPS:
        score += 2
        reasons.append(f"moderate role ({group})")
    else:
        score += 1

    # 2. Keywords (Max 3)
    text = f"{job.get('title','')} {job.get('snippet','')}".lower()
    hits = sum(1 for kw in RESUME_KEYWORDS if kw in text)
    if hits >= 5: 
        score += 3
        reasons.append(f"{hits} skill matches")
    elif hits >= 3: 
        score += 2
        reasons.append(f"{hits} skill matches")
    elif hits >= 1: 
        score += 1

    # 3. Location (Max 3)
    loc = (job.get("location") or "").lower()
    if any(c in loc for c in PREFERRED_CITIES_HIGH):
        score += 3
        reasons.append("Hyd/Remote")
    elif "india" in loc:
        score += 1
        
    return score, "; ".join(reasons) if reasons else "No strong signals"

def llm_enhance(job):
    """Uses Gemini to get a proper explanation and gaps."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return job["fit_reason"], "GEMINI_API_KEY not set."
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Analyze this job for a B.Tech CSE student (graduating 2027) with skills in Python, React, FastAPI, AI/ML, and Cloud.
    Job Title: {job['title']}
    Company: {job['company']}
    Snippet: {job['snippet']}
    
    Give a 1-sentence explanation of why it fits.
    Give a 1-sentence explanation of the main gap.
    Return ONLY valid JSON: {{"explanation": "...", "gaps": "..."}}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        data = json.loads(text)
        return data.get("explanation", job["fit_reason"]), data.get("gaps", "")
    except Exception as e:
        print(f"LLM failed: {e}")
        return job["fit_reason"], "LLM Error"

def compute_fit(job):
    score, reason = rule_based_score(job)
    return max(1, min(10, score)), reason
