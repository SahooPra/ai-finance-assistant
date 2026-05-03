# app.py (root level - Hugging Face entry point)
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Suppress warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables (safe on HF - won't override secrets)
from dotenv import load_dotenv
load_dotenv()

# Launch the real Finnie app
from src.web_app.app import *