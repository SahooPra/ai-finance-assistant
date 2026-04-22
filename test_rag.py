# test_rag.py
from src.rag.knowledge_base import retrieve_context

result = retrieve_context("What is an ETF?")
print("=== RAG RESULT ===")
print(result[:500])
print("==================")