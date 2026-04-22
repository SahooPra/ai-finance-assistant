# Finnie — AI Finance Assistant

Democratizing financial literacy through intelligent conversational AI.

## What is Finnie?

Finnie is a multi-agent AI finance assistant built as a capstone project for the
Applied Agentic AI for SWEs course. It uses LangGraph to orchestrate six specialized
AI agents that help beginners learn about investing, analyze portfolios, track market
data, and plan financial goals.

## Architecture
User Question
│
▼
LangGraph State Machine
│
├── detect_intent node
│        │
│   (conditional edge)
│        │
├── QA Agent ──────── RAG (ChromaDB)
├── Market Agent ───── yFinance API
├── Portfolio Agent ── yFinance API
├── Goal Agent
├── News Agent ─────── yFinance News
└── Tax Agent

## Agents

| Agent | Purpose |
|---|---|
| Finance Q&A | General financial education with RAG |
| Market Agent | Live stock prices and market data |
| Portfolio Agent | Portfolio analysis with gain/loss tracking |
| Goal Planner | Retirement and savings goal planning |
| News Agent | Financial news summarization |
| Tax Agent | Tax concepts and account types |

## Tech Stack

| Component | Technology |
|---|---|
| Multi-Agent Orchestration | LangGraph |
| LLM | OpenAI GPT-4o-mini |
| RAG / Vector DB | ChromaDB + OpenAI Embeddings |
| Market Data | yFinance |
| Web Interface | Streamlit |
| Charts | Plotly |

## Setup Instructions

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd ai_finance_assistant
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate.bat   # Windows
source venv/bin/activate    # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
Create a `.env` file in the root folder:



OPENAI_API_KEY=your-openai-api-key-here

### 5. Run the app
```bash
streamlit run src/web_app/app.py
```

Open your browser at `http://localhost:8501`

## Usage Examples

### Chat Tab
- "What is a stock?"
- "Explain compound interest with an example"
- "What is the price of Apple stock?"
- "How does a Roth IRA work?"
- "What's the latest news on Tesla?"
- "How do I save for retirement?"

### Portfolio Tab
- Enter your stock holdings (ticker, shares, average cost)
- Click Analyze to get real-time gain/loss analysis
- View pie chart (allocation) and bar chart (gain/loss)
- Get Finnie's AI-powered portfolio insights

### Market Tab
- Enter any ticker symbol (AAPL, TSLA, SPY, etc.)
- Choose time period (1 month to 5 years)
- View interactive price history chart
- See live market overview of major stocks

## Project Structure



ai_finance_assistant/
├── src/
│   ├── agents/
│   │   ├── qa_agent.py          # General Q&A with RAG
│   │   ├── market_agent.py      # Live market data
│   │   ├── portfolio_agent.py   # Portfolio analysis
│   │   ├── goal_agent.py        # Goal planning
│   │   ├── news_agent.py        # News summarization
│   │   └── tax_agent.py         # Tax education
│   ├── core/
│   │   └── llm_config.py        # OpenAI LLM setup
│   ├── data/
│   │   └── articles/            # Financial education articles
│   ├── rag/
│   │   └── knowledge_base.py    # ChromaDB RAG system
│   ├── web_app/
│   │   └── app.py               # Streamlit UI
│   └── workflow/
│       ├── router.py            # Main entry point
│       └── graph.py             # LangGraph state machine
├── tests/
├── .env                         # API keys (never commit!)
├── config.yaml                  # App configuration
├── requirements.txt             # Python dependencies
└── README.md                    # This file



## Disclaimer

Finnie is an educational tool only. Nothing it says constitutes financial,
investment, or tax advice. Always consult qualified professionals for
personalized guidance.

