"""Insurance coverage tool for retrieving a patient's insurance data from OpenEMR.

This module provides a LangGraph-compatible tool that queries the OpenEMR
FHIR API (Coverage endpoint) to fetch insurance/coverage information for a
given patient.
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


def _parse_coverage(resource: dict) -> dict:
    """Extract relevant fields from a FHIR Coverage resource."""
    # Plan name — prefer class with type "plan", then fall back to others
    plan_name = None
    coverage_type = None
    for cls in resource.get("class", []):
        cls_type = cls.get("type", {})
        type_code = None
        type_codings = cls_type.get("coding", [])
        if type_codings:
            type_code = type_codings[0].get("code")
        if not type_code:
            type_code = cls_type.get("text", "")

        if type_code == "plan":
            plan_name = cls.get("name") or cls.get("value")
        elif type_code == "group":
            # Use group name as fallback if no plan name
            if not plan_name:
                plan_name = cls.get("name") or cls.get("value")

    # Coverage type from resource.type
    type_concept = resource.get("type", {})
    coverage_type = type_concept.get("text")
    if not coverage_type:
        type_codings = type_concept.get("coding", [])
        if type_codings:
            coverage_type = type_codings[0].get("display") or type_codings[0].get("code")

    # Insurer — payor reference
    insurer = None
    payors = resource.get("payor", [])
    if payors:
        insurer = payors[0].get("display")
        if not insurer:
            ref = payors[0].get("reference", "")
            insurer = ref.split("/")[-1] if ref else None

    # Policy number — identifier or subscriberId
    policy_number = resource.get("subscriberId")
    if not policy_number:
        identifiers = resource.get("identifier", [])
        if identifiers:
            policy_number = identifiers[0].get("value")

    # Effective dates — period
    period = resource.get("period", {})
    effective_start = period.get("start")
    effective_end = period.get("end")

    # Status
    status = resource.get("status", "unknown")

    # Relationship to subscriber
    relationship = None
    rel_concept = resource.get("relationship", {})
    rel_codings = rel_concept.get("coding", [])
    if rel_codings:
        relationship = rel_codings[0].get("display") or rel_codings[0].get("code")
    if not relationship:
        relationship = rel_concept.get("text")

    return {
        "plan_name": plan_name,
        "insurer": insurer,
        "policy_number": policy_number,
        "coverage_type": coverage_type,
        "effective_start": effective_start,
        "effective_end": effective_end,
        "status": status,
        "relationship": relationship,
    }


def _is_expired(coverage: dict) -> bool:
    """Check if a coverage has an end date in the past (simple string comparison)."""
    end = coverage.get("effective_end")
    if not end:
        return False
    # ISO date strings are lexicographically comparable
    from datetime import date

    try:
        return end < date.today().isoformat()
    except (TypeError, ValueError):
        return False


def _format_coverages(coverages: list[dict]) -> str:
    """Format a list of parsed coverage dicts into a readable string."""
    lines: list[str] = []

    active = [c for c in coverages if not _is_expired(c)]
    expired = [c for c in coverages if _is_expired(c)]

    if active:
        lines.append(f"Found {len(active)} active insurance coverage(s):\n")
        for cov in active:
            _append_coverage_lines(lines, cov)
    else:
        lines.append("No active insurance coverages found.\n")

    if expired:
        lines.append(f"\n{len(expired)} expired coverage(s):\n")
        for cov in expired:
            _append_coverage_lines(lines, cov, expired_flag=True)

    return "\n".join(lines).strip()


def _append_coverage_lines(
    lines: list[str], cov: dict, expired_flag: bool = False
) -> None:
    """Append formatted lines for a single coverage entry."""
    label = cov["plan_name"] or cov["insurer"] or "Unknown plan"
    if expired_flag:
        label += " (EXPIRED)"
    lines.append(f"- {label}")

    details: list[str] = []
    if cov["coverage_type"]:
        details.append(f"Type: {cov['coverage_type']}")
    if cov["status"]:
        details.append(f"Status: {cov['status']}")
    if details:
        lines.append(f"  {' | '.join(details)}")

    if cov["insurer"] and cov["insurer"] != label.replace(" (EXPIRED)", ""):
        lines.append(f"  Insurer: {cov['insurer']}")
    if cov["policy_number"]:
        lines.append(f"  Policy #: {cov['policy_number']}")
    if cov["relationship"]:
        lines.append(f"  Relationship: {cov['relationship']}")

    dates: list[str] = []
    if cov["effective_start"]:
        dates.append(f"Start: {cov['effective_start']}")
    if cov["effective_end"]:
        dates.append(f"End: {cov['effective_end']}")
    if dates:
        lines.append(f"  {' | '.join(dates)}")

    lines.append("")


@tool
async def insurance_coverage(patient_uuid: str) -> str:
    """Retrieve a patient's insurance coverage from the medical records system.

    Use this tool when you need to check a patient's insurance information,
    including plan name, insurer, policy number, coverage type, and effective
    dates. Provide the patient's UUID (obtainable from the patient_lookup tool).

    Returns a list of insurance coverages (active and expired) with plan name,
    insurer, policy number, coverage type, effective dates, and status.
    Returns a message if no insurance is on file.

    Examples:
        - insurance_coverage(patient_uuid="95f2f211-3580-4b58-9a15-2d9b29f49c72")
    """
    if not patient_uuid or not patient_uuid.strip():
        return "Error: patient_uuid is required."

    auth = OpenEMRAuth()

    try:
        async with auth.get_client() as client:
            resp = await client.get(
                f"{_FHIR_PREFIX}/Coverage",
                params={"patient": patient_uuid},
                timeout=10.0,
            )

            if resp.status_code == 401:
                # Force a fresh token and retry once.
                auth._access_token = None
                auth._refresh_token = None
                async with auth.get_client() as retry_client:
                    resp = await retry_client.get(
                        f"{_FHIR_PREFIX}/Coverage",
                        params={"patient": patient_uuid},
                        timeout=10.0,
                    )

            resp.raise_for_status()

    except httpx.TimeoutException:
        return "Unable to reach medical records system. Please try again."
    except httpx.HTTPStatusError as exc:
        logger.error("Insurance coverage API error: %s", exc)
        return "Unable to reach medical records system. Please try again."

    body = resp.json()

    # FHIR Bundle: entries live under "entry"; an empty bundle may omit the key.
    entries = body.get("entry", [])

    if not entries:
        return "No insurance coverage on file for this patient."

    coverages = [
        _parse_coverage(entry.get("resource", entry)) for entry in entries
    ]

    return _format_coverages(coverages)


# -- Standalone test ----------------------------------------------------------

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

        print(f"\n=== Step 2: Get insurance coverage for UUID {uuid} ===\n")
        result = await insurance_coverage.ainvoke({"patient_uuid": uuid})
        print(result)

    asyncio.run(_test())
