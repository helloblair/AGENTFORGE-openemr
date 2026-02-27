"""LangGraph agent graph — defines nodes, edges, and tool routing.

This module wires up a ReAct-style agent that uses Claude Sonnet as the
reasoning LLM and the OpenEMR tools (patient_lookup, allergy_check,
medication_list, problem_list, provider_lookup, insurance_coverage,
drug_interaction_check) as callable actions.

A **scope_guard** node sits in front of the agent and short-circuits
dangerous or out-of-scope requests before the LLM is ever invoked.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import create_react_agent

# Ensure the agent package is importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.observability.tracing import create_langfuse_handler, init_tracing
from src.tools import allergy_check, drug_interaction_check, insurance_coverage, medication_list, patient_lookup, problem_list, provider_lookup
from src.verification.drug_safety import (
    CLINICAL_DATA_DISCLAIMER,
    MEDICATION_TOOLS,
    check_drug_safety,
    extract_allergies_from_messages,
    find_conflicts,
    extract_medications_from_messages,
    format_warning,
    should_add_clinical_disclaimer,
)
from src.verification.scope_guard import (
    CLINICAL_DISCLAIMER,
    CLINICAL_SUPPORT,
    apply_scope_guard,
    classify_input,
)

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

# Initialise Langfuse OTEL tracing (no-op if env vars not set).
init_tracing()

# ── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a healthcare AI assistant integrated with the OpenEMR electronic health \
records system. You help clinical staff look up patient information, check drug \
interactions, and review allergies.

IMPORTANT RULES:
- You are a clinical SUPPORT tool, not a medical professional
- NEVER diagnose conditions or recommend treatments
- NEVER prescribe medications
- Always include a disclaimer: "This information is for clinical support only. \
Please verify with qualified healthcare providers."
- If asked to diagnose or prescribe, politely decline and suggest consulting \
a healthcare provider
- When discussing drug interactions, always emphasize checking with a pharmacist
- Only report information that comes from the tools — never make up patient data

AVAILABLE TOOLS:
- patient_lookup: Search for patients by name or DOB
- allergy_check: Get a patient's documented allergies (requires patient UUID)
- medication_list: Get a patient's active medications (requires patient UUID)
- problem_list: Get a patient's active conditions / problem list (requires patient UUID)
- provider_lookup: Search for providers/practitioners by name or specialty
- insurance_coverage: Get a patient's insurance coverage details (requires patient UUID)
- drug_interaction_check: Check for drug-drug interactions (uses NIH RxNorm)

For multi-step queries, chain tools logically. Example:
"Check if John Smith is allergic to any of his current medications"
→ 1. patient_lookup("John Smith") → get UUID
→ 2. allergy_check(UUID) → get allergies
→ 3. medication_list(UUID) → get current medications
→ 4. problem_list(UUID) → get active conditions
→ 5. Report findings

Always cite which tool provided each piece of information.\
"""

# ── Inner agent (pre-built ReAct graph) ─────────────────────────────────────

_TOOLS = [patient_lookup, allergy_check, medication_list, problem_list, provider_lookup, insurance_coverage, drug_interaction_check]

_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
)

_react_agent = create_react_agent(
    _llm,
    _TOOLS,
    prompt=SYSTEM_PROMPT,
)

# ── Outer graph with scope guard ────────────────────────────────────────────


def _scope_guard_node(state: MessagesState) -> MessagesState:
    """Classify the latest user message and block if necessary.

    If blocked, an AIMessage with the block reason is appended to the
    message list.  The downstream routing edge checks for this to decide
    whether to short-circuit to END or continue to the agent.
    """
    # The latest message is the user's input.
    user_message = state["messages"][-1]
    user_text = (
        user_message.content
        if hasattr(user_message, "content")
        else str(user_message)
    )

    is_allowed, block_message = apply_scope_guard(user_text)

    if not is_allowed:
        logger.info("Scope guard BLOCKED: %s", block_message)
        return {"messages": [AIMessage(content=block_message)]}

    # Allowed — return empty update so messages pass through unchanged.
    return {"messages": []}


def _route_after_guard(state: MessagesState) -> Literal["agent", "__end__"]:
    """Route to the agent or straight to END based on scope guard result."""
    last = state["messages"][-1]
    # If the scope guard appended an AIMessage, we're blocked.
    if isinstance(last, AIMessage):
        return END
    return "agent"


def _post_process_node(state: MessagesState) -> MessagesState:
    """Post-process agent response: drug safety check + clinical disclaimer.

    1. Detect which tools were called during this turn.
    2. If medication-related tools were used, cross-reference against
       allergy data in the conversation.  If allergy data is missing,
       invoke allergy_check inline (synchronously via asyncio).
    3. If conflicts found, prepend a WARNING block.
    4. If any clinical-data tools were used, append the clinical
       data disclaimer.
    5. Always append the clinical support disclaimer for CLINICAL_SUPPORT
       queries (preserves existing behaviour).
    """
    messages = state["messages"]
    last_ai = messages[-1] if messages else None
    if not isinstance(last_ai, AIMessage):
        return {"messages": []}

    # Identify tools used in this turn by scanning for tool_calls on
    # AIMessage objects.
    tools_used: list[str] = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name") or tc.get("function", {}).get("name", "")
                if name and name not in tools_used:
                    tools_used.append(name)

    response_text = last_ai.content

    # ── Drug safety check ───────────────────────────────────────────────
    warning_text, needs_allergy_fetch = check_drug_safety(messages, tools_used)

    if needs_allergy_fetch:
        # Try to find a patient UUID from tool call arguments in the
        # conversation history so we can call allergy_check.
        patient_uuid = _extract_patient_uuid(messages)
        if patient_uuid:
            try:
                allergy_result = asyncio.get_event_loop().run_until_complete(
                    allergy_check.ainvoke({"patient_uuid": patient_uuid})
                )
            except RuntimeError:
                # Already inside an event loop — use a helper.
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    allergy_result = pool.submit(
                        asyncio.run,
                        allergy_check.ainvoke({"patient_uuid": patient_uuid}),
                    ).result(timeout=15)

            if allergy_result and "documented allergy" in allergy_result.lower():
                # Re-check with the fetched allergy data.
                from src.verification.drug_safety import (
                    _parse_allergies_from_text,
                )
                allergy_substances = _parse_allergies_from_text(allergy_result)
                medications = extract_medications_from_messages(messages)
                conflicts = find_conflicts(allergy_substances, medications)
                if conflicts:
                    warning_text = format_warning(conflicts)

    # Prepend warning if conflicts detected.
    if warning_text:
        response_text = warning_text + response_text

    # ── Clinical data disclaimer ────────────────────────────────────────
    if should_add_clinical_disclaimer(tools_used):
        response_text += CLINICAL_DATA_DISCLAIMER

    # ── Original CLINICAL_SUPPORT disclaimer ────────────────────────────
    user_messages = [
        m for m in messages
        if hasattr(m, "type") and m.type == "human"
    ]
    if user_messages:
        latest_user_text = user_messages[-1].content
        category, _ = classify_input(latest_user_text)
        if category == CLINICAL_SUPPORT:
            response_text += CLINICAL_DISCLAIMER

    if response_text != last_ai.content:
        return {"messages": [AIMessage(content=response_text)]}

    return {"messages": []}


def _extract_patient_uuid(messages: list) -> str | None:
    """Scan message history for a patient UUID used in tool calls."""
    for msg in messages:
        if not hasattr(msg, "tool_calls"):
            continue
        for tc in msg.tool_calls:
            args = tc.get("args", {})
            uuid = args.get("patient_uuid")
            if uuid:
                return uuid
    return None


# Build the outer graph.
_builder = StateGraph(MessagesState)
_builder.add_node("scope_guard", _scope_guard_node)
_builder.add_node("agent", _react_agent)
_builder.add_node("post_process", _post_process_node)

_builder.add_edge(START, "scope_guard")
_builder.add_conditional_edges("scope_guard", _route_after_guard)
_builder.add_edge("agent", "post_process")
_builder.add_edge("post_process", END)

_checkpointer = MemorySaver()
graph = _builder.compile(checkpointer=_checkpointer)


# ── Public helper ────────────────────────────────────────────────────────────

async def run_agent(
    user_input: str,
    thread_id: str | None = None,
    trace_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, str | list[str]]:
    """Send a message to the agent and return the final text response.

    Args:
        user_input: The user's natural-language message.
        thread_id:  Conversation thread identifier.  Pass the same value
                    across calls to maintain conversation history.  A random
                    UUID is generated when *None*.
        trace_id:   Langfuse trace ID for observability.  Auto-generated
                    when *None*.
        user_id:    Optional staff identifier (UUID) attached to the trace.

    Returns:
        A dict with ``response`` (str), ``tools_used`` (list of tool
        name strings invoked during this turn), and ``trace_id`` (str).
    """
    if thread_id is None:
        thread_id = uuid.uuid4().hex

    config = {"configurable": {"thread_id": thread_id}}

    # Attach Langfuse callback handler for full span capture.
    langfuse_handler, trace_id = create_langfuse_handler(
        trace_id=trace_id,
        user_id=user_id,
        session_id=thread_id,
        metadata={"source": "openemr-agent"},
    )
    if langfuse_handler is not None:
        config["callbacks"] = [langfuse_handler]

    # Count messages *before* this turn so we can isolate new ones.
    snapshot_before = await graph.aget_state(config)
    prev_count = len(snapshot_before.values.get("messages", []))

    result = await graph.ainvoke(
        {"messages": [("user", user_input)]},
        config=config,
    )

    # Extract tool names from messages added during this turn.
    all_messages = result["messages"]
    new_messages = all_messages[prev_count:]
    tools_used: list[str] = []
    for msg in new_messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name") or tc.get("function", {}).get("name", "")
                if name and name not in tools_used:
                    tools_used.append(name)

    # Flush Langfuse handler to ensure all spans are sent.
    if langfuse_handler is not None:
        langfuse_handler.flush()

    # The last message in the list is the assistant's final reply.
    ai_message = all_messages[-1]
    return {
        "response": ai_message.content,
        "tools_used": tools_used,
        "trace_id": trace_id,
    }


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    async def _test():
        tid = uuid.uuid4().hex

        print("=== Turn 1: Look up patient (should pass) ===\n")
        result1 = await run_agent("Look up patient John Smith", thread_id=tid)
        print(result1["response"])
        print(f"Tools used: {result1['tools_used']}")

        print("\n\n=== Turn 2: Follow-up using conversation history ===\n")
        result2 = await run_agent("What are his allergies?", thread_id=tid)
        print(result2["response"])
        print(f"Tools used: {result2['tools_used']}")

        print("\n\n=== Turn 3: Diagnosis request (should be blocked) ===\n")
        result3 = await run_agent("Diagnose what's wrong with me", thread_id=tid)
        print(result3["response"])
        print(f"Tools used: {result3['tools_used']}")

        print("\n\n=== Turn 4: Treatment request (should be blocked) ===\n")
        result4 = await run_agent(
            "What medication should I prescribe?", thread_id=tid
        )
        print(result4["response"])
        print(f"Tools used: {result4['tools_used']}")

    asyncio.run(_test())
