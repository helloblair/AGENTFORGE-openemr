"""Drug Safety Validator — post-processing step that cross-references medications
against patient allergies and flags potential conflicts.

This module inspects the agent's response after tool calls involving
medication_list, medication_review, or drug_interaction_check.  When any of
these tools were used, it:

1. Checks whether allergy data is already in the conversation context.
   If not, calls ``allergy_check`` to fetch it.
2. Compares medication names / RxNorm codes against allergy substances
   using case-insensitive substring matching plus a curated cross-reactivity
   map (e.g. penicillin → amoxicillin).
3. If a match is found, prepends a prominent WARNING block to the response.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ── Cross-reactivity map ────────────────────────────────────────────────────
# Maps allergy substance (lowercased) to a list of drug names that are known
# to cross-react.  This is a curated MVP list; a production system would use
# RxNorm class membership or NDF-RT relationships.

CROSS_REACTIVITY: dict[str, list[str]] = {
    "penicillin": [
        "amoxicillin",
        "ampicillin",
        "augmentin",
        "amoxicillin/clavulanate",
        "piperacillin",
        "nafcillin",
        "oxacillin",
        "dicloxacillin",
    ],
    "sulfa": [
        "sulfamethoxazole",
        "trimethoprim/sulfamethoxazole",
        "bactrim",
        "sulfasalazine",
    ],
    "cephalosporin": [
        "cephalexin",
        "cefazolin",
        "ceftriaxone",
        "cefdinir",
        "cefuroxime",
    ],
    "nsaid": [
        "ibuprofen",
        "naproxen",
        "aspirin",
        "ketorolac",
        "indomethacin",
        "meloxicam",
        "diclofenac",
        "celecoxib",
    ],
    "aspirin": [
        "aspirin",
    ],
    "codeine": [
        "codeine",
        "hydrocodone",
        "oxycodone",
        "morphine",
        "tramadol",
    ],
}

# ── Clinical disclaimer ────────────────────────────────────────────────────
# Appended to EVERY response that involves clinical data (meds, allergies,
# conditions).

CLINICAL_DATA_DISCLAIMER = (
    "\n\n---\n"
    "*This is not medical advice — consult your healthcare provider "
    "before making any clinical decisions.*"
)

# Tools that trigger the drug safety check.
MEDICATION_TOOLS = {"medication_list", "drug_interaction_check"}

# Tools that indicate clinical data in the response (trigger disclaimer).
CLINICAL_DATA_TOOLS = {
    "medication_list",
    "drug_interaction_check",
    "allergy_check",
    "problem_list",
}


# ── Allergy parsing from tool output ────────────────────────────────────────


def _parse_allergies_from_text(allergy_text: str) -> list[str]:
    """Extract allergy substance names from allergy_check tool output.

    The allergy_check tool returns text like:
        Found 1 documented allergy(ies):

        - Penicillin
          Category: medication  |  Criticality: high
          Reactions: Anaphylaxis

    We extract the substance names (lines starting with ``- ``).
    """
    substances: list[str] = []
    for line in allergy_text.splitlines():
        line = line.strip()
        if line.startswith("- ") and "Category:" not in line and "Reactions:" not in line:
            substance = line[2:].strip()
            if substance and substance != "Unknown substance":
                substances.append(substance)
    return substances


def _normalize(name: str) -> str:
    """Lowercase and strip whitespace for comparison."""
    return name.lower().strip()


# ── Conflict detection ──────────────────────────────────────────────────────


def find_conflicts(
    allergy_substances: list[str],
    medication_names: list[str],
) -> list[dict[str, str]]:
    """Compare medications against allergies and return conflicts.

    Each conflict dict has keys: ``allergy``, ``medication``, ``reason``.
    """
    conflicts: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for allergy in allergy_substances:
        allergy_lower = _normalize(allergy)

        for med in medication_names:
            med_lower = _normalize(med)
            pair_key = (allergy_lower, med_lower)
            if pair_key in seen:
                continue

            # Direct match: allergy substance appears in drug name or vice versa.
            if allergy_lower in med_lower or med_lower in allergy_lower:
                seen.add(pair_key)
                conflicts.append({
                    "allergy": allergy,
                    "medication": med,
                    "reason": f"Direct match: patient is allergic to {allergy}",
                })
                continue

            # Cross-reactivity: check if allergy maps to drug class containing med.
            for allergy_key, cross_drugs in CROSS_REACTIVITY.items():
                if allergy_key not in allergy_lower:
                    continue
                cross_lower = [_normalize(d) for d in cross_drugs]
                for cross_drug in cross_lower:
                    if cross_drug in med_lower or med_lower in cross_drug:
                        if pair_key not in seen:
                            seen.add(pair_key)
                            conflicts.append({
                                "allergy": allergy,
                                "medication": med,
                                "reason": (
                                    f"Cross-reactivity: {med} belongs to the "
                                    f"{allergy_key} drug class — patient is "
                                    f"allergic to {allergy}"
                                ),
                            })
                        break

    return conflicts


def _parse_medications_from_text(med_text: str) -> list[str]:
    """Extract medication names from medication_list tool output.

    The medication_list tool returns text like:
        Found 2 active medication(s):

        - Lisinopril
          Dosage: 10 mg | Frequency: 1 per 1 day(s) | Route: oral
          ...

    We extract lines starting with ``- `` that are medication names,
    but only from sections that look like medication output (not allergy output).
    """
    # Only parse from text that looks like medication_list output.
    if "active medication" not in med_text.lower():
        return []

    medications: list[str] = []
    for line in med_text.splitlines():
        line = line.strip()
        if line.startswith("- ") and ":" not in line and "|" not in line:
            med_name = line[2:].strip()
            if med_name:
                medications.append(med_name)
    return medications


def _parse_drugs_from_interaction_text(text: str) -> list[str]:
    """Extract drug names from drug_interaction_check output or general response text.

    Looks for medication names mentioned in the response by scanning for
    common patterns in the agent's output text.
    """
    drugs: list[str] = []
    # Pattern: "- drug_a + drug_b" from interaction check output
    for match in re.finditer(r"^- (.+?) \+ (.+?)$", text, re.MULTILINE):
        drugs.extend([match.group(1).strip(), match.group(2).strip()])
    return drugs


# ── Warning formatter ───────────────────────────────────────────────────────


def format_warning(conflicts: list[dict[str, str]]) -> str:
    """Format conflict list into a prominent warning block."""
    lines = [
        "\n\n---",
        "**WARNING: POTENTIAL ALLERGY-MEDICATION CONFLICT DETECTED**\n",
    ]
    for c in conflicts:
        lines.append(
            f"- **{c['medication']}** — {c['reason']}"
        )
    lines.append(
        "\nPlease review with the prescribing provider and verify "
        "allergy records before proceeding."
    )
    lines.append("---\n")
    return "\n".join(lines)


# ── Main validator entry point ──────────────────────────────────────────────


def extract_medications_from_messages(messages: list) -> list[str]:
    """Scan message history for medication names from tool outputs."""
    medications: list[str] = []
    for msg in messages:
        content = getattr(msg, "content", "")
        if not isinstance(content, str):
            continue
        # From medication_list output
        medications.extend(_parse_medications_from_text(content))
        # From drug_interaction_check output
        medications.extend(_parse_drugs_from_interaction_text(content))
    return medications


def extract_allergies_from_messages(messages: list) -> list[str]:
    """Scan message history for allergy substances from tool outputs."""
    allergies: list[str] = []
    for msg in messages:
        content = getattr(msg, "content", "")
        if not isinstance(content, str):
            continue
        if "documented allergy" in content.lower() or "allergy" in content.lower():
            allergies.extend(_parse_allergies_from_text(content))
    return allergies


def check_drug_safety(
    messages: list,
    tools_used: list[str],
) -> tuple[str | None, bool]:
    """Run drug safety validation on the conversation state.

    Args:
        messages:   Full message history from the graph state.
        tools_used: List of tool names invoked during this turn.

    Returns:
        A tuple of (warning_text_or_none, needs_allergy_fetch).
        ``needs_allergy_fetch`` is True when medication tools were used
        but no allergy data was found in the conversation — the caller
        should invoke allergy_check and re-run this function.
    """
    med_tools_used = MEDICATION_TOOLS.intersection(tools_used)
    if not med_tools_used:
        return None, False

    medications = extract_medications_from_messages(messages)
    if not medications:
        return None, False

    allergies = extract_allergies_from_messages(messages)
    if not allergies:
        # Caller needs to fetch allergies and retry.
        return None, True

    conflicts = find_conflicts(allergies, medications)
    if not conflicts:
        return None, False

    return format_warning(conflicts), False


def should_add_clinical_disclaimer(tools_used: list[str]) -> bool:
    """Return True if the response involves clinical data and needs a disclaimer."""
    return bool(CLINICAL_DATA_TOOLS.intersection(tools_used))
