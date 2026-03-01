"""Organ transplant scoring criteria — pure computation, no I/O.

Contains organ-specific scoring algorithms used by the transplant_screening
tool. Each function returns a ScreeningResult dataclass.

Clinical thresholds based on published OPTN/UNOS policy.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field


@dataclass
class ScreeningResult:
    """Result of an organ-specific scoring computation."""

    organ_type: str
    score_name: str
    score_value: float | str | None
    threshold_met: bool
    threshold_description: str
    missing_data: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def _safe_float(value, default=None) -> float | None:
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def compute_kidney_score(labs: dict) -> ScreeningResult:
    """CKD staging based on eGFR.

    Threshold: eGFR < 20 mL/min/1.73m2.
    If eGFR not available but creatinine is, notes that lab-reported eGFR
    is needed (does NOT compute CKD-EPI to avoid clinical liability).
    """
    missing = []
    egfr = _safe_float(labs.get("egfr") or labs.get("33914-3"))
    creatinine = _safe_float(labs.get("creatinine") or labs.get("2160-0"))

    if egfr is None:
        missing.append("eGFR [LOINC 33914-3]")
        if creatinine is not None:
            # Can't compute eGFR from creatinine alone (liability)
            return ScreeningResult(
                organ_type="kidney",
                score_name="eGFR",
                score_value=None,
                threshold_met=False,
                threshold_description="eGFR < 20 mL/min/1.73m2",
                missing_data=missing,
                details={
                    "creatinine": creatinine,
                    "note": "Creatinine found but lab-reported eGFR required for staging",
                },
            )
        missing.append("Creatinine (Serum) [LOINC 2160-0]")
        return ScreeningResult(
            organ_type="kidney",
            score_name="eGFR",
            score_value=None,
            threshold_met=False,
            threshold_description="eGFR < 20 mL/min/1.73m2",
            missing_data=missing,
            details={"note": "Insufficient lab data for kidney scoring"},
        )

    threshold_met = egfr < 20
    ckd_stage = (
        "Stage 5 (ESRD)" if egfr < 15
        else "Stage 4" if egfr < 30
        else "Stage 3b" if egfr < 45
        else "Stage 3a" if egfr < 60
        else "Stage 2" if egfr < 90
        else "Stage 1"
    )

    return ScreeningResult(
        organ_type="kidney",
        score_name="eGFR",
        score_value=egfr,
        threshold_met=threshold_met,
        threshold_description="eGFR < 20 mL/min/1.73m2",
        missing_data=missing,
        details={
            "ckd_stage": ckd_stage,
            "creatinine": creatinine,
        },
    )


def compute_liver_meld(labs: dict) -> ScreeningResult:
    """MELD score from bilirubin, INR, creatinine, sodium.

    MELD = 10 * (0.957*ln(Cr) + 0.378*ln(Bili) + 1.120*ln(INR) + 0.643)
    Clamped per UNOS rules: Cr 1.0-4.0, Bili min 1.0, INR min 1.0
    MELD-Na adjustment when MELD > 11.
    Threshold: MELD >= 15.
    """
    missing = []
    creatinine = _safe_float(labs.get("creatinine") or labs.get("2160-0"))
    bilirubin = _safe_float(labs.get("bilirubin") or labs.get("1975-2"))
    inr = _safe_float(labs.get("inr") or labs.get("6301-6"))
    sodium = _safe_float(labs.get("sodium") or labs.get("2951-2"))

    if creatinine is None:
        missing.append("Creatinine (Serum) [LOINC 2160-0]")
    if bilirubin is None:
        missing.append("Bilirubin (Total) [LOINC 1975-2]")
    if inr is None:
        missing.append("INR [LOINC 6301-6]")

    if any(v is None for v in [creatinine, bilirubin, inr]):
        return ScreeningResult(
            organ_type="liver",
            score_name="MELD",
            score_value=None,
            threshold_met=False,
            threshold_description="MELD >= 15",
            missing_data=missing,
            details={"note": "Insufficient lab data for MELD calculation"},
        )

    # Clamp per UNOS rules
    cr = max(1.0, min(4.0, creatinine))
    bili = max(1.0, bilirubin)
    inr_val = max(1.0, inr)

    # MELD formula
    meld_raw = 10 * (
        0.957 * math.log(cr)
        + 0.378 * math.log(bili)
        + 1.120 * math.log(inr_val)
        + 0.643
    )
    meld = round(meld_raw)

    # MELD-Na adjustment
    if sodium is not None and meld > 11:
        na = max(125, min(137, sodium))
        meld_na = round(
            meld + 1.32 * (137 - na) - (0.033 * meld * (137 - na))
        )
        meld = max(meld, meld_na)
    elif sodium is None:
        missing.append("Sodium (Serum) [LOINC 2951-2] — needed for MELD-Na")

    # Cap at 40
    meld = min(40, max(6, meld))

    return ScreeningResult(
        organ_type="liver",
        score_name="MELD",
        score_value=meld,
        threshold_met=meld >= 15,
        threshold_description="MELD >= 15",
        missing_data=missing,
        details={
            "creatinine_raw": creatinine,
            "bilirubin_raw": bilirubin,
            "inr_raw": inr,
            "sodium_raw": sodium,
        },
    )


def compute_heart_score(labs: dict, conditions: list[dict] | None = None) -> ScreeningResult:
    """NYHA class from conditions + ejection fraction from labs.

    Threshold: NYHA Class III/IV or EF < 25%.
    NYHA is extracted from problem list conditions (ICD-10 or text).
    """
    missing = []
    ef = _safe_float(labs.get("ejection_fraction") or labs.get("10230-1"))
    bnp = _safe_float(labs.get("bnp") or labs.get("30934-4"))

    if ef is None:
        missing.append("Ejection Fraction [LOINC 10230-1]")

    # Try to extract NYHA class from conditions
    nyha_class = None
    if conditions:
        for cond in conditions:
            name = (cond.get("name") or cond.get("condition_name") or "").lower()
            code = cond.get("icd10_code", "")

            # Look for NYHA in text
            nyha_match = re.search(r"nyha\s+(class\s+)?(i{1,3}v?|[1-4])", name)
            if nyha_match:
                raw = nyha_match.group(2).strip().upper()
                nyha_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "IIIV": 4}
                nyha_class = nyha_map.get(raw) or int(raw) if raw.isdigit() else None
                break

    details = {}
    if ef is not None:
        details["ejection_fraction"] = ef
    if bnp is not None:
        details["bnp"] = bnp
    if nyha_class is not None:
        details["nyha_class"] = nyha_class

    # Determine threshold
    ef_met = ef is not None and ef < 25
    nyha_met = nyha_class is not None and nyha_class >= 3
    threshold_met = ef_met or nyha_met

    score_parts = []
    if nyha_class is not None:
        score_parts.append(f"NYHA Class {nyha_class}")
    if ef is not None:
        score_parts.append(f"EF {ef}%")
    score_display = " / ".join(score_parts) if score_parts else None

    return ScreeningResult(
        organ_type="heart",
        score_name="NYHA / EF",
        score_value=score_display,
        threshold_met=threshold_met,
        threshold_description="NYHA Class III+ or EF < 25%",
        missing_data=missing,
        details=details,
    )


def compute_lung_score(labs: dict) -> ScreeningResult:
    """FEV1 % predicted. Threshold: FEV1 < 25% predicted."""
    missing = []
    fev1_pct = _safe_float(labs.get("fev1_pct_predicted") or labs.get("19926-5"))
    fev1 = _safe_float(labs.get("fev1") or labs.get("20150-9"))

    if fev1_pct is None:
        missing.append("FEV1 % Predicted [LOINC 19926-5]")

    if fev1_pct is None and fev1 is None:
        missing.append("FEV1 [LOINC 20150-9]")
        return ScreeningResult(
            organ_type="lung",
            score_name="FEV1",
            score_value=None,
            threshold_met=False,
            threshold_description="FEV1 < 25% predicted",
            missing_data=missing,
            details={"note": "Insufficient PFT data for lung scoring"},
        )

    details = {}
    if fev1 is not None:
        details["fev1_absolute"] = fev1
    if fev1_pct is not None:
        details["fev1_pct_predicted"] = fev1_pct

    threshold_met = fev1_pct is not None and fev1_pct < 25

    return ScreeningResult(
        organ_type="lung",
        score_name="FEV1",
        score_value=f"{fev1_pct}% predicted" if fev1_pct is not None else None,
        threshold_met=threshold_met,
        threshold_description="FEV1 < 25% predicted",
        missing_data=missing,
        details=details,
    )
