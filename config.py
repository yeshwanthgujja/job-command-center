# config.py
ROLE_GROUPS = {
    "swe_junior": ["software engineer", "SDE", "software developer", "graduate engineer trainee"],
    "frontend": ["frontend developer", "react developer", "next.js developer", "UI engineer"],
    "backend": ["backend developer", "python developer", "fastapi developer", "node.js developer", "API developer"],
    "fullstack": ["full stack developer", "MERN developer", "full-stack engineer"],
    "ai_genai": ["AI engineer", "GenAI engineer", "LLM engineer", "RAG engineer", "agentic AI engineer", "prompt engineer"],
    "ml_data_science": ["machine learning engineer", "data scientist", "NLP engineer"],
    "data_engineering": ["data engineer", "analytics engineer", "ETL developer"],
    "devops_cloud": ["DevOps engineer", "cloud engineer", "platform engineer", "SRE"],
    "qa_sdet": ["QA automation", "SDET", "test engineer", "automation tester"],
    "security": ["security engineer", "AppSec", "DevSecOps"],
    "solutions_support": ["solutions engineer", "technical support engineer", "implementation engineer"],
    "recruiting_hr": ["technical recruiter", "talent sourcer", "TA intern"],
    "tech_writing_devrel": ["technical writer", "developer advocate", "DevRel"],
    "product_ba": ["product analyst", "business analyst", "associate product manager"],
    "automation_rpa": ["automation engineer", "RPA developer", "workflow automation"],
    "internships": ["software engineer intern", "AI ML intern", "data analyst intern", "DevOps intern", "frontend intern", "backend intern"],
    "campus_mass": ["TCS Digital", "Infosys Specialist Programmer", "Wipro Turbo", "Accenture ASE"],
}

# Only scrape these active groups to save time and stay within limits
PRIORITY_GROUPS_JOBSPY = [
    "swe_junior", "frontend", "backend", "fullstack",
    "ai_genai", "ml_data_science", "data_engineering", "devops_cloud",
]

LOCATION = "India"
RESULTS_PER_QUERY = 8
JOA_QUERIES = 6

# Thresholds
MIN_SCORE_MARKDOWN = 5
MIN_SCORE_TELEGRAM = 6
MAX_TELEGRAM_JOBS = 10
MAX_MARKDOWN_PER_RUN = 50
MAX_CSV_ROWS = 5000
