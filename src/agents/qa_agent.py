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
- Always end responses with this disclaimer:
  "Note: This is educational information only, not personalized financial advice.
   Please consult a financial advisor for personal guidance."
"""


def format_citations(citations: list) -> str:
    """
    Formats citations into a clean readable block.
    """
    if not citations:
        return ""

    citation_lines = ["\n\n---\n**Sources:**"]
    for i, c in enumerate(citations, 1):
        title = c.get("title", "Unknown")
        source = c.get("source", "Finnie Knowledge Base")
        url = c.get("url", "")

        if url:
            citation_lines.append(f"{i}. [{title}]({url}) — {source}")
        else:
            citation_lines.append(f"{i}. {title} — {source}")

    return "\n".join(citation_lines)


def run_qa_agent(
    question: str,
    chat_history: list = [],
    return_citations: bool = True
) -> str:
    """
    Answers general financial education questions using RAG.
    Appends source citations to the response.
    """
    llm = get_llm(temperature=0.3)

    # Retrieve relevant context AND citations from knowledge base
    context, citations = retrieve_context(question)

    system_content = SYSTEM_PROMPT
    if context:
        system_content += f"""

Here is relevant information from the knowledge base to help answer this question:

{context}

Use this information to give an accurate, grounded answer.
When referencing this content, naturally mention the source title
(e.g. "According to the Wikipedia article on ETFs..." or
"Based on our knowledge base on compound interest...").
"""

    messages = [SystemMessage(content=system_content)]

    for msg in chat_history[-6:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(SystemMessage(content=msg["content"]))

    messages.append(HumanMessage(content=question))

    response = llm.invoke(messages)
    answer = response.content

    # Append citations if we have them
    if return_citations and citations:
        answer += format_citations(citations)

    return answer