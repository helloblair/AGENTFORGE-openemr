"""Transplant candidacy screening orchestrator tool.

This module provides the main LangGraph-compatible tool that orchestrates
a full transplant candidacy evaluation by gathering clinical data, computing
organ-specific scores, screening contraindications, and generating a
comprehensive candidacy report. Also supports CRUD operations on screening
records via the OpenEMR REST API.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional

import httpx
from langchain_core.tools import tool

# Ensure the agent package is importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.auth.oauth2 import OpenEMRAuth
from src.tools.contraindication_screen import screen_contraindications
from src.tools.transplant_criteria import (
    compute_heart_score,
    compute_kidney_score,
    compute_liver_meld,
    compute_lung_score,
)
from src.tools.transplant_report import format_screening_report

logger = logging.getLogger(__name__)

_FHIR_PREFIX = "/apis/default/fhir"
_API_PREFIX = "/apis/default/api"

VALID_ORGAN_TYPES = {"kidney", "heart", "lung", "liver"}

# LOINC codes for transplant-relevant labs
_TRANSPLANT_LOINC = [
    "2160-0",   # Creatinine
    "33914-3",  # eGFR
    "1975-2",   # Bilirubin
    "6301-6",   # INR
    "2951-2",   # Sodium
    "20150-9",  # FEV1
    "19926-5",  # FEV1 % Predicted
    "10230-1",  # Ejection Fraction
    "30934-4",  # BNP
    "1751-7",   # Albumin
    "718-7",    # Hemoglobin
]


def _parse_lab_values(observations: list[dict]) -> dict:
    """Extract lab values as a dict keyed by LOINC code and common name."""
    labs: dict[str, float | str | None] = {}

    loinc_to_name = {
        "2160-0": "creatinine",
        "33914-3": "egfr",
        "1975-2": "bilirubin",
        "6301-6": "inr",
        "2951-2": "sodium",
        "20150-9": "fev1",
        "19926-5": "fev1_pct_predicted",
        "10230-1": "ejection_fraction",
        "30934-4": "bnp",
        "1751-7": "albumin",
        "718-7": "hemoglobin",
    }

    for obs in observations:
        loinc = obs.get("loinc_code", "")
        value = obs.get("value")

        if loinc and value is not None:
            # Store by LOINC code
            labs[loinc] = value
            # Also store by common name
            name = loinc_to_name.get(loinc)
            if name:
                labs[name] = value

    return labs


def _parse_fhir_observations(entries: list[dict]) -> list[dict]:
    """Parse FHIR Observation bundle entries into simplified dicts."""
    observations = []
    for entry in entries:
        resource = entry.get("resource", entry)
        code_obj = resource.get("code", {})
        codings = code_obj.get("coding", [])

        display_name = code_obj.get("text", "")
        loinc_code = ""
        for coding in codings:
            system = coding.get("system", "")
            if "loinc" in system.lower():
                loinc_code = coding.get("code", "")
                if not display_name:
                    display_name = coding.get("display", "")
                break

        value = None
        unit = ""
        value_quantity = resource.get("valueQuantity", {})
        if value_quantity:
            value = value_quantity.get("value")
            unit = value_quantity.get("unit", "")
        elif resource.get("valueString"):
            value = resource["valueString"]

        observations.append({
            "name": display_name or "Unknown Test",
            "value": value,
            "unit": unit,
            "loinc_code": loinc_code,
            "date": resource.get("effectiveDateTime", ""),
        })

    return observations


def _parse_fhir_conditions(entries: list[dict]) -> list[dict]:
    """Parse FHIR Condition bundle entries into simplified dicts."""
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


async def _fetch_fhir_resource(
    client: httpx.AsyncClient,
    resource_type: str,
    patient_uuid: str,
    params: dict | None = None,
) -> dict:
    """Fetch a FHIR resource bundle for a patient."""
    query_params = {"patient": patient_uuid}
    if params:
        query_params.update(params)

    resp = await client.get(
        f"{_FHIR_PREFIX}/{resource_type}",
        params=query_params,
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()


async def _evaluate_candidacy(
    client: httpx.AsyncClient,
    patient_uuid: str,
    organ_type: str,
) -> str:
    """Run the full candidacy evaluation pipeline.

    1. Gather clinical data (labs, conditions, medications) in parallel
    2. Parse results into structured formats
    3. Compute organ-specific score
    4. Screen for contraindications
    5. Format and return the screening report
    """
    # Fetch all clinical data in parallel
    lab_task = _fetch_fhir_resource(
        client, "Observation", patient_uuid,
        params={"code": ",".join(_TRANSPLANT_LOINC)},
    )
    condition_task = _fetch_fhir_resource(client, "Condition", patient_uuid)
    medication_task = _fetch_fhir_resource(
        client, "MedicationRequest", patient_uuid,
    )

    results = await asyncio.gather(
        lab_task, condition_task, medication_task,
        return_exceptions=True,
    )

    lab_body, condition_body, medication_body = results

    # Parse lab observations
    lab_entries = []
    if isinstance(lab_body, dict):
        lab_entries = lab_body.get("entry", [])
    observations = _parse_fhir_observations(lab_entries)
    labs = _parse_lab_values(observations)

    # Parse conditions
    condition_entries = []
    if isinstance(condition_body, dict):
        condition_entries = condition_body.get("entry", [])
    conditions = _parse_fhir_conditions(condition_entries)

    # Format medications text for the report
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
                    med_codings = med_concept.get("coding", [])
                    if med_codings:
                        med_name = med_codings[0].get("display", "")
                if med_name:
                    med_names.append(med_name)
            if med_names:
                medications_text = f"Active medications: {', '.join(med_names)}"
            else:
                medications_text = "No active medications found."
        else:
            medications_text = "No active medications found."

    # Compute organ-specific score
    if organ_type == "kidney":
        score = compute_kidney_score(labs)
    elif organ_type == "liver":
        score = compute_liver_meld(labs)
    elif organ_type == "heart":
        score = compute_heart_score(labs, conditions)
    elif organ_type == "lung":
        score = compute_lung_score(labs)
    else:
        return f"Error: Unsupported organ type '{organ_type}'."

    # Screen for contraindications
    contraindications = screen_contraindications(conditions)

    # Fetch criteria text for context
    criteria_text = ""
    try:
        criteria_resp = await client.get(
            f"{_API_PREFIX}/transplant/criteria",
            params={"organ_system": organ_type, "criteria_type": "qualifying_diagnosis"},
            timeout=10.0,
        )
        if criteria_resp.status_code == 200:
            criteria_body = criteria_resp.json()
            criteria_records = criteria_body.get("data", [])
            if criteria_records:
                codes = [f"{r.get('icd10_code', '')} ({r.get('short_description', '')})" for r in criteria_records[:10]]
                criteria_text = f"Qualifying diagnoses for {organ_type}: {'; '.join(codes)}"
    except Exception:
        pass  # Non-critical — report works without criteria text

    # Format the full report
    report = format_screening_report(
        organ_type=organ_type,
        score=score,
        contraindications=contraindications,
        medications_text=medications_text,
        criteria_text=criteria_text,
    )

    return report


async def _create_screening(
    client: httpx.AsyncClient,
    patient_uuid: str,
    organ_type: str,
) -> str:
    """Create a new screening record via the REST API."""
    data = {"organ_type": organ_type}

    resp = await client.post(
        f"{_API_PREFIX}/patient/{patient_uuid}/transplant_screening",
        json=data,
        timeout=15.0,
    )
    resp.raise_for_status()
    body = resp.json()

    if body.get("validationErrors"):
        return f"Validation error: {body['validationErrors']}"
    if body.get("internalErrors"):
        return "Internal error creating screening record. Please try again."

    record = body.get("data", {})
    return (
        f"Transplant screening record created successfully.\n"
        f"  Screening ID: {record.get('id', 'unknown')}\n"
        f"  Organ type: {organ_type}\n"
        f"  Status: {record.get('screening_status', 'initiated')}\n"
        f"  Eligibility: {record.get('overall_eligibility', 'incomplete')}"
    )


async def _get_screenings(
    client: httpx.AsyncClient,
    patient_uuid: str,
    organ_type: str,
) -> str:
    """Retrieve existing screening records for a patient."""
    resp = await client.get(
        f"{_API_PREFIX}/patient/{patient_uuid}/transplant_screening",
        timeout=15.0,
    )
    resp.raise_for_status()
    body = resp.json()

    records = body.get("data", [])
    if not records:
        return f"No transplant screening records found for this patient."

    # Filter by organ type
    filtered = [r for r in records if r.get("organ_type") == organ_type]
    if not filtered:
        filtered = records  # Show all if no match for the specified organ

    lines = [f"Found {len(filtered)} screening record(s):\n"]
    for r in filtered:
        lines.append(f"- Screening #{r.get('id', '?')}")
        lines.append(f"  Organ: {r.get('organ_type', '?')}")
        lines.append(f"  Status: {r.get('screening_status', '?')}")
        lines.append(f"  Eligibility: {r.get('overall_eligibility', '?')}")
        if r.get("qualifying_diagnosis_code"):
            lines.append(f"  Qualifying Dx: {r['qualifying_diagnosis_code']}")
        if r.get("priority_score"):
            lines.append(f"  Priority score: {r['priority_score']}")
        lines.append(f"  Created: {r.get('created_at', '?')}")
        lines.append("")

    return "\n".join(lines).strip()


async def _update_screening(
    client: httpx.AsyncClient,
    patient_uuid: str,
    screening_id: int,
    update_data: dict,
) -> str:
    """Update an existing screening record."""
    resp = await client.put(
        f"{_API_PREFIX}/patient/{patient_uuid}/transplant_screening/{screening_id}",
        json=update_data,
        timeout=15.0,
    )
    resp.raise_for_status()
    body = resp.json()

    if body.get("validationErrors"):
        return f"Validation error: {body['validationErrors']}"
    if body.get("internalErrors"):
        return "Internal error updating screening record. Please try again."

    return f"Screening record #{screening_id} updated successfully."


@tool
async def transplant_screening(
    patient_uuid: str,
    organ_type: str,
    action: Optional[str] = "evaluate",
    screening_id: Optional[int] = None,
    update_data: Optional[dict] = None,
) -> str:
    """Perform organ transplant candidacy screening for a patient.

    This tool orchestrates a comprehensive transplant evaluation by gathering
    lab results, problem list, and medications, then computing organ-specific
    clinical scores (eGFR, MELD, NYHA/EF, FEV1) and screening for
    contraindications against ICD-10 ranges.

    Actions:
    - evaluate: Run full candidacy assessment (default)
    - create: Start a new screening record in the system
    - get: Retrieve existing screening records
    - update: Modify a screening record (requires screening_id and update_data)

    Valid organ types: kidney, heart, lung, liver.

    Examples:
        - transplant_screening(patient_uuid="...", organ_type="kidney")
        - transplant_screening(patient_uuid="...", organ_type="liver", action="evaluate")
        - transplant_screening(patient_uuid="...", organ_type="heart", action="create")
        - transplant_screening(patient_uuid="...", organ_type="lung", action="get")
    """
    if not patient_uuid or not patient_uuid.strip():
        return "Error: patient_uuid is required."

    organ_type = (organ_type or "").strip().lower()
    if organ_type not in VALID_ORGAN_TYPES:
        return (
            f"Error: Invalid organ_type '{organ_type}'. "
            f"Valid options: {', '.join(sorted(VALID_ORGAN_TYPES))}."
        )

    action = (action or "evaluate").strip().lower()
    if action not in {"evaluate", "create", "get", "update"}:
        return (
            f"Error: Invalid action '{action}'. "
            "Valid options: evaluate, create, get, update."
        )

    if action == "update" and not screening_id:
        return "Error: screening_id is required for the 'update' action."

    auth = OpenEMRAuth()

    try:
        async with auth.get_client() as client:
            # Handle 401 with token refresh for all actions
            try:
                if action == "evaluate":
                    return await _evaluate_candidacy(client, patient_uuid, organ_type)
                elif action == "create":
                    return await _create_screening(client, patient_uuid, organ_type)
                elif action == "get":
                    return await _get_screenings(client, patient_uuid, organ_type)
                elif action == "update":
                    return await _update_screening(
                        client, patient_uuid, screening_id, update_data or {},
                    )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    # Force token refresh and retry
                    auth._access_token = None
                    auth._refresh_token = None
                    async with auth.get_client() as retry_client:
                        if action == "evaluate":
                            return await _evaluate_candidacy(retry_client, patient_uuid, organ_type)
                        elif action == "create":
                            return await _create_screening(retry_client, patient_uuid, organ_type)
                        elif action == "get":
                            return await _get_screenings(retry_client, patient_uuid, organ_type)
                        elif action == "update":
                            return await _update_screening(
                                retry_client, patient_uuid, screening_id, update_data or {},
                            )
                raise

    except httpx.TimeoutException:
        return "Unable to reach medical records system. Please try again."
    except httpx.HTTPStatusError as exc:
        logger.error("Transplant screening API error: %s", exc)
        return "Unable to reach medical records system. Please try again."


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    async def _test():
        from src.tools.patient_lookup import patient_lookup

        print("=== Step 1: Look up John Smith ===\n")
        lookup_result = await patient_lookup.ainvoke(
            {"last_name": "Smith", "first_name": "John"}
        )
        print(lookup_result)

        uuid = None
        for line in lookup_result.splitlines():
            if "UUID:" in line:
                uuid = line.split("UUID:")[1].strip().rstrip(")")
                break

        if not uuid:
            print("\nCould not extract UUID from lookup result. Exiting.")
            return

        print(f"\n=== Step 2: Screen for kidney transplant (UUID {uuid}) ===\n")
        result = await transplant_screening.ainvoke(
            {"patient_uuid": uuid, "organ_type": "kidney"}
        )
        print(result)

    asyncio.run(_test())
