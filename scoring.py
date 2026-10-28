# scoring.py — rule-based fit, no API needed.

STRONG_GROUPS = {"swe_junior", "frontend", "backend", "fullstack", "ai_genai", "internships"}
MODERATE_GROUPS = {"ml_data_science", "data_engineering", "devops_cloud",
                   "qa_sdet", "product_ba", "automation_rpa", "campus_mass"}
WEAK_GROUPS = {"security", "swe_mid", "solutions_support", "recruiting_hr", "tech_writing_devrel"}

RESUME_KEYWORDS = [
    "python", "typescript", "javascript", "sql",
    "react", "next.js", "nextjs", "tailwind", "zustand",
    "node", "node.js", "express", "fastapi", "django",
    "rest", "websocket", "openapi", "swagger",
    "postgresql", "postgres", "mongodb", "redis", "firebase", "pgvector",
    "pytorch", "numpy", "pandas", "scikit", "sklearn",
    "machine learning", "deep learning", "nlp", "ml",
    "llm", "rag", "embedding", "prompt", "agent",
    "function calling", "structured output", "langgraph", "langchain",
    "aws", "ec2", "s3", "lambda", "docker", "kubernetes",
    "k8s", "ci/cd", "nginx", "mlflow",
    "pytest", "jest", "playwright", "postman", "git", "github", "linux",
    "dsa", "data structures", "algorithms", "oop", "dbms", "system design",
]

PREFERRED_CITIES_HIGH = ["hyderabad", "remote", "work from home", "anywhere"]
PREFERRED_CITIES_MED = ["bangalore", "bengaluru"]
OTHER_INDIA_CITIES = ["pune", "chennai", "mumbai", "noida", "gurgaon", "gurugram",
                     "delhi", "kolkata", "ahmedabad", "india"]


def compute_fit(job):
    score = 0
    reasons = []

    group = job.get("role_group", "")
    if group in STRONG_GROUPS:
        score += 4; reasons.append(f"strong role fit ({group})")
    elif group in MODERATE_GROUPS:
        score += 2; reasons.append(f"moderate role fit ({group})")
    elif group in WEAK_GROUPS:
        score += 1; reasons.append(f"weak role fit ({group})")
    else:
        score += 2

    text = f"{job.get('title','')} {job.get('snippet','')}".lower()
    hits = sum(1 for kw in RESUME_KEYWORDS if kw in text)
    if hits >= 5:   score += 3; reasons.append(f"{hits} skill matches")
    elif hits >= 3: score += 2; reasons.append(f"{hits} skill matches")
    elif hits >= 1: score += 1; reasons.append(f"{hits} skill match")

    loc = (job.get("location") or "").lower()
    if any(c in loc for c in PREFERRED_CITIES_HIGH):
        score += 3; reasons.append("location match (Hyd/Remote)")
    elif any(c in loc for c in PREFERRED_CITIES_MED):
        score += 2; reasons.append("location (Bangalore)")
    elif any(c in loc for c in OTHER_INDIA_CITIES):
        score += 1

    score = max(1, min(10, score))
    return score, "; ".join(reasons) if reasons else "no strong signals"
