# src/workflow/graph.py
from typing import TypedDict
from langgraph.graph import StateGraph, END
from src.agents.qa_agent import run_qa_agent
from src.agents.market_agent import run_market_agent
from src.agents.portfolio_agent import run_portfolio_agent
from src.agents.goal_agent import run_goal_agent
from src.agents.news_agent import run_news_agent
from src.agents.tax_agent import run_tax_agent
from src.agents.trade_agent import run_trade_agent
from src.utils.guardrails import (
    check_input, check_output, add_referral_note
)


class FinanceState(TypedDict):
    question:      str
    intent:        str
    response:      str
    chat_history:  list
    holdings:      list
    error:         str
    blocked:       bool
    needs_referral: bool


# ── Input guardrail ───────────────────────────────────────────────────────────
def input_guardrail_node(state: FinanceState) -> FinanceState:
    print("[Guardrail] Checking input...")
    result = check_input(state["question"])
    if not result["safe"]:
        print(f"[Guardrail] Blocked: {result['reason']}")
        return {**state, "blocked": True, "response": result["response"]}
    return {
        **state,
        "blocked":       False,
        "needs_referral": result.get("needs_referral", False),
    }


def route_after_input_guardrail(state: FinanceState) -> str:
    return "blocked" if state.get("blocked") else "detect_intent"


# ── Intent detection ──────────────────────────────────────────────────────────
def detect_intent_node(state: FinanceState) -> FinanceState:
    question = state["question"].lower()

    trade_keywords = [
        "buy ", "sell ", "purchase ", "acquire ",
        "buy shares", "sell shares", "i want to buy",
        "i want to sell", "can you buy", "can you sell",
        "place a trade", "execute a trade",
        "add to my portfolio", "buy stock", "sell stock",
    ]
    market_keywords = [
        "price", "stock price", "trading at", "share price",
        "how much is", "current price", "market cap",
        "aapl", "tsla", "nvda", "msft", "googl", "amzn",
        "apple stock", "tesla stock", "sp500", "nasdaq", "dow",
    ]
    portfolio_keywords = [
        "my portfolio", "my stocks", "my holdings", "i own",
        "my shares", "portfolio analysis", "how am i doing",
    ]
    goal_keywords = [
        "retire", "retirement", "save for", "saving for", "goal",
        "emergency fund", "buy a house", "financial goal",
        "budget", "50/30/20", "how long will it take",
    ]
    news_keywords = [
        "news", "latest", "headline", "what happened",
        "recent", "market news", "what's happening",
    ]
    tax_keywords = [
        "tax", "taxes", "capital gains", "401k", "ira", "roth",
        "tax-advantaged", "pre-tax", "post-tax", "hsa",
    ]

    if any(w in question for w in trade_keywords):
        intent = "trade"
    elif any(w in question for w in market_keywords):
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


# ── Agent nodes ───────────────────────────────────────────────────────────────
def _run(fn, state, *args):
    try:
        response = fn(*args)
        return {**state, "response": response, "error": ""}
    except Exception as e:
        return {**state, "response": "", "error": str(e)}


def qa_node(state):
    print("[LangGraph] Running QA agent...")
    return _run(run_qa_agent, state,
                state["question"], state.get("chat_history", []))

def market_node(state):
    print("[LangGraph] Running Market agent...")
    return _run(run_market_agent, state,
                state["question"], state.get("chat_history", []))

def portfolio_node(state):
    print("[LangGraph] Running Portfolio agent...")
    return _run(run_portfolio_agent, state,
                state["question"],
                state.get("holdings", []),
                state.get("chat_history", []))

def goal_node(state):
    print("[LangGraph] Running Goal agent...")
    return _run(run_goal_agent, state,
                state["question"], state.get("chat_history", []))

def news_node(state):
    print("[LangGraph] Running News agent...")
    return _run(run_news_agent, state,
                state["question"], state.get("chat_history", []))

def tax_node(state):
    print("[LangGraph] Running Tax agent...")
    return _run(run_tax_agent, state,
                state["question"], state.get("chat_history", []))

def trade_node(state):
    print("[LangGraph] Running Trade agent...")
    return _run(run_trade_agent, state,
                state["question"], state.get("chat_history", []))

def blocked_node(state):
    print("[Guardrail] Returning blocked response.")
    return state

def error_handler_node(state):
    print(f"[LangGraph] Error: {state.get('error')}")
    return {**state, "response": (
        "I encountered an issue processing your request. "
        "Please try rephrasing and try again.\n\n"
        "*Note: Educational tool only, not financial advice.*"
    )}


# ── Output guardrail ──────────────────────────────────────────────────────────
def output_guardrail_node(state: FinanceState) -> FinanceState:
    print("[Guardrail] Checking output...")
    response = state.get("response", "")
    if not response:
        return state

    result  = check_output(response, state["question"])
    cleaned = result["cleaned_response"]

    if state.get("needs_referral"):
        cleaned = add_referral_note(cleaned)

    return {**state, "response": cleaned}


# ── Routing functions ─────────────────────────────────────────────────────────
def route_to_agent(state: FinanceState) -> str:
    return state["intent"]


def check_for_error(state: FinanceState) -> str:
    return "error" if state.get("error") else "output_guardrail"


# ── Build graph ───────────────────────────────────────────────────────────────
def build_finance_graph():
    graph = StateGraph(FinanceState)

    # Nodes
    graph.add_node("input_guardrail",  input_guardrail_node)
    graph.add_node("detect_intent",    detect_intent_node)
    graph.add_node("blocked",          blocked_node)
    graph.add_node("qa",               qa_node)
    graph.add_node("market",           market_node)
    graph.add_node("portfolio",        portfolio_node)
    graph.add_node("goal",             goal_node)
    graph.add_node("news",             news_node)
    graph.add_node("tax",              tax_node)
    graph.add_node("trade",            trade_node)
    graph.add_node("output_guardrail", output_guardrail_node)
    graph.add_node("error_handler",    error_handler_node)

    # Entry
    graph.set_entry_point("input_guardrail")

    # Input guardrail → blocked or detect_intent
    graph.add_conditional_edges(
        "input_guardrail",
        route_after_input_guardrail,
        {"blocked": "blocked", "detect_intent": "detect_intent"}
    )

    # Blocked → output guardrail → END
    graph.add_edge("blocked", "output_guardrail")

    # Intent → agent
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
            "trade":     "trade",
        }
    )

    # Each agent → error check → output guardrail or error
    for agent in [
        "qa", "market", "portfolio",
        "goal", "news", "tax", "trade"
    ]:
        graph.add_conditional_edges(
            agent,
            check_for_error,
            {
                "output_guardrail": "output_guardrail",
                "error":            "error_handler",
            }
        )

    graph.add_edge("output_guardrail", END)
    graph.add_edge("error_handler",    END)

    return graph.compile()


finance_graph = build_finance_graph()