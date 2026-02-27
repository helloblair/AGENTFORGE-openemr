"""End-to-end smoke tests — one query per tool, against the live OpenEMR API.

Each test sends a natural-language query to the agent, waits for the full
response, and checks that the expected tool was actually invoked.  Every test
runs in its own thread so conversation history never bleeds across cases.

Run from the agent/ directory:
    python -m scripts.smoke_test

Flags:
    --tool <name>   Run only the test for a specific tool
    --verbose       Print the full agent response for every test
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent.graph import run_agent

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

# ── ANSI colours ──────────────────────────────────────────────────────────────

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


# ── Test definition ───────────────────────────────────────────────────────────

@dataclass
class ToolTest:
    tool: str                        # tool name expected in tools_used
    query: str                       # natural-language query sent to the agent
    must_contain: list[str] = field(default_factory=list)  # substrings that should appear in the response


TESTS: list[ToolTest] = [
    ToolTest(
        tool="patient_lookup",
        query="Look up a patient named John Smith.",
        must_contain=["Smith"],
    ),
    ToolTest(
        tool="allergy_check",
        query="What allergies does John Smith have on file?",
        must_contain=[],   # empty = skip response-content check
    ),
    ToolTest(
        tool="medication_list",
        query="What medications is John Smith currently taking?",
        must_contain=[],
    ),
    ToolTest(
        tool="problem_list",
        query="What conditions are on John Smith's active problem list?",
        must_contain=[],
    ),
    ToolTest(
        tool="insurance_coverage",
        query="What insurance coverage does John Smith have?",
        must_contain=[],
    ),
    ToolTest(
        tool="drug_interaction_check",
        query="Are there any interactions between aspirin and warfarin?",
        must_contain=["aspirin", "warfarin"],
    ),
    ToolTest(
        tool="provider_lookup",
        query="Show me a list of all providers in the system.",
        must_contain=[],
    ),
]


# ── Runner ────────────────────────────────────────────────────────────────────

@dataclass
class Result:
    test: ToolTest
    passed: bool
    tools_used: list[str]
    response: str
    error: str = ""


async def run_one(test: ToolTest) -> Result:
    thread_id = uuid.uuid4().hex
    try:
        result = await run_agent(test.query, thread_id=thread_id)
    except Exception as exc:
        return Result(test=test, passed=False, tools_used=[], response="", error=str(exc))

    tools_used = result.get("tools_used", [])
    response   = result.get("response", "")

    # Pass criteria:
    #   1. Expected tool appears in tools_used
    #   2. All must_contain strings appear in the response (case-insensitive)
    tool_ok = test.tool in tools_used
    content_ok = all(s.lower() in response.lower() for s in test.must_contain)
    passed = tool_ok and content_ok

    return Result(test=test, passed=passed, tools_used=tools_used, response=response)


async def run_all(only_tool: str | None = None) -> list[Result]:
    tests = [t for t in TESTS if only_tool is None or t.tool == only_tool]
    # Run tests sequentially so output is readable and auth tokens are reused
    results = []
    for test in tests:
        results.append(await run_one(test))
    return results


# ── Output ────────────────────────────────────────────────────────────────────

def print_results(results: list[Result], verbose: bool = False) -> None:
    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}  OpenEMR Agent — Tool Smoke Tests{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}\n")

    passed = 0
    for r in results:
        icon = f"{GREEN}✓ PASS{RESET}" if r.passed else f"{RED}✗ FAIL{RESET}"
        tool_label = (
            f"{GREEN}{r.test.tool}{RESET}"
            if r.test.tool in r.tools_used
            else f"{RED}{r.test.tool}{RESET}"
        )

        print(f"  {icon}  {BOLD}{r.test.tool}{RESET}")
        print(f"         Query      : {CYAN}{r.test.query}{RESET}")
        print(f"         Tools used : {', '.join(r.tools_used) if r.tools_used else '(none)'}")

        if r.error:
            print(f"         {RED}Error: {r.error}{RESET}")
        elif not r.passed:
            if r.test.tool not in r.tools_used:
                print(f"         {YELLOW}⚠ Expected '{r.test.tool}' in tools_used{RESET}")
            for s in r.test.must_contain:
                if s.lower() not in r.response.lower():
                    print(f"         {YELLOW}⚠ Response missing '{s}'{RESET}")

        if verbose or not r.passed:
            # Indent and truncate long responses for readability
            preview = r.response[:600] + ("…" if len(r.response) > 600 else "")
            indented = "\n".join(f"         {line}" for line in preview.splitlines())
            print(f"\n{indented}\n")

        print()
        if r.passed:
            passed += 1

    total = len(results)
    colour = GREEN if passed == total else RED
    print(f"{BOLD}{'─' * 60}{RESET}")
    print(f"  {colour}{BOLD}{passed}/{total} tests passed{RESET}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test each agent tool against the live API.")
    parser.add_argument("--tool", metavar="NAME", help="Run only this tool's test")
    parser.add_argument("--verbose", action="store_true", help="Print full responses")
    args = parser.parse_args()

    if args.tool:
        known = {t.tool for t in TESTS}
        if args.tool not in known:
            print(f"Unknown tool '{args.tool}'. Known: {', '.join(sorted(known))}")
            sys.exit(1)

    results = asyncio.run(run_all(only_tool=args.tool))
    print_results(results, verbose=args.verbose)

    if not all(r.passed for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
