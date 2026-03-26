"""Format donor viability screening reports.

Assembles structured plain-text reports from donor scoring results.
Follows the same pattern as transplant_report.py but for the donor
perspective (living and deceased).
"""

from __future__ import annotations

from src.tools.donor_criteria import DonorScreeningResult
from src.tools.contraindication_screen import Contraindication

DONOR_DISCLAIMER = (
    "\n\n---\n"
    "**DONOR SCREENING DISCLAIMER**\n\n"
    "This is an automated donor viability assessment for clinical decision support only. "
    "It is NOT a definitive determination of organ donor suitability. "
    "Final donor eligibility must be determined by the transplant team following "
    "comprehensive evaluation including independent donor advocacy, psychosocial "
    "assessment, cross-sectional imaging, and informed consent.\n"
    "---"
)


def format_donor_report(
    organ_type: str,
    donor_type: str,
    score: DonorScreeningResult,
    contraindications: list[Contraindication] | None = None,
    medications_text: str = "",
    patient_name: str = "",
) -> str:
    """Assemble the full donor viability report.

    Args:
        organ_type: Target organ (kidney, liver, heart, lung).
        donor_type: "living" or "deceased".
        score: DonorScreeningResult from the scoring function.
        contraindications: Optional list of Contraindication objects.
        medications_text: Active medications text.
        patient_name: Donor patient name for the report header.

    Returns:
        Formatted plain-text report with markdown.
    """
    sections: list[str] = []
    contraindications = contraindications or []

    # Header
    donor_label = donor_type.upper()
    sections.append(
        f"## {organ_type.upper()} — {donor_label} DONOR VIABILITY REPORT\n"
    )
    if patient_name:
        sections.append(f"**Donor:** {patient_name}\n")

    # Viability summary
    if score.viable:
        sections.append("### VIABILITY: **POTENTIALLY VIABLE**")
    else:
        sections.append("### VIABILITY: **NOT VIABLE** (see details below)")

    # Score section
    sections.append(f"\n### Clinical Assessment: {score.score_name}")
    if score.score_value is not None:
        sections.append(f"  Value: {score.score_value}")
    else:
        sections.append("  Value: INCOMPLETE (see missing data below)")
    sections.append(f"  Criteria: {score.viability_description}")

    # Score details
    if score.details:
        sections.append("\n  Donor metrics:")
        for key, val in score.details.items():
            if val is not None:
                label = key.replace("_", " ").title()
                sections.append(f"    - {label}: {val}")

    # Risk factors
    if score.risk_factors:
        sections.append(f"\n### RISK FACTORS ({len(score.risk_factors)})")
        for rf in score.risk_factors:
            sections.append(f"  - {rf}")

    # Missing data
    if score.missing_data:
        sections.append("\n### MISSING DATA")
        for item in score.missing_data:
            sections.append(f"  - {item}")
        sections.append("  ** These values are needed for a complete assessment **")

    # Contraindications (for living donors)
    if contraindications:
        sections.append("\n### DONOR CONTRAINDICATIONS")
        absolute = [c for c in contraindications if c.severity == "absolute"]
        relative = [c for c in contraindications if c.severity == "relative"]

        if absolute:
            sections.append(f"\n  **ABSOLUTE CONTRAINDICATIONS ({len(absolute)}):**")
            for c in absolute:
                sections.append(
                    f"  - [{c.icd10_code}] {c.condition_name} "
                    f"({c.category}: {c.description})"
                )

        if relative:
            sections.append(f"\n  **RELATIVE CONTRAINDICATIONS ({len(relative)}):**")
            for c in relative:
                sections.append(
                    f"  - [{c.icd10_code}] {c.condition_name} "
                    f"({c.category}: {c.description})"
                )
    elif donor_type == "living":
        sections.append("\n### DONOR CONTRAINDICATIONS")
        sections.append("  No contraindications detected in the donor's problem list.")

    # Medications (living donors)
    if donor_type == "living" and medications_text and "no active medications" not in medications_text.lower():
        sections.append("\n### CURRENT MEDICATIONS")
        sections.append("  (Review for medications that may affect organ function or surgical risk)")

    # Next steps
    sections.append("\n### RECOMMENDED NEXT STEPS")
    if score.viable and not any(c.severity == "absolute" for c in contraindications):
        if donor_type == "living":
            sections.append("  1. Independent living donor advocate (ILDA) consultation")
            sections.append("  2. Complete cross-sectional imaging (CT/MRI angiography)")
            sections.append("  3. Psychosocial evaluation")
            sections.append("  4. ABO/HLA typing and crossmatch with intended recipient")
            if organ_type == "kidney":
                sections.append("  5. 24-hour urine collection (protein, creatinine clearance)")
                sections.append("  6. Split renal function study (MAG3 scan)")
            elif organ_type == "liver":
                sections.append("  5. Liver volumetry assessment")
                sections.append("  6. Hepatology clearance")
            sections.append(f"  {7 if organ_type in ('kidney', 'liver') else 5}. Surgical risk assessment and informed consent")
        else:
            sections.append("  1. Confirm brain death / DCD criteria per OPTN policy")
            sections.append("  2. Infectious disease screening panel (HIV, HBV, HCV, CMV, EBV)")
            sections.append("  3. ABO typing and HLA crossmatch with waitlisted recipients")
            sections.append("  4. Organ procurement team notification")
            if organ_type == "kidney":
                sections.append("  5. Confirm KDPI and allocate per OPTN kidney allocation policy")
                sections.append("  6. Machine perfusion if cold ischemia time > 24h anticipated")
            elif organ_type == "liver":
                sections.append("  5. Liver biopsy if DRI > 1.6 or age > 60")
                sections.append("  6. Minimize cold ischemia time (target < 8h)")
            elif organ_type == "heart":
                sections.append("  5. Echocardiogram and coronary angiography if age > 45")
                sections.append("  6. Minimize ischemia time (target < 4h)")
            elif organ_type == "lung":
                sections.append("  5. Bronchoscopy and sputum culture")
                sections.append("  6. Arterial blood gas on FiO2 1.0, PEEP 5")
    elif any(c.severity == "absolute" for c in contraindications):
        sections.append("  1. Absolute contraindication(s) detected — donor not eligible")
        sections.append("  2. Document findings and notify transplant coordinator")
    else:
        if score.missing_data:
            sections.append("  1. Obtain missing data to complete donor evaluation")
            sections.append("  2. Re-run screening when data is available")
        else:
            sections.append("  1. Donor does not meet viability criteria")
            sections.append("  2. Document findings for transplant team review")

    # Disclaimer
    sections.append(DONOR_DISCLAIMER)

    return "\n".join(sections)
