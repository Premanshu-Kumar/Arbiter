"""
Configuration settings for Multi-Agent Data Analyst
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Jev Configuration
JEV_API_KEY = os.getenv("JEV_API_KEY", "")
JEV_MODEL = os.getenv("JEV_MODEL", "jev-1")

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Model Configuration
CODER_MODEL = os.getenv("CODER_MODEL", "phi3:mini")
REASONING_MODEL = os.getenv("REASONING_MODEL", "phi3:mini")

# Execution Configuration
MAX_RETRIES = 3
EXECUTION_TIMEOUT = 30  # seconds

# File Configuration
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Paths
DATA_DIR = "data"
REPORTS_DIR = "reports"
PROMPTS_DIR = "prompts"
TEMPLATES_DIR = "templates"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
