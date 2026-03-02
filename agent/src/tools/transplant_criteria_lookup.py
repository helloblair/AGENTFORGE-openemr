"""Transplant criteria lookup tool for querying ICD-10 reference data.

This module provides a LangGraph-compatible tool that queries the OpenEMR
REST API to fetch transplant-relevant ICD-10 codes and OPTN eligibility
criteria for a given organ type.
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

_API_PREFIX = "/apis/default/api"

VALID_ORGAN_TYPES = {"kidney", "heart", "lung", "liver", "general"}
VALID_CRITERIA_TYPES = {
    "qualifying_diagnosis",
    "transplant_status",
    "complication",
    "contraindication",
    "screening",
}


def _format_criteria(data: list[dict], organ_type: str, criteria_type: str | None) -> str:
    """Format criteria records into a readable string."""
    if not data:
        filter_desc = f"organ_type={organ_type}"
        if criteria_type:
            filter_desc += f", criteria_type={criteria_type}"
        return f"No transplant criteria found for {filter_desc}."

    lines: list[str] = []
    lines.append(f"Found {len(data)} transplant criteria record(s):\n")

    # Group by criteria_type for readability
    grouped: dict[str, list[dict]] = {}
    for record in data:
        ct = record.get("criteria_type", "unknown")
        grouped.setdefault(ct, []).append(record)

    for ct, records in grouped.items():
        label = ct.replace("_", " ").title()
        lines.append(f"### {label} ({len(records)} codes)")
        for r in records:
            code = r.get("icd10_code", "")
            short = r.get("short_description", "")
            billable = "billable" if r.get("is_billable") else "header"
            lines.append(f"  - [{code}] {short} ({billable})")
        lines.append("")

    return "\n".join(lines).strip()


@tool
async def transplant_criteria_lookup(
    organ_type: str,
    criteria_type: Optional[str] = None,
) -> str:
    """Look up ICD-10 codes and clinical criteria for organ transplant screening.

    Use this tool to find qualifying diagnoses, contraindication codes, or
    transplant status codes relevant to a specific organ type. This queries
    the transplant ICD-10 criteria reference database.

    Valid organ types: kidney, heart, lung, liver, general.
    Valid criteria types: qualifying_diagnosis, transplant_status, complication,
    contraindication, screening.

    Examples:
        - transplant_criteria_lookup(organ_type="kidney")
        - transplant_criteria_lookup(organ_type="liver", criteria_type="qualifying_diagnosis")
        - transplant_criteria_lookup(organ_type="general", criteria_type="contraindication")
    """
    organ_type = (organ_type or "").strip().lower()
    if organ_type not in VALID_ORGAN_TYPES:
        return (
            f"Error: Invalid organ_type '{organ_type}'. "
            f"Valid options: {', '.join(sorted(VALID_ORGAN_TYPES))}."
        )

    if criteria_type:
        criteria_type = criteria_type.strip().lower()
        if criteria_type not in VALID_CRITERIA_TYPES:
            return (
                f"Error: Invalid criteria_type '{criteria_type}'. "
                f"Valid options: {', '.join(sorted(VALID_CRITERIA_TYPES))}."
            )

    auth = OpenEMRAuth()

    try:
        async with auth.get_client() as client:
            params: dict[str, str] = {"organ_system": organ_type}
            if criteria_type:
                params["criteria_type"] = criteria_type

            resp = await client.get(
                f"{_API_PREFIX}/transplant_criteria",
                params=params,
                timeout=15.0,
            )

            if resp.status_code == 401:
                auth._access_token = None
                auth._refresh_token = None
                async with auth.get_client() as retry_client:
                    resp = await retry_client.get(
                        f"{_API_PREFIX}/transplant_criteria",
                        params=params,
                        timeout=15.0,
                    )

            resp.raise_for_status()

    except httpx.TimeoutException:
        return "Unable to reach medical records system. Please try again."
    except httpx.HTTPStatusError as exc:
        logger.error("Transplant criteria API error: %s", exc)
        return "Unable to reach medical records system. Please try again."

    body = resp.json()

    # OpenEMR REST response format: { "validationErrors": [], "internalErrors": [], "data": [...] }
    if body.get("validationErrors"):
        return f"Validation error: {body['validationErrors']}"
    if body.get("internalErrors"):
        return "Internal error retrieving criteria. Please try again."

    records = body.get("data", [])
    return _format_criteria(records, organ_type, criteria_type)


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    async def _test():
        print("=== Test 1: Kidney criteria ===\n")
        result = await transplant_criteria_lookup.ainvoke(
            {"organ_type": "kidney"}
        )
        print(result)

        print("\n\n=== Test 2: General contraindications ===\n")
        result = await transplant_criteria_lookup.ainvoke(
            {"organ_type": "general", "criteria_type": "contraindication"}
        )
        print(result)

        print("\n\n=== Test 3: Invalid organ type ===\n")
        result = await transplant_criteria_lookup.ainvoke(
            {"organ_type": "brain"}
        )
        print(result)

    asyncio.run(_test())
