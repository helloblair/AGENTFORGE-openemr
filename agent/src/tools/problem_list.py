"""Problem list tool for retrieving a patient's active conditions from OpenEMR.

This module provides a LangGraph-compatible tool that queries the OpenEMR
FHIR API to fetch Condition resources for a given patient.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import httpx
from langchain_core.tools import tool

# Ensure the agent package is importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.auth.oauth2 import OpenEMRAuth

logger = logging.getLogger(__name__)

_FHIR_PREFIX = "/apis/default/fhir"


def _parse_condition(resource: dict) -> dict:
    """Extract relevant fields from a FHIR Condition resource."""
    # Condition name — prefer code.text, then first coding display
    code_concept = resource.get("code", {})
    name = code_concept.get("text")
    if not name:
        codings = code_concept.get("coding", [])
        if codings:
            name = codings[0].get("display")
    name = name or "Unknown condition"

    # ICD-10 code — look for a coding with system containing "icd10"
    icd10_code = None
    for coding in code_concept.get("coding", []):
        system = coding.get("system", "")
        if "icd10" in system.lower() or "icd-10" in system.lower():
            icd10_code = coding.get("code")
            break
    # Fallback: use the first coding code if no ICD-10 specific system found
    if not icd10_code:
        codings = code_concept.get("coding", [])
        if codings:
            icd10_code = codings[0].get("code")

    # Onset date — onsetDateTime or onsetPeriod.start
    onset_date = resource.get("onsetDateTime")
    if not onset_date:
        onset_period = resource.get("onsetPeriod", {})
        onset_date = onset_period.get("start")

    # Clinical status
    clinical_status_concept = resource.get("clinicalStatus", {})
    clinical_status = None
    cs_codings = clinical_status_concept.get("coding", [])
    if cs_codings:
        clinical_status = cs_codings[0].get("code")
    if not clinical_status:
        clinical_status = clinical_status_concept.get("text", "unknown")

    # Category — e.g. problem-list-item, encounter-diagnosis
    category = None
    categories = resource.get("category", [])
    if categories:
        cat_concept = categories[0]
        cat_codings = cat_concept.get("coding", [])
        if cat_codings:
            category = cat_codings[0].get("code")
        if not category:
            category = cat_concept.get("text")

    return {
        "name": name,
        "icd10_code": icd10_code,
        "onset_date": onset_date,
        "clinical_status": clinical_status,
        "category": category,
    }


def _format_conditions(conditions: list[dict]) -> str:
    """Format a list of parsed condition dicts into a readable string."""
    lines: list[str] = []
    lines.append(f"Found {len(conditions)} active condition(s):\n")

    for cond in conditions:
        lines.append(f"- {cond['name']}")
        details: list[str] = []
        if cond["icd10_code"]:
            details.append(f"ICD-10: {cond['icd10_code']}")
        if cond["clinical_status"]:
            details.append(f"Status: {cond['clinical_status']}")
        if cond["category"]:
            details.append(f"Category: {cond['category']}")
        if details:
            lines.append(f"  {' | '.join(details)}")
        if cond["onset_date"]:
            lines.append(f"  Onset date: {cond['onset_date']}")
        lines.append("")

    return "\n".join(lines).strip()


@tool
async def problem_list(patient_uuid: str) -> str:
    """Retrieve a patient's active conditions / problem list from the medical records system.

    Use this tool when you need to see a patient's diagnoses, medical problems,
    or conditions. Provide the patient's UUID (obtainable from the patient_lookup tool).

    Returns a list of active conditions with name, ICD-10 code, onset date,
    clinical status, and category. Returns a message if no active conditions
    are found.

    Examples:
        - problem_list(patient_uuid="95f2f211-3580-4b58-9a15-2d9b29f49c72")
    """
    if not patient_uuid or not patient_uuid.strip():
        return "Error: patient_uuid is required."

    auth = OpenEMRAuth()

    try:
        async with auth.get_client() as client:
            resp = await client.get(
                f"{_FHIR_PREFIX}/Condition",
                params={"patient": patient_uuid},
                timeout=10.0,
            )

            if resp.status_code == 401:
                # Force a fresh token and retry once.
                auth._access_token = None
                auth._refresh_token = None
                async with auth.get_client() as retry_client:
                    resp = await retry_client.get(
                        f"{_FHIR_PREFIX}/Condition",
                        params={"patient": patient_uuid},
                        timeout=10.0,
                    )

            resp.raise_for_status()

    except httpx.TimeoutException:
        return "Unable to reach medical records system. Please try again."
    except httpx.HTTPStatusError as exc:
        logger.error("Problem list API error: %s", exc)
        return "Unable to reach medical records system. Please try again."

    body = resp.json()

    # FHIR Bundle: entries live under "entry"; an empty bundle may omit the key.
    entries = body.get("entry", [])

    if not entries:
        return "No active conditions documented for this patient."

    conditions = [
        _parse_condition(entry.get("resource", entry)) for entry in entries
    ]

    return _format_conditions(conditions)


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    async def _test():
        # First, look up a test patient to get their UUID.
        from src.tools.patient_lookup import patient_lookup

        print("=== Step 1: Look up John Smith ===\n")
        lookup_result = await patient_lookup.ainvoke({"last_name": "Smith", "first_name": "John"})
        print(lookup_result)

        # Extract UUID from the lookup result.
        uuid = None
        for line in lookup_result.splitlines():
            if "UUID:" in line:
                uuid = line.split("UUID:")[1].strip().rstrip(")")
                break

        if not uuid:
            print("\nCould not extract UUID from lookup result. Exiting.")
            return

        print(f"\n=== Step 2: Get problem list for UUID {uuid} ===\n")
        result = await problem_list.ainvoke({"patient_uuid": uuid})
        print(result)

    asyncio.run(_test())
