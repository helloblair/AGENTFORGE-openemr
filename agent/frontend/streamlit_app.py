"""Streamlit chat UI for interacting with the OpenEMR AI agent."""

import os
import uuid

import requests
import streamlit as st

AGENT_API_URL = os.environ.get("AGENT_API_URL", "http://localhost:8400")

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="OpenEMR Healthcare Agent",
    page_icon="🏥",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏥 OpenEMR Healthcare Agent")
    st.markdown(
        "An AI-powered clinical support assistant connected to OpenEMR. "
        "It can look up patients, check drug interactions, and review allergies."
    )
    st.divider()
    st.markdown("**Example queries to try:**")
    st.markdown(
        "- *Look up patient John Smith*\n"
        "- *Check interactions between aspirin and warfarin*\n"
        "- *What allergies does Jane Doe have?*"
    )

# ── Session state ────────────────────────────────────────────────────────────

if "thread_id" not in st.session_state:
    st.session_state.thread_id = uuid.uuid4().hex

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Render chat history ─────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tools_used"):
            with st.expander("🔧 Tools called"):
                for tool in msg["tools_used"]:
                    st.code(tool)
        if "confidence_score" in msg:
            score = msg["confidence_score"]
            if score < 0.6:
                st.progress(score, text=f"Confidence: {score:.2f}")
            elif score < 0.8:
                st.progress(score, text=f"Confidence: {score:.2f}")
            else:
                st.progress(score, text=f"Confidence: {score:.2f}")

# ── Handle user input ───────────────────────────────────────────────────────

if prompt := st.chat_input("Ask the healthcare agent…"):
    # Display & store user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get agent response via FastAPI backend
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                resp = requests.post(
                    f"{AGENT_API_URL}/chat",
                    json={
                        "message": prompt,
                        "thread_id": st.session_state.thread_id,
                    },
                    timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()
                response = data["response"]
                tools_used = data.get("tools_used", [])
                confidence_score = data.get("confidence_score", 1.0)
                st.session_state.thread_id = data["thread_id"]
            except requests.ConnectionError:
                response = (
                    "**Agent service unavailable.** "
                    "Make sure the FastAPI backend is running at "
                    f"`{AGENT_API_URL}`."
                )
                tools_used = []
                confidence_score = 0.0
            except requests.RequestException as exc:
                response = f"**Error communicating with agent service:** {exc}"
                tools_used = []
                confidence_score = 0.0
        st.markdown(response)
        if tools_used:
            with st.expander("🔧 Tools called"):
                for tool in tools_used:
                    st.code(tool)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
            "tools_used": tools_used,
            "confidence_score": confidence_score,
        }
    )
