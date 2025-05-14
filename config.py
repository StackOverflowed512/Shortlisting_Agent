import os
from dotenv import load_dotenv

load_dotenv()

# Ollama Settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3:latest")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest") # or mxbai-embed-large

# Database Settings
DB_PATH = os.getenv("DB_PATH", "database/recruitment.db")

# Data Paths
JOB_DESCRIPTION_CSV = os.getenv("JOB_DESCRIPTION_CSV", "data/job_descriptions.csv")
RESUMES_DIR = os.getenv("RESUMES_DIR", "data/CVs")

# Agent Settings
SHORTLIST_THRESHOLD = float(os.getenv("SHORTLIST_THRESHOLD", "0.75")) # Adjusted threshold

# Email Settings (for Interview Scheduler) - Fill these in .env or here
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "omkarmutyalwar8072@example.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "rwya oeft ifqc gyh")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "omkarmutyalwar8072@example.com")
# Set to True to actually send emails, False to print to console
ENABLE_EMAIL_SENDING = os.getenv("ENABLE_EMAIL_SENDING", "True").lower() == "true"


# Logging
LOG_FILE = "logs/app.log"
LOG_LEVEL = "INFO" # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Ensure directories exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(RESUMES_DIR, exist_ok=True) # Ensure resume dir exists if not provided by user
# Ensure data dir exists for the JD csv
os.makedirs(os.path.dirname(JOB_DESCRIPTION_CSV), exist_ok=True)