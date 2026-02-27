"""Provider lookup tool for searching OpenEMR practitioners by name or specialty.

This module provides a LangGraph-compatible tool that queries the OpenEMR
FHIR Practitioner and PractitionerRole endpoints to find providers matching
name and/or specialty criteria.
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
_MAX_RESULTS = 10


def _format_fhir_practitioner(resource: dict) -> dict:
    """Extract relevant fields from a FHIR Practitioner resource."""
    # Name
    names = resource.get("name", [])
    name_obj = names[0] if names else {}
    given = " ".join(name_obj.get("given", []))
    family = name_obj.get("family", "")
    prefix = " ".join(name_obj.get("prefix", []))
    name_parts = [p for p in (prefix, given, family) if p]

    # Address
    addresses = resource.get("address", [])
    address = ""
    if addresses:
        addr = addresses[0]
        lines = addr.get("line", [])
        city = addr.get("city", "")
        state = addr.get("state", "")
        postal = addr.get("postalCode", "")
        parts = lines + [p for p in (city, state, postal) if p]
        address = ", ".join(parts)

    # Telecom (phone, email)
    phone = ""
    email = ""
    for telecom in resource.get("telecom", []):
        system = telecom.get("system", "")
        value = telecom.get("value", "")
        if system == "phone" and not phone:
            phone = value
        elif system == "email" and not email:
            email = value

    # NPI from identifiers
    npi = ""
    for ident in resource.get("identifier", []):
        if "us-npi" in (ident.get("system", "")):
            npi = ident.get("value", "")
            break

    return {
        "uuid": resource.get("id", ""),
        "name": " ".join(name_parts),
        "specialty": "",
        "facility": "",
        "phone": phone,
        "email": email,
        "address": address,
        "npi": npi,
    }


def _enrich_specialties(
    practitioners: list[dict], role_entries: list[dict]
) -> list[dict]:
    """Merge specialty info from FHIR PractitionerRole into practitioner dicts.

    If a practitioner already has a specialty from the REST API, it is kept.
    Otherwise we look for a matching PractitionerRole entry by UUID reference.
    """
    # Build a map: practitioner UUID → specialty from PractitionerRole
    specialty_map: dict[str, str] = {}
    for entry in role_entries:
        resource = entry.get("resource", entry)
        ref = resource.get("practitioner", {}).get("reference", "")
        # Reference looks like "Practitioner/<uuid>"
        uuid = ref.split("/")[-1] if "/" in ref else ""
        if not uuid:
            continue

        # Extract specialty from the first specialty coding
        specialties = resource.get("specialty", [])
        if specialties:
            concept = specialties[0]
            spec_name = concept.get("text")
            if not spec_name:
                codings = concept.get("coding", [])
                if codings:
                    spec_name = codings[0].get("display")
            if spec_name:
                specialty_map[uuid] = spec_name

    for pract in practitioners:
        if not pract["specialty"] and pract["uuid"] in specialty_map:
            pract["specialty"] = specialty_map[pract["uuid"]]

    return practitioners


def _matches_specialty(practitioner: dict, specialty_query: str) -> bool:
    """Check if a practitioner's specialty matches the query (case-insensitive partial)."""
    spec = practitioner.get("specialty", "")
    return specialty_query.lower() in spec.lower() if spec else False


def _format_providers(providers: list[dict], total: int | None = None) -> str:
    """Format a list of parsed practitioner dicts into a readable string."""
    lines: list[str] = []
    showing = len(providers)
    if total and total > showing:
        lines.append(f"Found {total} provider(s), showing first {showing}:\n")
    else:
        lines.append(f"Found {showing} provider(s):\n")

    for prov in providers:
        lines.append(f"- {prov['name']}")
        details: list[str] = []
        if prov["specialty"]:
            details.append(f"Specialty: {prov['specialty']}")
        if prov["npi"]:
            details.append(f"NPI: {prov['npi']}")
        if details:
            lines.append(f"  {' | '.join(details)}")
        if prov["facility"]:
            lines.append(f"  Facility: {prov['facility']}")
        if prov["phone"]:
            lines.append(f"  Phone: {prov['phone']}")
        if prov["email"]:
            lines.append(f"  Email: {prov['email']}")
        if prov["address"]:
            lines.append(f"  Address: {prov['address']}")
        lines.append(f"  UUID: {prov['uuid']}")
        lines.append("")

    return "\n".join(lines).strip()


@tool
async def provider_lookup(
    name: Optional[str] = None,
    specialty: Optional[str] = None,
) -> str:
    """Search for providers (practitioners) in the medical records system.

    Use this tool when you need to find a provider/practitioner by name or
    specialty. You can search by name (partial match supported), specialty,
    or both. If no filters are provided, the first 10 providers are returned
    as a directory listing.

    Returns provider details including name, specialty, facility, phone,
    email, address, and NPI number.

    Examples:
        - provider_lookup(name="Jones")
        - provider_lookup(specialty="Cardiology")
        - provider_lookup(name="Smith", specialty="Family Medicine")
        - provider_lookup()  # directory listing
    """
    auth = OpenEMRAuth()

    # ── Step 1: Query the FHIR Practitioner endpoint ──────────────────────
    # Fetch all practitioners (FHIR name search can cause 500 errors on some
    # OpenEMR versions, so we filter client-side).
    try:
        async with auth.get_client() as client:
            resp = await client.get(
                f"{_FHIR_PREFIX}/Practitioner",
                timeout=10.0,
            )

            if resp.status_code == 401:
                auth._access_token = None
                auth._refresh_token = None
                async with auth.get_client() as retry_client:
                    resp = await retry_client.get(
                        f"{_FHIR_PREFIX}/Practitioner",
                        timeout=10.0,
                    )

            resp.raise_for_status()

    except httpx.TimeoutException:
        return "Unable to reach medical records system. Please try again."
    except httpx.HTTPStatusError as exc:
        logger.error("Provider lookup API error: %s", exc)
        return "Unable to reach medical records system. Please try again."

    body = resp.json()
    entries = body.get("entry", [])

    if not entries:
        if name:
            return "No providers found matching the search criteria."
        return "No providers found in the system."

    practitioners = [
        _format_fhir_practitioner(e.get("resource", e)) for e in entries
    ]

    # Filter by name client-side (case-insensitive partial match).
    if name:
        query = name.strip().lower()
        practitioners = [
            p for p in practitioners if query in p["name"].lower()
        ]
        if not practitioners:
            return "No providers found matching the search criteria."

    # ── Step 2: Optionally enrich with FHIR PractitionerRole ─────────────
    # Fetch PractitionerRole when filtering by specialty or when practitioners
    # are missing specialty data.
    needs_specialty_data = specialty or any(
        not p["specialty"] for p in practitioners
    )

    if needs_specialty_data:
        try:
            async with auth.get_client() as client:
                role_resp = await client.get(
                    f"{_FHIR_PREFIX}/PractitionerRole",
                    timeout=10.0,
                )

                if role_resp.status_code == 401:
                    auth._access_token = None
                    auth._refresh_token = None
                    async with auth.get_client() as retry_client:
                        role_resp = await retry_client.get(
                            f"{_FHIR_PREFIX}/PractitionerRole",
                            timeout=10.0,
                        )

                role_resp.raise_for_status()

            role_body = role_resp.json()
            role_entries = role_body.get("entry", [])
            practitioners = _enrich_specialties(practitioners, role_entries)

        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.warning("PractitionerRole fetch failed, skipping specialty enrichment: %s", exc)

    # ── Step 3: Filter by specialty if requested ─────────────────────────
    if specialty:
        practitioners = [
            p for p in practitioners if _matches_specialty(p, specialty)
        ]
        if not practitioners:
            return f"No providers found matching specialty '{specialty}'."

    # ── Step 4: Limit and format results ─────────────────────────────────
    total = len(practitioners)
    providers = practitioners[:_MAX_RESULTS]

    return _format_providers(providers, total=total)


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    async def _test():
        print("=== Test 1: Directory listing (no filters) ===\n")
        result = await provider_lookup.ainvoke({})
        print(result)

        print("\n\n=== Test 2: Search by name ===\n")
        result = await provider_lookup.ainvoke({"name": "Smith"})
        print(result)

        print("\n\n=== Test 3: Search by specialty ===\n")
        result = await provider_lookup.ainvoke({"specialty": "Family"})
        print(result)

        print("\n\n=== Test 4: Search by name and specialty ===\n")
        result = await provider_lookup.ainvoke({"name": "Smith", "specialty": "Family"})
        print(result)

    asyncio.run(_test())
