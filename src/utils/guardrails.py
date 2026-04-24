# src/utils/guardrails.py
import re
from src.core.llm_config import get_llm
from langchain_core.messages import HumanMessage, SystemMessage


# ── Blocked patterns ──────────────────────────────────────────────────────────
# These are checked instantly without calling the LLM (fast + cheap)

BLOCKED_INPUT_PATTERNS = [
    # Requests for specific stock picks
    r"\bshould i (buy|sell|invest in|short)\b",
    r"\bwill .* (go up|go down|rise|fall|crash|moon)\b",
    r"\bbest stock(s)? to buy\b",
    r"\bguaranteed (return|profit|gain)\b",
    r"\bhow to get rich quick\b",
    r"\bget rich\b",

    # Illegal financial activity
    r"\binsider trading\b",
    r"\bmarket manipulation\b",
    r"\bpump and dump\b",
    r"\bmoney laundering\b",
    r"\btax (evasion|fraud)\b",
    r"\bponzi\b",

    # Completely off-topic
    r"\b(porn|xxx|adult content)\b",
    r"\bhow to (hack|crack|exploit)\b",
    r"\b(drugs|weapons|explosives)\b",
]

BLOCKED_OUTPUT_PATTERNS = [
    # Specific investment recommendations
    r"\byou should (definitely|certainly|absolutely) (buy|sell|invest)\b",
    r"\bi (strongly |highly )?(recommend|suggest) (buying|selling|investing in)\b",
    r"\bguaranteed (to|returns?|profit)\b",
    r"\bwill definitely (rise|fall|go up|go down)\b",
    r"\b100% (sure|certain|guaranteed)\b",
]

# Topics Finnie should redirect to professionals
PROFESSIONAL_REFERRAL_TOPICS = [
    r"\bmy specific (situation|portfolio|finances)\b",
    r"\bam i (doing|on track|ready) (right|well|for retirement)\b",
    r"\bshould i (file|claim|deduct)\b.*\btax\b",
    r"\bhow much (should i|do i need to) (invest|save|contribute)\b",
]


# ── Input Guardrail ───────────────────────────────────────────────────────────
def check_input(question: str) -> dict:
    """
    Checks user input before sending to any agent.

    Returns:
        {
            "safe": True/False,
            "reason": "why it was blocked",
            "response": "message to show user if blocked",
            "needs_referral": True/False  -- suggest professional
        }
    """
    question_lower = question.lower().strip()

    # Check completely blocked patterns
    for pattern in BLOCKED_INPUT_PATTERNS:
        if re.search(pattern, question_lower):
            return {
                "safe": False,
                "reason": "blocked_pattern",
                "response": _blocked_response(question),
                "needs_referral": False,
            }

    # Check if question needs professional referral
    for pattern in PROFESSIONAL_REFERRAL_TOPICS:
        if re.search(pattern, question_lower):
            return {
                "safe": True,
                "reason": "needs_referral",
                "response": None,
                "needs_referral": True,
            }

    # Check if question is completely off-topic using LLM
    off_topic_result = _check_off_topic(question)
    if off_topic_result["off_topic"]:
        return {
            "safe": False,
            "reason": "off_topic",
            "response": _off_topic_response(question),
            "needs_referral": False,
        }

    return {
        "safe": True,
        "reason": "ok",
        "response": None,
        "needs_referral": False,
    }


def _check_off_topic(question: str) -> dict:
    """
    Uses LLM to detect completely off-topic questions.
    Only called when pattern matching doesn't find issues.
    """
    try:
        llm = get_llm(temperature=0)
        messages = [
            SystemMessage(content="""You are a content classifier for a financial education app.
Respond with ONLY 'yes' or 'no'.
Is this question related to any of these topics?
- Personal finance, investing, stocks, bonds, ETFs, mutual funds
- Retirement accounts (401k, IRA, Roth IRA)
- Budgeting, saving, financial goals
- Market data, stock prices, financial news
- Taxes related to investing
- Financial concepts and education

Answer 'yes' if related to finance/investing, 'no' if completely unrelated."""),
            HumanMessage(content=f"Question: {question}")
        ]
        response = llm.invoke(messages)
        answer = response.content.strip().lower()
        return {"off_topic": answer.startswith("no")}
    except Exception:
        # If LLM check fails, let it through (fail open)
        return {"off_topic": False}


# ── Output Guardrail ──────────────────────────────────────────────────────────
def check_output(response: str, question: str) -> dict:
    """
    Checks agent response before showing to user.

    Returns:
        {
            "safe": True/False,
            "cleaned_response": the response (possibly modified),
            "warning_added": True/False
        }
    """
    response_lower = response.lower()

    # Check for specific investment advice in output
    for pattern in BLOCKED_OUTPUT_PATTERNS:
        if re.search(pattern, response_lower):
            # Don't block — just add a stronger disclaimer
            cleaned = _add_strong_disclaimer(response)
            return {
                "safe": True,
                "cleaned_response": cleaned,
                "warning_added": True,
            }

    # Ensure disclaimer is always present
    if "educational" not in response_lower and "not financial advice" not in response_lower:
        response = response + (
            "\n\n*Note: This is educational information only, "
            "not personalized financial advice. Please consult "
            "a qualified financial advisor for guidance specific to your situation.*"
        )
        return {
            "safe": True,
            "cleaned_response": response,
            "warning_added": True,
        }

    return {
        "safe": True,
        "cleaned_response": response,
        "warning_added": False,
    }


# ── Helper response messages ──────────────────────────────────────────────────
def _blocked_response(question: str) -> str:
    return """I'm sorry, but I can't help with that request. 

As a financial **education** assistant, Finnie is designed to:
- Explain financial concepts and terminology
- Provide information about investment types
- Help you understand market data
- Educate about retirement accounts and tax concepts

I cannot provide specific investment recommendations, predict market movements, or assist with anything that could constitute financial advice or illegal activity.

Is there a financial concept you'd like me to explain instead?

*Note: This is an educational tool only, not a licensed financial advisor.*"""


def _off_topic_response(question: str) -> str:
    return """That question seems to be outside my area of expertise! 

I'm Finnie, your **financial education** assistant. I'm specifically designed to help with:

- 📈 **Investing basics** — stocks, bonds, ETFs, mutual funds
- 💰 **Personal finance** — budgeting, saving, compound interest  
- 🏦 **Retirement accounts** — 401(k), IRA, Roth IRA
- 📰 **Market data** — live stock prices and financial news
- 🧾 **Tax education** — capital gains, tax-advantaged accounts

Try asking me something like:
- *"What is an ETF?"*
- *"How does compound interest work?"*
- *"What is the difference between a Roth IRA and a 401k?"*"""


def _add_strong_disclaimer(response: str) -> str:
    disclaimer = (
        "\n\n---\n"
        "⚠️ **Important reminder:** The above is for educational purposes only. "
        "Finnie is not a licensed financial advisor and cannot recommend specific "
        "investments for your personal situation. Past performance does not guarantee "
        "future results. Please consult a qualified financial advisor before making "
        "any investment decisions."
    )
    # Remove any existing disclaimer first to avoid duplicates
    if "educational" in response.lower():
        lines = response.split("\n")
        lines = [l for l in lines if "educational information only" not in l.lower()]
        response = "\n".join(lines)

    return response + disclaimer


def add_referral_note(response: str) -> str:
    """
    Appends a professional referral note when the question
    is personal/specific rather than general education.
    """
    referral = (
        "\n\n---\n"
        "💡 **Personal guidance tip:** Since your question relates to your specific "
        "financial situation, I'd recommend speaking with a certified financial planner "
        "(CFP) or financial advisor who can give personalized advice based on your "
        "complete financial picture, goals, and risk tolerance.\n\n"
        "You can find a certified advisor at **[NAPFA.org](https://www.napfa.org)** "
        "(fee-only advisors) or **[CFP.net](https://www.cfp.net)**."
    )
    return response + referral