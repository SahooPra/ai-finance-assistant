# Finnie — AI Finance Assistant

> Democratizing financial literacy through intelligent conversational AI

---

## What is Finnie?

Finnie is a production-ready multi-agent AI finance assistant built as a capstone
project for the Applied Agentic AI for SWEs course (Interview Kickstart).

It uses **LangGraph** to orchestrate seven specialized AI agents that help beginners
learn about investing, analyze portfolios, track live market data, trade stocks via
chat, and plan financial goals — all through a single conversational interface.

---

## Architecture

```
User message
     │
     ▼
Streamlit UI  (Chat · Portfolio · Market tabs)
     │
     ▼
Guardrails layer
(input check · blocked patterns · off-topic filter · output disclaimer)
     │
     ▼
LangGraph state machine
(FinanceState · detect_intent node · conditional edges · error handler)
     │
     ├── Finance Q&A agent  ──── RAG (ChromaDB)
     ├── Market agent       ──── yFinance API
     ├── Portfolio agent    ──── yFinance API
     ├── Goal planner agent
     ├── News agent         ──── yFinance news
     ├── Tax agent
     └── Trade agent ────────── Portfolio manager
                                     │
                                portfolio.json (persistent storage)
```

The architecture diagram is saved as `docs/finnie_architecture_v2.svg`.

---

## Features

### Seven specialized AI agents

| Agent | Purpose | Tools used |
|---|---|---|
| Finance Q&A | General financial education | RAG + ChromaDB |
| Market agent | Live stock prices and data | yFinance API |
| Portfolio agent | Holdings analysis with P&L | yFinance API |
| Goal planner | Savings and retirement planning | LLM |
| News agent | Financial news summarization | yFinance news |
| Tax agent | Tax concepts and account types | LLM |
| Trade agent | Buy and sell via chat | Portfolio manager |

### Guardrails system

Three-layer protection built into the LangGraph pipeline:

- **Input guardrails** — blocks harmful requests (specific stock picks, market
  predictions, illegal activity, off-topic questions) before reaching any agent
- **Output guardrails** — ensures every response carries appropriate disclaimers
- **Professional referral** — detects personal-situation questions and appends
  links to certified financial advisors

### RAG knowledge base

- 11+ financial education articles indexed in ChromaDB
- 2 curated knowledge base files covering investing basics and retirement accounts
- 8 Wikipedia articles fetched automatically (ETF, bonds, IRA, 401k, compound
  interest, portfolio, mutual funds, stock market)
- Source citations appended to every RAG-grounded response
- Semantic chunking with overlap for accurate retrieval

### Portfolio management

- Persistent virtual portfolio stored in `portfolio.json`
- Default holdings: AAPL, MSFT, NVDA, SPY, TSLA with $10,000 cash
- Real-time gain/loss calculation with live prices
- Full transaction history with realized gain/loss tracking
- Buy and sell stocks naturally through the chat interface

### Streamlit UI

Three-tab interface:

- **Chat** — conversational interface with suggestion buttons and clear history
- **Portfolio** — live holdings table, allocation pie chart, gain/loss bar chart,
  transaction history, AI portfolio analysis
- **Market** — stock lookup, interactive price history chart, market overview table

---

## Tech stack

| Component | Technology |
|---|---|
| Multi-agent orchestration | LangGraph |
| LLM | OpenAI GPT-4o-mini |
| RAG vector database | ChromaDB |
| Embeddings | OpenAI text-embedding-3-small |
| Market data | yFinance |
| Web interface | Streamlit |
| Charts | Plotly |
| Portfolio storage | JSON (portfolio.json) |
| Guardrails | Custom + LLM-based classifier |

---

## Project structure

```
ai_finance_assistant/
├── src/
│   ├── agents/
│   │   ├── qa_agent.py          # General Q&A with RAG + citations
│   │   ├── market_agent.py      # Live stock prices
│   │   ├── portfolio_agent.py   # Portfolio P&L analysis
│   │   ├── goal_agent.py        # Goal and savings planning
│   │   ├── news_agent.py        # Financial news summarization
│   │   ├── tax_agent.py         # Tax and account education
│   │   └── trade_agent.py       # Buy/sell via natural language
│   ├── core/
│   │   └── llm_config.py        # OpenAI LLM setup
│   ├── data/
│   │   ├── articles/            # RAG knowledge base text files
│   │   └── fetch_wikipedia.py   # Wikipedia article fetcher
│   ├── mcp_server/
│   │   └── finance_mcp.py       # MCP server for Claude Desktop
│   ├── rag/
│   │   └── knowledge_base.py    # ChromaDB RAG with citations
│   ├── utils/
│   │   ├── guardrails.py        # Input and output safety checks
│   │   └── portfolio_manager.py # Buy/sell/summary/persistence
│   ├── web_app/
│   │   └── app.py               # Streamlit UI (3 tabs)
│   └── workflow/
│       ├── router.py            # Main entry point
│       └── graph.py             # LangGraph state machine
├── tests/
│   └── test_agents.py           # 6/6 tests passing
├── docs/
│   └── finnie_architecture_v2.svg
├── portfolio.json               # Persistent virtual portfolio
├── chroma_db/                   # ChromaDB vector store (auto-generated)
├── .env                         # API keys (never commit)
├── .env.example                 # Key template for setup
├── .gitignore
├── config.yaml                  # App configuration
├── requirements.txt             # Python dependencies
├── rebuild_db.py                # Rebuild ChromaDB from scratch
└── README.md
```

---

## Setup instructions

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/ai-finance-assistant.git
cd ai_finance_assistant
```

### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate.bat      # Windows
source venv/bin/activate       # Mac / Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Copy `.env.example` to `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-proj-your-key-here
```

### 5. Fetch Wikipedia articles (optional but recommended)

```bash
python src/data/fetch_wikipedia.py
```

### 6. Build the RAG knowledge base

```bash
python rebuild_db.py
```

### 7. Run the app

```bash
streamlit run src/web_app/app.py
```

Open your browser at `http://localhost:8501`

---

## Usage examples

### Chat — education questions

```
"What is an ETF?"
"How does compound interest work?"
"Explain the difference between stocks and bonds"
"What is diversification?"
```

### Chat — live market data

```
"What is the current price of Apple stock?"
"How is NVDA doing today?"
"What is Tesla trading at?"
```

### Chat — trading (virtual portfolio)

```
"Buy 5 shares of Apple"
"Sell 2 TSLA shares"
"Purchase 10 NVDA"
"Buy 3 shares of Microsoft"
```

### Chat — goal planning

```
"How do I save for retirement?"
"What is an emergency fund?"
"How does the 50/30/20 budget rule work?"
```

### Chat — tax education

```
"How does a Roth IRA work?"
"What is the difference between a Roth IRA and a 401k?"
"What are capital gains taxes?"
```

### Chat — financial news

```
"What's the latest news on Tesla?"
"What is happening in the market today?"
"Give me recent Apple headlines"
```

### Portfolio tab

Click **Refresh** to load live prices, view the allocation pie chart and
gain/loss bar chart, read transaction history, and click **Get AI Portfolio
Analysis** for Finnie's educational insights.

### Market tab

Enter any ticker symbol (AAPL, TSLA, SPY, BTC-USD) and choose a time period
to view an interactive price history chart plus a full market overview table.

---

## Guardrails — what Finnie blocks

| Request type | Example | Response |
|---|---|---|
| Specific stock advice | "Should I buy Tesla?" | Blocked with redirect |
| Market prediction | "Will AAPL go up?" | Blocked with redirect |
| Illegal activity | "How does insider trading work?" | Blocked |
| Off-topic | "Best pizza recipe?" | Blocked as off-topic |
| Personal situation | "How much should I invest?" | Passes + referral note |

---

## Running tests

```bash
python tests/test_agents.py
```

Expected output:
```
Running Finnie test suite...

PASS: stock data fetch - AAPL price: $xxx
PASS: portfolio analysis - Total value: $xxx
PASS: RAG retrieval working
PASS: market intent routing
PASS: qa intent routing
PASS: tax intent routing

All tests passed!
```

---

## Rebuilding the knowledge base

Run this after adding new articles to `src/data/articles/`:

```bash
python rebuild_db.py
```

---

## MCP server (optional — Claude Desktop integration)

Finnie exposes six tools via the Model Context Protocol so Claude Desktop
can call them directly:

- `get_stock_price` — live price for any ticker
- `analyze_portfolio` — full P&L analysis
- `search_finance_knowledge` — RAG knowledge base search
- `ask_finance_question` — general Q&A
- `get_goal_advice` — savings and goal planning
- `get_tax_education` — tax concept explanations

See `src/mcp_server/finance_mcp.py` for the implementation.

---

## Disclaimer

Finnie is an educational tool only. Nothing it produces constitutes financial,
investment, or tax advice. Always consult qualified professionals for personalized
guidance. The portfolio feature uses simulated (virtual) money only — no real
trades are executed.

---

## Course

Applied Agentic AI for SWEs · Interview Kickstart · Capstone Project
