# app.py (root level - temporary test)
import streamlit as st
import os

st.title("Finnie - Deployment Test")

# Check API key
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    st.success(f"✅ OpenAI API key found: ...{api_key[-4:]}")
else:
    st.error("❌ OPENAI_API_KEY secret is missing!")

# Check Python path
import sys
st.info(f"Python: {sys.version}")
st.info(f"Working directory: {os.getcwd()}")

# Check if src folder exists
if os.path.exists("src"):
    st.success("✅ src/ folder found")
else:
    st.error("❌ src/ folder NOT found")

# Check if key files exist
files_to_check = [
    "src/web_app/app.py",
    "src/workflow/router.py",
    "src/workflow/graph.py",
    "src/agents/qa_agent.py",
    "src/utils/guardrails.py",
    "src/utils/portfolio_manager.py",
]
st.subheader("File checks:")
for f in files_to_check:
    if os.path.exists(f):
        st.success(f"✅ {f}")
    else:
        st.error(f"❌ {f} NOT found")

# Try importing core modules one by one
st.subheader("Import checks:")
try:
    from dotenv import load_dotenv
    st.success("✅ dotenv imported")
except Exception as e:
    st.error(f"❌ dotenv: {e}")

try:
    from langchain_openai import ChatOpenAI
    st.success("✅ langchain_openai imported")
except Exception as e:
    st.error(f"❌ langchain_openai: {e}")

try:
    from langgraph.graph import StateGraph
    st.success("✅ langgraph imported")
except Exception as e:
    st.error(f"❌ langgraph: {e}")

try:
    import chromadb
    st.success("✅ chromadb imported")
except Exception as e:
    st.error(f"❌ chromadb: {e}")

try:
    import yfinance
    st.success("✅ yfinance imported")
except Exception as e:
    st.error(f"❌ yfinance: {e}")

try:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from src.core.llm_config import get_llm
    st.success("✅ llm_config imported")
except Exception as e:
    st.error(f"❌ llm_config: {e}")

try:
    from src.workflow.router import run_finance_assistant
    st.success("✅ router imported")
except Exception as e:
    st.error(f"❌ router: {e}")

st.subheader("Quick test:")
if st.button("Test OpenAI connection"):
    try:
        from src.core.llm_config import get_llm
        llm = get_llm()
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content="Say hello in one word")])
        st.success(f"✅ OpenAI working! Response: {response.content}")
    except Exception as e:
        st.error(f"❌ OpenAI failed: {e}")