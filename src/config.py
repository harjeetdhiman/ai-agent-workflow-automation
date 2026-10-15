import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Excel file path (defaults to data/ directory)
EXCEL_WORKFLOW_FILE = os.getenv(
    "EXCEL_WORKFLOW_FILE",
    str(DATA_DIR / "AI_Agent_Workflow_Assessment (1).xlsx")
)

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")  # 'openai', 'mock', or 'auto'
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))

# Thresholds
DEFAULT_THRESHOLD = int(os.getenv("DEFAULT_THRESHOLD", "10"))
DEFAULT_PRICE_VARIANCE_THRESHOLD = float(os.getenv("DEFAULT_PRICE_VARIANCE_THRESHOLD", "0.10"))  # 10%
DEFAULT_PERFORMANCE_FAILURE_THRESHOLD = float(os.getenv("DEFAULT_PERFORMANCE_FAILURE_THRESHOLD", "0.10"))  # 10%
DEFAULT_PERFORMANCE_LATENCY_THRESHOLD = float(os.getenv("DEFAULT_PERFORMANCE_LATENCY_THRESHOLD", "5.0"))  # seconds
DEFAULT_SIMILARITY_THRESHOLD = float(os.getenv("DEFAULT_SIMILARITY_THRESHOLD", "0.85"))
