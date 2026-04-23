# rebuild_db.py
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from src.rag.knowledge_base import rebuild_knowledge_base

print("Rebuilding ChromaDB knowledge base...")
rebuild_knowledge_base()
print("Done!")