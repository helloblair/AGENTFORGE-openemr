"""Donor viability screening tool for living and deceased organ donors.

This module provides a LangGraph-compatible tool that evaluates whether a
patient is a viable organ donor. Supports both living and deceased donor
pathways with organ-specific scoring (KDPI, DRI, EF, PaO2/FiO2).
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from langchain_core.tools import tool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.auth.oauth2 import OpenEMRAuth
from src.tools.contraindication_screen import screen_contraindications
from src.tools.donor_criteria import (
    compute_dri,
    compute_kdpi,
    evaluate_deceased_heart_donor,
    evaluate_deceased_lung_donor,
    evaluate_living_kidney_donor,
    evaluate_living_liver_donor,
)
from src.tools.donor_report import format_donor_report

logger = logging.getLogger(__name__)

_FHIR_PREFIX = "/apis/default/fhir"

VALID_ORGAN_TYPES = {"kidney", "liver", "heart", "lung"}
VALID_DONOR_TYPES = {"living", "deceased"}

# LOINC codes relevant to donor evaluation
_DONOR_LOINC = [
    "2160-0",   # Creatinine
    "33914-3",  # eGFR
    "1975-2",   # Bilirubin
    "6301-6",   # INR
    "2951-2",   # Sodium
    "1751-7",   # Albumin
    "718-7",    # Hemoglobin
    "10230-1",  # Ejection Fraction
]


def _parse_lab_values(entries: list[dict]) -> dict:
    """Extract lab values from FHIR Observation bundle entries."""
    loinc_to_name = {
        "2160-0": "creatinine",
        "33914-3": "egfr",
        "1975-2": "bilirubin",
        "6301-6": "inr",
        "2951-2": "sodium",
        "1751-7": "albumin",
        "718-7": "hemoglobin",
        "10230-1": "ejection_fraction",
    }

    labs: dict[str, float | str | None] = {}
    for entry in entries:
        resource = entry.get("resource", entry)
        codings = resource.get("code", {}).get("coding", [])

        loinc = ""
        for coding in codings:
            if "loinc" in coding.get("system", "").lower():
                loinc = coding.get("code", "")
                break

        value = None
        vq = resource.get("valueQuantity", {})
        if vq:
            value = vq.get("value")
        elif resource.get("valueString"):
            value = resource["valueString"]

        if loinc and value is not None:
            labs[loinc] = value
            name = loinc_to_name.get(loinc)
            if name:
                labs[name] = value

    return labs


def _parse_conditions(entries: list[dict]) -> list[dict]:
    """Parse FHIR Condition bundle entries."""
    conditions = []
    for entry in entries:
        resource = entry.get("resource", entry)
        code_concept = resource.get("code", {})

        name = code_concept.get("text")
        if not name:
            codings = code_concept.get("coding", [])
            if codings:
                name = codings[0].get("display")
        name = name or "Unknown condition"

        icd10_code = None
        for coding in code_concept.get("coding", []):
            system = coding.get("system", "")
            if "icd10" in system.lower() or "icd-10" in system.lower():
                icd10_code = coding.get("code")
                break
        if not icd10_code:
            codings = code_concept.get("coding", [])
            if codings:
                icd10_code = codings[0].get("code")

        conditions.append({
            "name": name,
            "icd10_code": icd10_code,
            "condition_name": name,
        })

    return conditions


def _extract_age_from_patient(patient: dict) -> float | None:
    """Calculate age from patient birthDate."""
    birth_date = patient.get("birthDate")
    if not birth_date:
        return None
    try:
        dob = datetime.strptime(birth_date, "%Y-%m-%d")
        today = datetime.now()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return float(age)
    except (ValueError, TypeError):
        return None


def _extract_bmi(patient: dict) -> float | None:
    """Extract BMI from patient extensions or vitals if available."""
    # BMI would typically come from vitals/observations, not patient resource
    # This is a placeholder — the tool fetches BMI from observations if available
    return None


async def _fetch_fhir(client: httpx.AsyncClient, resource: str, patient_uuid: str, params: dict | None = None) -> dict:
    """Fetch a FHIR resource bundle."""
    query = {"patient": patient_uuid}
    if params:
        query.update(params)
    resp = await client.get(f"{_FHIR_PREFIX}/{resource}", params=query, timeout=15.0)
    resp.raise_for_status()
    return resp.json()


async def _evaluate_donor(
    client: httpx.AsyncClient,
    patient_uuid: str,
    organ_type: str,
    donor_type: str,
) -> str:
    """Run the full donor viability evaluation."""

    # Fetch patient demographics, labs, conditions, medications in parallel
    patient_task = client.get(f"{_FHIR_PREFIX}/Patient/{patient_uuid}", timeout=15.0)
    lab_task = _fetch_fhir(
        client, "Observation", patient_uuid,
        params={"code": ",".join(_DONOR_LOINC)},
    )
    condition_task = _fetch_fhir(client, "Condition", patient_uuid)
    medication_task = _fetch_fhir(client, "MedicationRequest", patient_uuid)

    results = await asyncio.gather(
        patient_task, lab_task, condition_task, medication_task,
        return_exceptions=True,
    )

    patient_resp, lab_body, condition_body, medication_body = results

    # Parse patient demographics
    age = None
    bmi = None
    patient_name = ""
    if isinstance(patient_resp, httpx.Response) and patient_resp.status_code == 200:
        patient = patient_resp.json()
        age = _extract_age_from_patient(patient)
        names = patient.get("name", [])
        if names:
            given = " ".join(names[0].get("given", []))
            family = names[0].get("family", "")
            patient_name = f"{given} {family}".strip()

    # Parse labs
    lab_entries = []
    if isinstance(lab_body, dict):
        lab_entries = lab_body.get("entry", [])
    labs = _parse_lab_values(lab_entries)

    # Parse conditions
    condition_entries = []
    if isinstance(condition_body, dict):
        condition_entries = condition_body.get("entry", [])
    conditions = _parse_conditions(condition_entries)

    # Parse medications
    medications_text = ""
    if isinstance(medication_body, dict):
        med_entries = medication_body.get("entry", [])
        if med_entries:
            med_names = []
            for entry in med_entries:
                resource = entry.get("resource", entry)
                med_concept = resource.get("medicationCodeableConcept", {})
                med_name = med_concept.get("text") or ""
                if not med_name:
                    codings = med_concept.get("coding", [])
                    if codings:
                        med_name = codings[0].get("display", "")
                if med_name:
                    med_names.append(med_name)
            medications_text = f"Active medications: {', '.join(med_names)}" if med_names else "No active medications found."
        else:
            medications_text = "No active medications found."

    # Screen contraindications (relevant for living donors)
    contraindications = screen_contraindications(conditions) if donor_type == "living" else []

    # Run organ-specific scoring
    if donor_type == "living":
        if organ_type == "kidney":
            score = evaluate_living_kidney_donor(labs, age=age, bmi=bmi)
        elif organ_type == "liver":
            score = evaluate_living_liver_donor(labs, age=age, bmi=bmi)
        else:
            return f"Error: Living donation is not supported for {organ_type}. Living donation is available for kidney and liver only."
    else:
        # Deceased donor
        creatinine = labs.get("creatinine")
        ef = labs.get("ejection_fraction")

        if organ_type == "kidney":
            if age is None:
                return "Error: Cannot compute KDPI — donor age is required."
            cr = float(creatinine) if creatinine is not None else 1.0

            # Check conditions for diabetes/hypertension history
            has_diabetes = any("diabetes" in (c.get("name", "") or "").lower() for c in conditions)
            has_htn = any("hypertens" in (c.get("name", "") or "").lower() for c in conditions)
            has_hcv = any("hepatitis c" in (c.get("name", "") or "").lower() for c in conditions)

            score = compute_kdpi(
                age=age,
                creatinine=cr,
                hcv_positive=has_hcv,
                diabetes_history=has_diabetes,
                hypertension_history=has_htn,
            )
        elif organ_type == "liver":
            if age is None:
                return "Error: Cannot compute DRI — donor age is required."
            score = compute_dri(age=age)
        elif organ_type == "heart":
            if age is None:
                return "Error: Cannot evaluate heart donor — age is required."
            ef_val = float(ef) if ef is not None else None
            score = evaluate_deceased_heart_donor(age=age, ejection_fraction=ef_val)
        elif organ_type == "lung":
            if age is None:
                return "Error: Cannot evaluate lung donor — age is required."
            score = evaluate_deceased_lung_donor(age=age)
        else:
            return f"Error: Unsupported organ type '{organ_type}'."

    # Format the report
    report = format_donor_report(
        organ_type=organ_type,
        donor_type=donor_type,
        score=score,
        contraindications=contraindications,
        medications_text=medications_text,
        patient_name=patient_name,
    )

    return report


@tool
async def donor_viability(
    patient_uuid: str,
    organ_type: str,
    donor_type: str = "living",
) -> str:
    """Evaluate whether a patient is a viable organ donor (living or deceased).

    This tool assesses donor suitability by gathering labs, conditions, and
    demographics, then computing organ-specific donor scores:
    - Living kidney: eGFR-based evaluation (OPTN living donor criteria)
    - Living liver: LFT panel evaluation (bilirubin, INR, albumin)
    - Deceased kidney: KDPI (Kidney Donor Profile Index)
    - Deceased liver: DRI (Donor Risk Index)
    - Deceased heart: EF and age-based assessment
    - Deceased lung: PaO2/FiO2 and age-based assessment

    Note: Living donation is only available for kidney and liver.

    Args:
        patient_uuid: The donor patient's UUID (from patient_lookup).
        organ_type: Target organ — kidney, liver, heart, or lung.
        donor_type: "living" (default) or "deceased".

    Examples:
        - donor_viability(patient_uuid="...", organ_type="kidney", donor_type="living")
        - donor_viability(patient_uuid="...", organ_type="kidney", donor_type="deceased")
        - donor_viability(patient_uuid="...", organ_type="liver", donor_type="living")
        - donor_viability(patient_uuid="...", organ_type="heart", donor_type="deceased")
    """
    if not patient_uuid or not patient_uuid.strip():
        return "Error: patient_uuid is required."

    organ_type = (organ_type or "").strip().lower()
    if organ_type not in VALID_ORGAN_TYPES:
        return (
            f"Error: Invalid organ_type '{organ_type}'. "
            f"Valid options: {', '.join(sorted(VALID_ORGAN_TYPES))}."
        )

    donor_type = (donor_type or "living").strip().lower()
    if donor_type not in VALID_DONOR_TYPES:
        return (
            f"Error: Invalid donor_type '{donor_type}'. "
            f"Valid options: {', '.join(sorted(VALID_DONOR_TYPES))}."
        )

    if donor_type == "living" and organ_type not in {"kidney", "liver"}:
        return (
            f"Error: Living donation is only available for kidney and liver. "
            f"'{organ_type}' requires a deceased donor evaluation."
        )

    auth = OpenEMRAuth()

    try:
        async with auth.get_client() as client:
            try:
                return await _evaluate_donor(client, patient_uuid, organ_type, donor_type)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    auth._access_token = None
                    auth._refresh_token = None
                    async with auth.get_client() as retry_client:
                        return await _evaluate_donor(retry_client, patient_uuid, organ_type, donor_type)
                raise

    except httpx.TimeoutException:
        return "Unable to reach medical records system. Please try again."
    except httpx.HTTPStatusError as exc:
        logger.error("Donor viability API error: %s", exc)
        return "Unable to reach medical records system. Please try again."
