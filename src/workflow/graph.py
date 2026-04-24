# src/workflow/graph.py
from typing import TypedDict
from langgraph.graph import StateGraph, END
from src.agents.qa_agent import run_qa_agent
from src.agents.market_agent import run_market_agent
from src.agents.portfolio_agent import run_portfolio_agent
from src.agents.goal_agent import run_goal_agent
from src.agents.news_agent import run_news_agent
from src.agents.tax_agent import run_tax_agent
from src.utils.guardrails import (
    check_input,
    check_output,
    add_referral_note
)


class FinanceState(TypedDict):
    question: str
    intent: str
    response: str
    chat_history: list
    holdings: list
    error: str
    blocked: bool       # True if input guardrail blocked the question
    needs_referral: bool  # True if response should suggest a professional


# ── Node: Input Guardrail ─────────────────────────────────────────────────────
def input_guardrail_node(state: FinanceState) -> FinanceState:
    """
    First node — checks question before routing to any agent.
    Blocks harmful, off-topic, or illegal requests.
    """
    print("[Guardrail] Checking input...")
    result = check_input(state["question"])

    if not result["safe"]:
        print(f"[Guardrail] Input blocked: {result['reason']}")
        return {
            **state,
            "blocked": True,
            "response": result["response"],
        }

    return {
        **state,
        "blocked": False,
        "needs_referral": result.get("needs_referral", False),
    }


def route_after_input_guardrail(state: FinanceState) -> str:
    """Routes to blocked handler or intent detection."""
    if state.get("blocked"):
        return "blocked"
    return "detect_intent"


# ── Node: Intent Detection ────────────────────────────────────────────────────
def detect_intent_node(state: FinanceState) -> FinanceState:
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


# ── Agent Nodes ───────────────────────────────────────────────────────────────
def qa_node(state: FinanceState) -> FinanceState:
    print("[LangGraph] Running QA agent...")
    try:
        response = run_qa_agent(state["question"], state.get("chat_history", []))
        return {**state, "response": response, "error": ""}
    except Exception as e:
        return {**state, "response": "", "error": str(e)}


def market_node(state: FinanceState) -> FinanceState:
    print("[LangGraph] Running Market agent...")
    try:
        response = run_market_agent(state["question"], state.get("chat_history", []))
        return {**state, "response": response, "error": ""}
    except Exception as e:
        return {**state, "response": "", "error": str(e)}


def portfolio_node(state: FinanceState) -> FinanceState:
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
    print("[LangGraph] Running Goal agent...")
    try:
        response = run_goal_agent(state["question"], state.get("chat_history", []))
        return {**state, "response": response, "error": ""}
    except Exception as e:
        return {**state, "response": "", "error": str(e)}


def news_node(state: FinanceState) -> FinanceState:
    print("[LangGraph] Running News agent...")
    try:
        response = run_news_agent(state["question"], state.get("chat_history", []))
        return {**state, "response": response, "error": ""}
    except Exception as e:
        return {**state, "response": "", "error": str(e)}


def tax_node(state: FinanceState) -> FinanceState:
    print("[LangGraph] Running Tax agent...")
    try:
        response = run_tax_agent(state["question"], state.get("chat_history", []))
        return {**state, "response": response, "error": ""}
    except Exception as e:
        return {**state, "response": "", "error": str(e)}


# ── Node: Output Guardrail ────────────────────────────────────────────────────
def output_guardrail_node(state: FinanceState) -> FinanceState:
    """
    Last node before returning to user.
    Cleans response, adds disclaimers, appends referral note if needed.
    """
    print("[Guardrail] Checking output...")
    response = state.get("response", "")

    if not response:
        return state

    result = check_output(response, state["question"])
    cleaned = result["cleaned_response"]

    # Add professional referral note if flagged
    if state.get("needs_referral"):
        cleaned = add_referral_note(cleaned)
        print("[Guardrail] Added professional referral note.")

    if result["warning_added"]:
        print("[Guardrail] Added/strengthened disclaimer.")

    return {**state, "response": cleaned}


# ── Node: Blocked response ────────────────────────────────────────────────────
def blocked_node(state: FinanceState) -> FinanceState:
    """Passes through the blocked message from input guardrail."""
    print("[Guardrail] Returning blocked response.")
    return state


# ── Node: Error handler ───────────────────────────────────────────────────────
def error_handler_node(state: FinanceState) -> FinanceState:
    print(f"[LangGraph] Error handled: {state.get('error')}")
    fallback = (
        "I'm sorry, I encountered an issue processing your request. "
        "Please try rephrasing your question or try again in a moment.\n\n"
        "*Note: This is educational information only, not financial advice.*"
    )
    return {**state, "response": fallback}


def route_to_agent(state: FinanceState) -> str:
    return state["intent"]


def check_for_error(state: FinanceState) -> str:
    if state.get("error"):
        return "error"
    return "output_guardrail"


# ── Build the Graph ───────────────────────────────────────────────────────────
def build_finance_graph():
    graph = StateGraph(FinanceState)

    # Add all nodes
    graph.add_node("input_guardrail",  input_guardrail_node)
    graph.add_node("detect_intent",    detect_intent_node)
    graph.add_node("blocked",          blocked_node)
    graph.add_node("qa",               qa_node)
    graph.add_node("market",           market_node)
    graph.add_node("portfolio",        portfolio_node)
    graph.add_node("goal",             goal_node)
    graph.add_node("news",             news_node)
    graph.add_node("tax",              tax_node)
    graph.add_node("output_guardrail", output_guardrail_node)
    graph.add_node("error_handler",    error_handler_node)

    # Entry point → input guardrail always runs first
    graph.set_entry_point("input_guardrail")

    # After input guardrail: blocked or detect intent
    graph.add_conditional_edges(
        "input_guardrail",
        route_after_input_guardrail,
        {
            "blocked":      "blocked",
            "detect_intent": "detect_intent",
        }
    )

    # Blocked → output guardrail (to add formatting) → END
    graph.add_edge("blocked", "output_guardrail")

    # After intent detection → route to correct agent
    graph.add_conditional_edges(
        "detect_intent",
        route_to_agent,
        {
            "qa":        "qa",
            "market":    "market",
            "portfolio": "portfolio",
            "goal":      "goal",
            "news":      "news",
            "tax":       "tax",
        }
    )

    # After each agent → check for error or go to output guardrail
    for agent in ["qa", "market", "portfolio", "goal", "news", "tax"]:
        graph.add_conditional_edges(
            agent,
            check_for_error,
            {
                "output_guardrail": "output_guardrail",
                "error":            "error_handler",
            }
        )

    # Output guardrail and error handler → END
    graph.add_edge("output_guardrail", END)
    graph.add_edge("error_handler",    END)

    return graph.compile()


finance_graph = build_finance_graph()