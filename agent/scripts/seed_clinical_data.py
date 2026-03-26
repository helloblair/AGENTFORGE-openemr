"""Seed OpenEMR with realistic clinical data via the REST API.

Creates practitioners, insurance companies, and patients with full medical
profiles: demographics, encounters, vitals, medical problems, allergies,
medications, and insurance policies.

Usage (from the agent/ directory):
    python -m scripts.seed_clinical_data              # seed everything
    python -m scripts.seed_clinical_data --dry-run    # preview without writing
    python -m scripts.seed_clinical_data --patients 0 # skip patients, only add clinical data to existing

Requires write scopes on the OAuth2 client — see SEED_README.md for setup.

## How to extend this script for new tools

The pattern is always the same — 3 steps:

1. ADD A DATA DICT keyed by (fname, lname) at the top of the file:

    MY_NEW_DATA: dict[tuple[str, str], list[dict]] = {
        ("Maria", "Garcia"): [
            {"field1": "value1", "field2": "value2"},
        ],
    }

2. ADD A STEP in the seed() function that loops over patients and calls api_post():

    my_stats = Stats()
    print("\\n  STEP N: Adding my new data\\n")
    for key, pdata in created.items():
        puuid = pdata.get("uuid")
        if not puuid:
            continue
        for item in MY_NEW_DATA.get(key, []):
            label = f"MyThing '{item['field1']}' for {key[0]} {key[1]}"
            await api_post(client, f"{API}/patient/{puuid}/my_endpoint", item, label, my_stats)

3. ADD THE STATS to the summary print block at the end.

To find the right API endpoint and field names, check:
- apis/routes/_rest_routes_standard.inc.php  (search for POST routes)
- tests/Tests/Fixtures/                      (sample payloads)
- Or query /swagger on your OpenEMR instance

Common endpoints:
- POST /api/patient/{puuid}/medical_problem   — conditions (ICD-10)
- POST /api/patient/{puuid}/allergy           — allergies (RXCUI)
- POST /api/patient/{puuid}/medication        — medications
- POST /api/patient/{puuid}/encounter         — encounters/visits
- POST /api/patient/{puuid}/encounter/{eid}/vital — vitals
- POST /api/patient/{puuid}/surgery           — surgical history
- POST /api/patient/{puuid}/dental_issue      — dental issues
- POST /api/patient/{puuid}/insurance         — insurance policies
- POST /api/patient/{pid}/appointment         — appointments
- POST /api/patient/{pid}/document            — documents (multipart)
- POST /api/practitioner                      — providers
- POST /api/insurance_company                 — payers
- POST /api/facility                          — facilities
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.auth.oauth2 import OpenEMRAuth

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

API = "/apis/default/api"

# ── Realistic patient data ──────────────────────────────────────────────────

PATIENTS = [
    {
        "fname": "Maria",
        "lname": "Garcia",
        "DOB": "1968-04-12",
        "sex": "Female",
        "race": "white",
        "ethnicity": "hisp_or_latin",
        "status": "married",
        "street": "742 Evergreen Terrace",
        "city": "Springfield",
        "state": "MA",
        "postal_code": "01103",
        "phone_home": "(413) 555-0142",
        "email": "maria.garcia@example.com",
    },
    {
        "fname": "James",
        "lname": "Thompson",
        "DOB": "1955-11-03",
        "sex": "Male",
        "race": "black_or_african_american",
        "ethnicity": "not_hisp_or_latin",
        "status": "divorced",
        "street": "1600 Pennsylvania Ave",
        "city": "Boston",
        "state": "MA",
        "postal_code": "02101",
        "phone_home": "(617) 555-0198",
        "email": "jthompson@example.com",
    },
    {
        "fname": "Aisha",
        "lname": "Patel",
        "DOB": "1992-07-22",
        "sex": "Female",
        "race": "asian",
        "ethnicity": "not_hisp_or_latin",
        "status": "single",
        "street": "88 Beacon Street",
        "city": "Cambridge",
        "state": "MA",
        "postal_code": "02138",
        "phone_home": "(617) 555-0234",
        "email": "aisha.patel@example.com",
    },
    {
        "fname": "Robert",
        "lname": "Chen",
        "DOB": "1978-02-28",
        "sex": "Male",
        "race": "asian",
        "ethnicity": "not_hisp_or_latin",
        "status": "married",
        "street": "55 Milk Street",
        "city": "Worcester",
        "state": "MA",
        "postal_code": "01608",
        "phone_home": "(508) 555-0167",
        "email": "rchen@example.com",
    },
    {
        "fname": "Linda",
        "lname": "Washington",
        "DOB": "1945-09-15",
        "sex": "Female",
        "race": "black_or_african_american",
        "ethnicity": "not_hisp_or_latin",
        "status": "widowed",
        "street": "200 Newbury Street",
        "city": "Springfield",
        "state": "MA",
        "postal_code": "01105",
        "phone_home": "(413) 555-0289",
        "email": "lwashington@example.com",
    },
    {
        "fname": "David",
        "lname": "Kowalski",
        "DOB": "1988-12-05",
        "sex": "Male",
        "race": "white",
        "ethnicity": "not_hisp_or_latin",
        "status": "single",
        "street": "33 Harvard Ave",
        "city": "Brookline",
        "state": "MA",
        "postal_code": "02446",
        "phone_home": "(617) 555-0345",
        "email": "dkowalski@example.com",
    },
    {
        "fname": "Carmen",
        "lname": "Rivera",
        "DOB": "1973-06-18",
        "sex": "Female",
        "race": "white",
        "ethnicity": "hisp_or_latin",
        "status": "married",
        "street": "410 Main Street",
        "city": "Holyoke",
        "state": "MA",
        "postal_code": "01040",
        "phone_home": "(413) 555-0412",
        "email": "crivera@example.com",
    },
    {
        "fname": "William",
        "lname": "O'Brien",
        "DOB": "1960-03-30",
        "sex": "Male",
        "race": "white",
        "ethnicity": "not_hisp_or_latin",
        "status": "married",
        "street": "77 Summer Street",
        "city": "Boston",
        "state": "MA",
        "postal_code": "02110",
        "phone_home": "(617) 555-0478",
        "email": "wobrien@example.com",
    },
    {
        "fname": "Fatima",
        "lname": "Al-Hassan",
        "DOB": "1985-10-14",
        "sex": "Female",
        "race": "white",
        "ethnicity": "not_hisp_or_latin",
        "status": "married",
        "street": "123 Salem Street",
        "city": "Lowell",
        "state": "MA",
        "postal_code": "01852",
        "phone_home": "(978) 555-0523",
        "email": "falhassan@example.com",
    },
    {
        "fname": "Marcus",
        "lname": "Johnson",
        "DOB": "1999-01-25",
        "sex": "Male",
        "race": "black_or_african_american",
        "ethnicity": "not_hisp_or_latin",
        "status": "single",
        "street": "60 State Street",
        "city": "Northampton",
        "state": "MA",
        "postal_code": "01060",
        "phone_home": "(413) 555-0601",
        "email": "mjohnson@example.com",
    },
]

# ── Transplant screening demo patients ──────────────────────────────────────
# 5 patients designed to exercise the organ transplant candidacy screening
# tool with different outcomes: eligible, ineligible, incomplete, complex,
# and eligible-with-conditions.

TRANSPLANT_PATIENTS = [
    {
        "fname": "Clara",
        "lname": "Reeves",
        "DOB": "1973-08-20",
        "sex": "Female",
        "race": "white",
        "ethnicity": "not_hisp_or_latin",
        "status": "married",
        "street": "45 Maple Drive",
        "city": "Springfield",
        "state": "MA",
        "postal_code": "01104",
        "phone_home": "(413) 555-0710",
        "email": "creeves@example.com",
    },
    {
        "fname": "Marcus",
        "lname": "Blake",
        "DOB": "1978-11-15",
        "sex": "Male",
        "race": "black_or_african_american",
        "ethnicity": "not_hisp_or_latin",
        "status": "single",
        "street": "220 Congress Street",
        "city": "Boston",
        "state": "MA",
        "postal_code": "02210",
        "phone_home": "(617) 555-0822",
        "email": "mblake@example.com",
    },
    {
        "fname": "Diana",
        "lname": "Patel",
        "DOB": "1964-05-03",
        "sex": "Female",
        "race": "asian",
        "ethnicity": "not_hisp_or_latin",
        "status": "widowed",
        "street": "88 Federal Street",
        "city": "Worcester",
        "state": "MA",
        "postal_code": "01609",
        "phone_home": "(508) 555-0934",
        "email": "dpatel@example.com",
    },
    {
        "fname": "Robert",
        "lname": "Chen-Ramirez",
        "DOB": "1967-09-12",
        "sex": "Male",
        "race": "asian",
        "ethnicity": "hisp_or_latin",
        "status": "married",
        "street": "31 Winter Street",
        "city": "Cambridge",
        "state": "MA",
        "postal_code": "02139",
        "phone_home": "(617) 555-1045",
        "email": "rchenramirez@example.com",
    },
    {
        "fname": "Angela",
        "lname": "Torres",
        "DOB": "1981-12-28",
        "sex": "Female",
        "race": "white",
        "ethnicity": "hisp_or_latin",
        "status": "divorced",
        "street": "156 Tremont Street",
        "city": "Boston",
        "state": "MA",
        "postal_code": "02111",
        "phone_home": "(617) 555-1156",
        "email": "atorres@example.com",
    },
]

# ── Donor evaluation demo patients ─────────────────────────────────────────
# Living donors (healthy, good labs) + deceased donors (cause of death,
# organ-specific data) for the donor_viability tool.

DONOR_PATIENTS = [
    # Living kidney donor — healthy 34yo female, great eGFR
    {
        "fname": "Priya",
        "lname": "Sharma",
        "DOB": "1992-03-14",
        "sex": "Female",
        "race": "asian",
        "ethnicity": "not_hisp_or_latin",
        "status": "married",
        "street": "22 Brattle Street",
        "city": "Cambridge",
        "state": "MA",
        "postal_code": "02138",
        "phone_home": "(617) 555-1201",
        "email": "psharma@example.com",
    },
    # Living liver donor — healthy 41yo male, normal LFTs
    {
        "fname": "Tomás",
        "lname": "Herrera",
        "DOB": "1985-07-09",
        "sex": "Male",
        "race": "white",
        "ethnicity": "hisp_or_latin",
        "status": "married",
        "street": "510 Commonwealth Ave",
        "city": "Boston",
        "state": "MA",
        "postal_code": "02215",
        "phone_home": "(617) 555-1302",
        "email": "therrera@example.com",
    },
    # Deceased donor — 52yo male, CVA, good organs
    {
        "fname": "Gerald",
        "lname": "Franklin",
        "DOB": "1974-01-22",
        "sex": "Male",
        "race": "black_or_african_american",
        "ethnicity": "not_hisp_or_latin",
        "status": "married",
        "street": "85 Warren Street",
        "city": "Roxbury",
        "state": "MA",
        "postal_code": "02119",
        "phone_home": "(617) 555-1403",
        "email": "gfranklin@example.com",
    },
    # Deceased donor — 67yo female, anoxia, marginal organs
    {
        "fname": "Evelyn",
        "lname": "Matsuda",
        "DOB": "1959-11-05",
        "sex": "Female",
        "race": "asian",
        "ethnicity": "not_hisp_or_latin",
        "status": "widowed",
        "street": "44 Pearl Street",
        "city": "Worcester",
        "state": "MA",
        "postal_code": "01608",
        "phone_home": "(508) 555-1504",
        "email": "ematsuda@example.com",
    },
]

# Per-patient clinical profiles keyed by (fname, lname)

ALLERGIES: dict[tuple[str, str], list[dict]] = {
    ("Maria", "Garcia"): [
        {"type": "allergy", "title": "Penicillin", "reaction": "hives", "begdate": "1990-03-15", "diagnosis": "RXCUI:733"},
        {"type": "allergy", "title": "Sulfa drugs", "reaction": "rash", "begdate": "2005-07-20", "diagnosis": "RXCUI:10831"},
    ],
    ("James", "Thompson"): [
        {"type": "allergy", "title": "Aspirin", "reaction": "shortness of breath", "begdate": "1980-06-10", "diagnosis": "RXCUI:1191"},
        {"type": "allergy", "title": "Ibuprofen", "reaction": "stomach upset", "begdate": "1985-02-14", "diagnosis": "RXCUI:5640"},
        {"type": "allergy", "title": "Shellfish", "reaction": "anaphylaxis", "begdate": "1970-09-01"},
    ],
    ("Aisha", "Patel"): [
        {"type": "allergy", "title": "Latex", "reaction": "contact dermatitis", "begdate": "2015-11-20"},
    ],
    ("Robert", "Chen"): [
        {"type": "allergy", "title": "Amoxicillin", "reaction": "rash", "begdate": "2000-04-05", "diagnosis": "RXCUI:723"},
    ],
    ("Linda", "Washington"): [
        {"type": "allergy", "title": "Codeine", "reaction": "nausea and vomiting", "begdate": "1975-12-01", "diagnosis": "RXCUI:2670"},
        {"type": "allergy", "title": "ACE Inhibitors", "reaction": "angioedema", "begdate": "2010-08-15", "diagnosis": "RXCUI:29046"},
        {"type": "allergy", "title": "Peanuts", "reaction": "throat swelling", "begdate": "1950-03-01"},
    ],
    ("Carmen", "Rivera"): [
        {"type": "allergy", "title": "Metformin", "reaction": "diarrhea", "begdate": "2018-01-10", "diagnosis": "RXCUI:6809"},
    ],
    ("William", "O'Brien"): [
        {"type": "allergy", "title": "Statins", "reaction": "muscle pain", "begdate": "2015-06-22", "diagnosis": "RXCUI:36567"},
        {"type": "allergy", "title": "Bee stings", "reaction": "anaphylaxis", "begdate": "1990-07-04"},
    ],
    ("Fatima", "Al-Hassan"): [],  # No known allergies (NKDA)
    ("David", "Kowalski"): [
        {"type": "allergy", "title": "Ciprofloxacin", "reaction": "tendon pain", "begdate": "2020-09-12", "diagnosis": "RXCUI:2551"},
    ],
    ("Marcus", "Johnson"): [
        {"type": "allergy", "title": "Erythromycin", "reaction": "stomach cramps", "begdate": "2010-05-30", "diagnosis": "RXCUI:4053"},
    ],
    # ── Transplant patients ──
    ("Clara", "Reeves"): [],  # NKDA — clean candidate
    ("Marcus", "Blake"): [],  # No drug allergies (contraindications are substance abuse + BMI)
    ("Diana", "Patel"): [],  # No drug allergies
    ("Robert", "Chen-Ramirez"): [],  # No drug allergies
    ("Angela", "Torres"): [],  # No drug allergies
    # ── Donor patients ──
    ("Priya", "Sharma"): [],  # NKDA — healthy living donor
    ("Tomás", "Herrera"): [],  # NKDA — healthy living donor
    ("Gerald", "Franklin"): [],  # Deceased donor
    ("Evelyn", "Matsuda"): [
        {"type": "allergy", "title": "Lisinopril", "reaction": "cough", "begdate": "2010-05-20", "diagnosis": "RXCUI:29046"},
    ],
}

MEDICAL_PROBLEMS: dict[tuple[str, str], list[dict]] = {
    ("Maria", "Garcia"): [
        {"title": "Type 2 Diabetes Mellitus", "begdate": "2010-06-15", "diagnosis": "ICD10:E11.9"},
        {"title": "Essential Hypertension", "begdate": "2008-03-20", "diagnosis": "ICD10:I10"},
        {"title": "Hyperlipidemia", "begdate": "2012-09-01", "diagnosis": "ICD10:E78.5"},
    ],
    ("James", "Thompson"): [
        {"title": "Coronary Artery Disease", "begdate": "2005-11-10", "diagnosis": "ICD10:I25.10"},
        {"title": "Type 2 Diabetes Mellitus", "begdate": "2000-04-22", "diagnosis": "ICD10:E11.9"},
        {"title": "Chronic Kidney Disease Stage 3", "begdate": "2015-07-18", "diagnosis": "ICD10:N18.3"},
        {"title": "Essential Hypertension", "begdate": "1998-01-05", "diagnosis": "ICD10:I10"},
        {"title": "Atrial Fibrillation", "begdate": "2018-02-28", "diagnosis": "ICD10:I48.91"},
    ],
    ("Aisha", "Patel"): [
        {"title": "Generalized Anxiety Disorder", "begdate": "2018-09-14", "diagnosis": "ICD10:F41.1"},
        {"title": "Iron Deficiency Anemia", "begdate": "2020-03-05", "diagnosis": "ICD10:D50.9"},
    ],
    ("Robert", "Chen"): [
        {"title": "Asthma, Moderate Persistent", "begdate": "1995-05-12", "diagnosis": "ICD10:J45.40"},
        {"title": "Gastroesophageal Reflux Disease", "begdate": "2015-11-30", "diagnosis": "ICD10:K21.0"},
        {"title": "Seasonal Allergic Rhinitis", "begdate": "2000-04-01", "diagnosis": "ICD10:J30.2"},
    ],
    ("Linda", "Washington"): [
        {"title": "Congestive Heart Failure", "begdate": "2018-12-05", "diagnosis": "ICD10:I50.9"},
        {"title": "Type 2 Diabetes Mellitus", "begdate": "2005-06-20", "diagnosis": "ICD10:E11.9"},
        {"title": "Osteoarthritis of Knee", "begdate": "2010-03-15", "diagnosis": "ICD10:M17.9"},
        {"title": "Chronic Obstructive Pulmonary Disease", "begdate": "2015-09-01", "diagnosis": "ICD10:J44.1"},
        {"title": "Essential Hypertension", "begdate": "1995-01-10", "diagnosis": "ICD10:I10"},
        {"title": "Hypothyroidism", "begdate": "2008-07-22", "diagnosis": "ICD10:E03.9"},
    ],
    ("David", "Kowalski"): [
        {"title": "Major Depressive Disorder", "begdate": "2019-02-18", "diagnosis": "ICD10:F33.0"},
        {"title": "Lumbar Disc Herniation", "begdate": "2022-08-10", "diagnosis": "ICD10:M51.16"},
    ],
    ("Carmen", "Rivera"): [
        {"title": "Type 2 Diabetes Mellitus", "begdate": "2015-04-25", "diagnosis": "ICD10:E11.9"},
        {"title": "Obesity", "begdate": "2012-01-15", "diagnosis": "ICD10:E66.01"},
        {"title": "Obstructive Sleep Apnea", "begdate": "2017-10-08", "diagnosis": "ICD10:G47.33"},
        {"title": "Essential Hypertension", "begdate": "2016-06-12", "diagnosis": "ICD10:I10"},
    ],
    ("William", "O'Brien"): [
        {"title": "Essential Hypertension", "begdate": "2005-02-14", "diagnosis": "ICD10:I10"},
        {"title": "Benign Prostatic Hyperplasia", "begdate": "2018-11-20", "diagnosis": "ICD10:N40.0"},
        {"title": "Gout", "begdate": "2020-03-07", "diagnosis": "ICD10:M10.9"},
    ],
    ("Fatima", "Al-Hassan"): [
        {"title": "Migraine without Aura", "begdate": "2010-08-30", "diagnosis": "ICD10:G43.009"},
        {"title": "Polycystic Ovary Syndrome", "begdate": "2012-05-14", "diagnosis": "ICD10:E28.2"},
    ],
    ("Marcus", "Johnson"): [
        {"title": "Seasonal Allergic Rhinitis", "begdate": "2015-04-01", "diagnosis": "ICD10:J30.2"},
        {"title": "Attention Deficit Hyperactivity Disorder", "begdate": "2008-09-15", "diagnosis": "ICD10:F90.0"},
    ],
    # ── Transplant patients ──
    # Clara Reeves — Kidney, ELIGIBLE
    ("Clara", "Reeves"): [
        {"title": "End-stage renal disease", "begdate": "2023-06-10", "diagnosis": "ICD10:N18.6"},
        {"title": "Dependence on renal dialysis", "begdate": "2024-01-15", "diagnosis": "ICD10:Z99.2"},
    ],
    # Marcus Blake — Heart, INELIGIBLE (contraindications)
    ("Marcus", "Blake"): [
        {"title": "Chronic systolic heart failure, NYHA Class II", "begdate": "2022-03-20", "diagnosis": "ICD10:I50.22"},
        {"title": "Dilated cardiomyopathy", "begdate": "2021-11-05", "diagnosis": "ICD10:I42.0"},
        {"title": "Alcohol dependence, uncomplicated", "begdate": "2025-12-01", "diagnosis": "ICD10:F10.20"},
        {"title": "Morbid obesity due to excess calories", "begdate": "2020-06-15", "diagnosis": "ICD10:E66.01"},
    ],
    # Diana Patel — Liver, INCOMPLETE (missing evaluations)
    ("Diana", "Patel"): [
        {"title": "Unspecified cirrhosis of liver", "begdate": "2020-08-12", "diagnosis": "ICD10:K74.60"},
        {"title": "Chronic hepatic failure without coma", "begdate": "2022-01-20", "diagnosis": "ICD10:K72.10"},
        {"title": "Chronic viral hepatitis C", "begdate": "2015-03-10", "enddate": "2019-09-15", "diagnosis": "ICD10:B18.2"},
    ],
    # Robert Chen-Ramirez — Kidney+Heart, ELIGIBLE/PENDING REVIEW
    ("Robert", "Chen-Ramirez"): [
        {"title": "Chronic kidney disease, stage 5", "begdate": "2023-09-01", "diagnosis": "ICD10:N18.5"},
        {"title": "Chronic combined systolic and diastolic heart failure, NYHA Class III", "begdate": "2022-05-18", "diagnosis": "ICD10:I50.42"},
        {"title": "Type 2 diabetes with diabetic chronic kidney disease", "begdate": "2015-02-28", "diagnosis": "ICD10:E11.22"},
        {"title": "Hypertensive chronic kidney disease", "begdate": "2016-10-12", "diagnosis": "ICD10:I12.9"},
    ],
    # Angela Torres — Lung, ELIGIBLE WITH CONDITIONS
    ("Angela", "Torres"): [
        {"title": "Pulmonary fibrosis, unspecified", "begdate": "2021-04-22", "diagnosis": "ICD10:J84.10"},
        {"title": "Chronic respiratory failure, unspecified", "begdate": "2023-08-10", "diagnosis": "ICD10:J96.10"},
        {"title": "Nicotine dependence, cigarettes, uncomplicated", "begdate": "2010-01-01", "enddate": "2024-03-01", "diagnosis": "ICD10:F17.210"},
    ],
    # ── Donor patients ──
    # Priya Sharma — Living kidney donor, HEALTHY
    ("Priya", "Sharma"): [
        {"title": "Seasonal Allergic Rhinitis", "begdate": "2015-04-01", "diagnosis": "ICD10:J30.2"},
    ],
    # Tomás Herrera — Living liver donor, HEALTHY
    ("Tomás", "Herrera"): [
        {"title": "Mild intermittent asthma", "begdate": "2005-06-01", "diagnosis": "ICD10:J45.20"},
    ],
    # Gerald Franklin — Deceased donor, CVA (stroke), good organs
    ("Gerald", "Franklin"): [
        {"title": "Essential Hypertension", "begdate": "2010-03-15", "diagnosis": "ICD10:I10"},
        {"title": "Cerebrovascular accident (stroke)", "begdate": "2026-03-20", "diagnosis": "ICD10:I63.9"},
    ],
    # Evelyn Matsuda — Deceased donor, cardiac arrest, marginal organs
    ("Evelyn", "Matsuda"): [
        {"title": "Essential Hypertension", "begdate": "2000-06-10", "diagnosis": "ICD10:I10"},
        {"title": "Type 2 Diabetes Mellitus", "begdate": "2005-09-22", "diagnosis": "ICD10:E11.9"},
        {"title": "Cardiac arrest, cause unspecified", "begdate": "2026-03-18", "diagnosis": "ICD10:I46.9"},
    ],
}

MEDICATIONS: dict[tuple[str, str], list[dict]] = {
    ("Maria", "Garcia"): [
        {"title": "Metformin 500mg", "begdate": "2010-06-15", "drug": "Metformin Hydrochloride 500 MG Oral Tablet"},
        {"title": "Lisinopril 10mg", "begdate": "2008-03-20", "drug": "Lisinopril 10 MG Oral Tablet"},
        {"title": "Atorvastatin 20mg", "begdate": "2012-09-01", "drug": "Atorvastatin 20 MG Oral Tablet"},
    ],
    ("James", "Thompson"): [
        {"title": "Metoprolol 50mg", "begdate": "2005-11-10", "drug": "Metoprolol Tartrate 50 MG Oral Tablet"},
        {"title": "Warfarin 5mg", "begdate": "2018-02-28", "drug": "Warfarin Sodium 5 MG Oral Tablet"},
        {"title": "Insulin Glargine", "begdate": "2010-01-15", "drug": "Insulin Glargine 100 UNT/ML Injectable Solution"},
        {"title": "Amlodipine 5mg", "begdate": "2008-05-20", "drug": "Amlodipine 5 MG Oral Tablet"},
    ],
    ("Aisha", "Patel"): [
        {"title": "Sertraline 50mg", "begdate": "2018-09-14", "drug": "Sertraline 50 MG Oral Tablet"},
        {"title": "Ferrous Sulfate 325mg", "begdate": "2020-03-05", "drug": "Ferrous Sulfate 325 MG Oral Tablet"},
    ],
    ("Robert", "Chen"): [
        {"title": "Albuterol Inhaler", "begdate": "1995-05-12", "drug": "Albuterol 0.83 MG/ML Inhalation Solution"},
        {"title": "Fluticasone Inhaler", "begdate": "2005-03-20", "drug": "Fluticasone Propionate 110 MCG/ACTUAT Metered Dose Inhaler"},
        {"title": "Omeprazole 20mg", "begdate": "2015-11-30", "drug": "Omeprazole 20 MG Delayed Release Oral Capsule"},
        {"title": "Cetirizine 10mg", "begdate": "2000-04-01", "drug": "Cetirizine Hydrochloride 10 MG Oral Tablet"},
    ],
    ("Linda", "Washington"): [
        {"title": "Furosemide 40mg", "begdate": "2018-12-05", "drug": "Furosemide 40 MG Oral Tablet"},
        {"title": "Carvedilol 12.5mg", "begdate": "2018-12-05", "drug": "Carvedilol 12.5 MG Oral Tablet"},
        {"title": "Insulin Lispro", "begdate": "2015-02-10", "drug": "Insulin Lispro 100 UNT/ML Injectable Solution"},
        {"title": "Levothyroxine 75mcg", "begdate": "2008-07-22", "drug": "Levothyroxine Sodium 0.075 MG Oral Tablet"},
        {"title": "Acetaminophen 500mg", "begdate": "2010-03-15", "drug": "Acetaminophen 500 MG Oral Tablet"},
        {"title": "Tiotropium Inhaler", "begdate": "2015-09-01", "drug": "Tiotropium Bromide 2.5 MCG/ACTUAT Inhalation Spray"},
    ],
    ("David", "Kowalski"): [
        {"title": "Bupropion 150mg", "begdate": "2019-02-18", "drug": "Bupropion Hydrochloride 150 MG Extended Release Oral Tablet"},
        {"title": "Ibuprofen 800mg", "begdate": "2022-08-10", "drug": "Ibuprofen 800 MG Oral Tablet"},
    ],
    ("Carmen", "Rivera"): [
        {"title": "Glipizide 5mg", "begdate": "2015-04-25", "drug": "Glipizide 5 MG Oral Tablet"},
        {"title": "Losartan 50mg", "begdate": "2016-06-12", "drug": "Losartan Potassium 50 MG Oral Tablet"},
    ],
    ("William", "O'Brien"): [
        {"title": "Hydrochlorothiazide 25mg", "begdate": "2005-02-14", "drug": "Hydrochlorothiazide 25 MG Oral Tablet"},
        {"title": "Tamsulosin 0.4mg", "begdate": "2018-11-20", "drug": "Tamsulosin Hydrochloride 0.4 MG Oral Capsule"},
        {"title": "Allopurinol 100mg", "begdate": "2020-03-07", "drug": "Allopurinol 100 MG Oral Tablet"},
    ],
    ("Fatima", "Al-Hassan"): [
        {"title": "Sumatriptan 50mg", "begdate": "2010-08-30", "drug": "Sumatriptan 50 MG Oral Tablet"},
        {"title": "Spironolactone 25mg", "begdate": "2012-05-14", "drug": "Spironolactone 25 MG Oral Tablet"},
    ],
    ("Marcus", "Johnson"): [
        {"title": "Loratadine 10mg", "begdate": "2015-04-01", "drug": "Loratadine 10 MG Oral Tablet"},
        {"title": "Amphetamine/Dextroamphetamine 20mg", "begdate": "2016-01-10", "drug": "Amphetamine Aspartate/Amphetamine Sulfate/Dextroamphetamine Saccharate/Dextroamphetamine Sulfate 20 MG Oral Tablet"},
    ],
    # ── Transplant patients ──
    ("Clara", "Reeves"): [
        {"title": "Epoetin alfa", "begdate": "2024-01-15", "drug": "Epoetin Alfa 10000 UNT/ML Injectable Solution"},
        {"title": "Sevelamer 800mg", "begdate": "2024-01-15", "drug": "Sevelamer Carbonate 800 MG Oral Tablet"},
        {"title": "Lisinopril 10mg", "begdate": "2023-06-10", "drug": "Lisinopril 10 MG Oral Tablet"},
    ],
    ("Marcus", "Blake"): [
        {"title": "Carvedilol 25mg", "begdate": "2022-03-20", "drug": "Carvedilol 25 MG Oral Tablet"},
        {"title": "Furosemide 40mg", "begdate": "2022-03-20", "drug": "Furosemide 40 MG Oral Tablet"},
        {"title": "Lisinopril 20mg", "begdate": "2021-11-05", "drug": "Lisinopril 20 MG Oral Tablet"},
    ],
    ("Diana", "Patel"): [
        {"title": "Lactulose", "begdate": "2022-01-20", "drug": "Lactulose 10 GM/15 ML Oral Solution"},
        {"title": "Spironolactone 100mg", "begdate": "2021-06-15", "drug": "Spironolactone 100 MG Oral Tablet"},
        {"title": "Propranolol 40mg", "begdate": "2020-08-12", "drug": "Propranolol Hydrochloride 40 MG Oral Tablet"},
    ],
    ("Robert", "Chen-Ramirez"): [
        {"title": "Insulin Glargine", "begdate": "2018-05-01", "drug": "Insulin Glargine 100 UNT/ML Injectable Solution"},
        {"title": "Metoprolol 50mg", "begdate": "2022-05-18", "drug": "Metoprolol Tartrate 50 MG Oral Tablet"},
        {"title": "Amlodipine 10mg", "begdate": "2016-10-12", "drug": "Amlodipine 10 MG Oral Tablet"},
        {"title": "Atorvastatin 40mg", "begdate": "2017-03-15", "drug": "Atorvastatin 40 MG Oral Tablet"},
        {"title": "Furosemide 20mg", "begdate": "2023-09-01", "drug": "Furosemide 20 MG Oral Tablet"},
    ],
    ("Angela", "Torres"): [
        {"title": "Pirfenidone 801mg", "begdate": "2021-04-22", "drug": "Pirfenidone 267 MG Oral Capsule"},
        {"title": "Albuterol Inhaler", "begdate": "2022-06-01", "drug": "Albuterol 0.83 MG/ML Inhalation Solution"},
    ],
    # ── Donor patients ──
    ("Priya", "Sharma"): [
        {"title": "Cetirizine 10mg", "begdate": "2015-04-01", "drug": "Cetirizine Hydrochloride 10 MG Oral Tablet"},
    ],
    ("Tomás", "Herrera"): [
        {"title": "Albuterol Inhaler", "begdate": "2005-06-01", "drug": "Albuterol 0.83 MG/ML Inhalation Solution"},
    ],
    ("Gerald", "Franklin"): [
        {"title": "Amlodipine 5mg", "begdate": "2010-03-15", "drug": "Amlodipine 5 MG Oral Tablet"},
    ],
    ("Evelyn", "Matsuda"): [
        {"title": "Metformin 1000mg", "begdate": "2005-09-22", "drug": "Metformin Hydrochloride 1000 MG Oral Tablet"},
        {"title": "Losartan 50mg", "begdate": "2010-05-20", "drug": "Losartan Potassium 50 MG Oral Tablet"},
    ],
}

# Vitals are added per-encounter; these are the readings for the most recent visit
VITALS: dict[tuple[str, str], dict] = {
    ("Maria", "Garcia"): {"bps": "138", "bpd": "88", "weight": "172", "height": "63", "temperature": "98.4", "pulse": "78", "respiration": "16", "oxygen_saturation": "97"},
    ("James", "Thompson"): {"bps": "152", "bpd": "92", "weight": "210", "height": "70", "temperature": "98.2", "pulse": "88", "respiration": "18", "oxygen_saturation": "94"},
    ("Aisha", "Patel"): {"bps": "118", "bpd": "72", "weight": "128", "height": "64", "temperature": "98.6", "pulse": "68", "respiration": "14", "oxygen_saturation": "99"},
    ("Robert", "Chen"): {"bps": "124", "bpd": "78", "weight": "175", "height": "71", "temperature": "98.8", "pulse": "74", "respiration": "16", "oxygen_saturation": "96"},
    ("Linda", "Washington"): {"bps": "148", "bpd": "86", "weight": "155", "height": "62", "temperature": "97.8", "pulse": "82", "respiration": "20", "oxygen_saturation": "92"},
    ("David", "Kowalski"): {"bps": "122", "bpd": "76", "weight": "185", "height": "72", "temperature": "98.6", "pulse": "70", "respiration": "14", "oxygen_saturation": "98"},
    ("Carmen", "Rivera"): {"bps": "142", "bpd": "90", "weight": "198", "height": "65", "temperature": "98.4", "pulse": "80", "respiration": "16", "oxygen_saturation": "96"},
    ("William", "O'Brien"): {"bps": "136", "bpd": "84", "weight": "195", "height": "69", "temperature": "98.2", "pulse": "72", "respiration": "16", "oxygen_saturation": "97"},
    ("Fatima", "Al-Hassan"): {"bps": "116", "bpd": "70", "weight": "140", "height": "66", "temperature": "98.6", "pulse": "66", "respiration": "14", "oxygen_saturation": "99"},
    ("Marcus", "Johnson"): {"bps": "120", "bpd": "74", "weight": "168", "height": "73", "temperature": "98.4", "pulse": "72", "respiration": "14", "oxygen_saturation": "98"},
    # ── Transplant patients ──
    ("Clara", "Reeves"): {"bps": "134", "bpd": "82", "weight": "170", "height": "65", "temperature": "98.4", "pulse": "76", "respiration": "16", "oxygen_saturation": "97"},  # BMI ~28.3
    ("Marcus", "Blake"): {"bps": "148", "bpd": "94", "weight": "298", "height": "71", "temperature": "98.6", "pulse": "92", "respiration": "20", "oxygen_saturation": "93"},  # BMI ~41.6
    ("Diana", "Patel"): {"bps": "108", "bpd": "66", "weight": "148", "height": "64", "temperature": "97.8", "pulse": "84", "respiration": "18", "oxygen_saturation": "96"},  # BMI ~25.4
    ("Robert", "Chen-Ramirez"): {"bps": "156", "bpd": "96", "weight": "228", "height": "69", "temperature": "98.2", "pulse": "86", "respiration": "18", "oxygen_saturation": "95"},  # BMI ~33.7
    ("Angela", "Torres"): {"bps": "118", "bpd": "72", "weight": "138", "height": "66", "temperature": "98.0", "pulse": "94", "respiration": "22", "oxygen_saturation": "89"},  # BMI ~22.3, low O2
    # ── Donor patients ──
    ("Priya", "Sharma"): {"bps": "112", "bpd": "68", "weight": "130", "height": "64", "temperature": "98.6", "pulse": "64", "respiration": "14", "oxygen_saturation": "99"},  # BMI ~22.3, healthy
    ("Tomás", "Herrera"): {"bps": "118", "bpd": "74", "weight": "175", "height": "70", "temperature": "98.4", "pulse": "68", "respiration": "14", "oxygen_saturation": "99"},  # BMI ~25.1, healthy
    ("Gerald", "Franklin"): {"bps": "0", "bpd": "0", "weight": "195", "height": "72", "temperature": "96.5", "pulse": "0", "respiration": "0", "oxygen_saturation": "0"},  # deceased
    ("Evelyn", "Matsuda"): {"bps": "0", "bpd": "0", "weight": "145", "height": "62", "temperature": "96.2", "pulse": "0", "respiration": "0", "oxygen_saturation": "0"},  # deceased
}

# Encounter reason for each patient's office visit
ENCOUNTER_REASONS: dict[tuple[str, str], str] = {
    ("Maria", "Garcia"): "Follow-up for diabetes management and blood pressure check",
    ("James", "Thompson"): "Cardiology follow-up, INR check, and kidney function review",
    ("Aisha", "Patel"): "Anxiety follow-up and iron level recheck",
    ("Robert", "Chen"): "Asthma maintenance and GERD symptom review",
    ("Linda", "Washington"): "Heart failure follow-up, medication reconciliation",
    ("David", "Kowalski"): "Depression follow-up, back pain management",
    ("Carmen", "Rivera"): "Diabetes and hypertension quarterly check",
    ("William", "O'Brien"): "Hypertension follow-up, prostate symptom review",
    ("Fatima", "Al-Hassan"): "Migraine frequency assessment, PCOS follow-up",
    ("Marcus", "Johnson"): "ADHD medication review, allergy season check",
    # ── Transplant patients ──
    ("Clara", "Reeves"): "Transplant evaluation: kidney candidacy screening, dialysis follow-up",
    ("Marcus", "Blake"): "Heart failure follow-up, cardiology referral assessment",
    ("Diana", "Patel"): "Liver transplant workup: cirrhosis management, lab review",
    ("Robert", "Chen-Ramirez"): "Multi-organ evaluation: kidney transplant candidacy, cardiac function review",
    ("Angela", "Torres"): "Pulmonary fibrosis progression, transplant re-evaluation after sobriety milestone",
    # ── Donor patients ──
    ("Priya", "Sharma"): "Living kidney donor evaluation: pre-donation screening and labs",
    ("Tomás", "Herrera"): "Living liver donor evaluation: pre-donation hepatic function panel",
    ("Gerald", "Franklin"): "Deceased donor organ procurement: brain death after CVA, organ viability assessment",
    ("Evelyn", "Matsuda"): "Deceased donor organ procurement: cardiac arrest, organ viability assessment",
}

# ── Practitioners (providers) ───────────────────────────────────────────────

PRACTITIONERS = [
    {
        "title": "Dr.",
        "fname": "Sarah",
        "lname": "Martinez",
        "npi": "1234567890",
        "specialty": "Internal Medicine",
        "email": "smartinez@springfieldmed.example.com",
        "street": "100 Medical Center Drive",
        "city": "Springfield",
        "state": "MA",
        "zip": "01103",
        "phone": "(413) 555-1000",
        "username": "smartinez",
    },
    {
        "title": "Dr.",
        "fname": "Michael",
        "lname": "Nguyen",
        "npi": "2345678901",
        "specialty": "Cardiology",
        "email": "mnguyen@springfieldmed.example.com",
        "street": "100 Medical Center Drive",
        "city": "Springfield",
        "state": "MA",
        "zip": "01103",
        "phone": "(413) 555-1001",
        "username": "mnguyen",
    },
    {
        "title": "Dr.",
        "fname": "Rachel",
        "lname": "Kim",
        "npi": "3456789012",
        "specialty": "Psychiatry",
        "email": "rkim@springfieldmed.example.com",
        "street": "100 Medical Center Drive",
        "city": "Springfield",
        "state": "MA",
        "zip": "01103",
        "phone": "(413) 555-1002",
        "username": "rkim",
    },
    {
        "title": "Dr.",
        "fname": "Anthony",
        "lname": "Brooks",
        "npi": "4567890123",
        "specialty": "Pulmonology",
        "email": "abrooks@springfieldmed.example.com",
        "street": "100 Medical Center Drive",
        "city": "Springfield",
        "state": "MA",
        "zip": "01103",
        "phone": "(413) 555-1003",
        "username": "abrooks",
    },
    {
        "title": "NP",
        "fname": "Jennifer",
        "lname": "Walsh",
        "npi": "5678901234",
        "specialty": "Family Practice",
        "email": "jwalsh@springfieldmed.example.com",
        "street": "100 Medical Center Drive",
        "city": "Springfield",
        "state": "MA",
        "zip": "01103",
        "phone": "(413) 555-1004",
        "username": "jwalsh",
    },
]

# ── Insurance companies ─────────────────────────────────────────────────────

INSURANCE_COMPANIES = [
    {
        "name": "Blue Cross Blue Shield of Massachusetts",
        "line1": "101 Huntington Ave",
        "city": "Boston",
        "state": "MA",
        "zip": "02199",
        "country": "USA",
        "cms_id": "BCBS-MA",
    },
    {
        "name": "Aetna Health Plans",
        "line1": "151 Farmington Ave",
        "city": "Hartford",
        "state": "CT",
        "zip": "06156",
        "country": "USA",
        "cms_id": "AETNA",
    },
    {
        "name": "Medicare Part A and B",
        "line1": "7500 Security Blvd",
        "city": "Baltimore",
        "state": "MD",
        "zip": "21244",
        "country": "USA",
        "cms_id": "MEDICARE",
    },
    {
        "name": "MassHealth (Medicaid)",
        "line1": "1 Ashburton Place",
        "city": "Boston",
        "state": "MA",
        "zip": "02108",
        "country": "USA",
        "cms_id": "MASSHEALTH",
    },
]

# Insurance policies: maps (fname, lname) -> {insurance_company_name, policy fields}
# The insurance_company_name is resolved to an ID at runtime after companies are created.
INSURANCE_POLICIES: dict[tuple[str, str], dict] = {
    ("Maria", "Garcia"): {
        "insurance_company_name": "Blue Cross Blue Shield of Massachusetts",
        "plan_name": "BCBS HMO Blue",
        "policy_number": "BCB-88412961",
        "group_number": "GRP-40125",
        "subscriber_relationship": "self",
        "date": "2020-01-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("James", "Thompson"): {
        "insurance_company_name": "Medicare Part A and B",
        "plan_name": "Medicare Traditional",
        "policy_number": "1EG4-TE5-MK72",
        "group_number": "MEDICARE",
        "subscriber_relationship": "self",
        "date": "2020-11-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("Aisha", "Patel"): {
        "insurance_company_name": "Aetna Health Plans",
        "plan_name": "Aetna PPO Open Access",
        "policy_number": "AET-W5523187",
        "group_number": "GRP-87204",
        "subscriber_relationship": "self",
        "date": "2022-06-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("Robert", "Chen"): {
        "insurance_company_name": "Blue Cross Blue Shield of Massachusetts",
        "plan_name": "BCBS PPO Blue",
        "policy_number": "BCB-77301845",
        "group_number": "GRP-40125",
        "subscriber_relationship": "self",
        "date": "2019-03-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("Linda", "Washington"): {
        "insurance_company_name": "Medicare Part A and B",
        "plan_name": "Medicare Traditional",
        "policy_number": "1EG4-TE5-MK73",
        "group_number": "MEDICARE",
        "subscriber_relationship": "self",
        "date": "2010-09-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("David", "Kowalski"): {
        "insurance_company_name": "Aetna Health Plans",
        "plan_name": "Aetna HMO",
        "policy_number": "AET-K9917234",
        "group_number": "GRP-55182",
        "subscriber_relationship": "self",
        "date": "2023-01-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("Carmen", "Rivera"): {
        "insurance_company_name": "MassHealth (Medicaid)",
        "plan_name": "MassHealth Standard",
        "policy_number": "MH-60284173",
        "group_number": "MASSHEALTH",
        "subscriber_relationship": "self",
        "date": "2021-07-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("William", "O'Brien"): {
        "insurance_company_name": "Blue Cross Blue Shield of Massachusetts",
        "plan_name": "BCBS HMO Blue",
        "policy_number": "BCB-66209534",
        "group_number": "GRP-33018",
        "subscriber_relationship": "self",
        "date": "2018-01-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("Fatima", "Al-Hassan"): {
        "insurance_company_name": "Aetna Health Plans",
        "plan_name": "Aetna PPO Open Access",
        "policy_number": "AET-H3318290",
        "group_number": "GRP-87204",
        "subscriber_relationship": "self",
        "date": "2021-01-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("Marcus", "Johnson"): {
        "insurance_company_name": "MassHealth (Medicaid)",
        "plan_name": "MassHealth Standard",
        "policy_number": "MH-91057382",
        "group_number": "MASSHEALTH",
        "subscriber_relationship": "self",
        "date": "2022-09-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    # ── Transplant patients ──
    ("Clara", "Reeves"): {
        "insurance_company_name": "Medicare Part A and B",
        "plan_name": "Medicare ESRD",
        "policy_number": "1EG4-TE5-CR01",
        "group_number": "MEDICARE",
        "subscriber_relationship": "self",
        "date": "2023-06-10",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("Marcus", "Blake"): {
        "insurance_company_name": "Blue Cross Blue Shield of Massachusetts",
        "plan_name": "BCBS PPO Blue",
        "policy_number": "BCB-44718293",
        "group_number": "GRP-92015",
        "subscriber_relationship": "self",
        "date": "2021-01-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("Diana", "Patel"): {
        "insurance_company_name": "MassHealth (Medicaid)",
        "plan_name": "MassHealth Standard",
        "policy_number": "MH-72839104",
        "group_number": "MASSHEALTH",
        "subscriber_relationship": "self",
        "date": "2020-08-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("Robert", "Chen-Ramirez"): {
        "insurance_company_name": "Medicare Part A and B",
        "plan_name": "Medicare Traditional",
        "policy_number": "1EG4-TE5-RC02",
        "group_number": "MEDICARE",
        "subscriber_relationship": "self",
        "date": "2023-09-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
    ("Angela", "Torres"): {
        "insurance_company_name": "Aetna Health Plans",
        "plan_name": "Aetna PPO Open Access",
        "policy_number": "AET-T6629183",
        "group_number": "GRP-44021",
        "subscriber_relationship": "self",
        "date": "2022-01-01",
        "accept_assignment": "TRUE",
        "type": "primary",
    },
}

# ── Lab results for transplant patients ─────────────────────────────────────
# These are seeded via SQL (procedure_order → procedure_report → procedure_result)
# because OpenEMR has no REST API for creating lab results.
# LOINC codes match what transplant_screening.py and lab_results.py query.

TRANSPLANT_LABS: dict[tuple[str, str], list[dict]] = {
    # Clara Reeves — Kidney ELIGIBLE: eGFR 12, Cr 6.8
    ("Clara", "Reeves"): [
        {"loinc": "33914-3", "name": "eGFR", "value": "12", "unit": "mL/min", "range": ">60"},
        {"loinc": "2160-0", "name": "Creatinine", "value": "6.8", "unit": "mg/dL", "range": "0.6-1.2"},
        {"loinc": "718-7", "name": "Hemoglobin", "value": "9.8", "unit": "g/dL", "range": "12.0-16.0"},
        {"loinc": "1751-7", "name": "Albumin", "value": "3.5", "unit": "g/dL", "range": "3.4-5.4"},
    ],
    # Marcus Blake — Heart INELIGIBLE: LVEF 30%, BNP 850
    ("Marcus", "Blake"): [
        {"loinc": "10230-1", "name": "Ejection Fraction", "value": "30", "unit": "%", "range": "55-70"},
        {"loinc": "30934-4", "name": "BNP", "value": "850", "unit": "pg/mL", "range": "<100"},
        {"loinc": "718-7", "name": "Hemoglobin", "value": "13.2", "unit": "g/dL", "range": "13.5-17.5"},
        {"loinc": "1751-7", "name": "Albumin", "value": "3.8", "unit": "g/dL", "range": "3.4-5.4"},
    ],
    # Diana Patel — Liver INCOMPLETE: MELD ~22 (bilirubin 4.2, INR 1.8, Cr 1.4, Na 131)
    ("Diana", "Patel"): [
        {"loinc": "1975-2", "name": "Bilirubin Total", "value": "4.2", "unit": "mg/dL", "range": "0.1-1.2"},
        {"loinc": "6301-6", "name": "INR", "value": "1.8", "unit": "", "range": "0.8-1.2"},
        {"loinc": "2160-0", "name": "Creatinine", "value": "1.4", "unit": "mg/dL", "range": "0.6-1.2"},
        {"loinc": "2951-2", "name": "Sodium", "value": "131", "unit": "mEq/L", "range": "136-145"},
        {"loinc": "1751-7", "name": "Albumin", "value": "2.8", "unit": "g/dL", "range": "3.4-5.4"},
        {"loinc": "718-7", "name": "Hemoglobin", "value": "10.5", "unit": "g/dL", "range": "12.0-16.0"},
    ],
    # Robert Chen-Ramirez — Kidney+Heart: eGFR 18, LVEF 32%, HbA1c 7.8
    ("Robert", "Chen-Ramirez"): [
        {"loinc": "33914-3", "name": "eGFR", "value": "18", "unit": "mL/min", "range": ">60"},
        {"loinc": "2160-0", "name": "Creatinine", "value": "4.9", "unit": "mg/dL", "range": "0.6-1.2"},
        {"loinc": "10230-1", "name": "Ejection Fraction", "value": "32", "unit": "%", "range": "55-70"},
        {"loinc": "30934-4", "name": "BNP", "value": "620", "unit": "pg/mL", "range": "<100"},
        {"loinc": "718-7", "name": "Hemoglobin", "value": "10.8", "unit": "g/dL", "range": "13.5-17.5"},
        {"loinc": "1751-7", "name": "Albumin", "value": "3.2", "unit": "g/dL", "range": "3.4-5.4"},
    ],
    # Angela Torres — Lung ELIGIBLE WITH CONDITIONS: FEV1 22%
    ("Angela", "Torres"): [
        {"loinc": "19926-5", "name": "FEV1 % Predicted", "value": "22", "unit": "%", "range": ">80"},
        {"loinc": "20150-9", "name": "FEV1", "value": "0.68", "unit": "L", "range": ">2.0"},
        {"loinc": "718-7", "name": "Hemoglobin", "value": "14.1", "unit": "g/dL", "range": "12.0-16.0"},
        {"loinc": "1751-7", "name": "Albumin", "value": "3.9", "unit": "g/dL", "range": "3.4-5.4"},
    ],
}


# ── API helpers ─────────────────────────────────────────────────────────────

class Stats:
    def __init__(self):
        self.created = 0
        self.failed = 0
        self.skipped = 0

    def __str__(self):
        return f"{self.created} created, {self.failed} failed, {self.skipped} skipped"


async def api_post(client, path: str, data: dict, label: str, stats: Stats) -> dict | None:
    """POST to the OpenEMR API and return the response data, or None on failure."""
    try:
        resp = await client.post(path, json=data)
    except Exception as e:
        logger.error("  %s — request error: %s", label, e)
        stats.failed += 1
        return None

    if resp.status_code in (200, 201):
        body = resp.json()
        if body.get("validationErrors") or body.get("internalErrors"):
            logger.error("  %s — server errors: %s", label, json.dumps(body.get("validationErrors") or body.get("internalErrors")))
            stats.failed += 1
            return None
        result = body.get("data", body)
        stats.created += 1
        return result

    logger.error("  %s — HTTP %s: %s", label, resp.status_code, resp.text[:200])
    stats.failed += 1
    return None


async def get_facility_id(client) -> str | None:
    """Get the first facility ID from the system."""
    try:
        resp = await client.get(f"{API}/facility")
        if resp.status_code == 200:
            body = resp.json()
            facilities = body.get("data", [])
            if facilities:
                return facilities[0].get("id") or facilities[0].get("uuid")
    except Exception as e:
        logger.warning("Could not fetch facilities: %s", e)
    return None


def _generate_lab_sql(
    patient_pids: dict[tuple[str, str], str],
    encounters: dict[tuple[str, str], str],
    output_path: Path,
) -> None:
    """Generate SQL to insert lab results into the procedure_order chain.

    OpenEMR stores lab results in three linked tables:
      procedure_order (the lab order, linked to patient + encounter)
      procedure_report (the report container)
      procedure_result (individual LOINC-coded values)

    The FHIR Observation endpoint reads from procedure_result, so these
    inserts make the labs queryable via GET /fhir/Observation.
    """
    lines = [
        "-- Transplant patient lab results",
        "-- Generated by seed_clinical_data.py",
        "-- Run against your OpenEMR database to populate lab values.",
        "--",
        "-- These inserts create procedure_order → procedure_report → procedure_result",
        "-- records that the FHIR Observation endpoint can read.",
        "",
    ]

    lab_date = (date.today() - timedelta(days=14)).strftime("%Y-%m-%d 08:00:00")

    for key, pid in patient_pids.items():
        labs = TRANSPLANT_LABS.get(key)
        if not labs or not pid:
            continue

        eid = encounters.get(key, "0")
        fname, lname = key
        safe_lname = lname.replace("'", "''")

        lines.append(f"-- Lab results for {fname} {safe_lname} (pid={pid})")
        lines.append(f"SET @po_pid = {pid};")
        lines.append(f"SET @po_eid = {eid};")
        lines.append("")

        # Create procedure_order
        lines.append(
            f"INSERT INTO procedure_order "
            f"(uuid, provider_id, patient_id, encounter_id, date_ordered, "
            f"order_priority, order_status, procedure_order_type, activity) "
            f"VALUES "
            f"(UUID_TO_BIN(UUID()), 0, @po_pid, @po_eid, '{lab_date}', "
            f"'normal', 'complete', 'laboratory_test', 1);"
        )
        lines.append("SET @order_id = LAST_INSERT_ID();")
        lines.append("")

        # Create procedure_order_code (one entry for the panel)
        lines.append(
            f"INSERT INTO procedure_order_code "
            f"(procedure_order_id, procedure_order_seq, procedure_code, "
            f"procedure_name, procedure_source) "
            f"VALUES "
            f"(@order_id, 1, 'TRANSPLANT_PANEL', "
            f"'Transplant Evaluation Panel', '1');"
        )
        lines.append("")

        # Create procedure_report
        lines.append(
            f"INSERT INTO procedure_report "
            f"(uuid, procedure_order_id, procedure_order_seq, "
            f"date_collected, date_report, report_status, review_status) "
            f"VALUES "
            f"(UUID_TO_BIN(UUID()), @order_id, 1, "
            f"'{lab_date}', '{lab_date}', 'final', 'reviewed');"
        )
        lines.append("SET @report_id = LAST_INSERT_ID();")
        lines.append("")

        # Create procedure_result for each lab value
        for lab in labs:
            loinc = lab["loinc"]
            name = lab["name"].replace("'", "''")
            value = lab["value"]
            unit = lab["unit"]
            rng = lab["range"].replace("'", "''")
            # Determine abnormal flag
            abnormal = ""
            try:
                val_f = float(value)
                if rng.startswith(">"):
                    threshold = float(rng[1:])
                    if val_f < threshold:
                        abnormal = "low"
                elif rng.startswith("<"):
                    threshold = float(rng[1:])
                    if val_f > threshold:
                        abnormal = "high"
                elif "-" in rng:
                    parts = rng.split("-")
                    if len(parts) == 2:
                        low, high = float(parts[0]), float(parts[1])
                        if val_f < low:
                            abnormal = "low"
                        elif val_f > high:
                            abnormal = "high"
            except (ValueError, IndexError):
                pass

            lines.append(
                f"INSERT INTO procedure_result "
                f"(uuid, procedure_report_id, result_data_type, result_code, "
                f"result_text, date, units, result, `range`, abnormal, "
                f"result_status) "
                f"VALUES "
                f"(UUID_TO_BIN(UUID()), @report_id, 'N', '{loinc}', "
                f"'{name}', '{lab_date}', '{unit}', '{value}', '{rng}', "
                f"'{abnormal}', 'final');"
            )

        lines.append("")
        lines.append("")

    output_path.write_text("\n".join(lines))


# ── Main seeding logic ──────────────────────────────────────────────────────

async def seed(dry_run: bool = False, skip_patients: bool = False) -> None:
    auth = OpenEMRAuth()

    practitioner_stats = Stats()
    insurance_co_stats = Stats()
    patient_stats = Stats()
    allergy_stats = Stats()
    problem_stats = Stats()
    med_stats = Stats()
    encounter_stats = Stats()
    vital_stats = Stats()
    insurance_stats = Stats()

    async with auth.get_client() as client:
        # Get facility for encounters and practitioners
        facility_id = await get_facility_id(client)
        if facility_id:
            logger.info("Using facility ID: %s", facility_id)
        else:
            logger.warning("No facility found — encounters may fail")

        # ── 1. Create practitioners ───────────────────────────────────
        print("\n========================================")
        print("  STEP 1: Creating practitioners")
        print("========================================\n")

        for prac in PRACTITIONERS:
            label = f"Practitioner {prac['title']} {prac['fname']} {prac['lname']}"

            if dry_run:
                logger.info("  [DRY RUN] Would create %s", label)
                practitioner_stats.skipped += 1
                continue

            prac_data = dict(prac)
            if facility_id:
                prac_data["facility_id"] = facility_id
            result = await api_post(client, f"{API}/practitioner", prac_data, label, practitioner_stats)
            if result:
                logger.info("  Created %s (id=%s, uuid=%s)", label, result.get("id", "?"), result.get("uuid", "?"))

        # ── 2. Create insurance companies ─────────────────────────────
        print("\n========================================")
        print("  STEP 2: Creating insurance companies")
        print("========================================\n")

        # Map company name -> company ID for linking policies later
        insurance_company_ids: dict[str, str] = {}

        for company in INSURANCE_COMPANIES:
            label = f"Insurance company '{company['name']}'"

            if dry_run:
                logger.info("  [DRY RUN] Would create %s", label)
                insurance_co_stats.skipped += 1
                continue

            result = await api_post(client, f"{API}/insurance_company", company, label, insurance_co_stats)
            if result:
                co_id = result.get("id") or result.get("uuid")
                if co_id:
                    insurance_company_ids[company["name"]] = str(co_id)
                logger.info("  Created %s (id=%s)", label, co_id or "?")

        # Track created patients: (fname, lname) -> {pid, uuid}
        created: dict[tuple[str, str], dict] = {}

        # ── 3. Create patients ──────────────────────────────────────────
        if not skip_patients:
            print("\n========================================")
            print("  STEP 3: Creating patients")
            print("========================================\n")

            all_patients = PATIENTS + TRANSPLANT_PATIENTS + DONOR_PATIENTS
            for p in all_patients:
                key = (p["fname"], p["lname"])
                label = f"Patient {p['fname']} {p['lname']}"

                if dry_run:
                    logger.info("  [DRY RUN] Would create %s", label)
                    patient_stats.skipped += 1
                    continue

                result = await api_post(client, f"{API}/patient", p, label, patient_stats)
                if result:
                    created[key] = result
                    logger.info("  Created %s (pid=%s, uuid=%s)", label, result.get("pid", "?"), result.get("uuid", "?"))
        else:
            # Look up existing patients by name
            print("\n========================================")
            print("  STEP 3: Looking up existing patients")
            print("========================================\n")

            all_patients = PATIENTS + TRANSPLANT_PATIENTS + DONOR_PATIENTS
            for p in all_patients:
                key = (p["fname"], p["lname"])
                try:
                    resp = await client.get(f"{API}/patient", params={"fname": p["fname"], "lname": p["lname"]})
                    if resp.status_code == 200:
                        body = resp.json()
                        patients = body.get("data", [])
                        if patients:
                            created[key] = patients[0]
                            logger.info("  Found %s %s (pid=%s)", p["fname"], p["lname"], patients[0].get("pid", "?"))
                        else:
                            logger.warning("  Not found: %s %s — skipping clinical data", p["fname"], p["lname"])
                except Exception as e:
                    logger.error("  Error looking up %s %s: %s", p["fname"], p["lname"], e)

        if dry_run:
            print("\n[DRY RUN] Would create clinical data for all patients.")
            print("Re-run without --dry-run to execute.\n")
            return

        if not created:
            print("\nNo patients available. Nothing to seed.")
            return

        # ── 4. Create encounters (one per patient) ──────────────────────
        print("\n========================================")
        print("  STEP 4: Creating encounters")
        print("========================================\n")

        # Map (fname, lname) -> encounter ID
        encounters: dict[tuple[str, str], str] = {}

        for key, pdata in created.items():
            puuid = pdata.get("uuid")
            if not puuid:
                logger.warning("  No UUID for %s %s — skipping encounter", *key)
                continue

            reason = ENCOUNTER_REASONS.get(key, "Routine office visit")
            encounter_data = {
                "date": (date.today() - timedelta(days=14)).isoformat(),
                "reason": reason,
                "class_code": "AMB",
                "sensitivity": "normal",
            }
            if facility_id:
                encounter_data["facility_id"] = facility_id
                encounter_data["billing_facility"] = facility_id

            label = f"Encounter for {key[0]} {key[1]}"
            result = await api_post(client, f"{API}/patient/{puuid}/encounter", encounter_data, label, encounter_stats)
            if result:
                eid = result.get("encounter") or result.get("eid") or result.get("uuid")
                encounters[key] = str(eid)
                logger.info("  %s (eid=%s)", label, eid)

        # ── 5. Add vitals to encounters ─────────────────────────────────
        print("\n========================================")
        print("  STEP 5: Adding vitals")
        print("========================================\n")

        for key, pdata in created.items():
            puuid = pdata.get("uuid")
            eid = encounters.get(key)
            if not puuid or not eid:
                logger.warning("  Skipping vitals for %s %s — no encounter", *key)
                vital_stats.skipped += 1
                continue

            vitals = VITALS.get(key)
            if not vitals:
                continue

            label = f"Vitals for {key[0]} {key[1]}"
            await api_post(client, f"{API}/patient/{puuid}/encounter/{eid}/vital", vitals, label, vital_stats)

        # ── 6. Add medical problems ─────────────────────────────────────
        print("\n========================================")
        print("  STEP 6: Adding medical problems")
        print("========================================\n")

        for key, pdata in created.items():
            puuid = pdata.get("uuid")
            if not puuid:
                continue

            problems = MEDICAL_PROBLEMS.get(key, [])
            for prob in problems:
                label = f"Problem '{prob['title']}' for {key[0]} {key[1]}"
                await api_post(client, f"{API}/patient/{puuid}/medical_problem", prob, label, problem_stats)

        # ── 7. Add allergies ────────────────────────────────────────────
        print("\n========================================")
        print("  STEP 7: Adding allergies")
        print("========================================\n")

        for key, pdata in created.items():
            puuid = pdata.get("uuid")
            if not puuid:
                continue

            allergies = ALLERGIES.get(key, [])
            if not allergies:
                logger.info("  %s %s — NKDA (no known drug allergies)", *key)
                allergy_stats.skipped += 1
                continue

            for allergy in allergies:
                label = f"Allergy '{allergy['title']}' for {key[0]} {key[1]}"
                await api_post(client, f"{API}/patient/{puuid}/allergy", allergy, label, allergy_stats)

        # ── 8. Add medications ──────────────────────────────────────────
        print("\n========================================")
        print("  STEP 8: Adding medications")
        print("========================================\n")

        for key, pdata in created.items():
            puuid = pdata.get("uuid")
            if not puuid:
                continue

            meds = MEDICATIONS.get(key, [])
            for med in meds:
                label = f"Medication '{med['title']}' for {key[0]} {key[1]}"
                await api_post(client, f"{API}/patient/{puuid}/medication", med, label, med_stats)

        # ── 9. Add insurance policies ──────────────────────────────────
        print("\n========================================")
        print("  STEP 9: Adding insurance policies")
        print("========================================\n")

        for key, pdata in created.items():
            puuid = pdata.get("uuid")
            if not puuid:
                continue

            policy_template = INSURANCE_POLICIES.get(key)
            if not policy_template:
                logger.info("  %s %s — no insurance policy defined", *key)
                insurance_stats.skipped += 1
                continue

            # Resolve insurance company name to ID
            co_name = policy_template.get("insurance_company_name", "")
            co_id = insurance_company_ids.get(co_name)
            if not co_id:
                logger.warning("  %s %s — insurance company '%s' not found, skipping", *key, co_name)
                insurance_stats.failed += 1
                continue

            # Build the policy payload with subscriber info from patient data
            patient_info = pdata
            policy = {
                "provider": co_id,
                "plan_name": policy_template.get("plan_name", ""),
                "policy_number": policy_template.get("policy_number", ""),
                "group_number": policy_template.get("group_number", ""),
                "subscriber_lname": patient_info.get("lname", key[1]),
                "subscriber_fname": patient_info.get("fname", key[0]),
                "subscriber_relationship": policy_template.get("subscriber_relationship", "self"),
                "subscriber_DOB": patient_info.get("DOB", ""),
                "subscriber_street": patient_info.get("street", ""),
                "subscriber_city": patient_info.get("city", ""),
                "subscriber_state": patient_info.get("state", ""),
                "subscriber_postal_code": patient_info.get("postal_code", ""),
                "subscriber_sex": patient_info.get("sex", ""),
                "date": policy_template.get("date", ""),
                "accept_assignment": policy_template.get("accept_assignment", "TRUE"),
                "type": policy_template.get("type", "primary"),
            }

            label = f"Insurance '{policy_template.get('plan_name')}' for {key[0]} {key[1]}"
            await api_post(client, f"{API}/patient/{puuid}/insurance", policy, label, insurance_stats)

    # ── 10. Generate lab results SQL for transplant patients ────────
    # OpenEMR has no REST API for creating lab results — they live in the
    # procedure_order → procedure_report → procedure_result chain.
    # We generate a SQL file that can be run against the database.

    transplant_pids: dict[tuple[str, str], str] = {}
    for key in TRANSPLANT_LABS:
        pdata = created.get(key)
        if pdata:
            transplant_pids[key] = str(pdata.get("pid", ""))

    if transplant_pids and not dry_run:
        print("\n========================================")
        print("  STEP 10: Generating lab results SQL")
        print("========================================\n")

        sql_path = Path(__file__).resolve().parent / "seed_transplant_labs.sql"
        _generate_lab_sql(transplant_pids, encounters, sql_path)
        print(f"  Generated: {sql_path}")
        print()
        print("  To load lab results, run this SQL against your OpenEMR database:")
        print(f"    mysql -u root -p openemr < {sql_path}")
        print()
        print("  Or via Docker:")
        print("    docker exec -i <container> mysql -u root --password=root openemr < seed_transplant_labs.sql")
        print()
        print("  Or via production Docker Compose:")
        print("    docker compose -f docker-compose.prod.yml exec -T mariadb mysql -u root -p$MYSQL_ROOT_PASSWORD openemr < seed_transplant_labs.sql")
        print()

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n========================================")
    print("  SEEDING COMPLETE")
    print("========================================\n")
    print(f"  Practitioners:      {practitioner_stats}")
    print(f"  Insurance Companies:{insurance_co_stats}")
    print(f"  Patients:           {patient_stats}")
    print(f"  Encounters:         {encounter_stats}")
    print(f"  Vitals:             {vital_stats}")
    print(f"  Medical Problems:   {problem_stats}")
    print(f"  Allergies:          {allergy_stats}")
    print(f"  Medications:        {med_stats}")
    print(f"  Insurance Policies: {insurance_stats}")
    if transplant_pids:
        n_labs = sum(len(TRANSPLANT_LABS.get(k, [])) for k in transplant_pids)
        print(f"  Lab Results (SQL):  {n_labs} values for {len(transplant_pids)} transplant patients")
    print()

    if created:
        print("Seeded patients:")
        for (fname, lname), data in created.items():
            pid = data.get("pid", "?")
            n_problems = len(MEDICAL_PROBLEMS.get((fname, lname), []))
            n_allergies = len(ALLERGIES.get((fname, lname), []))
            n_meds = len(MEDICATIONS.get((fname, lname), []))
            ins = INSURANCE_POLICIES.get((fname, lname), {}).get("plan_name", "(none)")
            n_labs = len(TRANSPLANT_LABS.get((fname, lname), []))
            lab_str = f", {n_labs} labs" if n_labs else ""
            print(f"  {fname} {lname} (pid={pid}) — {n_problems} problems, {n_allergies} allergies, {n_meds} meds, ins: {ins}{lab_str}")
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Seed OpenEMR with clinical data")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be created without making changes")
    parser.add_argument("--patients", type=int, default=10, help="Number of patients to create (0 = skip, use existing)")
    args = parser.parse_args()

    asyncio.run(seed(dry_run=args.dry_run, skip_patients=(args.patients == 0)))


if __name__ == "__main__":
    main()
