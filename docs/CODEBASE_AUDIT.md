# Codebase Audit — AgentForge
> Living map of the codebase. Updated with every significant change.
> Organized by component. Check Status field for current state.

## Observability / Langfuse Tracing (updated 2026-02-26)

**Location:** `agent/src/observability/tracing.py`, `agent/src/config.py`
**Purpose:** Sends OpenTelemetry traces to Langfuse for every agent request — LLM calls, tool invocations, chain steps. Provides user feedback scoring via Langfuse REST API.
**Dependencies:** `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `httpx`, `langchain-core` (BaseCallbackHandler)
**Exposes:** `init_tracing()`, `create_langfuse_handler()`, `log_feedback()`, `LangfuseOtelHandler` class
**Status:** working — integration tested 2026-02-26
**Notes:** Uses pure OTEL + Langfuse REST API instead of the `langfuse` Python SDK, which is broken on Python 3.14 (pydantic v1 incompatibility). Tracing is a no-op when `LANGFUSE_SECRET_KEY`/`LANGFUSE_PUBLIC_KEY` env vars are empty. Feedback endpoint at `POST /feedback` accepts `{trace_id, score, comment}`.

## Tools / medication_list (updated 2026-02-26)

**Location:** `agent/src/tools/medication_list.py`
**Purpose:** Retrieves a patient's active medications from OpenEMR via the FHIR `MedicationRequest` endpoint. Parses drug name, dosage, frequency, route, prescriber, start date, and status from FHIR resources.
**Dependencies:** `httpx`, `langchain-core` (@tool decorator), `src.auth.oauth2.OpenEMRAuth`
**Exposes:** `medication_list` async tool function (LangChain-compatible)
**Status:** working — integration tested 2026-02-26
**Notes:** Requires `user/MedicationRequest.read` OAuth scope (added to default scopes in `config.py`). Same auth/retry pattern as `allergy_check`. Registered in `tools/__init__.py` and wired into the ReAct agent in `graph.py`. Returns human-readable formatted string. Handles empty bundles with "No active medications documented" message.

## Tools / problem_list (updated 2026-02-26)

**Location:** `agent/src/tools/problem_list.py`
**Purpose:** Retrieves a patient's active conditions / problem list from OpenEMR via the FHIR `Condition` endpoint. Parses condition name, ICD-10 code, onset date, clinical status, and category from FHIR resources.
**Dependencies:** `httpx`, `langchain-core` (@tool decorator), `src.auth.oauth2.OpenEMRAuth`
**Exposes:** `problem_list` async tool function (LangChain-compatible)
**Status:** working — integration tested 2026-02-26
**Notes:** Requires `user/Condition.read` OAuth scope (added to default scopes in `config.py`). Same auth/retry pattern as `medication_list`. Registered in `tools/__init__.py` and wired into the ReAct agent in `graph.py`. Returns human-readable formatted string. Handles empty bundles with "No active conditions documented" message. ICD-10 code extraction looks for coding systems containing "icd10" or "icd-10", falls back to first coding code.

## Tools / provider_lookup (updated 2026-02-26)

**Location:** `agent/src/tools/provider_lookup.py`
**Purpose:** Searches for providers/practitioners in OpenEMR by name and/or specialty. Uses the FHIR `Practitioner` endpoint for lookup with client-side name filtering and optionally enriches with FHIR `PractitionerRole` for specialty data.
**Dependencies:** `httpx`, `langchain-core` (@tool decorator), `src.auth.oauth2.OpenEMRAuth`
**Exposes:** `provider_lookup` async tool function (LangChain-compatible)
**Status:** working — integration tested 2026-02-26
**Notes:** Requires `user/Practitioner.read` and `user/PractitionerRole.read` OAuth scopes. Originally used REST `/api/practitioner` but switched to FHIR `/Practitioner` because the REST endpoint returns 401 on this deployment (requires admin ACL beyond OAuth scopes). FHIR `?name=` search triggers a SQL error, so all practitioners are fetched and filtered client-side. PractitionerRole is queried for specialty enrichment only when needed. Returns first 10 results when no filters provided (directory listing). Registered in `tools/__init__.py` and wired into the ReAct agent in `graph.py`.

## Tools / insurance_coverage (updated 2026-02-26)

**Location:** `agent/src/tools/insurance_coverage.py`
**Purpose:** Retrieves a patient's insurance coverage from OpenEMR via the FHIR `Coverage` endpoint. Parses plan name, insurer, policy number, coverage type, effective dates, status, and subscriber relationship from FHIR resources. Separates active from expired coverages.
**Dependencies:** `httpx`, `langchain-core` (@tool decorator), `src.auth.oauth2.OpenEMRAuth`
**Exposes:** `insurance_coverage` async tool function (LangChain-compatible)
**Status:** working — integration tested 2026-02-26
**Notes:** Requires `user/Coverage.read` OAuth scope (added to default scopes in `config.py`). Same auth/retry pattern as other FHIR tools. Parses FHIR Coverage `class` array for plan/group names, `payor` for insurer, `subscriberId` for policy numbers, `period` for effective dates. Expired coverage detection via ISO date comparison. Registered in `tools/__init__.py` and wired into the ReAct agent in `graph.py`. Returns human-readable formatted string with active/expired sections. Handles no-insurance-on-file with descriptive message.

## Verification / scope_guard (updated 2026-02-26)

**Location:** `agent/src/verification/scope_guard.py`
**Purpose:** Pre-processing step that classifies user input before it reaches the agent. Blocks diagnosis/treatment requests, allows data retrieval and clinical support queries.
**Dependencies:** `re` (stdlib only)
**Exposes:** `classify_input()`, `apply_scope_guard()`
**Status:** working — integration tested 2026-02-26
**Notes:** Keyword-based classification (MVP). Added `condition`, `conditions`, `problem`, `problems` to clinical support keywords and `insurance`, `coverage`, `check`, `what` to data retrieval keywords to support problem_list and insurance_coverage tool queries. Order matters: blocked categories (diagnosis, treatment) checked before allowed categories (clinical support, data retrieval).

## Verification / drug_safety (updated 2026-02-26)

**Location:** `agent/src/verification/drug_safety.py`
**Purpose:** Post-processing step that cross-references medications against patient allergies after agent tool calls. Detects direct matches and cross-reactivity (penicillin→amoxicillin, sulfa→bactrim, NSAID→ibuprofen, codeine→hydrocodone, cephalosporin→cephalexin). Prepends WARNING block if conflict found. Also manages the "not medical advice" clinical data disclaimer for all clinical tool responses.
**Dependencies:** `re`, `logging` (stdlib only). Called from `graph.py` post_process node; may trigger inline `allergy_check` tool invocation if allergy data is missing from conversation.
**Exposes:** `check_drug_safety()`, `find_conflicts()`, `format_warning()`, `should_add_clinical_disclaimer()`, `extract_medications_from_messages()`, `extract_allergies_from_messages()`, `CLINICAL_DATA_DISCLAIMER`, `MEDICATION_TOOLS`, `CLINICAL_DATA_TOOLS`, `CROSS_REACTIVITY`
**Status:** working — 24 unit tests passing
**Notes:** Cross-reactivity map is a curated MVP (6 drug classes). Production would use RxNorm/RxClass API for class membership. Medication parsing requires "active medication" header to avoid false matches from allergy text. The `_post_process_node` in graph.py replaced the old `_append_disclaimer` node and handles drug safety + both disclaimers in one pass. Inline allergy fetch uses concurrent.futures ThreadPoolExecutor to work inside LangGraph's sync node callbacks.

## Integration Test Summary (2026-02-26)

All 7 tools verified end-to-end through the agent graph:
- **patient_lookup**: working
- **allergy_check**: working
- **medication_list**: working
- **problem_list**: working
- **provider_lookup**: working (fixed: REST→FHIR)
- **insurance_coverage**: working
- **drug_interaction_check**: working
- **Multi-tool chaining**: working (patient_lookup → follow-up tools)
- **Scope guard**: working (blocks diagnosis/treatment, allows clinical/data queries)
