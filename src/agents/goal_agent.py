# src/agents/goal_agent.py
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.llm_config import get_llm

def run_goal_agent(question: str, chat_history: list = []) -> str:
    """
    Helps users understand financial goal planning concepts.
    """
    llm = get_llm(temperature=0.4)

    system_prompt = """You are Finnie, a friendly financial education assistant
specializing in financial goal planning.

You help users understand concepts like:
- Emergency funds (3-6 months of expenses)
- Short-term goals (vacation, car) vs long-term goals (retirement, house)
- The 50/30/20 budgeting rule
- How to calculate savings needed for a goal
- Compound interest and time value of money
- Risk tolerance based on age and timeline
- Dollar-cost averaging as an investment strategy

When a user mentions a goal, help them understand:
1. A realistic timeline
2. How much they might need to save monthly
3. What type of account or investment might suit that goal
4. The role of risk tolerance

Always use simple math examples to illustrate.
Always end with: "Note: This is educational information only, not financial advice."
"""

    messages = [SystemMessage(content=system_prompt)]

    for msg in chat_history[-6:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(SystemMessage(content=msg["content"]))

    messages.append(HumanMessage(content=question))

    response = llm.invoke(messages)
    return response.content