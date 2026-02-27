"""Hallucination detector — LLM-based fact-checking of agent responses.

After the agent generates a final response, this module sends the response
and all tool outputs from the current request to a fast, cheap LLM (OpenAI
GPT-4o-mini preferred, Claude Haiku fallback) to identify claims not
supported by the source data.

Results:
- CLEAN → no action taken
- Unsupported claims found → appends warning to response
- API error / unavailable → appends "Verification unavailable" note
- All results logged to Langfuse when available

Design constraints:
- Must not add more than 2–3 s latency → short max_tokens (256)
- Must not block the response if the check fails
"""

from __future__ import annotations

import logging
import time

from langchain_core.messages import AIMessage, ToolMessage

from src.config import ANTHROPIC_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

CLEAN_VERDICT = "CLEAN"

HALLUCINATION_WARNING = (
    "\n\n---\n"
    "\u26a0\ufe0f **Some claims in this response could not be verified "
    "against the source data.** Please double-check with clinical records.\n"
    "---"
)

VERIFICATION_UNAVAILABLE = (
    "\n\n---\n"
    "*Verification unavailable for this response.*\n"
    "---"
)

_FACT_CHECK_PROMPT = """\
You are a strict fact-checker for a healthcare AI assistant. Your job is to \
compare the RESPONSE against the SOURCE DATA that came from tool calls to an \
electronic health record system.

Rules:
1. List every claim in RESPONSE that is NOT directly supported by SOURCE DATA.
2. A "claim" is any specific fact: names, dates, dosages, diagnoses, test \
results, provider names, insurance details, or medical assertions.
3. General disclaimers, confidence scores, and hedging language are NOT claims.
4. If the response simply says "no data found" or similar and the source data \
confirms that, it is supported.
5. If ALL factual claims are supported by SOURCE DATA, respond with exactly: \
CLEAN
6. If you find unsupported claims, list them as a numbered list. Do NOT \
include any other commentary.

SOURCE DATA:
{source_data}

RESPONSE:
{response}"""

# ── Helpers ──────────────────────────────────────────────────────────────────


def _collect_tool_outputs(messages: list) -> str:
    """Extract all ToolMessage content from the message list.

    Returns a single string with each tool output separated by a divider.
    """
    outputs: list[str] = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            tool_name = getattr(msg, "name", "unknown_tool")
            outputs.append(f"[Tool: {tool_name}]\n{content}")

    return "\n\n---\n\n".join(outputs) if outputs else ""


def _get_response_text(messages: list) -> str:
    """Get the final AI response text from the message list."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content
    return ""


async def _check_with_openai(prompt: str) -> str:
    """Call OpenAI GPT-4o-mini for fact-checking."""
    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 256,
                "temperature": 0.0,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


async def _check_with_claude(prompt: str) -> str:
    """Fallback: call Claude Haiku for fact-checking."""
    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 256,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()


# ── Public API ───────────────────────────────────────────────────────────────


async def check_hallucination(
    messages: list,
    tools_used: list[str],
) -> dict[str, str | bool | float]:
    """Run hallucination detection on the agent's response.

    Args:
        messages: Full message list from the current turn (includes
            ToolMessages and the final AIMessage).
        tools_used: List of tool names invoked during this turn.

    Returns:
        A dict with:
        - ``verdict``: "CLEAN", "FLAGGED", or "ERROR"
        - ``detail``: The raw LLM output (unsupported claims or "CLEAN")
        - ``warning``: The user-facing warning string to append (empty if clean)
        - ``latency_ms``: Time taken for the check in milliseconds
    """
    # Skip if no tools were used — nothing to fact-check against.
    if not tools_used:
        return {
            "verdict": "CLEAN",
            "detail": "No tools used — skipped",
            "warning": "",
            "latency_ms": 0.0,
        }

    source_data = _collect_tool_outputs(messages)
    response_text = _get_response_text(messages)

    if not source_data or not response_text:
        return {
            "verdict": "CLEAN",
            "detail": "No source data or response — skipped",
            "warning": "",
            "latency_ms": 0.0,
        }

    prompt = _FACT_CHECK_PROMPT.format(
        source_data=source_data,
        response=response_text,
    )

    start = time.monotonic()

    try:
        # Prefer OpenAI (cheaper, faster) if key is available.
        if OPENAI_API_KEY:
            result = await _check_with_openai(prompt)
        elif ANTHROPIC_API_KEY:
            result = await _check_with_claude(prompt)
        else:
            raise RuntimeError("No API key available for hallucination check")
    except Exception:
        elapsed = (time.monotonic() - start) * 1000
        logger.exception("Hallucination check failed (%.0f ms)", elapsed)
        return {
            "verdict": "ERROR",
            "detail": "API call failed",
            "warning": VERIFICATION_UNAVAILABLE,
            "latency_ms": elapsed,
        }

    elapsed = (time.monotonic() - start) * 1000
    logger.info("Hallucination check completed in %.0f ms", elapsed)

    # Parse the result.
    is_clean = result.strip().upper() == CLEAN_VERDICT

    if is_clean:
        logger.info("Hallucination check: CLEAN")
        return {
            "verdict": "CLEAN",
            "detail": result,
            "warning": "",
            "latency_ms": elapsed,
        }
    else:
        logger.warning("Hallucination check: FLAGGED — %s", result)
        return {
            "verdict": "FLAGGED",
            "detail": result,
            "warning": HALLUCINATION_WARNING,
            "latency_ms": elapsed,
        }
