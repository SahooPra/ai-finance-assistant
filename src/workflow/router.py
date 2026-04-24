# src/workflow/router.py
from src.workflow.graph import finance_graph

def run_finance_assistant(
    question:     str,
    chat_history: list = [],
    holdings:     list = []
) -> str:
    initial_state = {
        "question":       question,
        "intents":        [],
        "responses":      {},
        "final_response": "",
        "chat_history":   chat_history,
        "holdings":       holdings,
        "error":          "",
        "blocked":        False,
        "needs_referral": False,
    }
    final_state = finance_graph.invoke(initial_state)
    return final_state.get(
        "final_response",
        "I could not generate a response. Please try again."
    )