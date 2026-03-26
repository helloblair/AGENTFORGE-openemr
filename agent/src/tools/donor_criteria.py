"""Organ donor viability scoring criteria — pure computation, no I/O.

Contains organ-specific donor evaluation algorithms for both living and
deceased donors. Each function returns a DonorScreeningResult dataclass.

Clinical thresholds based on published OPTN/UNOS living donor policy and
KDPI/DRI organ quality metrics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class DonorScreeningResult:
    """Result of a donor viability scoring computation."""

    organ_type: str
    donor_type: str  # "living" or "deceased"
    score_name: str
    score_value: float | str | None
    viable: bool
    viability_description: str
    missing_data: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    risk_factors: list[str] = field(default_factory=list)


def _safe_float(value, default=None) -> float | None:
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ── Living donor scoring ─────────────────────────────────────────────────────


def evaluate_living_kidney_donor(labs: dict, age: float | None = None, bmi: float | None = None) -> DonorScreeningResult:
    """Evaluate living kidney donor viability.

    Criteria (OPTN/UNOS Living Donor Policy):
    - eGFR >= 80 mL/min/1.73m2 (age-adjusted: >= 70 if age > 60)
    - Age 18-70 preferred
    - BMI < 35 preferred (< 30 ideal)
    - No proteinuria, no uncontrolled HTN, no diabetes
    """
    missing = []
    risk_factors = []

    egfr = _safe_float(labs.get("egfr") or labs.get("33914-3"))
    creatinine = _safe_float(labs.get("creatinine") or labs.get("2160-0"))
    hemoglobin = _safe_float(labs.get("hemoglobin") or labs.get("718-7"))
    albumin = _safe_float(labs.get("albumin") or labs.get("1751-7"))

    if egfr is None:
        missing.append("eGFR [LOINC 33914-3]")
    if creatinine is None:
        missing.append("Creatinine (Serum) [LOINC 2160-0]")

    details = {}
    viable = True

    # Age check
    if age is not None:
        details["age"] = age
        if age < 18:
            viable = False
            risk_factors.append("Below minimum donor age (18)")
        elif age > 70:
            viable = False
            risk_factors.append("Above maximum donor age (70)")
        elif age > 60:
            risk_factors.append("Age > 60 — requires age-adjusted eGFR threshold (>= 70)")

    # BMI check
    if bmi is not None:
        details["bmi"] = bmi
        if bmi >= 35:
            viable = False
            risk_factors.append(f"BMI {bmi} >= 35 — exceeds donor threshold")
        elif bmi >= 30:
            risk_factors.append(f"BMI {bmi} >= 30 — relative contraindication, requires evaluation")

    # eGFR check
    if egfr is not None:
        details["egfr"] = egfr
        threshold = 70 if (age is not None and age > 60) else 80
        if egfr < threshold:
            viable = False
            risk_factors.append(f"eGFR {egfr} < {threshold} — below donor threshold")
        else:
            details["egfr_status"] = "Adequate for donation"

    if creatinine is not None:
        details["creatinine"] = creatinine

    if hemoglobin is not None:
        details["hemoglobin"] = hemoglobin
        if hemoglobin < 12.0:
            risk_factors.append(f"Hemoglobin {hemoglobin} < 12.0 — anemia evaluation needed")

    if albumin is not None:
        details["albumin"] = albumin

    # If critical data missing, can't determine viability
    if egfr is None:
        viable = False

    score_display = f"eGFR {egfr}" if egfr is not None else "INCOMPLETE"

    return DonorScreeningResult(
        organ_type="kidney",
        donor_type="living",
        score_name="Living Kidney Donor eGFR",
        score_value=score_display,
        viable=viable and len([r for r in risk_factors if "exceeds" in r or "below" in r or "Below" in r or "Above" in r]) == 0,
        viability_description="eGFR >= 80 (>= 70 if age > 60), age 18-70, BMI < 35",
        missing_data=missing,
        details=details,
        risk_factors=risk_factors,
    )


def evaluate_living_liver_donor(labs: dict, age: float | None = None, bmi: float | None = None) -> DonorScreeningResult:
    """Evaluate living liver donor viability.

    Criteria:
    - Normal liver function (bilirubin < 1.2, INR < 1.1, albumin > 3.5)
    - Age 18-60 preferred
    - BMI < 35
    - No hepatic steatosis > 10% (would need imaging — flagged as missing)
    """
    missing = []
    risk_factors = []

    bilirubin = _safe_float(labs.get("bilirubin") or labs.get("1975-2"))
    inr = _safe_float(labs.get("inr") or labs.get("6301-6"))
    albumin = _safe_float(labs.get("albumin") or labs.get("1751-7"))
    creatinine = _safe_float(labs.get("creatinine") or labs.get("2160-0"))

    if bilirubin is None:
        missing.append("Bilirubin (Total) [LOINC 1975-2]")
    if inr is None:
        missing.append("INR [LOINC 6301-6]")
    if albumin is None:
        missing.append("Albumin (Serum) [LOINC 1751-7]")

    details = {}
    viable = True

    # Age check
    if age is not None:
        details["age"] = age
        if age < 18:
            viable = False
            risk_factors.append("Below minimum donor age (18)")
        elif age > 60:
            risk_factors.append("Age > 60 — increased surgical risk for living liver donation")

    # BMI check
    if bmi is not None:
        details["bmi"] = bmi
        if bmi >= 35:
            viable = False
            risk_factors.append(f"BMI {bmi} >= 35 — exceeds donor threshold")
        elif bmi >= 30:
            risk_factors.append(f"BMI {bmi} >= 30 — hepatic steatosis risk, imaging required")

    # Liver function checks
    if bilirubin is not None:
        details["bilirubin"] = bilirubin
        if bilirubin >= 1.2:
            risk_factors.append(f"Bilirubin {bilirubin} >= 1.2 — elevated")
            if bilirubin >= 2.0:
                viable = False

    if inr is not None:
        details["inr"] = inr
        if inr >= 1.1:
            risk_factors.append(f"INR {inr} >= 1.1 — coagulopathy evaluation needed")
            if inr >= 1.5:
                viable = False

    if albumin is not None:
        details["albumin"] = albumin
        if albumin < 3.5:
            risk_factors.append(f"Albumin {albumin} < 3.5 — low, hepatic synthetic dysfunction")
            if albumin < 3.0:
                viable = False

    # Imaging note
    missing.append("Liver volumetry / steatosis imaging (CT or MRI required)")

    if any(v is None for v in [bilirubin, inr, albumin]):
        viable = False

    score_parts = []
    if bilirubin is not None:
        score_parts.append(f"Bili {bilirubin}")
    if inr is not None:
        score_parts.append(f"INR {inr}")
    if albumin is not None:
        score_parts.append(f"Alb {albumin}")
    score_display = " / ".join(score_parts) if score_parts else "INCOMPLETE"

    return DonorScreeningResult(
        organ_type="liver",
        donor_type="living",
        score_name="Living Liver Donor Panel",
        score_value=score_display,
        viable=viable,
        viability_description="Bilirubin < 1.2, INR < 1.1, Albumin > 3.5, age 18-60, BMI < 35",
        missing_data=missing,
        details=details,
        risk_factors=risk_factors,
    )


# ── Deceased donor scoring ───────────────────────────────────────────────────


def compute_kdpi(
    age: float,
    creatinine: float,
    hcv_positive: bool = False,
    dcd: bool = False,
    height_cm: float | None = None,
    weight_kg: float | None = None,
    diabetes_history: bool = False,
    hypertension_history: bool = False,
    cause_of_death: str = "other",
) -> DonorScreeningResult:
    """Compute Kidney Donor Profile Index (KDPI) for deceased donors.

    KDPI is derived from the Kidney Donor Risk Index (KDRI).
    Uses the 2024 OPTN mapping table approximation.

    KDRI = exp(coefficients * risk factors)
    KDPI = percentile rank of KDRI among reference population
    """
    risk_factors = []
    details = {}

    # KDRI coefficients (simplified from OPTN KDRI calculator)
    kdri_log = 0.0

    # Age contribution
    details["age"] = age
    if age < 18:
        kdri_log += -0.0194 * (age - 40)
    elif age <= 50:
        kdri_log += 0.0128 * (age - 40)
    else:
        kdri_log += 0.0128 * (age - 40) + 0.0107 * (age - 50)
        risk_factors.append(f"Donor age {age} > 50 increases KDRI")

    # Creatinine (terminal)
    details["creatinine"] = creatinine
    cr = max(0.1, creatinine)
    kdri_log += 0.2200 * (cr - 1.0)
    if creatinine > 1.5:
        kdri_log += 0.2090
        risk_factors.append(f"Terminal creatinine {creatinine} > 1.5")

    # HCV
    if hcv_positive:
        kdri_log += 0.2400
        risk_factors.append("HCV positive donor")
        details["hcv"] = "Positive"
    else:
        details["hcv"] = "Negative"

    # DCD (donation after circulatory death)
    if dcd:
        kdri_log += 0.1330
        risk_factors.append("DCD donor (donation after circulatory death)")
        details["dcd"] = True

    # Diabetes
    if diabetes_history:
        kdri_log += 0.1300
        risk_factors.append("Donor history of diabetes")
        details["diabetes"] = True

    # Hypertension
    if hypertension_history:
        kdri_log += 0.1260
        risk_factors.append("Donor history of hypertension")
        details["hypertension"] = True

    # Cause of death
    if cause_of_death.lower() in ("cva", "stroke", "cerebrovascular"):
        kdri_log += 0.0881
        risk_factors.append("Cause of death: cerebrovascular")
        details["cause_of_death"] = "Cerebrovascular"
    else:
        details["cause_of_death"] = cause_of_death

    # BMI from height/weight
    if height_cm is not None and weight_kg is not None:
        bmi = weight_kg / ((height_cm / 100) ** 2)
        details["bmi"] = round(bmi, 1)
        # Weight contribution
        if weight_kg < 80:
            kdri_log += -0.0024 * (weight_kg - 80)

    kdri = math.exp(kdri_log)
    details["kdri"] = round(kdri, 4)

    # KDPI approximation from KDRI (using 2024 reference median KDRI = 1.25)
    # KDPI = CDF of KDRI in reference population
    # Simplified: KDPI ≈ 100 * Φ((ln(KDRI) - μ) / σ)
    # Using approximate reference: μ = 0.22, σ = 0.42
    z = (math.log(kdri) - 0.22) / 0.42
    kdpi = 100 * (0.5 * (1 + math.erf(z / math.sqrt(2))))
    kdpi = round(max(0, min(100, kdpi)))

    details["kdpi"] = kdpi

    # Viability assessment
    if kdpi <= 20:
        quality = "Excellent quality (KDPI <= 20%)"
    elif kdpi <= 50:
        quality = "Good quality (KDPI 21-50%)"
    elif kdpi <= 85:
        quality = "Acceptable quality (KDPI 51-85%)"
    else:
        quality = "High-risk donor (KDPI > 85%)"
        risk_factors.append("KDPI > 85% — high-risk kidney, expanded criteria")

    details["quality_tier"] = quality

    return DonorScreeningResult(
        organ_type="kidney",
        donor_type="deceased",
        score_name="KDPI",
        score_value=f"{kdpi}%",
        viable=kdpi <= 85,
        viability_description="KDPI <= 85% generally acceptable; <= 20% ideal",
        missing_data=[],
        details=details,
        risk_factors=risk_factors,
    )


def compute_dri(
    age: float,
    cause_of_death: str = "other",
    dcd: bool = False,
    split_liver: bool = False,
    height_cm: float | None = None,
    cold_ischemia_hours: float | None = None,
) -> DonorScreeningResult:
    """Compute Donor Risk Index (DRI) for deceased liver donors.

    Based on Feng et al. 2006 model with OPTN modifications.
    DRI > 1.6 considered high-risk.
    """
    risk_factors = []
    details = {"age": age}

    dri_log = 0.0

    # Age
    if age < 40:
        pass  # reference
    elif age < 50:
        dri_log += 0.154
    elif age < 60:
        dri_log += 0.274
        risk_factors.append(f"Donor age {age} (50-59 range)")
    elif age < 70:
        dri_log += 0.424
        risk_factors.append(f"Donor age {age} (60-69 range)")
    else:
        dri_log += 0.501
        risk_factors.append(f"Donor age {age} >= 70")

    # Cause of death
    if cause_of_death.lower() in ("cva", "stroke", "cerebrovascular"):
        dri_log += 0.079
        details["cause_of_death"] = "Cerebrovascular"
    elif cause_of_death.lower() in ("anoxia", "anoxic"):
        dri_log += 0.079
        details["cause_of_death"] = "Anoxia"
    else:
        details["cause_of_death"] = cause_of_death

    # DCD
    if dcd:
        dri_log += 0.411
        risk_factors.append("DCD donor — increased biliary complication risk")
        details["dcd"] = True

    # Split liver
    if split_liver:
        dri_log += 0.422
        risk_factors.append("Split/partial graft")
        details["split"] = True

    # Cold ischemia time
    if cold_ischemia_hours is not None:
        details["cold_ischemia_hours"] = cold_ischemia_hours
        if cold_ischemia_hours > 12:
            dri_log += 0.010 * (cold_ischemia_hours - 12)
            risk_factors.append(f"Cold ischemia time {cold_ischemia_hours}h > 12h")

    dri = math.exp(dri_log)
    details["dri"] = round(dri, 4)

    if dri <= 1.0:
        quality = "Low risk (DRI <= 1.0)"
    elif dri <= 1.6:
        quality = "Standard risk (DRI 1.0-1.6)"
    elif dri <= 2.0:
        quality = "High risk (DRI 1.6-2.0)"
    else:
        quality = "Very high risk (DRI > 2.0)"
        risk_factors.append("DRI > 2.0 — very high risk graft")

    details["quality_tier"] = quality

    return DonorScreeningResult(
        organ_type="liver",
        donor_type="deceased",
        score_name="DRI",
        score_value=f"{round(dri, 2)}",
        viable=dri <= 2.0,
        viability_description="DRI <= 1.6 standard risk; DRI <= 2.0 acceptable; > 2.0 high risk",
        missing_data=[],
        details=details,
        risk_factors=risk_factors,
    )


def evaluate_deceased_heart_donor(
    age: float,
    ejection_fraction: float | None = None,
    ischemia_hours: float | None = None,
    cause_of_death: str = "other",
    downtime_minutes: float | None = None,
) -> DonorScreeningResult:
    """Evaluate deceased heart donor viability.

    Criteria:
    - Age < 55 preferred (< 65 acceptable)
    - EF >= 50% (>= 40% marginal)
    - Ischemia time < 4 hours preferred
    - No prolonged cardiac arrest
    """
    missing = []
    risk_factors = []
    details = {"age": age, "cause_of_death": cause_of_death}
    viable = True

    if ejection_fraction is None:
        missing.append("Ejection Fraction [LOINC 10230-1]")
    if ischemia_hours is None:
        missing.append("Anticipated ischemia time")

    # Age
    if age >= 65:
        viable = False
        risk_factors.append(f"Donor age {age} >= 65 — exceeds heart donor limit")
    elif age >= 55:
        risk_factors.append(f"Donor age {age} >= 55 — marginal, extended criteria")

    # EF
    if ejection_fraction is not None:
        details["ejection_fraction"] = ejection_fraction
        if ejection_fraction < 40:
            viable = False
            risk_factors.append(f"EF {ejection_fraction}% < 40% — not viable")
        elif ejection_fraction < 50:
            risk_factors.append(f"EF {ejection_fraction}% < 50% — marginal function")

    # Ischemia
    if ischemia_hours is not None:
        details["ischemia_hours"] = ischemia_hours
        if ischemia_hours > 6:
            viable = False
            risk_factors.append(f"Ischemia time {ischemia_hours}h > 6h — graft failure risk")
        elif ischemia_hours > 4:
            risk_factors.append(f"Ischemia time {ischemia_hours}h > 4h — elevated risk")

    # Downtime
    if downtime_minutes is not None:
        details["downtime_minutes"] = downtime_minutes
        if downtime_minutes > 30:
            risk_factors.append(f"Cardiac downtime {downtime_minutes}min > 30min")

    if ejection_fraction is None:
        viable = False

    score_display = f"EF {ejection_fraction}%" if ejection_fraction is not None else "INCOMPLETE"

    return DonorScreeningResult(
        organ_type="heart",
        donor_type="deceased",
        score_name="Heart Donor Assessment",
        score_value=score_display,
        viable=viable,
        viability_description="Age < 55, EF >= 50%, ischemia < 4h",
        missing_data=missing,
        details=details,
        risk_factors=risk_factors,
    )


def evaluate_deceased_lung_donor(
    age: float,
    pao2: float | None = None,
    smoking_pack_years: float | None = None,
    chest_xray_clear: bool | None = None,
    ischemia_hours: float | None = None,
) -> DonorScreeningResult:
    """Evaluate deceased lung donor viability.

    Criteria:
    - Age < 55 preferred (< 65 acceptable)
    - PaO2/FiO2 > 300 (on FiO2 1.0)
    - Smoking < 20 pack-years preferred
    - Clear chest X-ray
    - Ischemia < 6 hours
    """
    missing = []
    risk_factors = []
    details = {"age": age}
    viable = True

    if pao2 is None:
        missing.append("PaO2/FiO2 ratio")
    if chest_xray_clear is None:
        missing.append("Chest X-ray assessment")

    # Age
    if age >= 65:
        viable = False
        risk_factors.append(f"Donor age {age} >= 65 — exceeds lung donor limit")
    elif age >= 55:
        risk_factors.append(f"Donor age {age} >= 55 — extended criteria")

    # PaO2/FiO2
    if pao2 is not None:
        details["pao2_fio2"] = pao2
        if pao2 < 300:
            risk_factors.append(f"PaO2/FiO2 {pao2} < 300 — impaired gas exchange")
            if pao2 < 200:
                viable = False

    # Smoking
    if smoking_pack_years is not None:
        details["smoking_pack_years"] = smoking_pack_years
        if smoking_pack_years > 20:
            risk_factors.append(f"Smoking history {smoking_pack_years} pack-years > 20")

    # Chest X-ray
    if chest_xray_clear is not None:
        details["chest_xray"] = "Clear" if chest_xray_clear else "Abnormal"
        if not chest_xray_clear:
            risk_factors.append("Abnormal chest X-ray — further evaluation needed")

    # Ischemia
    if ischemia_hours is not None:
        details["ischemia_hours"] = ischemia_hours
        if ischemia_hours > 8:
            viable = False
            risk_factors.append(f"Ischemia time {ischemia_hours}h > 8h — exceeds limit")
        elif ischemia_hours > 6:
            risk_factors.append(f"Ischemia time {ischemia_hours}h > 6h — elevated risk")

    if pao2 is None:
        viable = False

    score_display = f"PaO2/FiO2 {pao2}" if pao2 is not None else "INCOMPLETE"

    return DonorScreeningResult(
        organ_type="lung",
        donor_type="deceased",
        score_name="Lung Donor Assessment",
        score_value=score_display,
        viable=viable,
        viability_description="Age < 55, PaO2/FiO2 > 300, smoking < 20 py, clear CXR",
        missing_data=missing,
        details=details,
        risk_factors=risk_factors,
    )
