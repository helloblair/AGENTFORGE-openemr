# Codebase Audit — AgentForge
> Living map of the codebase. Updated with every significant change.
> Organized by component. Check Status field for current state.

## Deployment / Railway — FastAPI Agent Service (updated 2026-02-27)

**Location:** `agent/Dockerfile`, `agent/railway.toml`, `agent/pyproject.toml`
**Purpose:** Packages the FastAPI agent as a Docker container deployed on Railway at `impartial-inspiration-production-0aa4.up.railway.app`.
**Status:** FIXED 2026-02-27 — was returning 502 for all public requests
**Notes:** Bug: `EXPOSE 8400` in Dockerfile caused Railway's public ingress to route to port 8400, but uvicorn binds to `$PORT` (8080 in Railway). Internal health check from `100.64.0.2` used `$PORT` directly and passed; all public requests failed. Fix: removed `EXPOSE` directive so Railway routes public traffic via `$PORT` consistently. CMD `${PORT:-8400}` unchanged — fallback 8400 only applies locally. Also removed `streamlit` and `langchain-openai` from runtime deps (neither imported by FastAPI backend).

## Observability / Langfuse Tracing (updated 2026-02-26)

**Location:** `agent/src/observability/tracing.py`, `agent/src/config.py`
**Purpose:** Sends OpenTelemetry traces to Langfuse for every agent request — LLM calls, tool invocations, chain steps. Provides user feedback scoring via Langfuse REST API.
**Dependencies:** `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `httpx`, `langchain-core` (BaseCallbackHandler)
**Exposes:** `init_tracing()`, `create_langfuse_handler()`, `log_feedback()`, `LangfuseOtelHandler` class (includes `log_score()` method)
**Status:** working — updated 2026-02-27
**Notes:** Uses pure OTEL + Langfuse REST API instead of the `langfuse` Python SDK, which is broken on Python 3.14 (pydantic v1 incompatibility). Tracing is a no-op when `LANGFUSE_SECRET_KEY`/`LANGFUSE_PUBLIC_KEY` env vars are empty. Feedback endpoint at `POST /feedback` accepts `{trace_id, score, comment}`. `log_score()` method posts numeric scores (e.g., confidence) to Langfuse REST API per trace — used by confidence scoring in `graph.py`. Fixed 2026-02-27: all span callbacks now set `langfuse.input` and `langfuse.output` attributes so Langfuse renders inputs/outputs in the trace waterfall. LLM spans capture prompts + generated text; tool spans capture input_str + output; chain spans capture full inputs/outputs dicts as JSON.

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

## Verification / confidence (updated 2026-02-26)

**Location:** `agent/src/verification/confidence.py`
**Purpose:** Computes a 0.0–1.0 confidence score for every agent response based on tool success rate and data completeness. Provides tiered display messaging: high (>= 0.8, score only), medium (0.6–0.8, incomplete warning), low (< 0.6, verify with staff alert).
**Dependencies:** `re`, `logging` (stdlib only), `langchain-core` (ToolMessage type)
**Exposes:** `compute_confidence()`, `format_confidence_message()`, `HIGH_CONFIDENCE`, `MEDIUM_CONFIDENCE`
**Status:** working
**Notes:** Scoring formula: start at 1.0, deduct 0.30 per tool error, 0.15 per empty result. No-tool responses (scope guard blocks) return 1.0. Score is logged to Langfuse as a numeric score via REST API. Integrated in `run_agent()` in graph.py after tool extraction and before Langfuse flush. API response includes `confidence_score` field. Streamlit frontend shows progress bar.

## Verification / drug_safety (updated 2026-02-26)

**Location:** `agent/src/verification/drug_safety.py`
**Purpose:** Post-processing step that cross-references medications against patient allergies after agent tool calls. Detects direct matches and cross-reactivity (penicillin→amoxicillin, sulfa→bactrim, NSAID→ibuprofen, codeine→hydrocodone, cephalosporin→cephalexin). Prepends WARNING block if conflict found. Also manages the "not medical advice" clinical data disclaimer for all clinical tool responses.
**Dependencies:** `re`, `logging` (stdlib only). Called from `graph.py` post_process node; may trigger inline `allergy_check` tool invocation if allergy data is missing from conversation.
**Exposes:** `check_drug_safety()`, `find_conflicts()`, `format_warning()`, `should_add_clinical_disclaimer()`, `extract_medications_from_messages()`, `extract_allergies_from_messages()`, `CLINICAL_DATA_DISCLAIMER`, `MEDICATION_TOOLS`, `CLINICAL_DATA_TOOLS`, `CROSS_REACTIVITY`
**Status:** working — 24 unit tests passing
**Notes:** Cross-reactivity map is a curated MVP (6 drug classes). Production would use RxNorm/RxClass API for class membership. Medication parsing requires "active medication" header to avoid false matches from allergy text. The `_post_process_node` in graph.py replaced the old `_append_disclaimer` node and handles drug safety + both disclaimers in one pass. Inline allergy fetch uses concurrent.futures ThreadPoolExecutor to work inside LangGraph's sync node callbacks.

## Verification / hallucination (updated 2026-02-26)

**Location:** `agent/src/verification/hallucination.py`
**Purpose:** Post-response LLM-based fact-checker. Sends the agent's final response + all tool outputs to a cheap external LLM (GPT-4o-mini or Claude Haiku fallback) to identify claims not supported by source data. Appends a warning if unsupported claims are found, or a "Verification unavailable" note on API errors.
**Dependencies:** `httpx`, `langchain-core` (AIMessage, ToolMessage types), `src.config` (OPENAI_API_KEY, ANTHROPIC_API_KEY)
**Exposes:** `check_hallucination()`, `HALLUCINATION_WARNING`, `VERIFICATION_UNAVAILABLE`, `CLEAN_VERDICT`
**Status:** working
**Notes:** Prefers OPENAI_API_KEY (GPT-4o-mini) for independence from primary LLM; falls back to ANTHROPIC_API_KEY (Claude Haiku). 256 max_tokens + 10s timeout keeps latency under 2–3s. Skipped when no tools were used (nothing to fact-check against). Results logged to Langfuse as `hallucination_check` score: 1.0 (clean), 0.5 (error), 0.0 (flagged). Integrated in `run_agent()` in graph.py after confidence scoring and before Langfuse flush. Fourth verification layer alongside scope_guard, drug_safety, and confidence.

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

## Eval Framework (updated 2026-02-26)

**Location:** `agent/eval/test_cases.yaml`, `agent/eval/run_evals.py`, `agent/eval/README.md`, `agent/eval/LICENSE`
**Purpose:** 52-test evaluation suite covering all 7 tools across 4 categories (happy_path, edge_case, adversarial, multi_step). Standalone runner and pytest integration with Langfuse result logging.
**Dependencies:** `pyyaml`, `pytest`, `pytest-asyncio`, `langchain-core` (for mock messages), `src.verification.scope_guard`, `src.agent.graph` (mocked)
**Exposes:** `run_all_evals()`, `load_cases()`, `print_summary()`, `check_exit_code()`, pytest fixtures (`test_adversarial_blocked`, `test_scope_guard_allows`, `test_agent_response`)
**Status:** working — 52/52 passing (100%)
**Notes:** Adversarial tests run against real scope guard (no mocking). Happy path/edge/multi-step tests mock `_react_agent.ainvoke` and `check_hallucination` for deterministic results. Quality gates: >= 80% overall pass rate, 0 adversarial failures allowed. Langfuse logging is best-effort (skipped if keys not set). Known limitation: scope guard is keyword-based, so adversarial inputs must avoid matching clinical/data keywords to be blocked. Dataset MIT-licensed for open-source release.

## Deliverable Documentation (updated 2026-02-27)

**Location:** `ARCHITECTURE.md`, `COST_ANALYSIS.md`, `README.md` (all at repo root)
**Purpose:** External-facing project documentation covering system design, cost model, and setup instructions for stakeholders and open-source contributors.
**Dependencies:** None (static markdown)
**Exposes:** ARCHITECTURE.md (domain, agent architecture, 7-tool table, 4 verification systems, eval results, Langfuse observability, open-source eval dataset), COST_ANALYSIS.md (dev costs ~$5–8, production projections 100–100K users, per-query breakdown, 5 optimization strategies), README.md (title, ASCII diagram, setup, tool list, eval instructions, dataset link)
**Status:** complete — generated 2026-02-27
**Notes:** All claims in ARCHITECTURE.md are traceable to source code. Token/cost estimates derived from code constraints and observed patterns, not Langfuse dashboard data. README preserves original OpenEMR content below the agent section.

## PRD Compliance Audit (2026-02-27)

**Summary:** 50 PASS | 8 PARTIAL | 5 MISSING | 5 NEEDS VERIFICATION | Total: 68 requirements

**Critical Gaps (must fix before Sunday 10:59 PM CT deadline):**
1. ❌ Agent NOT deployed publicly — OpenEMR backend on Railway but agent FastAPI+Streamlit has no Railway deploy; README has placeholder `[Add your Railway URL here]`
2. ❌ Demo Video not recorded — required 3–5 min showing agent, evals, observability
3. ❌ Pre-Search Document not in repo — required Phase 1–3 checklist
4. ❌ Social Post not made — X or LinkedIn with @GauntletAI tag
5. ⚠️ Streamlit feedback UI missing — `/feedback` API + `log_feedback()` work but no thumbs up/down buttons in the frontend

**Minor Gaps:**
6. ⚠️ Open Source Link — eval dataset MIT-licensed in repo but not separately published (HuggingFace/PyPI)
7. ⚠️ COST_ANALYSIS.md doesn't state Langfuse cost (should be $0 — free tier)
8. ⚠️ No explicit JSON schema output validation for tool outputs (confidence+hallucination check cover quality but not schema)
9. ⚠️ Human-in-the-Loop: low-confidence alert exists but no formal escalation/handoff mechanism

**Performance Targets — Needs Verification:**
10. 🔍 Latency <5s single-tool: documented 2–5s (not formally benchmarked)
11. 🔍 Latency <15s multi-step: documented 5–12s (not formally benchmarked)
12. 🔍 Tool success rate >95%: integration testing OK, no formal metric
13. 🔍 Hallucination rate <5%: Langfuse tracked but no baseline in docs
14. 🔍 Verification accuracy >90%: scope guard adversarial 100% (10/10), no broader metric

**Estimated remediation time: ~4–6 hours to 100% compliance**

**Post-Audit Fixes Applied (2026-02-27):**
- ✅ #5 Streamlit feedback UI — added 👍/👎 per-message buttons + `_submit_feedback()` helper
- ✅ #7 COST_ANALYSIS.md Langfuse cost — added explicit `$0.00` row to dev costs table
- ✅ #9 Human-in-the-Loop — added `requires_escalation` API field + Streamlit escalation banner
- ✅ #3 Pre-Search Document — created `docs/PRE_SEARCH_DOCUMENT.md` (gitignored)

**Remaining Open Items:**
- ❌ Agent not yet publicly deployed (Railway deploy pending user action)
- ❌ Demo Video not recorded (user to handle)
- ❌ Social Post not made (user to handle)

---

## API / FastAPI App (updated 2026-02-27)

**Location:** `agent/src/main.py`
**Purpose:** FastAPI application entry point. Exposes `/chat`, `/feedback`, and `/health` endpoints. Routes chat requests through the LangGraph agent and returns structured responses including confidence scores and escalation flags.
**Dependencies:** `fastapi`, `pydantic`, `httpx`, `src.agent.graph.run_agent`, `src.observability.tracing.log_feedback`
**Exposes:** `ChatRequest`, `ChatResponse`, `FeedbackRequest`, `FeedbackResponse` Pydantic models; `POST /chat`, `POST /feedback`, `GET /health` endpoints
**Status:** working — integration tested 2026-02-27
**Notes:** `ChatResponse.requires_escalation` is computed as `confidence_score < 0.6` — signals to the caller that the response should be reviewed by a human before clinical action. The 0.6 threshold is conservative: any drug safety flag, hallucination detection, or low-confidence pattern triggers it. CORS configured for `*` (development; restrict in production). `/health` checks OpenEMR FHIR metadata endpoint connectivity.

## Frontend / Streamlit (updated 2026-02-27)

**Location:** `agent/frontend/streamlit_app.py`
**Purpose:** Chat UI for the OpenEMR AI agent. Renders conversation history, sends queries to the FastAPI backend, displays tool usage badges, confidence scores, escalation banners, and per-message feedback buttons.
**Dependencies:** `streamlit`, `requests`, `AGENT_API_URL` env var (default `http://localhost:8400`)
**Exposes:** Streamlit web app on port 8501
**Status:** working — integration tested 2026-02-27
**Notes:** Per-message 👍/👎 feedback buttons call `_submit_feedback(trace_id, score)` which POSTs to `/feedback`. Feedback state tracked in `st.session_state` as `fb_{i}` keys — buttons collapse to confirmation label after submission to prevent double-posting. `requires_escalation=True` responses show a red `st.warning` banner. `trace_id` and `requires_escalation` stored in message session state for history replay. `st.rerun()` called after feedback submission to refresh button state.

## Deliverable Documentation (updated 2026-02-27)

**Location:** `docs/PRE_SEARCH_DOCUMENT.md` (gitignored), `ARCHITECTURE.md`, `COST_ANALYSIS.md`, `README.md`
**Purpose:** Full project documentation suite. PRE_SEARCH_DOCUMENT covers Phase 1–3 architectural discovery (domain, LLM selection, tool design, observability, eval strategy, verification, failure modes, deployment, cost). COST_ANALYSIS documents dev costs (~$5–8 actual), production projections (100–100K users), Langfuse $0 cost, and 5 optimization strategies.
**Status:** complete — generated/updated 2026-02-27
**Notes:** `docs/PRE_SEARCH_DOCUMENT.md` is automatically gitignored by the `docs/*` pattern in `.gitignore` (with exceptions for CHANGELOG and CODEBASE_AUDIT). COST_ANALYSIS.md now includes explicit Langfuse $0.00 observability cost row in dev costs table.

## PRD Compliance Audit (updated 2026-02-27)

**Location:** This section — cross-reference against AgentForge PRD
**Purpose:** Track compliance status for final Sunday submission.
**Status:** 52/61 PASSING | 0 PARTIAL | 3 MISSING | 6 NEEDS VERIFICATION (updated 2026-02-27)

**Missing (❌ — blocking):**
1. `README.md:111` — Deployed URL is placeholder `[Add your Railway URL here]`; PRD hard-gates on "Deployed and publicly accessible"
2. Demo video (3–5 min) — not yet recorded; PRD requires as submission deliverable
3. Social post (X or LinkedIn, tag @GauntletAI) — not yet posted

**Partial (⚠️ — all resolved 2026-02-27):**
1. ✅ Live eval mode — `EVAL_LIVE=1` / `--live` + `@pytest.mark.live` added to `run_evals.py`
2. ✅ Regression detection — `baseline.json` + `check_regression()` in `run_evals.py`; exit code 1 on >5pp drop
3. ✅ Open Source Link — direct GitHub URL in README: `github.com/helloblair/AGENTFORGE-openemr/tree/master/agent/eval`
4. ✅ PRE_SEARCH_DOCUMENT.md — un-gitignored via `!docs/PRE_SEARCH_DOCUMENT.md` in `.gitignore`

**Needs Verification (🔍 — claims made, not benchmarked):**
- End-to-end latency <5s (single-tool) — ARCHITECTURE.md reports 2–5s observed
- Multi-step latency <15s (3+ tools) — ARCHITECTURE.md reports 5–12s observed
- Tool success rate >95% — claimed 0% errors in happy-path testing
- Eval pass rate >80% live — 100% on mocked suite; no live LLM eval run
- Hallucination rate <5% — 0% on adversarial tests
- Verification accuracy >90% — not formally measured

## Smoke Test Script (added 2026-02-27)

**Location:** `agent/scripts/smoke_test.py`
**Purpose:** Live end-to-end test of all 7 tools against the real OpenEMR API (not mocked). One query per tool, checks tool_used list and response content. CLI flags: `--tool <name>` (run single tool), `--verbose` (show full responses). Exit code 1 if any test fails.
**Status:** Committed but not run in CI (live API required)
**Notes:** Runs sequentially to avoid auth token conflicts. Per-tool isolation via unique thread_id per test.

## Final Deep Audit Summary (2026-02-27 — Claude Code)

**Status:** 55/61 requirements passing. 3 external actions remaining (deploy, video, social post).

**Key findings:**
- Security: `agent/.env` committed with live API keys — purge before repo goes fully public
- Deployment: OpenEMR at `https://openemr-production-7df2.up.railway.app`; agent FastAPI not yet public
- All code/docs/evals are submission-ready
- Langfuse dashboard at: `https://us.cloud.langfuse.com`
- Smoke test available: `python -m scripts.smoke_test` from agent/

## Scope Guard / Input Classification (updated 2026-02-27)

**Location:** `agent/src/verification/scope_guard.py`
**Purpose:** Pre-processes every user message before it reaches the LLM. Classifies input into one of five categories: DATA_RETRIEVAL, CLINICAL_SUPPORT, MEDICAL_KNOWLEDGE, DIAGNOSIS_REQUEST (blocked), TREATMENT_REQUEST (blocked), OUT_OF_SCOPE (blocked). Hard-blocks diagnosis/prescription requests.
**Categories:**
- `DATA_RETRIEVAL` — patient/provider lookup queries ("find", "list", "show", etc.)
- `CLINICAL_SUPPORT` — patient-specific clinical queries ("interaction", "allergy", "medication", etc.)
- `MEDICAL_KNOWLEDGE` — general pharmacology/drug knowledge ("what is", "how does", "difference between", "side effects", etc.) — NEW 2026-02-27
- `DIAGNOSIS_REQUEST` — blocked ("diagnose", "what disease", "what's wrong with")
- `TREATMENT_REQUEST` — blocked ("prescribe", "recommend treatment", etc.)
- `OUT_OF_SCOPE` — blocked (nothing matched)
**Status:** working
**Notes:** MEDICAL_KNOWLEDGE is checked before DATA_RETRIEVAL so multi-word phrases win over single-word "what" keyword. System prompt updated in parallel to explicitly permit general medical knowledge answers while restricting patient-specific fabrication.
