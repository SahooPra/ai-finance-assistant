# src/web_app/app.py
import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.workflow.router import run_finance_assistant
from src.agents.portfolio_agent import analyze_portfolio
from src.agents.market_agent import get_stock_data

# Add these imports for trade execution and portfolio management
from src.utils.portfolio_manager import (
    get_portfolio_summary,
    reset_portfolio,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finnie - AI Finance Assistant",
    page_icon="💰",
    layout="wide"
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("💰 Finnie")
    st.caption("Your AI Finance Assistant")
    st.divider()
    st.markdown("**What can Finnie do?**")
    st.markdown("""
- 📚 Answer finance questions
- 📈 Look up live stock prices
- 💼 Analyze your portfolio
- 🎯 Help plan financial goals
- 📰 Summarize market news
- 🧾 Explain tax concepts
    """)
    st.divider()
    st.caption("⚠️ Educational use only. Not financial advice.")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["💬 Chat with Finnie", "💼 Portfolio Analysis", "📈 Market Data"])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — CHAT
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Chat with Finnie")
    st.caption("Ask me anything about investing, stocks, taxes, or financial planning!")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Starter suggestions
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
                st.session_state.messages.append({"role": "user", "content": suggestion})
                with st.spinner("Finnie is thinking..."):
                    response = run_finance_assistant(suggestion, st.session_state.messages[:-1])
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()

    # Chat history
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask me anything about investing..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        with st.spinner("Finnie is thinking..."):
            response = run_finance_assistant(
                prompt,
                st.session_state.messages[:-1]
            )

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)

    # Clear chat button
    if st.session_state.messages:
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 2: MY PORTFOLIO 
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("My Portfolio")
    st.caption("Live portfolio updated automatically as you trade via chat.")

    col_r, col_reset = st.columns([6, 1])
    with col_r:
        st.button("🔄 Refresh", type="primary")
    with col_reset:
        if st.button("↺ Reset"):
            reset_portfolio()
            st.success("Portfolio reset to default!")
            st.rerun()

    with st.spinner("Loading live portfolio..."):
        summary = get_portfolio_summary()

    # ── Metrics ──
    st.divider()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Value",
              f"${summary['total_portfolio_value']:,.2f}")
    c2.metric("Invested",
              f"${summary['total_invested']:,.2f}")
    c3.metric("Market Value",
              f"${summary['total_market_value']:,.2f}")
    c4.metric("Gain / Loss",
              f"${summary['total_gain_loss']:,.2f}",
              f"{summary['total_gain_loss_pct']}%")
    c5.metric("Cash Available",
              f"${summary['cash_balance']:,.2f}")

    st.divider()

    # ── Holdings table ──
    st.markdown("#### Holdings")
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
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # ── Charts ──
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("#### Allocation")
            fig_pie = px.pie(
                values=[h["market_value"] for h in summary["holdings"]],
                names=[h["ticker"]       for h in summary["holdings"]],
                hole=0.4,
            )
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_right:
            st.markdown("#### Gain / Loss by Stock")
            colors = [
                "#10B981" if h["gain_loss"] >= 0 else "#EF4444"
                for h in summary["holdings"]
            ]
            fig_bar = go.Figure(go.Bar(
                x=[h["ticker"]    for h in summary["holdings"]],
                y=[h["gain_loss"] for h in summary["holdings"]],
                marker_color=colors,
                text=[f"${h['gain_loss']:,.2f}" for h in summary["holdings"]],
                textposition="outside",
            ))
            fig_bar.update_layout(
                yaxis_title="Gain / Loss ($)",
                margin=dict(t=20, b=10),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.info(
            "No holdings yet! Go to the **Chat** tab and try:\n"
            "*\"Buy 5 shares of Apple\"*"
        )

    # ── Transaction history ──
    st.divider()
    st.markdown("#### Transaction History")
    transactions = summary.get("transactions", [])
    if transactions:
        tx_rows = []
        for tx in transactions[:20]:
            g = tx.get("realized_gain", "")
            tx_rows.append({
                "Date":   tx["date"],
                "Type":   tx["type"],
                "Ticker": tx["ticker"],
                "Shares": tx["shares"],
                "Price":  f"${tx['price']:,.2f}",
                "Total":  f"${tx['total']:,.2f}",
                "Realized G/L": (
                    f"+${g:,.2f}" if isinstance(g, float) and g >= 0
                    else f"-${abs(g):,.2f}" if isinstance(g, float)
                    else ""
                ),
                "Note": tx.get("note", ""),
            })
        st.dataframe(
            pd.DataFrame(tx_rows),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No transactions yet.")

    # ── AI analysis ──
    st.divider()
    if st.button("🤖 Get AI Portfolio Analysis"):
        holdings_list = [
            {"ticker": h["ticker"],
             "shares": h["shares"],
             "avg_cost": h["avg_cost"]}
            for h in summary["holdings"]
        ]
        with st.spinner("Finnie is analyzing..."):
            ai_resp = run_finance_assistant(
                "Analyze my portfolio and give educational insights "
                "about diversification, sector exposure, and risk.",
                holdings=holdings_list
            )
        st.info(ai_resp)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — MARKET DATA
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Live Market Data")
    st.caption("Real-time stock prices and charts powered by yFinance.")

    # Stock lookup
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker_input = st.text_input(
            "Enter a ticker symbol:",
            value="AAPL",
            placeholder="e.g. AAPL, TSLA, NVDA, SPY"
        ).upper().strip()
    with col2:
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"])

    if st.button("🔍 Look Up Stock", type="primary") or ticker_input:
        with st.spinner(f"Fetching data for {ticker_input}..."):
            data = get_stock_data(ticker_input)

        if "error" in data:
            st.error(data["error"])
        else:
            # ── Stock metrics ──
            col1, col2, col3, col4 = st.columns(4)
            change_sign = "+" if data["change"] >= 0 else ""
            col1.metric("Current Price", f"${data['price']}")
            col2.metric(
                "Today's Change",
                f"{change_sign}${data['change']}",
                f"{change_sign}{data['change_pct']}%"
            )
            col3.metric("52-Week High", f"${data['52_week_high']}")
            col4.metric("52-Week Low", f"${data['52_week_low']}")

            # ── Price chart ──
            st.markdown(f"#### {data['name']} — Price History")
            try:
                hist = yf.Ticker(ticker_input).history(period=period)
                if not hist.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=hist["Close"],
                        mode="lines",
                        name="Close Price",
                        line=dict(color="#1f77b4", width=2),
                        fill="tozeroy",
                        fillcolor="rgba(31,119,180,0.1)"
                    ))
                    fig.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Price (USD)",
                        margin=dict(t=20, b=0),
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig, width='stretch')
            except Exception as e:
                st.warning(f"Could not load chart: {e}")

            # ── Stock details ──
            st.markdown("#### Stock Details")
            detail_cols = st.columns(3)
            detail_cols[0].metric("P/E Ratio", data["pe_ratio"])
            detail_cols[1].metric("Sector", data["sector"])
            detail_cols[2].metric(
                "Market Cap",
                f"${data['market_cap']:,.0f}" if isinstance(data["market_cap"], (int, float)) else "N/A"
            )

    # ── Market overview ──
    st.divider()
    st.markdown("#### Market Overview")
    st.caption("Major indices and popular stocks")

    watchlist = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META"]
    watchlist_data = []

    with st.spinner("Loading market overview..."):
        for t in watchlist:
            d = get_stock_data(t)
            if "error" not in d:
                watchlist_data.append({
                    "Ticker": d["ticker"],
                    "Name": d["name"],
                    "Price": f"${d['price']}",
                    "Change": f"${d['change']}",
                    "Change %": f"{d['change_pct']}%",
                })

    if watchlist_data:
        st.dataframe(pd.DataFrame(watchlist_data), width='stretch')