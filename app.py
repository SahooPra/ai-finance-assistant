# app.py - Hugging Face entry point
import sys
import os

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Streamlit config via env vars BEFORE importing streamlit
# This bypasses the .streamlit/config.toml which HF ignores
os.environ["STREAMLIT_SERVER_PORT"] = "7860"
os.environ["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_SERVER_ENABLE_CORS"] = "false"
os.environ["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "false"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from src.workflow.router import run_finance_assistant
from src.utils.portfolio_manager import get_portfolio_summary, reset_portfolio
from src.agents.market_agent import get_stock_data
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf

st.set_page_config(
    page_title="Finnie - AI Finance Assistant",
    page_icon="💰",
    layout="wide"
)

with st.sidebar:
    st.title("💰 Finnie")
    st.caption("Your AI Finance Assistant")
    st.divider()
    st.markdown("""
- 📚 Answer finance questions
- 📈 Look up live stock prices
- 💼 Manage your portfolio
- 🛒 Buy and sell via chat
- 🎯 Plan financial goals
- 📰 Summarize market news
- 🧾 Explain tax concepts
    """)
    st.divider()
    st.caption("⚠️ Simulated portfolio only. Not real money.")

tab1, tab2, tab3 = st.tabs([
    "💬 Chat with Finnie",
    "💼 My Portfolio",
    "📈 Market Data"
])

with tab1:
    st.subheader("Chat with Finnie")
    st.caption("Ask me anything about investing!")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if len(st.session_state.messages) == 0:
        st.markdown("**Try asking:**")
        cols = st.columns(3)
        suggestions = [
            "What is a stock?",
            "How does compound interest work?",
            "What is the price of Apple stock?",
            "How do I save for retirement?",
            "What's the latest news on Tesla?",
            "How does a Roth IRA work?",
        ]
        for i, suggestion in enumerate(suggestions):
            if cols[i % 3].button(suggestion, key=f"sug_{i}"):
                st.session_state.messages.append(
                    {"role": "user", "content": suggestion}
                )
                with st.spinner("Finnie is thinking..."):
                    try:
                        response = run_finance_assistant(
                            suggestion,
                            st.session_state.messages[:-1]
                        )
                    except Exception as e:
                        response = f"⚠️ Error: {str(e)}"
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )
                st.rerun()

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("Ask me anything about investing..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        with st.spinner("Finnie is thinking..."):
            try:
                response = run_finance_assistant(
                    prompt, st.session_state.messages[:-1]
                )
            except Exception as e:
                response = f"⚠️ Error: {str(e)}"
        st.session_state.messages.append(
            {"role": "assistant", "content": response}
        )
        st.chat_message("assistant").write(response)

    if st.session_state.messages:
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()

with tab2:
    st.subheader("My Portfolio")
    col_r, col_reset = st.columns([6, 1])
    with col_reset:
        if st.button("↺ Reset"):
            reset_portfolio()
            st.rerun()

    with st.spinner("Loading portfolio..."):
        try:
            summary = get_portfolio_summary()
        except Exception as e:
            st.error(f"Portfolio error: {e}")
            st.stop()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Value",  f"${summary['total_portfolio_value']:,.2f}")
    c2.metric("Invested",     f"${summary['total_invested']:,.2f}")
    c3.metric("Market Value", f"${summary['total_market_value']:,.2f}")
    c4.metric("Gain / Loss",  f"${summary['total_gain_loss']:,.2f}",
                               f"{summary['total_gain_loss_pct']}%")
    c5.metric("Cash",         f"${summary['cash_balance']:,.2f}")

    st.divider()
    if summary["holdings"]:
        rows = []
        for h in summary["holdings"]:
            g = h["gain_loss"]
            p = h["gain_loss_pct"]
            rows.append({
                "Ticker":        h["ticker"],
                "Shares":        h["shares"],
                "Avg Cost":      f"${h['avg_cost']:,.2f}",
                "Current Price": f"${h['current_price']:,.2f}",
                "Market Value":  f"${h['market_value']:,.2f}",
                "Gain/Loss":     f"+${g:,.2f}" if g >= 0 else f"-${abs(g):,.2f}",
                "Return %":      f"+{p}%" if p >= 0 else f"{p}%",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True)

        col_left, col_right = st.columns(2)
        with col_left:
            fig_pie = px.pie(
                values=[h["market_value"] for h in summary["holdings"]],
                names=[h["ticker"] for h in summary["holdings"]],
                hole=0.4,
            )
            st.plotly_chart(fig_pie)
        with col_right:
            colors = [
                "#10B981" if h["gain_loss"] >= 0 else "#EF4444"
                for h in summary["holdings"]
            ]
            fig_bar = go.Figure(go.Bar(
                x=[h["ticker"]    for h in summary["holdings"]],
                y=[h["gain_loss"] for h in summary["holdings"]],
                marker_color=colors,
            ))
            st.plotly_chart(fig_bar)

    st.divider()
    transactions = summary.get("transactions", [])
    if transactions:
        tx_rows = []
        for tx in transactions[:20]:
            tx_rows.append({
                "Date":   tx["date"],
                "Type":   tx["type"],
                "Ticker": tx["ticker"],
                "Shares": tx["shares"],
                "Price":  f"${tx['price']:,.2f}",
                "Total":  f"${tx['total']:,.2f}",
            })
        st.dataframe(pd.DataFrame(tx_rows), hide_index=True)

with tab3:
    st.subheader("Live Market Data")
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker_input = st.text_input(
            "Ticker symbol:", value="AAPL"
        ).upper().strip()
    with col2:
        period = st.selectbox(
            "Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"]
        )

    if st.button("🔍 Look Up", type="primary"):
        with st.spinner(f"Fetching {ticker_input}..."):
            try:
                data = get_stock_data(ticker_input)
                if "error" in data:
                    st.error(data["error"])
                else:
                    c1, c2, c3, c4 = st.columns(4)
                    sign = "+" if data["change"] >= 0 else ""
                    c1.metric("Price",    f"${data['price']}")
                    c2.metric("Change",   f"{sign}${data['change']}",
                                          f"{sign}{data['change_pct']}%")
                    c3.metric("52W High", f"${data['52_week_high']}")
                    c4.metric("52W Low",  f"${data['52_week_low']}")

                    hist = yf.Ticker(ticker_input).history(period=period)
                    if not hist.empty:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=hist.index, y=hist["Close"],
                            mode="lines",
                            line=dict(color="#1f77b4", width=2),
                            fill="tozeroy",
                        ))
                        st.plotly_chart(fig)
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()
    st.markdown("#### Market Overview")
    watchlist = ["SPY","QQQ","AAPL","MSFT","NVDA","TSLA","AMZN","META"]
    with st.spinner("Loading..."):
        watchlist_data = []
        for t in watchlist:
            try:
                d = get_stock_data(t)
                if "error" not in d:
                    watchlist_data.append({
                        "Ticker":   d["ticker"],
                        "Price":    f"${d['price']}",
                        "Change %": f"{d['change_pct']}%",
                    })
            except Exception:
                pass
    if watchlist_data:
        st.dataframe(pd.DataFrame(watchlist_data), hide_index=True)