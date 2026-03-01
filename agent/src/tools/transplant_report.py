"""Format transplant candidacy screening reports.

Assembles structured plain-text reports from scoring results,
contraindication findings, and medication context. All reports
include a mandatory screening disclaimer.
"""

from __future__ import annotations

from src.tools.transplant_criteria import ScreeningResult
from src.tools.contraindication_screen import Contraindication

SCREENING_DISCLAIMER = (
    "\n\n---\n"
    "**SCREENING TOOL DISCLAIMER**\n\n"
    "This is an automated screening assessment for clinical decision support only. "
    "It is NOT a diagnostic determination of transplant candidacy. "
    "Final transplant listing decisions must be made by a qualified transplant team "
    "following comprehensive evaluation including psychosocial assessment, "
    "imaging, and specialist consultation.\n"
    "---"
)


def format_screening_report(
    organ_type: str,
    score: ScreeningResult,
    contraindications: list[Contraindication],
    medications_text: str = "",
    criteria_text: str = "",
) -> str:
    """Assemble the full candidacy screening report.

    Args:
        organ_type: Target organ (kidney, liver, heart, lung).
        score: ScreeningResult from the scoring function.
        contraindications: List of Contraindication objects found.
        medications_text: Raw text from medication_list tool.
        criteria_text: Raw text from criteria lookup tool.

    Returns:
        Formatted plain-text report with markdown.
    """
    sections: list[str] = []

    # Header
    sections.append(
        f"## {organ_type.upper()} TRANSPLANT CANDIDACY SCREENING REPORT\n"
    )

    # Score section
    sections.append(f"### Clinical Score: {score.score_name}")
    if score.score_value is not None:
        sections.append(f"  Value: {score.score_value}")
    else:
        sections.append("  Value: INCOMPLETE (see missing data below)")
    sections.append(f"  Threshold: {score.threshold_description}")

    if score.score_value is not None:
        meets = "**YES** — meets referral criteria" if score.threshold_met else "**NO** — does not meet referral criteria"
        sections.append(f"  Meets referral criteria: {meets}")
    else:
        sections.append("  Meets referral criteria: **UNDETERMINED** (missing data)")

    # Score details
    if score.details:
        sections.append("\n  Additional details:")
        for key, val in score.details.items():
            if val is not None and key != "note":
                sections.append(f"    - {key}: {val}")
        note = score.details.get("note")
        if note:
            sections.append(f"    Note: {note}")

    # Missing data alerts
    if score.missing_data:
        sections.append("\n### MISSING DATA ALERTS")
        for item in score.missing_data:
            sections.append(f"  - {item}")
        sections.append(
            "  ** These values are needed for a complete assessment **"
        )

    # Contraindication flags
    sections.append("\n### CONTRAINDICATION SCREENING")
    if not contraindications:
        sections.append(
            "  No contraindications detected in the current problem list."
        )
    else:
        absolute = [c for c in contraindications if c.severity == "absolute"]
        relative = [c for c in contraindications if c.severity == "relative"]

        if absolute:
            sections.append(
                f"\n  **ABSOLUTE CONTRAINDICATIONS ({len(absolute)}):**"
            )
            for c in absolute:
                sections.append(
                    f"  - [{c.icd10_code}] {c.condition_name} "
                    f"({c.category}: {c.description})"
                )

        if relative:
            sections.append(
                f"\n  **RELATIVE CONTRAINDICATIONS ({len(relative)}):**"
            )
            for c in relative:
                sections.append(
                    f"  - [{c.icd10_code}] {c.condition_name} "
                    f"({c.category}: {c.description})"
                )

    # Medication context (brief)
    if medications_text and "no active medications" not in medications_text.lower():
        sections.append("\n### CURRENT MEDICATIONS")
        sections.append("  (See medication list for immunosuppression planning)")

    # Next steps
    sections.append("\n### RECOMMENDED NEXT STEPS")
    if score.threshold_met and not any(
        c.severity == "absolute" for c in contraindications
    ):
        sections.append("  1. Refer to transplant center for comprehensive evaluation")
        sections.append("  2. Complete any missing lab work identified above")
        sections.append("  3. Schedule required pre-transplant evaluations:")
        sections.append("     - Psychosocial assessment")
        sections.append("     - Substance screening")
        sections.append("     - HLA typing and crossmatch")
        if organ_type == "kidney":
            sections.append("     - Cardiac clearance")
        elif organ_type == "heart":
            sections.append("     - Right heart catheterization")
            sections.append("     - Pulmonary function tests")
        elif organ_type == "lung":
            sections.append("     - Cardiac clearance")
            sections.append("     - 6-minute walk test")
        elif organ_type == "liver":
            sections.append("     - Hepatology assessment")
            sections.append("     - Cardiac clearance")
        sections.append("  4. Verify insurance coverage for transplant")
    elif any(c.severity == "absolute" for c in contraindications):
        sections.append(
            "  1. Address absolute contraindication(s) before proceeding"
        )
        sections.append(
            "  2. Consult with transplant team about contraindication resolution"
        )
        sections.append(
            "  3. Re-screen after contraindication status changes"
        )
    elif not score.threshold_met and score.score_value is not None:
        sections.append(
            "  1. Patient does not currently meet transplant referral thresholds"
        )
        sections.append("  2. Continue monitoring disease progression")
        sections.append("  3. Re-screen if clinical status changes")
    else:
        sections.append("  1. Obtain missing lab work to complete screening")
        sections.append("  2. Re-run screening when data is available")

    # Disclaimer
    sections.append(SCREENING_DISCLAIMER)

    return "\n".join(sections)
