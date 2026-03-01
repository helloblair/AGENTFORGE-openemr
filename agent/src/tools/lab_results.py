"""Lab results tool for retrieving patient laboratory data from OpenEMR.

This module provides a LangGraph-compatible tool that queries the OpenEMR
FHIR API to fetch Observation resources (lab values) for a given patient.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import httpx
from langchain_core.tools import tool

# Ensure the agent package is importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.auth.oauth2 import OpenEMRAuth

logger = logging.getLogger(__name__)

_FHIR_PREFIX = "/apis/default/fhir"

# Common LOINC codes for transplant-relevant lab values
LOINC_CODES = {
    "2160-0": "Creatinine (Serum)",
    "33914-3": "eGFR",
    "1975-2": "Bilirubin (Total)",
    "6301-6": "INR",
    "2951-2": "Sodium (Serum)",
    "1751-7": "Albumin (Serum)",
    "20150-9": "FEV1",
    "19926-5": "FEV1 % Predicted",
    "10230-1": "Ejection Fraction",
    "30934-4": "BNP",
    "718-7": "Hemoglobin",
}


def _parse_observation(resource: dict) -> dict:
    """Extract relevant fields from a FHIR Observation resource."""
    code_obj = resource.get("code", {})
    codings = code_obj.get("coding", [])

    # Extract display name and LOINC code
    display_name = code_obj.get("text", "")
    loinc_code = ""
    for coding in codings:
        system = coding.get("system", "")
        if "loinc" in system.lower():
            loinc_code = coding.get("code", "")
            if not display_name:
                display_name = coding.get("display", "")
            break
        if not display_name:
            display_name = coding.get("display", "")

    if not display_name:
        display_name = "Unknown Test"

    # Extract value
    value = None
    unit = ""
    value_quantity = resource.get("valueQuantity", {})
    if value_quantity:
        value = value_quantity.get("value")
        unit = value_quantity.get("unit", "")
    elif resource.get("valueString"):
        value = resource["valueString"]
    elif resource.get("valueCodeableConcept"):
        value = resource["valueCodeableConcept"].get("text", "")

    return {
        "name": display_name,
        "value": value,
        "unit": unit,
        "loinc_code": loinc_code,
        "date": resource.get("effectiveDateTime", ""),
        "status": resource.get("status", ""),
    }


def _format_observations(observations: list[dict]) -> str:
    """Format parsed observations into a readable string."""
    lines: list[str] = []
    lines.append(f"Found {len(observations)} lab result(s):\n")

    for obs in observations:
        name = obs["name"]
        lines.append(f"- {name}")

        value_str = ""
        if obs["value"] is not None:
            value_str = f"  Value: {obs['value']}"
            if obs["unit"]:
                value_str += f" {obs['unit']}"
            if obs["loinc_code"]:
                value_str += f"  |  LOINC: {obs['loinc_code']}"
        lines.append(value_str)

        date_str = f"  Date: {obs['date']}" if obs["date"] else "  Date: unknown"
        if obs["status"]:
            date_str += f"  |  Status: {obs['status']}"
        lines.append(date_str)
        lines.append("")

    return "\n".join(lines).strip()


@tool
async def lab_results(
    patient_uuid: str,
    loinc_codes: Optional[list[str]] = None,
) -> str:
    """Retrieve a patient's laboratory results from the medical records system.

    Use this tool when you need to check a patient's lab values such as
    creatinine, bilirubin, INR, eGFR, sodium, FEV1, ejection fraction, BNP,
    hemoglobin, or other laboratory test results.

    Provide the patient's UUID (obtainable from the patient_lookup tool).
    Optionally provide LOINC codes to filter for specific tests.

    Returns a list of lab results with test name, value, unit, date, and
    LOINC code. Returns a message if no lab results are found.

    Examples:
        - lab_results(patient_uuid="95f2f211-3580-4b58-9a15-2d9b29f49c72")
        - lab_results(patient_uuid="95f2f211-...", loinc_codes=["2160-0", "33914-3"])
    """
    if not patient_uuid or not patient_uuid.strip():
        return "Error: patient_uuid is required."

    auth = OpenEMRAuth()

    try:
        async with auth.get_client() as client:
            params: dict[str, str] = {"patient": patient_uuid}

            # If specific LOINC codes requested, add as comma-separated filter
            if loinc_codes:
                params["code"] = ",".join(loinc_codes)

            resp = await client.get(
                f"{_FHIR_PREFIX}/Observation",
                params=params,
                timeout=15.0,
            )

            if resp.status_code == 401:
                auth._access_token = None
                auth._refresh_token = None
                async with auth.get_client() as retry_client:
                    resp = await retry_client.get(
                        f"{_FHIR_PREFIX}/Observation",
                        params=params,
                        timeout=15.0,
                    )

            resp.raise_for_status()

    except httpx.TimeoutException:
        return "Unable to reach medical records system. Please try again."
    except httpx.HTTPStatusError as exc:
        logger.error("Lab results API error: %s", exc)
        return "Unable to reach medical records system. Please try again."

    body = resp.json()

    entries = body.get("entry", [])

    if not entries:
        return "No lab results found for this patient."

    observations = [
        _parse_observation(entry.get("resource", entry))
        for entry in entries
    ]

    # Sort by date descending (most recent first)
    observations.sort(key=lambda o: o.get("date", ""), reverse=True)

    return _format_observations(observations)


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

        print(f"\n=== Step 2: Get lab results for UUID {uuid} ===\n")
        result = await lab_results.ainvoke({"patient_uuid": uuid})
        print(result)

    asyncio.run(_test())
