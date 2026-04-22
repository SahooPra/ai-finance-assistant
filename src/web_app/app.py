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
# TAB 2 — PORTFOLIO ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Portfolio Analysis")
    st.caption("Enter your holdings to get a real-time analysis of your portfolio.")

    # Portfolio input form
    with st.expander("➕ Add Your Holdings", expanded=True):
        st.markdown("Enter each stock you own:")

        if "holdings" not in st.session_state:
            st.session_state.holdings = [
                {"ticker": "AAPL", "shares": 10, "avg_cost": 150.0},
                {"ticker": "MSFT", "shares": 5, "avg_cost": 300.0},
                {"ticker": "NVDA", "shares": 3, "avg_cost": 400.0},
            ]

        # Editable holdings table
        holdings_df = pd.DataFrame(st.session_state.holdings)
        edited_df = st.data_editor(
            holdings_df,
            num_rows="dynamic",
            column_config={
                "ticker": st.column_config.TextColumn("Ticker Symbol", help="e.g. AAPL, TSLA"),
                "shares": st.column_config.NumberColumn("Shares Owned", min_value=0.0),
                "avg_cost": st.column_config.NumberColumn("Avg Cost Per Share ($)", min_value=0.0),
            },
            width='stretch',
        )

        analyze_btn = st.button("📊 Analyze My Portfolio", type="primary")

    if analyze_btn:
        holdings_list = edited_df.to_dict("records")
        st.session_state.holdings = holdings_list

        with st.spinner("Fetching live prices and analyzing your portfolio..."):
            analysis = analyze_portfolio(holdings_list)

        if not analysis["holdings"]:
            st.error("Could not fetch data. Please check your ticker symbols.")
        else:
            # ── Summary metrics ──
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            gain_color = "normal" if analysis["total_gain_loss"] >= 0 else "inverse"
            col1.metric("Total Value", f"${analysis['total_value']:,.2f}")
            col2.metric("Total Cost", f"${analysis['total_cost']:,.2f}")
            col3.metric(
                "Total Gain/Loss",
                f"${analysis['total_gain_loss']:,.2f}",
                f"{analysis['total_gain_loss_pct']}%"
            )
            col4.metric("Holdings", len(analysis["holdings"]))

            st.divider()

            # ── Holdings table ──
            st.markdown("#### Holdings Breakdown")
            rows = []
            for h in analysis["holdings"]:
                rows.append({
                    "Ticker": h["ticker"],
                    "Shares": h["shares"],
                    "Avg Cost": f"${h['avg_cost']}",
                    "Current Price": f"${h['current_price']}",
                    "Market Value": f"${h['market_value']:,.2f}",
                    "Gain/Loss": f"${h['gain_loss']:,.2f}",
                    "Gain/Loss %": f"{h['gain_loss_pct']}%",
                })
            st.dataframe(pd.DataFrame(rows), width='stretch')

            st.divider()

            # ── Charts ──
            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("#### Portfolio Allocation")
                fig_pie = px.pie(
                    values=[h["market_value"] for h in analysis["holdings"]],
                    names=[h["ticker"] for h in analysis["holdings"]],
                    hole=0.4,
                )
                fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, width='stretch')

            with col_right:
                st.markdown("#### Gain / Loss by Stock")
                colors = ["green" if h["gain_loss"] >= 0 else "red"
                          for h in analysis["holdings"]]
                fig_bar = go.Figure(go.Bar(
                    x=[h["ticker"] for h in analysis["holdings"]],
                    y=[h["gain_loss"] for h in analysis["holdings"]],
                    marker_color=colors,
                    text=[f"${h['gain_loss']:,.2f}" for h in analysis["holdings"]],
                    textposition="outside",
                ))
                fig_bar.update_layout(
                    yaxis_title="Gain / Loss ($)",
                    margin=dict(t=20, b=0),
                )
                st.plotly_chart(fig_bar, width='stretch')

            # ── AI Analysis ──
            st.divider()
            st.markdown("#### Finnie's Analysis")
            with st.spinner("Finnie is reviewing your portfolio..."):
                portfolio_question = "Please analyze my portfolio and give me educational insights about diversification and risk."
                ai_response = run_finance_assistant(
                    portfolio_question,
                    holdings=holdings_list
                )
            st.info(ai_response)


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