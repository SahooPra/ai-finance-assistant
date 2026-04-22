# src/agents/qa_agent.py
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.llm_config import get_llm
from src.rag.knowledge_base import retrieve_context

SYSTEM_PROMPT = """You are Finnie, a friendly and knowledgeable financial education
assistant. Your goal is to help beginners understand investing and personal finance.

Guidelines:
- Use simple, jargon-free language
- Give clear, practical explanations with real examples
- If context from the knowledge base is provided, use it to ground your answer
- Always cite when you are using provided reference material
- Always end responses with this disclaimer:
  "Note: This is educational information only, not personalized financial advice.
   Please consult a financial advisor for personal guidance."
"""

def run_qa_agent(question: str, chat_history: list = []) -> str:
    """
    Answers general financial education questions using RAG.
    """
    llm = get_llm(temperature=0.3)

    # Retrieve relevant context from knowledge base
    context = retrieve_context(question)

    # Build system message with context if found
    system_content = SYSTEM_PROMPT
    if context:
        system_content += f"""

Here is relevant information from the knowledge base to help answer this question:

{context}

Use this information to give an accurate, grounded answer.
"""

    messages = [SystemMessage(content=system_content)]

    # Add chat history for context
    for msg in chat_history[-6:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(SystemMessage(content=msg["content"]))

    messages.append(HumanMessage(content=question))

    response = llm.invoke(messages)
    return response.content