# test_multi_agent.py
import sys, os
sys.path.insert(0, os.path.abspath("."))

from src.workflow.router import run_finance_assistant

tests = [
    {
        "label": "Trade + News (2 agents)",
        "q": "Buy 2 shares of Apple and show me the latest news on it"
    },
    {
        "label": "Market + QA (2 agents)",
        "q": "What is the current price of NVDA and what is an ETF?"
    },
    {
        "label": "Trade + Portfolio (2 agents)",
        "q": "Sell 1 TSLA share and then show me my portfolio"
    },
    {
        "label": "Market + News (2 agents)",
        "q": "How is Apple stock doing today and what is the latest news?"
    },
    {
        "label": "Tax + Goal (2 agents)",
        "q": "How do capital gains taxes work when saving for retirement?"
    },
    {
        "label": "Single agent still works",
        "q": "What is compound interest?"
    },
]

for test in tests:
    print(f"\n{'='*60}")
    print(f"Test: {test['label']}")
    print(f"Q: {test['q']}")
    print("-"*60)
    response = run_finance_assistant(test["q"])
    print(response[:400] + "..." if len(response) > 400 else response)