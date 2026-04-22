# src/workflow/router.py
from src.workflow.graph import finance_graph

def run_finance_assistant(
    question: str,
    chat_history: list = [],
    holdings: list = []
) -> str:
    """
    Main entry point for the finance assistant.
    Now powered by LangGraph state machine.
    """
    # Build initial state
    initial_state = {
        "question": question,
        "intent": "",
        "response": "",
        "chat_history": chat_history,
        "holdings": holdings,
        "error": "",
    }

    # Run the graph
    final_state = finance_graph.invoke(initial_state)

    # Return the response
    return final_state.get("response", "I could not generate a response. Please try again.")