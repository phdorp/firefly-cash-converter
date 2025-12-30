import logging
from pathlib import Path
from dotenv import load_dotenv

# Disable logging during test execution
logging.disable(logging.CRITICAL)

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
