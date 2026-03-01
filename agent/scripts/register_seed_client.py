"""Register a new OAuth2 client with write scopes for data seeding.

Usage (from agent/ directory):
    python -m scripts.register_seed_client

After running, enable the client in the OpenEMR admin UI:
    Administration > System > API Clients > Enable
Then update .env with the printed client_id and client_secret.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import OPENEMR_BASE_URL

import httpx

SEED_SCOPES = (
    "openid api:oemr api:fhir "
    # Patient demographics
    "user/patient.read user/patient.write "
    # Clinical data
    "user/allergy.read user/allergy.write "
    "user/medical_problem.read user/medical_problem.write "
    "user/medication.read user/medication.write "
    "user/encounter.read user/encounter.write "
    "user/vital.read user/vital.write "
    "user/appointment.read user/appointment.write "
    # Practitioners
    "user/practitioner.read user/practitioner.write "
    # Insurance
    "user/insurance.read user/insurance.write "
    "user/insurance_company.read user/insurance_company.write "
    # Facility (read-only, for linking)
    "user/facility.read "
    # FHIR read scopes (for the agent tools)
    "user/AllergyIntolerance.read "
    "user/MedicationRequest.read "
    "user/Condition.read "
    "user/Practitioner.read "
    "user/PractitionerRole.read "
    "user/Coverage.read"
)


async def main():
    base_url = OPENEMR_BASE_URL.rstrip("/")
    print(f"\nRegistering OAuth2 client on: {base_url}")
    print(f"Scopes: {SEED_SCOPES}\n")

    payload = {
        "application_type": "private",
        "redirect_uris": [base_url],
        "post_logout_redirect_uris": [base_url],
        "client_name": "OpenEMR Data Seeder",
        "token_endpoint_auth_method": "client_secret_post",
        "contacts": ["seed@example.com"],
        "scope": SEED_SCOPES,
    }

    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(
            f"{base_url}/oauth2/default/registration",
            json=payload,
        )

    if resp.status_code != 200:
        print(f"Registration failed (HTTP {resp.status_code}):")
        print(resp.text)
        sys.exit(1)

    data = resp.json()
    client_id = data["client_id"]
    client_secret = data["client_secret"]

    print("Registration successful!\n")
    print("Add these to your agent/.env file:\n")
    print(f'  OPENEMR_CLIENT_ID="{client_id}"')
    print(f'  OPENEMR_CLIENT_SECRET="{client_secret}"')
    print()
    print("IMPORTANT: You must enable this client before use:")
    print(f"  1. Log into {base_url} as admin")
    print("  2. Go to Administration > System > API Clients")
    print("  3. Find 'OpenEMR Data Seeder' and click Enable")
    print()


if __name__ == "__main__":
    asyncio.run(main())
