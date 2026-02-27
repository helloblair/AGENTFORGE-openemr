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
        "- *What allergies does Jane Doe have?*\n"
        "- *Find patient John Smith and check if his meds conflict with his allergies*"
    )
    st.divider()
    st.caption("👍 / 👎 feedback is logged to Langfuse for quality tracking.")

# ── Session state ────────────────────────────────────────────────────────────

if "thread_id" not in st.session_state:
    st.session_state.thread_id = uuid.uuid4().hex

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Helper: submit feedback to API ──────────────────────────────────────────


def _submit_feedback(trace_id: str, score: int) -> None:
    """POST feedback score (1=thumbs up, 0=thumbs down) to the agent API."""
    if not trace_id:
        st.toast("No trace ID — feedback not recorded.", icon="⚠️")
        return
    try:
        resp = requests.post(
            f"{AGENT_API_URL}/feedback",
            json={"trace_id": trace_id, "score": score},
            timeout=10,
        )
        resp.raise_for_status()
        icon = "👍" if score == 1 else "👎"
        st.toast(f"Feedback recorded {icon}", icon="✅")
    except Exception as exc:
        st.toast(f"Could not record feedback: {exc}", icon="⚠️")


# ── Render chat history ─────────────────────────────────────────────────────

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant":
            if msg.get("tools_used"):
                with st.expander("🔧 Tools called"):
                    for tool in msg["tools_used"]:
                        st.code(tool)

            if "confidence_score" in msg:
                st.progress(msg["confidence_score"], text=f"Confidence: {msg['confidence_score']:.2f}")

            # Escalation banner for low-confidence responses
            if msg.get("requires_escalation"):
                st.warning(
                    "⚠️ **Clinical review recommended** — "
                    "Low confidence. Please verify with a qualified healthcare provider.",
                    icon="🔴",
                )

            # Thumbs up / down feedback buttons
            trace_id = msg.get("trace_id", "")
            fb_key = f"fb_{i}"
            if fb_key not in st.session_state:
                st.session_state[fb_key] = None

            if st.session_state[fb_key] is None:
                col1, col2, _ = st.columns([1, 1, 10])
                with col1:
                    if st.button("👍", key=f"up_{i}", help="Helpful response"):
                        _submit_feedback(trace_id, score=1)
                        st.session_state[fb_key] = 1
                        st.rerun()
                with col2:
                    if st.button("👎", key=f"dn_{i}", help="Unhelpful or inaccurate"):
                        _submit_feedback(trace_id, score=0)
                        st.session_state[fb_key] = 0
                        st.rerun()
            else:
                label = "👍 Helpful" if st.session_state[fb_key] == 1 else "👎 Not helpful"
                st.caption(f"Feedback: {label}")

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
                trace_id = data.get("trace_id", "")
                requires_escalation = data.get("requires_escalation", False)
                st.session_state.thread_id = data["thread_id"]
            except requests.ConnectionError:
                response = (
                    "**Agent service unavailable.** "
                    "Make sure the FastAPI backend is running at "
                    f"`{AGENT_API_URL}`."
                )
                tools_used = []
                confidence_score = 0.0
                trace_id = ""
                requires_escalation = False
            except requests.RequestException as exc:
                response = f"**Error communicating with agent service:** {exc}"
                tools_used = []
                confidence_score = 0.0
                trace_id = ""
                requires_escalation = False

        st.markdown(response)

        if tools_used:
            with st.expander("🔧 Tools called"):
                for tool in tools_used:
                    st.code(tool)

        st.progress(confidence_score, text=f"Confidence: {confidence_score:.2f}")

        if requires_escalation:
            st.warning(
                "⚠️ **Clinical review recommended** — "
                "Low confidence. Please verify with a qualified healthcare provider.",
                icon="🔴",
            )

        # Inline feedback buttons for this new message
        new_msg_index = len(st.session_state.messages)
        fb_key = f"fb_{new_msg_index}"
        st.session_state[fb_key] = None
        col1, col2, _ = st.columns([1, 1, 10])
        with col1:
            if st.button("👍", key=f"up_{new_msg_index}", help="Helpful response"):
                _submit_feedback(trace_id, score=1)
                st.session_state[fb_key] = 1
        with col2:
            if st.button("👎", key=f"dn_{new_msg_index}", help="Unhelpful or inaccurate"):
                _submit_feedback(trace_id, score=0)
                st.session_state[fb_key] = 0

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
            "tools_used": tools_used,
            "confidence_score": confidence_score,
            "trace_id": trace_id,
            "requires_escalation": requires_escalation,
        }
    )
