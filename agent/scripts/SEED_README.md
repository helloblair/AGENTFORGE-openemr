# Seeding Clinical Data into OpenEMR

This script creates practitioners, insurance companies, and 10 patients with full medical profiles (conditions, allergies, medications, vitals, encounters, insurance policies) via the OpenEMR REST API.

## Prerequisites

1. **Python 3.10+** with `httpx` and `python-dotenv` (already in `agent/requirements.txt`)
2. **OAuth2 client with write scopes** registered and enabled on your OpenEMR instance

## One-time Setup: Register an OAuth2 Client with Write Scopes

Your existing OAuth2 client likely has read-only scopes. The seeding script needs write access. You have two options:

### Option A: Re-register a new client (recommended)

```bash
# From the agent/ directory
python -m scripts.register_seed_client
```

This will print a new `client_id` and `client_secret`. Then:

1. Log into OpenEMR as admin
2. Go to **Administration > System > API Clients**
3. Find the new client and click **Enable**
4. Update `agent/.env` with the new credentials (or set env vars)

### Option B: Manually update scopes on existing client

In the OpenEMR admin UI, edit your existing API client and add these scopes:

```
user/patient.write user/allergy.write user/medical_problem.write
user/medication.write user/encounter.write user/vital.write
user/practitioner.write user/insurance.write user/insurance_company.write
```

## Running the Seed Script

```bash
cd agent/

# Preview what will be created (no changes made)
python -m scripts.seed_clinical_data --dry-run

# Seed all 10 patients with full clinical data
python -m scripts.seed_clinical_data

# Skip patient creation, only add clinical data to existing patients
python -m scripts.seed_clinical_data --patients 0
```

## What Gets Created

| Resource | Count | Details |
|----------|-------|---------|
| Practitioners | 5 | Internal med, cardiology, psychiatry, pulmonology, family practice |
| Insurance Companies | 4 | BCBS MA, Aetna, Medicare, MassHealth |
| Patients | 10 | Diverse demographics (age 27-80, race, ethnicity) |
| Encounters | 10 | One office visit per patient (2 weeks ago) |
| Vitals | 10 | BP, weight, height, temp, pulse, O2 sat |
| Medical Problems | 30+ | Diabetes, HTN, CAD, asthma, depression, etc. |
| Allergies | 18 | Drug allergies with reactions + 1 NKDA patient |
| Medications | 29 | Matching conditions (metformin for DM, etc.) |
| Insurance Policies | 10 | One primary policy per patient |

### Practitioners

| Name | Specialty | NPI |
|------|-----------|-----|
| Dr. Sarah Martinez | Internal Medicine | 1234567890 |
| Dr. Michael Nguyen | Cardiology | 2345678901 |
| Dr. Rachel Kim | Psychiatry | 3456789012 |
| Dr. Anthony Brooks | Pulmonology | 4567890123 |
| NP Jennifer Walsh | Family Practice | 5678901234 |

### Patient Profiles

| Patient | Age | Key Conditions | Allergies | Insurance |
|---------|-----|----------------|-----------|-----------|
| Maria Garcia | 57 | T2DM, HTN, Hyperlipidemia | Penicillin, Sulfa drugs | BCBS HMO Blue |
| James Thompson | 70 | CAD, T2DM, CKD3, AFib | Aspirin, Ibuprofen, Shellfish | Medicare |
| Aisha Patel | 33 | Anxiety, Iron-deficiency anemia | Latex | Aetna PPO |
| Robert Chen | 47 | Asthma, GERD, Allergic rhinitis | Amoxicillin | BCBS PPO Blue |
| Linda Washington | 80 | CHF, T2DM, OA, COPD, HTN | Codeine, ACE inhibitors, Peanuts | Medicare |
| David Kowalski | 37 | Depression, Lumbar disc herniation | Ciprofloxacin | Aetna HMO |
| Carmen Rivera | 52 | T2DM, Obesity, Sleep apnea, HTN | Metformin | MassHealth |
| William O'Brien | 65 | HTN, BPH, Gout | Statins, Bee stings | BCBS HMO Blue |
| Fatima Al-Hassan | 40 | Migraines, PCOS | NKDA | Aetna PPO |
| Marcus Johnson | 27 | Allergic rhinitis, ADHD | Erythromycin | MassHealth |

## Extending for New Tools

The script's docstring contains a step-by-step guide for adding new data types. The pattern is always:

1. Add a data dict keyed by `(fname, lname)`
2. Add a step in `seed()` that calls `api_post()` with the right endpoint
3. Add the stats to the summary

See the top of `seed_clinical_data.py` for the full guide and a list of all available API endpoints.

## Using Synthea Instead (Alternative)

For larger datasets or more detailed medical histories, you can use Synthea:

```bash
# Install Synthea (requires Java JDK)
git clone https://github.com/synthetichealth/synthea.git
cd synthea && ./gradlew build

# Generate 20 patients with deterministic seed
java -jar build/libs/synthea-with-dependencies.jar \
  -p 20 -s 42 --exporter.ccda.export=true Massachusetts

# Then import the CCDAs into OpenEMR (inside the container):
OPENEMR_ENABLE_CCDA_IMPORT=1 php /var/www/localhost/htdocs/openemr/contrib/util/ccda_import/import_ccda.php \
  --sourcePath=/path/to/synthea/output/ccda \
  --site=default \
  --openemrPath=/var/www/localhost/htdocs/openemr \
  --isDev=true
```

## Troubleshooting

- **401 Unauthorized**: Your OAuth2 client doesn't have write scopes. Re-register (see setup above).
- **400 Bad Request**: Check the OpenEMR PHP error log for details.
- **Duplicate patients**: The script doesn't check for existing patients before creating. Run `--patients 0` to add clinical data to existing patients only.
