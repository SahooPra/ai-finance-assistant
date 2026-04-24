# src/agents/trade_agent.py
import re
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.llm_config import get_llm
from src.utils.portfolio_manager import (
    buy_stock,
    sell_stock,
    get_portfolio_summary,
    get_live_price,
)

# Company name → ticker map
COMPANY_MAP = {
    "apple":     "AAPL",
    "microsoft": "MSFT",
    "google":    "GOOGL",
    "alphabet":  "GOOGL",
    "amazon":    "AMZN",
    "tesla":     "TSLA",
    "nvidia":    "NVDA",
    "meta":      "META",
    "facebook":  "META",
    "netflix":   "NFLX",
    "sp500":     "SPY",
    "s&p 500":   "SPY",
    "nasdaq":    "QQQ",
    "disney":    "DIS",
    "nike":      "NKE",
    "coca cola": "KO",
    "walmart":   "WMT",
    "jpmorgan":  "JPM",
}

SKIP_WORDS = {
    "BUY", "SELL", "SHARES", "SHARE", "STOCK",
    "THE", "AND", "FOR", "OF", "AT", "IN",
    "MY", "ME", "NOW", "ALL", "ANY",
    "WANT", "PLEASE", "LIKE", "SOME",
}


def extract_trade_details(question: str) -> dict:
    """
    Parses natural language into trade action, ticker, and shares.
    Handles both company names and ticker symbols.
    """
    q_lower = question.lower()

    # Detect action
    action = None
    if any(w in q_lower for w in [
        "buy", "purchase", "acquire", "add", "get", "long"
    ]):
        action = "buy"
    elif any(w in q_lower for w in [
        "sell", "dispose", "exit", "close", "offload", "dump"
    ]):
        action = "sell"

    # Detect number of shares
    shares = None
    match = re.search(r"(\d+\.?\d*)\s*(shares?|units?)?", q_lower)
    if match:
        shares = float(match.group(1))

    # Detect ticker from company name first
    ticker = None
    for name, sym in COMPANY_MAP.items():
        if name in q_lower:
            ticker = sym
            break

    # Then look for uppercase ticker symbol
    if not ticker:
        for word in question.split():
            clean = word.strip(".,!?")
            if (2 <= len(clean) <= 5
                    and clean.isupper()
                    and clean.isalpha()
                    and clean not in SKIP_WORDS):
                ticker = clean
                break

    return {"action": action, "ticker": ticker, "shares": shares}


def run_trade_agent(question: str, chat_history: list = []) -> str:
    """
    Processes natural language trade requests.
    Executes buy/sell and returns a conversational response.
    """
    llm     = get_llm(temperature=0.3)
    details = extract_trade_details(question)
    action  = details["action"]
    ticker  = details["ticker"]
    shares  = details["shares"]

    # ── Missing details ───────────────────────────────────────────────────────
    if not action or not ticker or not shares:
        missing = []
        if not action:  missing.append("action (buy or sell)")
        if not ticker:  missing.append("stock ticker or company name")
        if not shares:  missing.append("number of shares")
        return (
            f"I'd love to help you trade! I just need a bit more info:\n\n"
            f"**Missing:** {', '.join(missing)}\n\n"
            f"Try:\n"
            f"- *\"Buy 5 shares of Apple\"*\n"
            f"- *\"Sell 2 TSLA\"*\n"
            f"- *\"Purchase 10 NVDA shares\"*\n\n"
            f"*Note: This is a simulated portfolio for educational purposes.*"
        )

    # ── BUY ───────────────────────────────────────────────────────────────────
    if action == "buy":
        price = get_live_price(ticker)
        if not price:
            return (
                f"I couldn't find a valid price for **{ticker}**. "
                f"Please check the ticker symbol and try again."
            )

        result = buy_stock(ticker, shares, note="Bought via chat")

        if result["success"]:
            updated = get_portfolio_summary()
            system_prompt = f"""You are Finnie, a friendly financial education assistant.
A simulated buy trade was executed. Confirm it conversationally and add
a brief educational insight about the stock or investing concept.

Trade executed:
- Bought {shares} shares of {ticker} at ${price}
- Total cost: ${result['total']:,.2f}
- Remaining cash: ${result['remaining_cash']:,.2f}
- Portfolio total value: ${updated['total_portfolio_value']:,.2f}

Keep response under 120 words. Be warm and encouraging.
Remind the user this is a simulated educational portfolio.
Do not say "Note:" — weave the disclaimer naturally."""

            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=question)
            ])
            return response.content

        else:
            return f"❌ {result['message']}"

    # ── SELL ──────────────────────────────────────────────────────────────────
    elif action == "sell":
        price = get_live_price(ticker)
        if not price:
            return (
                f"I couldn't find a valid price for **{ticker}**. "
                f"Please check the ticker symbol and try again."
            )

        result = sell_stock(ticker, shares, note="Sold via chat")

        if result["success"]:
            updated  = get_portfolio_summary()
            gain     = result["realized_gain"]
            gain_pct = result["realized_pct"]
            gain_label = (
                f"a gain of **${gain:,.2f} ({gain_pct}%)**"
                if gain >= 0
                else f"a loss of **${abs(gain):,.2f} ({gain_pct}%)**"
            )

            system_prompt = f"""You are Finnie, a friendly financial education assistant.
A simulated sell trade was executed. Confirm it conversationally.

Trade executed:
- Sold {shares} shares of {ticker} at ${price}
- Proceeds: ${result['proceeds']:,.2f}
- Realized {gain_label}
- Updated cash: ${result['updated_cash']:,.2f}
- Portfolio total value: ${updated['total_portfolio_value']:,.2f}

{"Briefly mention capital gains tax concepts since there was a gain." if gain > 0 else "Briefly mention tax-loss harvesting since there was a loss."}

Keep under 140 words. Be warm and encouraging.
Remind the user this is a simulated educational portfolio naturally."""

            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=question)
            ])
            return response.content

        else:
            return f"❌ {result['message']}"

    return (
        "I couldn't process that trade. Try: "
        "*\"Buy 5 Apple shares\"* or *\"Sell 2 TSLA\"*"
    )