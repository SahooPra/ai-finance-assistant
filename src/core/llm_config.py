# src/core/llm_config.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

def get_llm(temperature=0.3):
    """
    Returns a ChatOpenAI instance.
    temperature=0.3 means fairly focused answers (0=robotic, 1=creative)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found! Check your .env file.")
    
    return ChatOpenAI(
        model="gpt-4o-mini",  # cheap and fast, great for learning
        temperature=temperature,
        api_key=api_key
    )