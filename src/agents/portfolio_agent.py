# src/agents/portfolio_agent.py
import yfinance as yf
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.llm_config import get_llm

def analyze_portfolio(holdings: list) -> dict:
    """
    holdings: list of dicts like [{"ticker": "AAPL", "shares": 10, "avg_cost": 150}]
    Returns full portfolio analysis.
    """
    portfolio = []
    total_value = 0
    total_cost = 0

    for holding in holdings:
        ticker = holding["ticker"].upper()
        shares = holding["shares"]
        avg_cost = holding["avg_cost"]

        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if hist.empty:
                continue
            current_price = round(hist["Close"].iloc[-1], 2)
            market_value = round(current_price * shares, 2)
            cost_basis = round(avg_cost * shares, 2)
            gain_loss = round(market_value - cost_basis, 2)
            gain_loss_pct = round((gain_loss / cost_basis) * 100, 2)

            portfolio.append({
                "ticker": ticker,
                "shares": shares,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "market_value": market_value,
                "cost_basis": cost_basis,
                "gain_loss": gain_loss,
                "gain_loss_pct": gain_loss_pct,
            })

            total_value += market_value
            total_cost += cost_basis

        except Exception as e:
            print(f"Error fetching {ticker}: {e}")

    total_gain_loss = round(total_value - total_cost, 2)
    total_gain_loss_pct = round((total_gain_loss / total_cost) * 100, 2) if total_cost > 0 else 0

    return {
        "holdings": portfolio,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_gain_loss": total_gain_loss,
        "total_gain_loss_pct": total_gain_loss_pct,
    }


def run_portfolio_agent(question: str, holdings: list = [], chat_history: list = []) -> str:
    """
    Analyzes user portfolio and provides educational insights.
    """
    llm = get_llm(temperature=0.3)

    portfolio_summary = ""
    if holdings:
        analysis = analyze_portfolio(holdings)
        portfolio_summary = f"""
Portfolio Summary:
- Total Market Value: ${analysis['total_value']}
- Total Cost Basis: ${analysis['total_cost']}
- Total Gain/Loss: ${analysis['total_gain_loss']} ({analysis['total_gain_loss_pct']}%)

Individual Holdings:
"""
        for h in analysis["holdings"]:
            status = "GAIN" if h["gain_loss"] >= 0 else "LOSS"
            portfolio_summary += f"""
  {h['ticker']}: {h['shares']} shares
    Current Price: ${h['current_price']} | Market Value: ${h['market_value']}
    Avg Cost: ${h['avg_cost']} | {status}: ${abs(h['gain_loss'])} ({h['gain_loss_pct']}%)
"""

    system_prompt = f"""You are Finnie, a friendly financial education assistant
specializing in portfolio analysis.

{f"Here is the user's current portfolio data: {portfolio_summary}" if portfolio_summary else "The user has not entered any portfolio holdings yet."}

Guidelines:
- Explain portfolio concepts clearly for beginners
- Comment on diversification, concentration risk, and balance
- Explain what gain/loss percentages mean in simple terms
- Never say "buy this" or "sell that" — only educate
- Always end with: "Note: This is educational information only, not financial advice."
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question)
    ]

    response = llm.invoke(messages)
    return response.content