# src/workflow/graph.py
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from src.agents.qa_agent import run_qa_agent
from src.agents.market_agent import run_market_agent
from src.agents.portfolio_agent import run_portfolio_agent
from src.agents.goal_agent import run_goal_agent
from src.agents.news_agent import run_news_agent
from src.agents.tax_agent import run_tax_agent


# ── State Definition ──────────────────────────────────────────────────────────
# This is the shared memory that flows through the entire graph.
# Every node can read and write to this state.
class FinanceState(TypedDict):
    question: str           # the user's question
    intent: str             # detected intent (qa, market, portfolio, etc.)
    response: str           # the final answer
    chat_history: list      # conversation history
    holdings: list          # portfolio holdings if provided
    error: str              # error message if something goes wrong


# ── Node 1: Intent Detection ──────────────────────────────────────────────────
def detect_intent_node(state: FinanceState) -> FinanceState:
    """
    Examines the question and decides which agent to use.
    Updates the 'intent' field in state.
    """
    question = state["question"].lower()

    market_keywords = [
        "price", "stock price", "trading at", "share price",
        "how much is", "current price", "market cap",
        "aapl", "tsla", "nvda", "msft", "googl", "amzn", "meta",
        "apple stock", "tesla stock", "nvidia stock",
        "sp500", "nasdaq", "dow", "s&p"
    ]
    portfolio_keywords = [
        "my portfolio", "my stocks", "my holdings", "i own",
        "i bought", "my shares", "portfolio analysis",
        "my investment", "how am i doing", "my position"
    ]
    goal_keywords = [
        "retire", "retirement", "save for", "saving for", "goal",
        "how much do i need", "emergency fund", "buy a house",
        "college fund", "financial goal", "budget", "50/30/20",
        "how long will it take"
    ]
    news_keywords = [
        "news", "latest", "headline", "what happened",
        "recent", "today's news", "market news", "what's happening"
    ]
    tax_keywords = [
        "tax", "taxes", "capital gains", "401k", "ira", "roth",
        "traditional ira", "tax-advantaged", "pre-tax", "post-tax",
        "deduction", "dividend tax", "tax loss", "hsa"
    ]

    if any(w in question for w in market_keywords):
        intent = "market"
    elif any(w in question for w in portfolio_keywords):
        intent = "portfolio"
    elif any(w in question for w in goal_keywords):
        intent = "goal"
    elif any(w in question for w in news_keywords):
        intent = "news"
    elif any(w in question for w in tax_keywords):
        intent = "tax"
    else:
        intent = "qa"

    print(f"[LangGraph] Intent detected: {intent}")
    return {**state, "intent": intent}


# ── Node 2: Agent Execution Nodes ─────────────────────────────────────────────
def qa_node(state: FinanceState) -> FinanceState:
    """Runs the QA agent with RAG support."""
    print("[LangGraph] Running QA agent...")
    try:
        response = run_qa_agent(
            state["question"],
            state.get("chat_history", [])
        )
        return {**state, "response": response, "error": ""}
    except Exception as e:
        return {**state, "response": "", "error": str(e)}


def market_node(state: FinanceState) -> FinanceState:
    """Runs the Market Data agent."""
    print("[LangGraph] Running Market agent...")
    try:
        response = run_market_agent(
            state["question"],
            state.get("chat_history", [])
        )
        return {**state, "response": response, "error": ""}
    except Exception as e:
        return {**state, "response": "", "error": str(e)}


def portfolio_node(state: FinanceState) -> FinanceState:
    """Runs the Portfolio Analysis agent."""
    print("[LangGraph] Running Portfolio agent...")
    try:
        response = run_portfolio_agent(
            state["question"],
            state.get("holdings", []),
            state.get("chat_history", [])
        )
        return {**state, "response": response, "error": ""}
    except Exception as e:
        return {**state, "response": "", "error": str(e)}


def goal_node(state: FinanceState) -> FinanceState:
    """Runs the Goal Planning agent."""
    print("[LangGraph] Running Goal agent...")
    try:
        response = run_goal_agent(
            state["question"],
            state.get("chat_history", [])
        )
        return {**state, "response": response, "error": ""}
    except Exception as e:
        return {**state, "response": "", "error": str(e)}


def news_node(state: FinanceState) -> FinanceState:
    """Runs the News Synthesizer agent."""
    print("[LangGraph] Running News agent...")
    try:
        response = run_news_agent(
            state["question"],
            state.get("chat_history", [])
        )
        return {**state, "response": response, "error": ""}
    except Exception as e:
        return {**state, "response": "", "error": str(e)}


def tax_node(state: FinanceState) -> FinanceState:
    """Runs the Tax Education agent."""
    print("[LangGraph] Running Tax agent...")
    try:
        response = run_tax_agent(
            state["question"],
            state.get("chat_history", [])
        )
        return {**state, "response": response, "error": ""}
    except Exception as e:
        return {**state, "response": "", "error": str(e)}


# ── Node 3: Error Handler ─────────────────────────────────────────────────────
def error_handler_node(state: FinanceState) -> FinanceState:
    """
    Catches errors from any agent and returns a friendly message.
    """
    print(f"[LangGraph] Error handled: {state.get('error')}")
    fallback = (
        "I'm sorry, I encountered an issue processing your request. "
        "Please try rephrasing your question or try again in a moment.\n\n"
        "Note: This is educational information only, not financial advice."
    )
    return {**state, "response": fallback}


# ── Routing Function ──────────────────────────────────────────────────────────
def route_to_agent(state: FinanceState) -> str:
    """
    Called after intent detection.
    Returns the name of the next node to execute.
    This is LangGraph's conditional edge.
    """
    return state["intent"]


def check_for_error(state: FinanceState) -> str:
    """
    Called after each agent node.
    Routes to error handler if something went wrong.
    """
    if state.get("error"):
        return "error"
    return "done"


# ── Build the Graph ───────────────────────────────────────────────────────────
def build_finance_graph():
    """
    Assembles the full LangGraph workflow.
    Returns a compiled, runnable graph.
    """
    graph = StateGraph(FinanceState)

    # Add all nodes
    graph.add_node("detect_intent", detect_intent_node)
    graph.add_node("qa", qa_node)
    graph.add_node("market", market_node)
    graph.add_node("portfolio", portfolio_node)
    graph.add_node("goal", goal_node)
    graph.add_node("news", news_node)
    graph.add_node("tax", tax_node)
    graph.add_node("error_handler", error_handler_node)

    # Set entry point
    graph.set_entry_point("detect_intent")

    # Conditional edge: after intent detection, route to correct agent
    graph.add_conditional_edges(
        "detect_intent",
        route_to_agent,
        {
            "qa": "qa",
            "market": "market",
            "portfolio": "portfolio",
            "goal": "goal",
            "news": "news",
            "tax": "tax",
        }
    )

    # After each agent, check for errors
    for agent in ["qa", "market", "portfolio", "goal", "news", "tax"]:
        graph.add_conditional_edges(
            agent,
            check_for_error,
            {
                "done": END,
                "error": "error_handler"
            }
        )

    # Error handler always ends
    graph.add_edge("error_handler", END)

    return graph.compile()


# Compile once at module level so it's reused
finance_graph = build_finance_graph()