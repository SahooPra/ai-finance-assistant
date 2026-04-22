# tests/test_agents.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.workflow.router import run_finance_assistant
from src.agents.market_agent import get_stock_data
from src.agents.portfolio_agent import analyze_portfolio
from src.rag.knowledge_base import retrieve_context


def test_intent_routing_market():
    """Market questions should return stock price info."""
    response = run_finance_assistant("What is the price of Apple stock?")
    assert isinstance(response, str)
    assert len(response) > 50
    print("PASS: market intent routing")


def test_intent_routing_qa():
    """General questions should return educational content."""
    response = run_finance_assistant("What is a stock?")
    assert isinstance(response, str)
    assert len(response) > 50
    print("PASS: qa intent routing")


def test_intent_routing_tax():
    """Tax questions should route to tax agent."""
    response = run_finance_assistant("How does a Roth IRA work?")
    assert isinstance(response, str)
    assert len(response) > 50
    print("PASS: tax intent routing")


def test_get_stock_data():
    """Stock data fetch should return price info."""
    data = get_stock_data("AAPL")
    assert "error" not in data
    assert "price" in data
    assert data["price"] > 0
    print(f"PASS: stock data fetch - AAPL price: ${data['price']}")


def test_portfolio_analysis():
    """Portfolio analysis should calculate gain/loss correctly."""
    holdings = [
        {"ticker": "AAPL", "shares": 10, "avg_cost": 150.0},
        {"ticker": "MSFT", "shares": 5, "avg_cost": 300.0},
    ]
    result = analyze_portfolio(holdings)
    assert "total_value" in result
    assert "total_gain_loss" in result
    assert len(result["holdings"]) > 0
    print(f"PASS: portfolio analysis - Total value: ${result['total_value']}")


def test_rag_retrieval():
    """RAG should return relevant content for finance questions."""
    result = retrieve_context("What is an ETF?")
    assert isinstance(result, str)
    assert len(result) > 0
    assert "ETF" in result or "fund" in result.lower()
    print("PASS: RAG retrieval working")


if __name__ == "__main__":
    print("Running Finnie test suite...\n")
    test_get_stock_data()
    test_portfolio_analysis()
    test_rag_retrieval()
    test_intent_routing_market()
    test_intent_routing_qa()
    test_intent_routing_tax()
    print("\nAll tests passed!")