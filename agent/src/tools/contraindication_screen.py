"""Contraindication screening using ICD-10-CM code ranges.

Screens a patient's problem list against ICD-10 contraindication ranges
for organ transplant candidacy. Uses prefix matching against published
OPTN/UNOS contraindication categories.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Contraindication:
    """A detected contraindication from the patient's problem list."""

    category: str  # e.g., "substance_abuse", "malignancy", "obesity", "psychiatric"
    icd10_code: str
    condition_name: str
    severity: str  # "absolute" or "relative"
    description: str


# ICD-10 prefix ranges for transplant contraindications.
# Derived from CMS ICD-10-CM FY2026 code set, filtered per OPTN policy.
CONTRAINDICATION_RANGES: dict[str, dict] = {
    "substance_abuse": {
        "prefix_range": ("F10", "F19"),
        "severity": "absolute",
        "description": "Active substance use disorders",
    },
    "malignancy": {
        "prefix_range": ("C00", "C96"),
        "severity": "absolute",
        "description": "Active malignancy (review within 5-year window)",
    },
    "obesity": {
        "prefix_range": ("E66", "E66"),
        "severity": "relative",
        "description": "Obesity (may require weight management before listing)",
    },
    "psychiatric": {
        "prefix_range": ("F20", "F29"),
        "severity": "relative",
        "description": "Schizophrenia spectrum and other psychotic disorders",
    },
}


def _code_in_range(icd10_code: str, range_start: str, range_end: str) -> bool:
    """Check if an ICD-10 code falls within a prefix range.

    Uses the first 3 characters of the code for prefix comparison.
    E.g., "F10.20" falls within ("F10", "F19").
    """
    prefix = icd10_code.replace(".", "")[:3].upper()
    start = range_start.replace(".", "")[:3].upper()
    end = range_end.replace(".", "")[:3].upper()
    return start <= prefix <= end


def screen_contraindications(conditions: list[dict]) -> list[Contraindication]:
    """Screen a list of patient conditions for transplant contraindications.

    Args:
        conditions: List of dicts, each with at least 'icd10_code' and 'name' keys.
            These match the output format of problem_list tool parsing.

    Returns:
        List of Contraindication objects found. Empty list = no contraindications.
    """
    found: list[Contraindication] = []

    for condition in conditions:
        code = condition.get("icd10_code", "")
        name = condition.get("name", "") or condition.get("condition_name", "")

        if not code:
            continue

        for category, spec in CONTRAINDICATION_RANGES.items():
            range_start, range_end = spec["prefix_range"]
            if _code_in_range(code, range_start, range_end):
                found.append(Contraindication(
                    category=category,
                    icd10_code=code,
                    condition_name=name,
                    severity=spec["severity"],
                    description=spec["description"],
                ))
                break  # Each condition matches at most one category

    return found
