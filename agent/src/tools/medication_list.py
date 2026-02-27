"""Medication list tool for retrieving a patient's active medications from OpenEMR.

This module provides a LangGraph-compatible tool that queries the OpenEMR
FHIR API to fetch MedicationRequest resources for a given patient.
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


def _parse_medication(resource: dict) -> dict:
    """Extract relevant fields from a FHIR MedicationRequest resource."""
    # Drug name — prefer medicationCodeableConcept.text, then coding display
    med_concept = resource.get("medicationCodeableConcept", {})
    drug_name = med_concept.get("text")
    if not drug_name:
        codings = med_concept.get("coding", [])
        if codings:
            drug_name = codings[0].get("display")
    drug_name = drug_name or "Unknown medication"

    # Dosage instructions
    dosage_instructions = resource.get("dosageInstruction", [])
    dosage = None
    frequency = None
    route = None

    if dosage_instructions:
        first_dosage = dosage_instructions[0]

        # Dosage amount
        dose_and_rate = first_dosage.get("doseAndRate", [])
        if dose_and_rate:
            dose_quantity = dose_and_rate[0].get("doseQuantity", {})
            value = dose_quantity.get("value")
            unit = dose_quantity.get("unit", "")
            if value is not None:
                dosage = f"{value} {unit}".strip()

        # Frequency from timing
        timing = first_dosage.get("timing", {})
        repeat = timing.get("repeat", {})
        freq = repeat.get("frequency")
        period = repeat.get("period")
        period_unit = repeat.get("periodUnit")
        if freq and period and period_unit:
            unit_map = {"h": "hour(s)", "d": "day(s)", "wk": "week(s)", "mo": "month(s)"}
            period_label = unit_map.get(period_unit, period_unit)
            frequency = f"{freq} per {period} {period_label}"
        elif first_dosage.get("text"):
            frequency = first_dosage["text"]

        # Route
        route_concept = first_dosage.get("route", {})
        route = route_concept.get("text")
        if not route:
            route_codings = route_concept.get("coding", [])
            if route_codings:
                route = route_codings[0].get("display")

    # Prescriber (requester)
    requester = resource.get("requester", {})
    prescriber = requester.get("display")
    if not prescriber:
        ref = requester.get("reference", "")
        prescriber = ref.split("/")[-1] if ref else None

    # Start date (authoredOn)
    start_date = resource.get("authoredOn", None)

    # Status
    status = resource.get("status", "unknown")

    return {
        "drug_name": drug_name,
        "dosage": dosage,
        "frequency": frequency,
        "route": route,
        "prescriber": prescriber,
        "start_date": start_date,
        "status": status,
    }


def _format_medications(medications: list[dict]) -> str:
    """Format a list of parsed medication dicts into a readable string."""
    lines: list[str] = []
    lines.append(f"Found {len(medications)} active medication(s):\n")

    for med in medications:
        lines.append(f"- {med['drug_name']}")
        details: list[str] = []
        if med["dosage"]:
            details.append(f"Dosage: {med['dosage']}")
        if med["frequency"]:
            details.append(f"Frequency: {med['frequency']}")
        if med["route"]:
            details.append(f"Route: {med['route']}")
        if details:
            lines.append(f"  {' | '.join(details)}")
        if med["prescriber"]:
            lines.append(f"  Prescriber: {med['prescriber']}")
        if med["start_date"]:
            lines.append(f"  Start date: {med['start_date']}")
        lines.append(f"  Status: {med['status']}")
        lines.append("")

    return "\n".join(lines).strip()


@tool
async def medication_list(patient_uuid: str) -> str:
    """Retrieve a patient's active medications from the medical records system.

    Use this tool when you need to see what medications a patient is currently
    taking. Provide the patient's UUID (obtainable from the patient_lookup tool).

    Returns a list of active medications with drug name, dosage, frequency,
    route, prescriber, start date, and status. Returns a message if no active
    medications are found.

    Examples:
        - medication_list(patient_uuid="95f2f211-3580-4b58-9a15-2d9b29f49c72")
    """
    if not patient_uuid or not patient_uuid.strip():
        return "Error: patient_uuid is required."

    auth = OpenEMRAuth()

    try:
        async with auth.get_client() as client:
            resp = await client.get(
                f"{_FHIR_PREFIX}/MedicationRequest",
                params={"patient": patient_uuid},
                timeout=10.0,
            )

            if resp.status_code == 401:
                # Force a fresh token and retry once.
                auth._access_token = None
                auth._refresh_token = None
                async with auth.get_client() as retry_client:
                    resp = await retry_client.get(
                        f"{_FHIR_PREFIX}/MedicationRequest",
                        params={"patient": patient_uuid},
                        timeout=10.0,
                    )

            resp.raise_for_status()

    except httpx.TimeoutException:
        return "Unable to reach medical records system. Please try again."
    except httpx.HTTPStatusError as exc:
        logger.error("Medication list API error: %s", exc)
        return "Unable to reach medical records system. Please try again."

    body = resp.json()

    # FHIR Bundle: entries live under "entry"; an empty bundle may omit the key.
    entries = body.get("entry", [])

    if not entries:
        return "No active medications documented for this patient."

    medications = [
        _parse_medication(entry.get("resource", entry)) for entry in entries
    ]

    return _format_medications(medications)


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

        print(f"\n=== Step 2: Get medications for UUID {uuid} ===\n")
        result = await medication_list.ainvoke({"patient_uuid": uuid})
        print(result)

    asyncio.run(_test())
