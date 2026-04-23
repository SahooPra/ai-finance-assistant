# test_citations.py
import sys, os
sys.path.insert(0, os.path.abspath("."))

from src.agents.qa_agent import run_qa_agent

questions = [
    "What is an ETF?",
    "How does compound interest work?",
    "What is a 401k?",
]

for q in questions:
    print(f"\nQ: {q}")
    print("-" * 50)
    response = run_qa_agent(q)
    print(response)
    print()