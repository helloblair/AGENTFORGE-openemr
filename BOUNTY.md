# Bounty: Organ Transplant Candidacy Screening

## Customer

A regional transplant center using OpenEMR needs automated transplant candidacy screening integrated into their clinical workflow. Clinicians currently perform manual chart reviews to determine if patients meet referral criteria for kidney, liver, heart, or lung transplant — a process that takes 30-60 minutes per patient and risks missing qualifying candidates.

## Feature Summary

An AI-powered transplant candidacy screening system that:

1. **Integrates the CMS ICD-10-CM FY2026 code set** as an external data source, filtered to 2,475 transplant-relevant diagnostic codes across kidney, heart, lung, liver, and general categories.

2. **Implements OPTN/UNOS clinical thresholds** for four organ types:
   - **Kidney**: eGFR < 20 mL/min/1.73m² (CKD staging)
   - **Liver**: MELD score >= 15 (with MELD-Na correction)
   - **Heart**: NYHA Class III+ or Ejection Fraction < 25%
   - **Lung**: FEV1 < 25% predicted

3. **Screens contraindications** against ICD-10 prefix ranges: active substance abuse (F10-F19), malignancy (C00-C96), obesity (E66), and psychiatric disorders (F20-F29).

4. **Generates comprehensive candidacy reports** with clinical scores, missing data alerts, contraindication flags (absolute/relative), organ-specific next steps, and a mandatory screening disclaimer.

## Data Source

**ICD-10-CM FY2026** — The official diagnosis code set maintained by the Centers for Medicare & Medicaid Services (CMS), effective October 1, 2025.

- **Source URL**: https://www.cms.gov/files/zip/2026-code-descriptions-tabular-order.zip
- **Format**: Fixed-width text file within ZIP archive
- **Total codes in dataset**: ~74,000+
- **Transplant-relevant codes extracted**: 2,475
- **Code categories**: Qualifying diagnoses, transplant status, complications, contraindications, screening indicators
- **Organ systems covered**: Kidney (20 codes), Heart (119 codes), Lung (55 codes), Liver (33 codes), General (2,248 codes)

## Technical Implementation

### Full-Stack Integration

| Layer | Components | Files |
|-------|-----------|-------|
| Data Pipeline | CMS ICD-10 downloader/parser | `agent/scripts/parse_icd10.py` |
| Reference Data | OPTN criteria JSON, ICD-10 CSV/JSON | `agent/data/` (3 files) |
| Database | 3 MySQL tables (InnoDB, FK to patient_data) | `agent/sql/transplant_schema.sql` |
| PHP REST API | 2 Services, 2 Controllers, 7 Routes | `src/Services/`, `src/RestControllers/` |
| Agent Tools | 3 new @tools, 3 support modules | `agent/src/tools/` (6 files) |
| Tool Schemas | 6 tool definitions | `agent/data/transplant_tools_schema.json` |
| Evaluation | 19 new test cases (71 total) | `agent/eval/test_cases.yaml` |
| Seed Data | 5 transplant demo patients with labs | `agent/scripts/seed_clinical_data.py` |

### New Agent Tools

| Tool | Type | Purpose |
|------|------|---------|
| `lab_results` | @tool | FHIR Observation retrieval (creatinine, eGFR, bilirubin, INR, etc.) |
| `transplant_criteria_lookup` | @tool | Query ICD-10 reference data via REST API |
| `transplant_screening` | @tool | Full candidacy evaluation orchestrator |

### OpenEMR REST API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/transplant_criteria` | List ICD-10 transplant criteria |
| GET | `/api/transplant_criteria/:code` | Look up specific ICD-10 code |
| POST | `/api/patient/:puuid/transplant_screening` | Create screening record |
| GET | `/api/patient/:puuid/transplant_screening` | List patient screenings |
| GET | `/api/patient/:puuid/transplant_screening/:sid` | Get specific screening |
| PUT | `/api/patient/:puuid/transplant_screening/:sid` | Update screening |
| DELETE | `/api/patient/:puuid/transplant_screening/:sid` | Delete screening |

## Impact

- **Reduces screening time** from 30-60 minutes to under 2 minutes per patient
- **Prevents missed referrals** by systematically checking all qualifying diagnoses against OPTN thresholds
- **Standardizes the screening process** with consistent clinical scoring algorithms (MELD, eGFR, NYHA/EF, FEV1)
- **Flags contraindications early** to avoid unnecessary referrals
- **Identifies missing data** so clinicians know exactly which labs/evaluations to order
- **Maintains safety guardrails** with mandatory screening disclaimers and clinical decision support framing
- **Expands the agent from 7 to 10 tools**, adding lab results retrieval and transplant-specific capabilities
- **Grows the eval suite from 52 to 71 test cases** with zero regression on existing tests
- **Ships with 5 transplant demo patients** (Clara Reeves/kidney, Marcus Blake/heart, Diana Patel/liver, Robert Chen-Ramirez/kidney+heart, Angela Torres/lung) seeded via REST API with full clinical profiles and lab results

## Deployment Checklist

```bash
# 1. Create transplant database tables
mysql -u openemr -p openemr < agent/sql/transplant_schema.sql

# 2. Load ICD-10 reference data and OPTN criteria
python agent/scripts/load_transplant_data.py

# 3. Register OAuth2 client with transplant scopes (if not already done)
python -m scripts.register_seed_client

# 4. Seed transplant demo patients and lab results
python -m scripts.seed_clinical_data
docker exec -i <container> mysql -u root --password=root openemr < agent/scripts/seed_transplant_labs.sql

# 5. Verify endpoints respond
curl -H "Authorization: Bearer $TOKEN" https://<host>/apis/default/api/transplant_criteria?organ_system=kidney
```
