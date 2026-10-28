# scoring.py
# Rule-based fit scoring for Phase 2a. No API needed.

# Strong-fit role groups (from Career_Role_Map_2026.xlsx "Fit Now" = S)
STRONG_GROUPS = {
    "swe_junior", "frontend", "backend", "fullstack",
    "ai_genai", "internships",
}

# Moderate-fit role groups (Excel "Fit Now" = M, or "S/M")
MODERATE_GROUPS = {
    "ml_data_science", "data_engineering", "devops_cloud",
    "qa_sdet", "product_ba", "automation_rpa", "campus_mass",
}

# Weak-fit role groups (Excel "Fit Now" = N, or deferred bands)
WEAK_GROUPS = {
    "security", "swe_mid", "solutions_support",
    "recruiting_hr", "tech_writing_devrel",
}

# Resume keywords — extracted from your resume
RESUME_KEYWORDS = [
    # Languages
    "python", "typescript", "javascript", "sql",
    # Frontend
    "react", "next.js", "nextjs", "tailwind", "zustand",
    # Backend
    "node", "node.js", "express", "fastapi", "django",
    "rest", "websocket", "openapi", "swagger",
    # Databases
    "postgresql", "postgres", "mongodb", "redis", "firebase", "pgvector",
    # AI/ML
    "pytorch", "numpy", "pandas", "scikit", "sklearn",
    "machine learning", "deep learning", "nlp", "ml",
    # GenAI
    "llm", "rag", "embedding", "prompt", "agent",
    "function calling", "structured output", "langgraph", "langchain",
    # Cloud/DevOps
    "aws", "ec2", "s3", "lambda", "docker", "kubernetes",
    "k8s", "ci/cd", "nginx", "mlflow",
    # Testing
    "pytest", "jest", "playwright", "postman", "git", "github", "linux",
    # Core
    "dsa", "data structures", "algorithms", "oop", "dbms", "system design",
]

PREFERRED_CITIES_HIGH = ["hyderabad", "remote", "work from home", "anywhere"]
PREFERRED_CITIES_MED = ["bangalore", "bengaluru"]
OTHER_INDIA_CITIES = [
    "pune", "chennai", "mumbai", "noida", "gurgaon", "gurugram",
    "delhi", "kolkata", "ahmedabad", "india",
]


def compute_fit(job):
    """Return (score 1-10, reason string)."""
    score = 0
    reasons = []

    # --- 1. Role group fit (0-4 points) ---
    group = job.get("role_group", "")
    if group in STRONG_GROUPS:
        score += 4
        reasons.append(f"strong role fit ({group})")
    elif group in MODERATE_GROUPS:
        score += 2
        reasons.append(f"moderate role fit ({group})")
    elif group in WEAK_GROUPS:
        score += 1
        reasons.append(f"weak role fit ({group})")
    else:
        score += 2  # unknown group, neutral

    # --- 2. Resume keyword overlap (0-3 points) ---
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
        reasons.append(f"{hits} skill match")

    # --- 3. Location fit (0-3 points) ---
    loc = (job.get("location") or "").lower()
    if any(c in loc for c in PREFERRED_CITIES_HIGH):
        score += 3
        reasons.append("location match (Hyd/Remote)")
    elif any(c in loc for c in PREFERRED_CITIES_MED):
        score += 2
        reasons.append("location (Bangalore)")
    elif any(c in loc for c in OTHER_INDIA_CITIES):
        score += 1

    # Clamp to 1-10
    score = max(1, min(10, score))
    reason = "; ".join(reasons) if reasons else "no strong signals"
    return score, reason
