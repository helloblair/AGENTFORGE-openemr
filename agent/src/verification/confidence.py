"""Confidence scoring for agent responses.

Computes a 0.0–1.0 confidence score based on:
- Tool success rate (all returned data = 1.0, errors = lower)
- Data completeness (empty results reduce score)
- Tool errors during execution reduce score

Display tiers:
- >= 0.8: no extra messaging
- 0.6–0.8: warning about incomplete information
- < 0.6: low confidence — recommend verifying with clinical staff
"""

from __future__ import annotations

import logging
import re

from langchain_core.messages import AIMessage, ToolMessage

logger = logging.getLogger(__name__)

# ── Display thresholds ────────────────────────────────────────────────────────

HIGH_CONFIDENCE = 0.8
MEDIUM_CONFIDENCE = 0.6

MEDIUM_WARNING = (
    "\n\n---\n"
    "\u26a0\ufe0f **Confidence: {score:.2f}** — Some information may be incomplete.\n"
    "---"
)

LOW_WARNING = (
    "\n\n---\n"
    "\U0001f534 **Confidence: {score:.2f}** — Low confidence — "
    "recommend verifying with clinical staff.\n"
    "---"
)

HIGH_BADGE = "\n\n---\n**Confidence: {score:.2f}**\n---"

# Patterns indicating empty / no-data results from tools.
_EMPTY_RESULT_PATTERNS = [
    re.compile(r"no\s+active\s+(medications?|conditions?)", re.IGNORECASE),
    re.compile(r"no\s+(providers?|practitioners?)\s+found", re.IGNORECASE),
    re.compile(r"no\s+insurance\s+coverage\s+on\s+file", re.IGNORECASE),
    re.compile(r"no\s+documented\s+allerg", re.IGNORECASE),
    re.compile(r"no\s+(patients?|results?)\s+found", re.IGNORECASE),
    re.compile(r"no\s+active\s+.*documented", re.IGNORECASE),
    re.compile(r"no\s+known\s+drug\s+interactions?\s+found", re.IGNORECASE),
]

# Patterns indicating tool-level errors.
_ERROR_PATTERNS = [
    re.compile(r"error\s+(fetching|retrieving|looking up|checking)", re.IGNORECASE),
    re.compile(r"timed?\s*out", re.IGNORECASE),
    re.compile(r"failed\s+to\s+(fetch|retrieve|connect)", re.IGNORECASE),
    re.compile(r"authentication\s+(failed|error)", re.IGNORECASE),
    re.compile(r"could\s+not\s+(reach|connect|access)", re.IGNORECASE),
]


def _is_empty_result(text: str) -> bool:
    """Check if tool output indicates no data was returned."""
    return any(p.search(text) for p in _EMPTY_RESULT_PATTERNS)


def _is_error_result(text: str) -> bool:
    """Check if tool output indicates an error occurred."""
    return any(p.search(text) for p in _ERROR_PATTERNS)


def compute_confidence(messages: list, tools_used: list[str]) -> float:
    """Compute a 0.0–1.0 confidence score for the agent's response.

    Scoring formula:
    - Start at 1.0
    - If no tools were used (scope-guard blocked or pure LLM): return 1.0
    - For each tool invocation, check the corresponding ToolMessage:
      - Success with data: no penalty
      - Success but empty result: -0.15 per tool
      - Error: -0.30 per tool
    - Clamp to [0.0, 1.0]
    """
    if not tools_used:
        # Scope-guard blocked or no tools needed — full confidence in the
        # (deterministic) response.
        return 1.0

    # Collect ToolMessage results from the conversation.
    tool_results: list[ToolMessage] = [
        msg for msg in messages
        if isinstance(msg, ToolMessage)
    ]

    if not tool_results:
        # Tools were supposedly used but no ToolMessages found — suspicious.
        return 0.5

    total_tools = len(tool_results)
    errors = 0
    empties = 0

    for tm in tool_results:
        content = tm.content if isinstance(tm.content, str) else str(tm.content)
        if _is_error_result(content):
            errors += 1
        elif _is_empty_result(content):
            empties += 1

    # Compute score: start at 1.0, penalise errors and empties.
    score = 1.0
    if total_tools > 0:
        score -= (errors / total_tools) * 0.30 * total_tools
        score -= (empties / total_tools) * 0.15 * total_tools

    # Simpler: deduct per-tool penalties directly.
    score = 1.0 - (errors * 0.30) - (empties * 0.15)

    return max(0.0, min(1.0, score))


def format_confidence_message(score: float) -> str:
    """Return a display string for the confidence score.

    >= 0.8: numeric score only (no warning)
    0.6–0.8: warning about incomplete info
    < 0.6: low confidence alert
    """
    if score >= HIGH_CONFIDENCE:
        return HIGH_BADGE.format(score=score)
    elif score >= MEDIUM_CONFIDENCE:
        return MEDIUM_WARNING.format(score=score)
    else:
        return LOW_WARNING.format(score=score)
