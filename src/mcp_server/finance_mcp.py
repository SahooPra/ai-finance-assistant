# src/mcp_server/finance_mcp.py
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from src.agents.market_agent import get_stock_data
from src.agents.portfolio_agent import analyze_portfolio
from src.rag.knowledge_base import retrieve_context
from src.agents.qa_agent import run_qa_agent
from src.agents.goal_agent import run_goal_agent
from src.agents.tax_agent import run_tax_agent

# Create the MCP server instance
server = Server("finnie-finance-server")


# ── Tool 1: Get Stock Price ───────────────────────────────────────────────────
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    Declares all tools that Finnie exposes via MCP.
    Claude Desktop will see these as available tools.
    """
    return [
        types.Tool(
            name="get_stock_price",
            description="Get real-time stock price and details for a ticker symbol. Returns current price, daily change, 52-week high/low, P/E ratio, and sector.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol e.g. AAPL, TSLA, NVDA, SPY"
                    }
                },
                "required": ["ticker"]
            }
        ),
        types.Tool(
            name="analyze_portfolio",
            description="Analyze a stock portfolio with real-time prices. Calculates total value, cost basis, and gain/loss for each holding.",
            inputSchema={
                "type": "object",
                "properties": {
                    "holdings": {
                        "type": "array",
                        "description": "List of stock holdings",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ticker": {"type": "string", "description": "Stock ticker symbol"},
                                "shares": {"type": "number", "description": "Number of shares owned"},
                                "avg_cost": {"type": "number", "description": "Average cost per share in USD"}
                            },
                            "required": ["ticker", "shares", "avg_cost"]
                        }
                    }
                },
                "required": ["holdings"]
            }
        ),
        types.Tool(
            name="search_finance_knowledge",
            description="Search the financial education knowledge base for information about investing concepts, retirement accounts, ETFs, bonds, and more.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Financial question or topic to search for"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="ask_finance_question",
            description="Ask Finnie a general financial education question. Gets a beginner-friendly explanation with RAG-grounded knowledge.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Financial education question to ask Finnie"
                    }
                },
                "required": ["question"]
            }
        ),
        types.Tool(
            name="get_goal_advice",
            description="Get financial goal planning advice. Ask about saving for retirement, emergency funds, house down payment, or any savings goal.",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "The financial goal or planning question"
                    }
                },
                "required": ["goal"]
            }
        ),
        types.Tool(
            name="get_tax_education",
            description="Get educational information about investment taxes, 401k, Roth IRA, Traditional IRA, capital gains, and tax-advantaged accounts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Tax-related question about investing"
                    }
                },
                "required": ["question"]
            }
        ),
    ]


# ── Tool Execution ────────────────────────────────────────────────────────────
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Handles tool calls from Claude Desktop.
    Routes to the appropriate Finnie agent.
    """
    try:
        if name == "get_stock_price":
            ticker = arguments["ticker"]
            data = get_stock_data(ticker)

            if "error" in data:
                result = f"Error: {data['error']}"
            else:
                direction = "up" if data["change"] >= 0 else "down"
                result = f"""Stock Data for {data['name']} ({data['ticker']}):
- Current Price: ${data['price']}
- Today's Change: {direction} ${abs(data['change'])} ({data['change_pct']}%)
- 52-Week High: ${data['52_week_high']}
- 52-Week Low: ${data['52_week_low']}
- P/E Ratio: {data['pe_ratio']}
- Sector: {data['sector']}
- Market Cap: ${data['market_cap']:,} if isinstance(data['market_cap'], (int, float)) else data['market_cap']
"""

        elif name == "analyze_portfolio":
            holdings = arguments["holdings"]
            analysis = analyze_portfolio(holdings)

            result = f"""Portfolio Analysis:
- Total Market Value: ${analysis['total_value']:,.2f}
- Total Cost Basis: ${analysis['total_cost']:,.2f}
- Total Gain/Loss: ${analysis['total_gain_loss']:,.2f} ({analysis['total_gain_loss_pct']}%)

Holdings Breakdown:"""
            for h in analysis["holdings"]:
                status = "GAIN" if h["gain_loss"] >= 0 else "LOSS"
                result += f"""
  {h['ticker']}: {h['shares']} shares
    Current: ${h['current_price']} | Value: ${h['market_value']:,.2f}
    Cost: ${h['avg_cost']}/share | {status}: ${abs(h['gain_loss']):,.2f} ({h['gain_loss_pct']}%)"""

        elif name == "search_finance_knowledge":
            query = arguments["query"]
            context = retrieve_context(query)
            result = context if context else "No relevant information found in knowledge base."

        elif name == "ask_finance_question":
            question = arguments["question"]
            result = run_qa_agent(question)

        elif name == "get_goal_advice":
            goal = arguments["goal"]
            result = run_goal_agent(goal)

        elif name == "get_tax_education":
            question = arguments["question"]
            result = run_tax_agent(question)

        else:
            result = f"Unknown tool: {name}"

    except Exception as e:
        result = f"Error executing {name}: {str(e)}"

    return [types.TextContent(type="text", text=result)]


# ── Run the server ────────────────────────────────────────────────────────────
async def main():
    print("Finnie MCP Server starting...", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())