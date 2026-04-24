# src/workflow/graph.py
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from concurrent.futures import ThreadPoolExecutor, as_completed

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
from src.core.llm_config import get_llm
from langchain_core.messages import HumanMessage, SystemMessage


# ── State ─────────────────────────────────────────────────────────────────────
class FinanceState(TypedDict):
    question:       str
    intents:        List[str]   # now a LIST — multiple agents possible
    responses:      dict        # agent_name → response text
    final_response: str         # synthesized combined response
    chat_history:   list
    holdings:       list
    error:          str
    blocked:        bool
    needs_referral: bool


# ── Agent registry ────────────────────────────────────────────────────────────
# Maps intent name → callable
def _get_agent_fn(intent: str):
    return {
        "qa":        lambda q, h, ho: run_qa_agent(q, h),
        "market":    lambda q, h, ho: run_market_agent(q, h),
        "portfolio": lambda q, h, ho: run_portfolio_agent(q, ho, h),
        "goal":      lambda q, h, ho: run_goal_agent(q, h),
        "news":      lambda q, h, ho: run_news_agent(q, h),
        "tax":       lambda q, h, ho: run_tax_agent(q, h),
        "trade":     lambda q, h, ho: run_trade_agent(q, h),
    }.get(intent)


# ── Node 1: Input guardrail ───────────────────────────────────────────────────
def input_guardrail_node(state: FinanceState) -> FinanceState:
    print("[Guardrail] Checking input...")
    result = check_input(state["question"])
    if not result["safe"]:
        print(f"[Guardrail] Blocked: {result['reason']}")
        return {
            **state,
            "blocked":       True,
            "final_response": result["response"],
        }
    return {
        **state,
        "blocked":       False,
        "needs_referral": result.get("needs_referral", False),
    }


def route_after_input_guardrail(state: FinanceState) -> str:
    return "blocked" if state.get("blocked") else "planner"


# ── Node 2: Planner ───────────────────────────────────────────────────────────
def planner_node(state: FinanceState) -> FinanceState:
    """
    Reads the question and decides which agents are needed.
    Can return multiple intents for complex multi-part questions.
    Uses both keyword matching AND an LLM planner for accuracy.
    """
    question = state["question"]
    q_lower  = question.lower()

    # Keyword maps
    keyword_map = {
        "trade":     ["buy ", "sell ", "purchase ", "acquire ",
                      "i want to buy", "i want to sell"],
        "market":    ["price", "trading at", "how much is",
                      "current price", "market cap",
                      "aapl", "tsla", "nvda", "msft", "googl",
                      "apple stock", "tesla stock", "sp500"],
        "portfolio": ["my portfolio", "my stocks", "my holdings",
                      "i own", "how am i doing"],
        "news":      ["news", "latest", "headline",
                      "what happened", "what's happening"],
        "tax":       ["tax", "capital gains", "401k", "ira",
                      "roth", "pre-tax", "post-tax", "hsa"],
        "goal":      ["retire", "retirement", "save for",
                      "emergency fund", "financial goal", "budget"],
        "qa":        ["what is", "explain", "how does",
                      "tell me about", "difference between"],
    }

    # Detect all matching intents
    detected = []
    for intent, keywords in keyword_map.items():
        if any(kw in q_lower for kw in keywords):
            detected.append(intent)

    # If multiple found, use LLM to confirm and order them
    if len(detected) > 1 or len(detected) == 0:
        detected = _llm_planner(question, detected)

    # Default fallback
    if not detected:
        detected = ["qa"]

    # Deduplicate while preserving order
    seen = set()
    intents = []
    for i in detected:
        if i not in seen:
            seen.add(i)
            intents.append(i)

    print(f"[Planner] Intents: {intents}")
    return {**state, "intents": intents, "responses": {}}


def _llm_planner(question: str, detected: list) -> list:
    """
    Uses LLM to identify which agents are needed for complex questions.
    Returns ordered list of agent names.
    """
    try:
        llm = get_llm(temperature=0)
        system = """You are a planner for a financial AI assistant.
Given a user question, identify which agents are needed.

Available agents:
- trade     : buy or sell stocks in the virtual portfolio
- market    : get live stock prices and market data
- portfolio : analyze holdings, gain/loss, diversification
- news      : get latest financial news for a stock
- tax       : explain tax concepts, IRA, 401k, capital gains
- goal      : retirement planning, savings goals, budgeting
- qa        : general financial education questions

Rules:
- Return ONLY a comma-separated list of agent names needed
- Order them by logical execution (trade before portfolio, market before news)
- Include only agents actually needed for this question
- Maximum 4 agents per question
- If only one agent needed, return just that one name

Examples:
Q: "Buy 5 Apple shares and tell me the news"   → trade,news
Q: "What is an ETF and how is SPY doing?"       → qa,market
Q: "Sell my TSLA and analyze my portfolio"      → trade,portfolio
Q: "How do taxes work on my gains?"             → tax,portfolio
Q: "What is compound interest?"                 → qa
Q: "Price of NVDA and latest news on it"        → market,news"""

        response = llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=f"Question: {question}")
        ])

        raw = response.content.strip().lower()
        valid = {"trade","market","portfolio","news","tax","goal","qa"}
        result = [
            a.strip() for a in raw.split(",")
            if a.strip() in valid
        ]
        return result if result else detected or ["qa"]

    except Exception as e:
        print(f"[Planner] LLM planner error: {e}")
        return detected or ["qa"]


# ── Node 3: Multi-agent executor ──────────────────────────────────────────────
def multi_agent_executor_node(state: FinanceState) -> FinanceState:
    """
    Runs all required agents.
    Uses parallel execution when multiple agents are needed.
    """
    intents      = state.get("intents", ["qa"])
    question     = state["question"]
    chat_history = state.get("chat_history", [])
    holdings     = state.get("holdings", [])
    responses    = {}

    if len(intents) == 1:
        # Single agent — run directly
        intent = intents[0]
        print(f"[Executor] Single agent: {intent}")
        fn = _get_agent_fn(intent)
        if fn:
            try:
                responses[intent] = fn(question, chat_history, holdings)
            except Exception as e:
                responses[intent] = f"Error in {intent} agent: {str(e)}"
    else:
        # Multiple agents — run in parallel threads
        print(f"[Executor] Running {len(intents)} agents in parallel: {intents}")

        def run_agent(intent):
            fn = _get_agent_fn(intent)
            if fn:
                try:
                    return intent, fn(question, chat_history, holdings)
                except Exception as e:
                    return intent, f"Error in {intent} agent: {str(e)}"
            return intent, f"Agent '{intent}' not found."

        with ThreadPoolExecutor(max_workers=len(intents)) as executor:
            futures = {
                executor.submit(run_agent, intent): intent
                for intent in intents
            }
            for future in as_completed(futures):
                intent, response = future.result()
                responses[intent] = response
                print(f"[Executor] {intent} agent completed.")

    return {**state, "responses": responses, "error": ""}


# ── Node 4: Synthesizer ───────────────────────────────────────────────────────
def synthesizer_node(state: FinanceState) -> FinanceState:
    """
    Combines multiple agent responses into a single coherent answer.
    If only one agent responded, passes it through directly.
    """
    responses = state.get("responses", {})
    intents   = state.get("intents", [])
    question  = state["question"]

    # Single agent — pass through directly
    if len(responses) == 1:
        final = list(responses.values())[0]
        return {**state, "final_response": final}

    # Multiple agents — synthesize with LLM
    print(f"[Synthesizer] Combining {len(responses)} responses...")

    # Build context from all agent responses
    agent_labels = {
        "trade":     "Trade execution",
        "market":    "Market data",
        "portfolio": "Portfolio analysis",
        "news":      "Financial news",
        "tax":       "Tax education",
        "goal":      "Goal planning",
        "qa":        "Financial education",
    }

    combined_context = ""
    for intent in intents:
        if intent in responses:
            label = agent_labels.get(intent, intent.title())
            combined_context += f"\n\n=== {label} ===\n{responses[intent]}"

    try:
        llm = get_llm(temperature=0.3)
        system = """You are Finnie, a friendly financial education assistant.
Multiple specialized agents have processed the user's question.
Your job is to synthesize their responses into ONE clear, coherent answer.

Rules:
- Combine all information naturally — don't just paste responses together
- Use a logical flow: actions first, then data, then education
- Remove duplicate disclaimers — include ONE at the very end
- Keep it conversational and friendly
- If a trade was executed, confirm it clearly at the top
- Maximum 300 words total
- End with: "Note: This is educational information only, not financial advice."
"""

        response = llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=(
                f"User question: {question}\n\n"
                f"Agent responses to synthesize:{combined_context}"
            ))
        ])

        final = response.content

    except Exception as e:
        # Fallback: join responses with headers
        print(f"[Synthesizer] LLM synthesis failed: {e}, using fallback")
        parts = []
        for intent in intents:
            if intent in responses:
                label = agent_labels.get(intent, intent.title())
                parts.append(f"**{label}**\n{responses[intent]}")
        final = "\n\n---\n\n".join(parts)

    return {**state, "final_response": final}


# ── Node 5: Output guardrail ──────────────────────────────────────────────────
def output_guardrail_node(state: FinanceState) -> FinanceState:
    print("[Guardrail] Checking output...")
    response = state.get("final_response", "")
    if not response:
        return state

    result  = check_output(response, state["question"])
    cleaned = result["cleaned_response"]

    if state.get("needs_referral"):
        cleaned = add_referral_note(cleaned)

    return {**state, "final_response": cleaned}


# ── Node 6: Blocked / Error handlers ─────────────────────────────────────────
def blocked_node(state: FinanceState) -> FinanceState:
    print("[Guardrail] Returning blocked response.")
    return state


def error_handler_node(state: FinanceState) -> FinanceState:
    print(f"[LangGraph] Error: {state.get('error')}")
    return {**state, "final_response": (
        "I encountered an issue processing your request. "
        "Please try rephrasing and try again.\n\n"
        "*Note: Educational tool only, not financial advice.*"
    )}


def check_for_error(state: FinanceState) -> str:
    return "error" if state.get("error") else "synthesizer"


# ── Build graph ───────────────────────────────────────────────────────────────
def build_finance_graph():
    graph = StateGraph(FinanceState)

    graph.add_node("input_guardrail",  input_guardrail_node)
    graph.add_node("planner",          planner_node)
    graph.add_node("blocked",          blocked_node)
    graph.add_node("multi_agent",      multi_agent_executor_node)
    graph.add_node("synthesizer",      synthesizer_node)
    graph.add_node("output_guardrail", output_guardrail_node)
    graph.add_node("error_handler",    error_handler_node)

    # Entry → input guardrail
    graph.set_entry_point("input_guardrail")

    # Input guardrail → blocked or planner
    graph.add_conditional_edges(
        "input_guardrail",
        route_after_input_guardrail,
        {
            "blocked": "blocked",
            "planner": "planner",
        }
    )

    # Blocked → output guardrail
    graph.add_edge("blocked", "output_guardrail")

    # Planner → multi_agent executor
    graph.add_edge("planner", "multi_agent")

    # Executor → synthesizer or error
    graph.add_conditional_edges(
        "multi_agent",
        check_for_error,
        {
            "synthesizer": "synthesizer",
            "error":       "error_handler",
        }
    )

    # Synthesizer → output guardrail → END
    graph.add_edge("synthesizer",      "output_guardrail")
    graph.add_edge("output_guardrail", END)
    graph.add_edge("error_handler",    END)

    return graph.compile()


finance_graph = build_finance_graph()