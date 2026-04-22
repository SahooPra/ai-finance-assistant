# src/agents/market_agent.py
import yfinance as yf
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.llm_config import get_llm

def get_stock_data(ticker: str) -> dict:
    """
    Fetches real-time stock data for a given ticker symbol.
    Example: get_stock_data("AAPL") for Apple
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info
        hist = stock.history(period="5d")  # last 5 days

        if hist.empty:
            return {"error": f"No data found for ticker '{ticker}'"}

        latest_price = hist["Close"].iloc[-1]
        prev_price = hist["Close"].iloc[-2] if len(hist) > 1 else latest_price
        change = latest_price - prev_price
        change_pct = (change / prev_price) * 100

        return {
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker.upper()),
            "price": round(latest_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": info.get("volume", "N/A"),
            "market_cap": info.get("marketCap", "N/A"),
            "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
            "pe_ratio": info.get("trailingPE", "N/A"),
            "sector": info.get("sector", "N/A"),
        }
    except Exception as e:
        return {"error": f"Could not fetch data for '{ticker}': {str(e)}"}


def run_market_agent(question: str, chat_history: list = []) -> str:
    """
    Handles market data questions. Detects ticker symbols in the question,
    fetches live data, then asks the LLM to explain it in plain English.
    """
    llm = get_llm(temperature=0.2)
# Check for direct ticker symbols (e.g. AAPL, TSLA)
    SKIP_WORDS = {
        "WHAT", "WHEN", "WHERE", "HOW", "THE", "FOR", "AND", "IS",
        "ARE", "WAS", "WILL", "CAN", "DOES", "PRICE", "STOCK",
        "APPLE", "TELL", "ME", "ABOUT", "GIVE", "SHOW", "TODAY"
    }

    words = question.upper().split()
    for word in words:
        clean = word.strip("?.,!")
    if (2 <= len(clean) <= 5
            and clean.isalpha()
            and clean not in SKIP_WORDS):
        found_tickers.append(clean)


    # Common tickers to detect in questions
    common_tickers = {
        "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL",
        "alphabet": "GOOGL", "amazon": "AMZN", "tesla": "TSLA",
        "meta": "META", "facebook": "META", "nvidia": "NVDA",
        "netflix": "NFLX", "sp500": "SPY", "s&p": "SPY",
        "nasdaq": "QQQ", "dow": "DIA", "bitcoin": "BTC-USD",
    }

    # Find tickers mentioned in the question
    question_lower = question.lower()
    found_tickers = []

    # Check for company names
    for name, ticker in common_tickers.items():
        if name in question_lower:
            found_tickers.append(ticker)

    # Check for direct ticker symbols (e.g. AAPL, TSLA)
    words = question.upper().split()
    for word in words:
        clean = word.strip("?.,!")
        if 2 <= len(clean) <= 5 and clean.isalpha() and clean not in ["WHAT", "WHEN", "WHERE", "HOW", "THE", "FOR", "AND"]:
            found_tickers.append(clean)

    # Remove duplicates
    found_tickers = list(set(found_tickers))

    # Fetch stock data for found tickers
    stock_info = ""
    if found_tickers:
        for ticker in found_tickers[:3]:  # max 3 stocks at once
            data = get_stock_data(ticker)
            if "error" not in data:
                direction = "up" if data["change"] >= 0 else "down"
                stock_info += f"""
{data['name']} ({data['ticker']}):
- Current Price: ${data['price']}
- Today's Change: {direction} ${abs(data['change'])} ({data['change_pct']}%)
- 52-Week High: ${data['52_week_high']}
- 52-Week Low: ${data['52_week_low']}
- P/E Ratio: {data['pe_ratio']}
- Sector: {data['sector']}
"""
            else:
                stock_info += f"\n{data['error']}\n"

    system_prompt = f"""You are Finnie, a friendly financial education assistant.
You help beginners understand stock market data in plain, simple English.

{'Here is the current market data I retrieved:' + stock_info if stock_info else ''}

Guidelines:
- Explain what the numbers mean for a beginner
- Put price changes in context (is this normal? big move?)
- Never tell users to buy or sell specific stocks
- Always end with: "Note: This is educational information only, not financial advice."
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question)
    ]

    response = llm.invoke(messages)
    return response.content