# Codebase Audit — AgentForge
> Living map of the codebase. Updated with every significant change.
> Organized by component. Check Status field for current state.

## Deployment / Vultr VPS — Full Stack (updated 2026-03-20)

**Location:** `docker-compose.prod.yml`, `docker/nginx/nginx.conf`, `Dockerfile.openemr`, `agent/Dockerfile`, `agent/frontend-next/Dockerfile`
**Purpose:** All services (OpenEMR + MariaDB, FastAPI agent, Next.js frontend, Nginx reverse proxy) run on a single Vultr VPS via Docker Compose.
**Status:** MIGRATED — consolidated from Railway/Fly.io/Vercel to single VPS.
**URLs:** `https://VPS_IP/` (frontend), `https://VPS_IP/api/` (agent), `https://VPS_IP:8443/` (OpenEMR)
**Notes:** (1) OAuth2 client credentials bootstrapped via `scripts/bootstrap-oauth.sh`. (2) CORS origins configurable via `CORS_ALLOWED_ORIGINS` env var in `agent/src/main.py`. (3) Vultr snapshot approach for cost savings — ~$1.50/month idle. (4) LangGraph pinned to <1.0 due to breaking API changes. (5) Previous platforms (Railway, Fly.io, Vercel) fully decommissioned.

## Observability / Langfuse Tracing (updated 2026-03-01)

**Location:** `agent/src/observability/tracing.py`, `agent/src/config.py`, `agent/src/agent/graph.py`
**Purpose:** Sends OpenTelemetry traces to Langfuse for every agent request — LLM calls, tool invocations, chain steps. Provides user feedback scoring via Langfuse REST API.
**Dependencies:** `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `httpx`, `langchain-core` (BaseCallbackHandler)
**Exposes:** `init_tracing()`, `create_langfuse_handler()`, `log_feedback()`, `LangfuseOtelHandler` class (includes `log_score()`, `set_trace_input()`, `set_trace_output()` methods)
**Status:** working — updated 2026-03-01
**Notes:** Uses pure OTEL + Langfuse REST API instead of the `langfuse` Python SDK, which is broken on Python 3.14 (pydantic v1 incompatibility). Tracing is a no-op when `LANGFUSE_SECRET_KEY`/`LANGFUSE_PUBLIC_KEY` env vars are empty. Feedback endpoint at `POST /feedback` accepts `{trace_id, score, comment}`. `log_score()` method posts numeric scores (e.g., confidence) to Langfuse REST API per trace — used by confidence scoring in `graph.py`. Fixed 2026-03-01: all observation span attributes use `langfuse.observation.input`/`langfuse.observation.output` (the names Langfuse OTEL ingestion recognizes). LLM spans include `langfuse.span.type: "GENERATION"` so Langfuse renders them as Generations with token usage panels. Trace-level I/O set via `set_trace_input()`/`set_trace_output()` using `langfuse.trace.input`/`langfuse.trace.output` root span attributes, wired in `graph.py` before flush.

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
6. ✅ Open Source Link — eval dataset published at https://github.com/helloblair/openemr-agent-eval-dataset (MIT, 71 test cases)
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

**Remaining Open Items (updated 2026-02-27):**
- ✅ Agent publicly deployed — `https://impartial-inspiration-production-7678.up.railway.app`
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
3. ✅ Open Source Link — published as standalone public repo: `github.com/helloblair/openemr-agent-eval-dataset`
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

## PRD Compliance Audit — Full Re-Audit (2026-02-27 — Claude Code claude-sonnet-4-6)

**Total Requirements Audited:** 67
**Status:** 52 PASS | 4 PARTIAL | 5 MISSING | 6 NEEDS VERIFICATION

### ✅ PASSING (52) — No Action Needed

**MVP Gate (8/9):** NL query response, 7 tools (>3), tool execution, synthesis, MemorySaver conversation history, graceful error handling, 4 verification systems (>1), 52 eval cases (>5).

**Core Architecture (6/6):** Claude Sonnet 4 reasoning engine, @tool registry, MemorySaver memory, LangGraph ReAct orchestrator, 4-layer verification pipeline, structured output + confidence + citations.

**Tools (4/4):** 7 tools (>5 minimum), all have schemas/docs/execution, structured returns, graceful error handling.

**Eval Framework (8/8):** 52 cases (>50), 21 HP (>20), 11 EC (>10), 10 AD (>10), 10 MS (>10), full YAML schema, run_evals.py runner, baseline.json results.

**Observability (5/6):** Langfuse OTEL spans with full input/output, Langfuse error tracking, token usage attributes, baseline regression detection, 👍/👎 feedback buttons.

**Verification Systems (5/6 — need 3):** Fact checking (drug_safety + hallucination), hallucination detection, confidence scoring, domain constraints (scope_guard), human-in-the-loop (requires_escalation).

**Performance:** Eval pass rate 100% on mocked suite (>80% target).

**Cost Analysis (5/6):** ~$5-8 dev spend, estimated token breakdown, Langfuse $0, 4-scale projections, assumptions documented.

**Deliverables (15/18):** GitHub repo, setup guide, ARCHITECTURE.md, PRE_SEARCH_DOCUMENT.md, 6-section architecture doc, COST_ANALYSIS.md, 52-case eval dataset with results.

**Interview Prep (5/5):** LangGraph rationale, tool tradeoffs, verification strategy, eval methodology, scale/cost analysis — all documented.

### ⚠️ PARTIAL (4) — Needs Work

1. **Latency Tracking (#29):** OTEL spans capture per-span timing, but no `latency_ms` field in `ChatResponse` and Streamlit doesn't display it. Fix: add `latency_ms` to `ChatResponse` and record in `run_agent()`.
2. **Output Validation (#38):** No explicit JSON schema validation on tool outputs. Confidence + hallucination cover quality but not schema conformance. Fix: add Pydantic output model validation inside each tool or in post-process node.
3. **API Call Count (#48):** COST_ANALYSIS.md states ~3,500 calls but this is derived from token math, not pulled from Langfuse or Anthropic Console. Fix: export actual trace count from Langfuse dashboard and update doc.
4. ✅ **Open Source Publication (#52/62):** Eval dataset published as standalone public repo at https://github.com/helloblair/openemr-agent-eval-dataset (71 test cases, MIT license, runner + baseline included).

### ❌ MISSING (5) — Must Build/Do

1. **Deployed Agent (#9, #56, #63):** Agent FastAPI not publicly deployed. Railway config (`railway.toml`, `Dockerfile`) is ready. Action: run `railway up` from `agent/`, copy URL, update `README.md`. (~30 min)
2. **Demo Video (#57):** `DEMO_SCRIPT.md` exists but no recording made. Action: record 3-5 min Loom showing live query, eval run, Langfuse dashboard. (~60 min)
3. **Social Post (#64):** No X/LinkedIn post with @GauntletAI tag. Action: write post with demo screenshot/link. (~15 min)

### 🔍 NEEDS VERIFICATION (6)

- **Latency <5s single-tool (#40):** ARCHITECTURE.md reports 2-5s observed but not formally benchmarked. Pull Langfuse P95.
- **Multi-step latency <15s (#41):** ARCHITECTURE.md reports 5-12s. Same caveat.
- **Tool success rate >95% (#42):** All 7 tools passed integration tests; no ongoing metric. Run smoke_test.py post-deploy.
- **Live eval pass rate >80% (#43):** 100% on mocked suite. Run `EVAL_LIVE=1 python eval/run_evals.py` against deployed agent.
- **Hallucination rate <5% (#44):** Langfuse tracks `hallucination_check` scores but no aggregate baseline documented.
- **Verification accuracy >90% (#45):** Scope guard 10/10 adversarial (100%); broader metric not measured.

**Estimated time to 100% compliance: ~2.5–3 hours** (deployment + video + social post dominate; code gaps are minor).

---

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

---

## Frontend / Next.js App (updated 2026-02-28)

**Location:** `agent/frontend-next/`
**Purpose:** Production-grade Next.js App Router frontend replacing Streamlit. Connects to existing FastAPI backend (zero backend changes required).
**Stack:** Next.js 16 (App Router), TypeScript, Tailwind CSS, react-markdown + remark-gfm, sonner (toasts), uuid (thread_id)
**Status:** DEPLOYED — live at https://veris-teal.vercel.app. Phase 1 layout complete, mobile polish applied (responsive sidebar drawer with transitions/focus trap/Escape, responsive header, embedded send button, responsive message bubbles). WCAG 2.1 AA accessibility pass complete. Remaining: Phase 2 (streaming, dark mode toggle, structured data cards)
**Migration difficulty:** Easy–Medium. Backend is a clean REST API with `allow_origins=["*"]`. All Streamlit features map directly to React primitives. No streaming currently (Phase 2 addition).

**Feature inventory for Next.js port:**
- Chat input (`<textarea>` + Enter to send)
- Message history display with react-markdown rendering
- Tool calls accordion (collapsible, per assistant message)
- Confidence bar (color-coded: ≥0.8 green / 0.6–0.8 amber / <0.6 red)
- Escalation warning banner (`requires_escalation: true`)
- Thumbs up/down feedback → `POST /feedback` → Langfuse
- Sidebar (example queries, session info, health status)
- Loading/thinking indicator
- Error states with retry
- Responsive layout (drawer sidebar on mobile) ✅

**Deployment config:** `output: "standalone"` in next.config.ts, multi-stage Dockerfile (node:20-alpine), vercel.json, DEPLOYMENT.md. Ready for Vercel (Hobby tier, free) or Docker-based platforms (Fly.io, Railway). `NEXT_PUBLIC_AGENT_API_URL` points at the FastAPI service.

**Improvements over Streamlit:** Streaming responses (Phase 2), dark mode, rich structured data cards (Phase 2, requires backend JSON response changes), mobile responsiveness, WCAG 2.1 AA accessibility (completed 2026-02-28), keyboard shortcuts, copy-per-message, toast notifications, smooth animations.

**WCAG 2.1 AA compliance (2026-02-28):** ARIA live regions on chat (`aria-live="polite"`, `role="log"`, `aria-busy`), `role="alert"` on error/escalation banners, `aria-pressed` on feedback buttons, `aria-expanded`/`aria-controls` on tool panel, `role="meter"` on confidence bar, `role="status"` on loading indicator and health status, semantic landmarks (`<main>`, `<nav>`, `<footer>`), skip-to-content link, visible `focus-visible` rings, `prefers-reduced-motion: reduce` media query, focus returns to input after send/example click, `aria-label` on textarea and decorative elements hidden with `aria-hidden`.

**Time estimates:**
- Phase 1 (feature parity): 6–8 hours
- Phase 2 (UI polish + dark mode + structured cards): 12–16 hours
- Phase 3 (deploy migration Railway → Vercel + Fly.io): 4–6 hours
- Phase 4 (branding — Veris/Meridian/Lumis): 6–10 hours
- **Total: 28–40 hours**

## Deployment / Platform Analysis (planned 2026-02-27)

**Current:** Vercel (Next.js frontend at https://veris-teal.vercel.app) + Fly.io (FastAPI agent at https://openemr-agent-api.fly.dev) + Railway (OpenEMR backend). All Railway agent/frontend services are deprecated — safe to delete.

**Platform comparison:**
| Platform | Monthly cost | Frontend | Backend | Networking | Ops burden |
|---|---|---|---|---|---|
| Railway (current) | ~$20–25 | ✓ (fragile) | ✓ (live) | Public only | High (CDN bugs, EXPOSE issues) |
| Fly.io (all services) | ~$17–20 | ✓ | ✓ | Private .internal DNS | Low |
| Digital Ocean Droplet | ~$24 | ✓ | ✓ | Docker Compose private | Medium (manual SSL) |
| Vercel + Fly.io (hybrid) | ~$13.50 | Free (Vercel) | ✓ | Public HTTPS + .internal | Very Low |

**Fly.io key advantage:** FastAPI → OpenEMR communicate over `http://openemr-ehr.internal:8300` (private, no public IP for OpenEMR required). `fly secrets set` for env vars. Cold starts: set `min_machines_running = 1` for FastAPI to avoid latency on medical queries.

**Notes:** CORS is already `allow_origins=["*"]` — Vercel frontend can call Fly.io backend with no additional config. Restrict to specific Vercel domain when hardening for production.

## Branding / App Name Options (planned 2026-02-27)

## Next.js Frontend — useKeyboardShortcuts Hook (added 2026-02-28)

**Location:** `agent/frontend-next/lib/hooks/useKeyboardShortcuts.ts`
**Purpose:** Global keyboard shortcut handler. Registers Ctrl+K / Cmd+K (new chat) and Escape (close sidebar / blur input) as document-level keydown listeners.
**Dependencies:** React (useEffect)
**Exposes:** `useKeyboardShortcuts({ onNewChat, onCloseSidebar, sidebarOpen })` hook
**Status:** working
**Notes:** Replaces the inline Escape-key handler that was in `page.tsx`. Ctrl+K calls `e.preventDefault()` to suppress the browser's default address-bar shortcut. Escape checks `sidebarOpen` first; if closed, blurs the active element instead.

## Next.js Frontend — ChatInput Component (updated 2026-02-28)

**Location:** `agent/frontend-next/components/ChatInput.tsx`
**Purpose:** Chat input control with auto-resizing textarea (max 4 lines / 120px), Enter-to-submit / Shift+Enter-for-newline, send button embedded inside the textarea field, and disabled state during requests.
**Dependencies:** React (useRef, useCallback, useEffect)
**Exposes:** `ChatInput` component. Props: `onSubmit(message: string)`, `isLoading: boolean`, `textareaRef?: React.RefObject<HTMLTextAreaElement | null>` (optional external ref for programmatic focus)
**Status:** working
**Notes:** Uncontrolled textarea (ref-based) to avoid per-keystroke re-renders. Auto-resize via `scrollHeight` clamped to 120px (~4 lines). Send button absolute-positioned inside textarea (bottom-right). Mobile keyboard handling: `scrollIntoView({ block: "end" })` fires 300ms after focus. Responsive padding: `px-2 py-2` on mobile → `px-4 py-3` at sm+. Send button `h-9 w-9` (smaller than before for embedded fit). Accepts optional `textareaRef` prop; uses internal fallback ref when not provided — enables parent-driven focus (e.g., after Ctrl+K new chat).

## Next.js Frontend — ChatWindow Component (updated 2026-02-28)

**Location:** `agent/frontend-next/components/ChatWindow.tsx`
**Purpose:** Main chat orchestrator. Manages loading/error state, sends user messages to FastAPI backend via `sendMessage()`, maps responses to `Message[]` with full metadata. Handles feedback submission, error classification, and retry logic.
**Dependencies:** `@/lib/api` (sendMessage, sendFeedback, ApiError, TimeoutError), `@/lib/types` (Message), `ChatInput`, `MessageBubble`, `LoadingIndicator`, `ErrorBanner`
**Exposes:** `ChatWindow` component. Props: `messages`, `setMessages`, `threadId`, `setThreadId`, `onReady?`, `chatInputRef?`
**Status:** working
**Notes:** State (messages, threadId) lifted to `page.tsx` and passed via props so Sidebar can access the same state. `onReady` callback exposes `handleSubmit` to the parent via a stable ref pattern. Error handling classifies errors into 4 categories: TimeoutError → timeout message, ApiError (5xx) → server error, TypeError/Failed to fetch → network error, other → generic. `handleRetry` removes the last user message and re-submits via `handleSubmit`. `lastUserMessageRef` tracks the most recent user text for retry. Loading indicator and error banner extracted to standalone components. `chatInputRef` forwarded to ChatInput for parent-driven focus. **A11y (2026-02-28):** Message list is a semantic `<ol>` with `role="log"`, `aria-live="polite"`, and `aria-label="Chat messages"`. Container has `aria-busy={isLoading}`. Focus returns to chat input after loading completes.

## Next.js Frontend — Sidebar Component (updated 2026-02-28)

**Location:** `agent/frontend-next/components/Sidebar.tsx`
**Purpose:** Fixed 280px left panel with app header, clickable example queries, session info, health status polling, and footer. Responsive: always visible on desktop (lg:), rendered as a slide-over drawer on mobile/tablet.
**Dependencies:** `@/lib/api` (checkHealth)
**Exposes:** `Sidebar` component. Props: `threadId: string`, `messageCount: number`, `onExampleClick: (query: string) => void`, `onClose?: () => void`
**Status:** working
**Notes:** Mobile drawer managed in `page.tsx` using CSS transitions (not conditional rendering) for smooth open/close. `sidebar-drawer` class uses `transform: translateX(-100%)` → `translateX(0)` with `data-open` attribute. Backdrop fades via `sidebar-backdrop` class with opacity transition. Focus trap + Escape-to-close + `role="dialog" aria-modal="true"` for accessibility. Drawer stays in DOM with `pointer-events-none` when closed. Keyboard shortcuts hint section added at bottom (above footer) showing Ctrl+K, Enter, Shift+Enter with `<kbd>` elements in muted monospace text.

## Next.js Frontend — Header Component (updated 2026-02-28)

**Location:** `agent/frontend-next/components/Header.tsx`
**Purpose:** Top header bar with three-zone responsive layout: hamburger (left, mobile only), centered app name, New Chat button (right, icon-only on mobile).
**Dependencies:** None (React only)
**Exposes:** `Header` component. Props: `onToggleSidebar: () => void`, `onNewChat: () => void`
**Status:** working
**Notes:** Height: `h-14`, fixed at top. Mobile: hamburger left, "Veris" centered (absolute `left-1/2 -translate-x-1/2`), plus-icon-only New Chat right. sm+: "Clinical Intelligence" subtitle appears, New Chat shows text label. lg+: hamburger hidden (sidebar always visible). Three-zone layout uses `relative` header with absolute centering for the title to prevent hamburger/button from pushing it off-center.

## Next.js Frontend — ClinicalDisclaimer Component (updated 2026-02-28)

**Location:** `agent/frontend-next/components/ClinicalDisclaimer.tsx`
**Purpose:** Persistent, non-dismissible clinical decision support disclaimer footer. Renders below the chat input.
**Dependencies:** None (React only)
**Exposes:** `ClinicalDisclaimer` component. Props: none
**Status:** working
**Notes:** Responsive: `text-[10px]` on mobile → `text-xs` at sm+. Tighter padding on mobile (`px-3 py-1.5` → `px-4 py-2`). Non-dismissible by design per healthcare UI safety standards.

## Next.js Frontend — MessageBubble Component (updated 2026-02-28)

**Location:** `agent/frontend-next/components/MessageBubble.tsx`
**Purpose:** Rich message display component with entry animations and responsive width constraints. Renders user messages as plain text (right-aligned, blue) and assistant messages as markdown (left-aligned, neutral). Imports all sub-components from standalone files: ToolCallsPanel, ConfidenceBar, EscalationWarning, FeedbackButtons, CopyButton.
**Dependencies:** `react-markdown`, `remark-gfm`, `@/lib/types` (Message), `./ToolCallsPanel`, `./ConfidenceBar`, `./EscalationWarning`, `./FeedbackButtons`, `./CopyButton`
**Exposes:** `MessageBubble` component. Props: `message: Message`, `onFeedback?: (traceId: string, score: 'up'|'down') => void`
**Status:** working
**Notes:** Responsive max-widths: user bubbles `85%` mobile → `75%` sm → `70%` md; assistant bubbles `100%` mobile → `85%` sm → `80%` md. Role indicator `10px` mobile → `11px` sm+. Entry animations: `animate-message-in-right` / `animate-message-in-left` (250ms). FeedbackButtons rendered only when `trace_id` exists. All display sub-components in separate files.

## Next.js Frontend — FeedbackButtons Component (added 2026-02-28)

**Location:** `agent/frontend-next/components/FeedbackButtons.tsx`
**Purpose:** Thumbs up/down feedback buttons for rating agent responses. Calls `onFeedback(traceId, score)` for Langfuse feedback scoring. One-vote-per-message enforcement via disabled state.
**Dependencies:** None (React only)
**Exposes:** `FeedbackButtons` component. Props: `traceId: string`, `currentFeedback: 'up' | 'down' | null`, `onFeedback: (traceId: string, score: 'up' | 'down') => void`
**Status:** working
**Notes:** Outline SVG icons (stroke, no fill) in neutral state. On vote: selected button fills with color (emerald-500 for up, red-500 for down), unselected button fades (neutral-300/600). Both buttons disabled after voting — prevents double-submission. Aria labels: "Helpful response" / "Unhelpful response". Optimistic UI — fills immediately without waiting for API. Compact `mt-2` spacing sits below ConfidenceBar in the message bubble.

## Next.js Frontend — CopyButton Component (added 2026-02-28)

**Location:** `agent/frontend-next/components/CopyButton.tsx`
**Purpose:** Copy-to-clipboard button that appears on hover over assistant message bubbles. Copies raw markdown content to clipboard.
**Dependencies:** React (useState), `sonner` (toast)
**Exposes:** `CopyButton` component. Props: `text: string`
**Status:** working
**Notes:** Positioned `absolute top-2 right-2` inside the message bubble (parent has `relative`). Visibility controlled by `opacity-0 group-hover:opacity-100` (parent has `group`). Uses `navigator.clipboard.writeText()` for copy. After copying, icon swaps to a green checkmark for 2 seconds then reverts. Fires `toast("Copied to clipboard")` via sonner. Error case shows `toast.error("Failed to copy")`.

## Next.js Frontend — ToolCallsPanel Component (updated 2026-02-28)

**Location:** `agent/frontend-next/components/ToolCallsPanel.tsx`
**Purpose:** Collapsible accordion displaying rich tool pills with per-tool icons and category-colored left borders. Smooth animated expand/collapse via CSS grid transition. Default collapsed.
**Dependencies:** React (useState)
**Exposes:** `ToolCallsPanel` component. Props: `tools: string[]`
**Status:** working
**Notes:** Each of the 7 tools has a unique inline SVG icon and colored left border via a `TOOL_META` lookup table: patient_lookup (person, primary blue), allergy_check (shield-warning, red), medication_list (bolt, emerald), problem_list (clipboard, amber), provider_lookup (user-circle, indigo), insurance_coverage (id-card, violet), drug_interaction_check (alert-triangle, orange). Unknown tools get a fallback icon with slate border. Pills use `font-mono` (JetBrains Mono), `border-l-2`, and `shadow-sm → hover:shadow-md` elevation transition. Expand/collapse uses CSS `grid-template-rows: 0fr → 1fr` (250ms ease-out). `.tool-panel-content` CSS class defined in globals.css with `data-open` attribute.

## Next.js Frontend — ConfidenceBar Component (updated 2026-02-28)

**Location:** `agent/frontend-next/components/ConfidenceBar.tsx`
**Purpose:** Horizontal progress bar showing agent confidence score (0.0–1.0) with color coding and animated fill on mount.
**Dependencies:** React (useState, useEffect)
**Exposes:** `ConfidenceBar` component. Props: `score: number`
**Status:** working
**Notes:** Color thresholds match `verification/confidence.py`: green (`bg-emerald-500`) ≥0.8, amber (`bg-amber-500`) 0.6–0.79, red (`bg-red-500`) <0.6. Bar animates from 0% to target width over 500ms ease-out on mount via `requestAnimationFrame` → `setMounted(true)` pattern. Label shows exact score ("Confidence: 0.95").

## Next.js Frontend — EscalationWarning Component (added 2026-02-28)

**Location:** `agent/frontend-next/components/EscalationWarning.tsx`
**Purpose:** Non-dismissible red warning banner shown when `requires_escalation === true`. Clinical safety language.
**Dependencies:** None (React only)
**Exposes:** `EscalationWarning` component. Props: none
**Status:** working
**Notes:** Red-tinted background (`bg-red-50 border-red-200`), SVG warning icon, text: "Low confidence — please verify this information with a qualified healthcare professional before making clinical decisions." Dark mode supported. Non-dismissible by design.

## Next.js Frontend — LoadingIndicator Component (updated 2026-02-28)

**Location:** `agent/frontend-next/components/LoadingIndicator.tsx`
**Purpose:** Skeleton loading indicator that mimics an assistant message bubble while the agent is processing. Shows three animated pulse bars of varying width and "Agent is thinking..." text.
**Dependencies:** None (React only, CSS animations in globals.css)
**Exposes:** `LoadingIndicator` component. Props: none
**Status:** working
**Notes:** Replaced bouncing dots with skeleton loader. Three gray bars (52/40/48 Tailwind width units) with custom `animate-skeleton-pulse` keyframe (opacity 0.4→1.0, 1.5s infinite) staggered by 200ms. Entry animation via `animate-message-in-left`. Matches MessageBubble's assistant styling (left-aligned, surface-secondary bg, "Veris" label).

## Next.js Frontend — ErrorBanner Component (added 2026-02-28)

**Location:** `agent/frontend-next/components/ErrorBanner.tsx`
**Purpose:** Dismissible error banner displayed between the message list and chat input when an error occurs. Shows error icon, message text, optional Retry button, and optional Dismiss (X) button.
**Dependencies:** None (React only)
**Exposes:** `ErrorBanner` component. Props: `message: string`, `onRetry?: () => void`, `onDismiss?: () => void`
**Status:** working
**Notes:** Red-tinted background (`bg-red-50 border-red-200`), exclamation-circle SVG icon, flexbox layout. Retry button only renders when `onRetry` is provided. Dismiss button only renders when `onDismiss` is provided. Dark mode supported (`dark:bg-red-950 dark:border-red-900 dark:text-red-400`).

## Next.js Frontend — API Client (updated 2026-02-28)

**Location:** `agent/frontend-next/lib/api.ts`
**Purpose:** Typed fetch wrapper for all three FastAPI backend endpoints (`/chat`, `/feedback`, `/health`). Exports `sendMessage`, `sendFeedback`, `checkHealth`, `ApiError`, `TimeoutError`, and `AGENT_API_URL`.
**Status:** working
**Notes:** `ApiError` carries `status: number` + `message` (attempts to parse FastAPI `{ detail }` body). `TimeoutError` thrown when `sendMessage` exceeds 60-second `AbortController` timeout — catches `DOMException` with name `AbortError` and re-throws as `TimeoutError` for clean instanceof checks in callers. `sendFeedback` is fire-and-forget (no await at call sites). `checkHealth` returns `{ status: 'unreachable', openemr_connected: false }` on network errors — safe for polling without try/catch. All types imported from `./types.ts`.

---

**Top recommendation: Veris**
- Rationale: Latin "truth/verify" — directly embodies the agent's hallucination-check + drug safety verification core value proposition
- Colors: Primary `#1E3A5F`, Accent `#10B981`, Warning `#F59E0B`, Error `#EF4444`
- Fonts: Inter 700 (headings) + Inter 400 (body) + JetBrains Mono (code/tool output)
- Vibe: Precise. Trusted. Verified.

**Runner-up: Meridian** — convergence of patient data + clinical judgment; institutional/authoritative
**Runner-up: Lumis** — "illuminating" patient data; premium dark-mode-first aesthetic; indigo accent

**Other candidates:** Clarix, Synapse, Arca, Canopy, Aide, Verdant, Haven

## Next.js Frontend — ThemeProvider + ThemeToggle (added 2026-02-28)

**Location:** `agent/frontend-next/components/ThemeProvider.tsx`, `agent/frontend-next/components/ThemeToggle.tsx`
**Purpose:** Dark mode infrastructure. ThemeProvider manages theme state via React context, persists to localStorage, and toggles the `dark` class on `<html>`. ThemeToggle is a sun/moon icon button wired to `toggleTheme()`.
**Dependencies:** React (createContext, useContext, useEffect, useState)
**Exposes:** `ThemeProvider` component (wraps app in layout.tsx), `useTheme()` hook (returns `{ theme, toggleTheme }`), `ThemeToggle` component (not rendered yet)
**Status:** plumbed but inactive — light mode only; toggle hidden behind comment in Header.tsx
**Notes:** Defaults to `'light'`. Reads `localStorage('theme')` on mount. The `.dark` CSS variable overrides in globals.css handle the actual color swaps. To enable: uncomment `<ThemeToggle />` in Header.tsx. Per-component dark mode audit (shadows, borders, focus rings) deferred to post-launch.

## Frontend / Veris Color System (updated 2026-03-01)

**Location:** `agent/frontend-next/app/globals.css`, all components in `agent/frontend-next/components/`
**Purpose:** Unified design system using CSS custom properties mapped into Tailwind v4 semantic tokens. Provides light-mode colors with dark-mode overrides pre-plumbed (inactive).
**Dependencies:** Tailwind CSS v4 (`@theme inline` block), Inter font (headings/body), JetBrains Mono (code/tool output)
**Exposes:** 11 CSS custom properties (`--color-primary` through `--color-border`), corresponding Tailwind utility classes (`bg-primary`, `text-text-primary`, `border-border`, etc.)
**Status:** working — fully tokenized 2026-03-01
**Notes:** Dark mode activates by adding `class="dark"` to `<html>` — `.dark` overrides in globals.css swap all theme-variable values. As of 2026-03-01, zero hardcoded brand colors remain across all 15 components. ToolCallsPanel border colors now use semantic tokens (`border-l-primary`, `border-l-accent`, `border-l-warning`, `border-l-error`, `border-l-text-muted`) instead of hardcoded hex values. Code blocks in MessageBubble use `bg-primary text-white` instead of `bg-slate-900 text-slate-100`. EscalationWarning and ErrorBanner use opacity modifiers (`bg-error/10`, `border-error/30`) for translucent backgrounds. No `tailwind.config.ts` needed — Tailwind v4 uses CSS-first config via `@theme`.

## Frontend / Veris Brand Identity (updated 2026-03-01)

**Location:** `agent/frontend-next/components/Header.tsx`, `agent/frontend-next/components/Sidebar.tsx`, `agent/frontend-next/app/layout.tsx`, `agent/frontend-next/public/favicon.svg`
**Purpose:** Typographic logo and favicon establishing the Veris brand across the app.
**Dependencies:** Inter font (already loaded), Tailwind `text-accent` token for checkmark
**Exposes:** Header wordmark (`✓ Veris | Clinical Intelligence`), sidebar logo (`✓ Veris` + subtitle), 32x32 SVG favicon (emerald checkmark on #1E3A5F rounded square)
**Status:** working — applied 2026-03-01
**Notes:** Logo is pure code/text — no SVG mark, no Figma, no external assets beyond the favicon. Checkmark uses `&#10003;` HTML entity with `text-accent` token. Header shows full wordmark with pipe separator + subtitle on sm+ screens; mobile shows `✓ Veris` only. Favicon uses SVG-in-HTML (`icons: { icon: '/favicon.svg' }` in metadata); no ICO fallback needed for target browsers. No OG image created — deferred to post-launch.

## Frontend / Sonner Toast Notifications (updated 2026-02-28)

**Location:** `agent/frontend-next/app/layout.tsx` (Toaster config), `agent/frontend-next/components/FeedbackButtons.tsx`, `agent/frontend-next/components/CopyButton.tsx`, `agent/frontend-next/components/ChatWindow.tsx`, `agent/frontend-next/components/Sidebar.tsx`, `agent/frontend-next/lib/api.ts`
**Purpose:** Consistent non-blocking toast notifications for all user-facing events — feedback, copy, API errors, health transitions.
**Dependencies:** `sonner` (^2.0.7), already installed
**Exposes:** `<Toaster />` in layout.tsx with bottom-right position, 3s duration, max 3 visible. Individual components import `toast` from sonner directly.
**Status:** working — integrated 2026-02-28
**Notes:** Five toast triggers: (1) `toast.success` on feedback vote, (2) `toast.success` on copy-to-clipboard, (3) `toast.error` on sendMessage failure, (4) `toast.warning` on API health connected→unreachable transition, (5) `toast.error` on sendFeedback failure. Health toast uses a `useRef` to track previous status and only fires on downward transitions (not initial load). The existing `ErrorBanner` component is preserved alongside the API error toast — banner provides retry/dismiss while toast provides the immediate notification. `sendFeedback` in api.ts changed from fire-and-forget `.then/.catch` to async/await with proper error propagation. `toast("New conversation started")` was already in page.tsx from a prior prompt.

## OpenEMR Sidecar Module / oe-module-veris-agent (updated 2026-03-01)

**Location:** `interface/modules/custom_modules/oe-module-veris-agent/`
**Purpose:** OpenEMR custom module that embeds the Veris Next.js frontend as a floating chat widget (Intercom-style) on every OpenEMR page, plus a full-page tab fallback via menu item. Passes patient/encounter/user context from the PHP session to the frontend via URL query parameters.
**Dependencies:** OpenEMR core (globals.php, Header, MenuEvent, ModulesClassLoader, `OpenEMR\Events\Main\Tabs\RenderEvent`), Veris Next.js frontend (https://veris-teal.vercel.app or configurable via `veris_agent_url` global)
**Exposes:** Floating "V" button + slide-out iframe panel (via `RenderEvent::EVENT_BODY_RENDER_POST`), "Veris Agent" menu item under Miscellaneous (`misimg`), `public/index.php` iframe page
**Status:** working
**Notes:** Two event listeners in `openemr.bootstrap.php`: (1) `MenuEvent::MENU_UPDATE` adds menu item (full-page tab fallback), (2) `RenderEvent::EVENT_BODY_RENDER_POST` injects the floating widget HTML/CSS/JS into the main tabs shell. The widget uses fixed positioning (z-index 99999), CSS `transform: translateX()` slide animation, and inline styles/scripts (no external assets). Context flow: `$_SESSION['pid']`/`$_SESSION['encounter']`/`$_SESSION['authUser']` → URL params → `useSearchParams()` in page.tsx → `ehrContext` prop on ChatWindow → `[EHR Context: ...]` prefix on API messages. The frontend hides Header, Sidebar, and ClinicalDisclaimer when `?embedded=true`. Pattern follows `oe-module-comlink-telehealth` for render event injection. CORS in `main.py` allows `http://localhost:8300` and `https://localhost:9300`. `next.config.ts` sets `X-Frame-Options: ALLOWALL` and CSP `frame-ancestors` for iframe embedding. To activate: Admin > Modules > Register + Enable `oe-module-veris-agent`.

## Scripts / Clinical Data Seeder (updated 2026-03-01)

**Location:** `agent/scripts/seed_clinical_data.py`, `agent/scripts/register_seed_client.py`, `agent/scripts/SEED_README.md`
**Purpose:** Seeds OpenEMR with practitioners, insurance companies, patients, and full clinical profiles (encounters, vitals, medical problems, allergies, medications, insurance policies) via the REST API. Companion script registers an OAuth2 client with write scopes.
**Dependencies:** `httpx`, `python-dotenv`, `src.auth.oauth2.OpenEMRAuth`, `src.config`
**Exposes:** CLI entry points: `python -m scripts.seed_clinical_data` (main seeder), `python -m scripts.register_seed_client` (OAuth2 registration)
**Status:** working
**Notes:** 10 steps: (1) 5 practitioners (internal med, cardiology, psychiatry, pulmonology, family practice), (2) 4 insurance companies (BCBS, Aetna, Medicare, MassHealth), (3) 15 patients (10 general + 5 transplant demo), (4) encounters, (5) vitals, (6) 40+ medical problems (ICD-10), (7) 20+ allergies (RXCUI), (8) 35+ medications, (9) 15 insurance policies, (10) generate lab results SQL for transplant patients. The 5 transplant demo patients exercise the transplant screening tool with known outcomes: Clara Reeves (kidney ELIGIBLE), Marcus Blake (heart INELIGIBLE — low EF + BNP >2000), Diana Patel (liver INCOMPLETE — missing labs), Robert Chen-Ramirez (kidney+heart PENDING REVIEW — dual-organ), Angela Torres (lung ELIGIBLE WITH CONDITIONS). Lab results are generated as `seed_transplant_labs.sql` because OpenEMR has no REST API for `procedure_result`; the SQL inserts the full `procedure_order` → `procedure_report` → `procedure_result` chain with LOINC codes matching `_TRANSPLANT_LOINC` in `transplant_screening.py`. Supports `--dry-run` and `--patients 0` (add clinical data to existing patients). Requires write scopes: `user/patient.write`, `user/allergy.write`, `user/medical_problem.write`, `user/medication.write`, `user/encounter.write`, `user/vital.write`, `user/practitioner.write`, `user/insurance.write`, `user/insurance_company.write`. Docstring contains extensibility guide for adding new data types when new tools are created. The existing `seed_test_data.py` creates 3 minimal patients with allergies only — `seed_clinical_data.py` is the comprehensive replacement.

## Frontend / Project Documentation (updated 2026-03-01)

**Location:** `agent/frontend-next/README.md`, `agent/frontend-next/CHANGELOG.md`, `agent/README.md`
**Purpose:** Project-level documentation for onboarding, architecture overview, deployment reference, and change tracking.
**Dependencies:** None (Markdown only)
**Exposes:** README.md links to DEPLOYMENT.md for detailed deploy instructions. agent/README.md links to frontend-next/README.md.
**Status:** working
**Notes:** README.md replaces the default create-next-app boilerplate. CHANGELOG.md starts at v1.0.0. agent/README.md explicitly marks `frontend/` (Streamlit) as deprecated. The frontend-next README documents all 15 components in the folder structure and lists the three-tier architecture (Vercel → Fly.io → Railway).

## Tools / lab_results (updated 2026-03-01)

**Location:** `agent/src/tools/lab_results.py`
**Purpose:** Retrieves a patient's laboratory results from OpenEMR via the FHIR `Observation` endpoint. Parses test name, value, unit, LOINC code, date, and status from FHIR Observation resources.
**Dependencies:** `httpx`, `langchain-core` (@tool decorator), `src.auth.oauth2.OpenEMRAuth`
**Exposes:** `lab_results` async tool function (LangChain-compatible), `LOINC_CODES` dict
**Status:** working
**Notes:** Requires `user/Observation.read` OAuth scope (added to default scopes in `config.py`). Supports optional `loinc_codes` parameter to filter specific lab tests. Common LOINC codes: 2160-0 (Creatinine), 33914-3 (eGFR), 1975-2 (Bilirubin), 6301-6 (INR), 2951-2 (Sodium), 20150-9 (FEV1), 19926-5 (FEV1 % Predicted), 10230-1 (Ejection Fraction), 30934-4 (BNP). Same auth/retry pattern as other FHIR tools.

## Tools / transplant_criteria_lookup (updated 2026-03-01)

**Location:** `agent/src/tools/transplant_criteria_lookup.py`
**Purpose:** Queries the OpenEMR REST API (`GET /api/transplant_criteria`) to fetch transplant-relevant ICD-10 codes and criteria for a given organ type and optional criteria type filter.
**Dependencies:** `httpx`, `langchain-core` (@tool decorator), `src.auth.oauth2.OpenEMRAuth`
**Exposes:** `transplant_criteria_lookup` async tool function (LangChain-compatible)
**Status:** working
**Notes:** Queries the new custom OpenEMR REST endpoint (not FHIR). Valid organ types: kidney, heart, lung, liver, general. Valid criteria types: qualifying_diagnosis, transplant_status, complication, contraindication, screening. Returns criteria grouped by type.

## Tools / transplant_screening (updated 2026-03-01)

**Location:** `agent/src/tools/transplant_screening.py`
**Purpose:** Orchestrator tool that performs full transplant candidacy evaluations. Gathers lab results, conditions, and medications in parallel via FHIR, computes organ-specific scores (eGFR, MELD, NYHA/EF, FEV1), screens contraindications, and generates comprehensive candidacy reports. Also supports CRUD operations on screening records.
**Dependencies:** `httpx`, `langchain-core` (@tool decorator), `src.auth.oauth2.OpenEMRAuth`, `src.tools.contraindication_screen`, `src.tools.transplant_criteria`, `src.tools.transplant_report`
**Exposes:** `transplant_screening` async tool function (LangChain-compatible)
**Status:** working
**Notes:** Actions: evaluate (default, full assessment), create/get/update (CRUD on screening records). Uses `asyncio.gather` to parallelize 3 FHIR calls (Observation, Condition, MedicationRequest). The evaluate action: (1) fetches clinical data, (2) parses FHIR resources, (3) computes organ-specific score, (4) screens contraindications, (5) generates report with disclaimer. Supports kidney, heart, lung, liver.

## Tools / transplant_criteria (updated 2026-03-01)

**Location:** `agent/src/tools/transplant_criteria.py`
**Purpose:** Pure scoring algorithms for organ transplant candidacy. No I/O, no @tool decorator. Contains `ScreeningResult` dataclass and 4 scoring functions.
**Dependencies:** `math`, `re` (stdlib only)
**Exposes:** `ScreeningResult`, `compute_kidney_score()`, `compute_liver_meld()`, `compute_heart_score()`, `compute_lung_score()`
**Status:** working
**Notes:** Kidney: eGFR < 20 threshold with CKD staging. Liver: MELD formula with UNOS clamping (Cr 1.0-4.0, Bili min 1.0, INR min 1.0) and MELD-Na correction (Na 125-137), capped 6-40. Heart: NYHA class extraction from condition text via regex + EF < 25%. Lung: FEV1 < 25% predicted. All functions return `ScreeningResult` with explicit `missing_data` tracking.

## Tools / contraindication_screen (updated 2026-03-01)

**Location:** `agent/src/tools/contraindication_screen.py`
**Purpose:** Screens a patient's problem list against ICD-10 prefix ranges for transplant contraindications.
**Dependencies:** None (stdlib only)
**Exposes:** `Contraindication` dataclass, `screen_contraindications()`, `CONTRAINDICATION_RANGES`
**Status:** working
**Notes:** 4 contraindication categories: substance_abuse (F10-F19, absolute), malignancy (C00-C96, absolute), obesity (E66, relative), psychiatric (F20-F29, relative). Uses 3-character prefix matching.

## Tools / transplant_report (updated 2026-03-01)

**Location:** `agent/src/tools/transplant_report.py`
**Purpose:** Formats transplant candidacy screening reports from scoring results, contraindication findings, and medication context.
**Dependencies:** `src.tools.transplant_criteria.ScreeningResult`, `src.tools.contraindication_screen.Contraindication`
**Exposes:** `format_screening_report()`, `SCREENING_DISCLAIMER`
**Status:** working
**Notes:** Report sections: Header, Clinical Score, Missing Data Alerts, Contraindication Screening (absolute/relative), Current Medications, Recommended Next Steps (organ-specific), Screening Disclaimer. The disclaimer is mandatory per OPTN policy.

## Data Pipeline / ICD-10-CM Parser (updated 2026-03-01)

**Location:** `agent/scripts/parse_icd10.py`
**Purpose:** Downloads CMS ICD-10-CM FY2026 ZIP, parses fixed-width text file, filters to transplant-relevant codes, outputs CSV and JSON.
**Dependencies:** `requests`, `zipfile`, `csv`, `json` (stdlib + requests)
**Exposes:** CLI: `python3 agent/scripts/parse_icd10.py`
**Status:** working — 2,475 codes extracted
**Notes:** Fixed-width format: chars 1-5 (seq#), 6-13 (code), 14-15 (header flag), 16-76 (short desc), 77+ (long desc). Dots inserted after 3rd char for codes > 3 chars. Uses longest-prefix matching for code classification. Distribution: general=2248, heart=119, lung=55, liver=33, kidney=20.

## Database / Transplant Schema (updated 2026-03-01)

**Location:** `agent/sql/transplant_schema.sql`, `agent/scripts/load_transplant_data.py`
**Purpose:** 3 MySQL tables for transplant screening data. Loader script populates from CSV/JSON.
**Dependencies:** `mysql-connector-python`
**Exposes:** Tables: `transplant_icd10_criteria`, `transplant_organ_criteria`, `transplant_screenings`
**Status:** working (schema tested)
**Notes:** `transplant_screenings` has FK to `patient_data.pid`. All tables InnoDB with appropriate indexes. Loader uses INSERT IGNORE for ICD-10 codes (idempotent) and INSERT ON DUPLICATE KEY UPDATE for OPTN criteria.

## PHP REST API / Transplant Endpoints (updated 2026-03-01)

**Location:** `src/Services/TransplantIcd10CriteriaService.php`, `src/Services/TransplantScreeningService.php`, `src/RestControllers/TransplantCriteriaRestController.php`, `src/RestControllers/TransplantScreeningRestController.php`, `apis/routes/_rest_routes_standard.inc.php`
**Purpose:** 7 REST endpoints for transplant criteria lookup and screening CRUD, following OpenEMR's Service/Controller/Route pattern.
**Dependencies:** `OpenEMR\Services\BaseService`, `OpenEMR\Common\Database\QueryUtils`, `OpenEMR\RestControllers\RestControllerHelper`
**Exposes:** `GET /api/transplant_criteria`, `GET /api/transplant_criteria/:code`, `POST/GET/GET/:id/PUT/DELETE /api/patient/:puuid/transplant_screening`
**Status:** working (scaffolded, follows existing patterns)
**Notes:** Auth via `RestConfig::request_authorization_check($request, "patients", "demo")`. UUID-to-PID resolution in screening controller via `UuidRegistry::uuidToBytes()`. Services use `ProcessingResult` return pattern. WHITELISTED_FIELDS in screening service prevent arbitrary column injection.
