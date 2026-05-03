# app.py  (root level — entry point for Hugging Face)
import sys
import os

# Make sure src is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Simply run the actual app
from src.web_app.app import *