# src/agents/news_agent.py
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.llm_config import get_llm
import yfinance as yf

def get_stock_news(ticker: str = "AAPL") -> list:
    """
    Fetches recent news headlines for a stock using yFinance.
    """
    try:
        stock = yf.Ticker(ticker)
        news = stock.news[:5]  # top 5 news items
        headlines = []
        for item in news:
            content = item.get("content", {})
            headlines.append({
                "title": content.get("title", "No title"),
                "summary": content.get("summary", ""),
            })
        return headlines
    except Exception as e:
        return [{"title": "Could not fetch news", "summary": str(e)}]


def run_news_agent(question: str, chat_history: list = []) -> str:
    """
    Fetches and explains financial news in simple terms.
    """
    llm = get_llm(temperature=0.3)

    # Detect ticker in question
    common_tickers = {
        "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL",
        "amazon": "AMZN", "tesla": "TSLA", "meta": "META",
        "nvidia": "NVDA", "netflix": "NFLX",
    }

    ticker = "SPY"  # default to S&P 500
    question_lower = question.lower()
    for name, t in common_tickers.items():
        if name in question_lower:
            ticker = t
            break

    # Check for direct ticker mention
    for word in question.upper().split():
        clean = word.strip("?.,!")
        if 2 <= len(clean) <= 5 and clean.isalpha():
            ticker = clean
            break

    news_items = get_stock_news(ticker)
    news_text = "\n".join([
        f"- {item['title']}: {item['summary']}"
        for item in news_items
    ])

    system_prompt = f"""You are Finnie, a friendly financial education assistant
specializing in making financial news easy to understand for beginners.

Here are the latest news headlines I found for {ticker}:
{news_text}

Guidelines:
- Summarize the news in plain, simple English
- Explain WHY this news might matter to investors (educationally)
- Avoid sensationalism — be calm and balanced
- Remind users that news alone should not drive investment decisions
- Always end with: "Note: This is educational information only, not financial advice."
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question)
    ]

    response = llm.invoke(messages)
    return response.content