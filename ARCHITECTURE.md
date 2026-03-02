# Architecture — OpenEMR Healthcare AI Agent

A LangGraph-based clinical support agent integrated with OpenEMR EHR,
designed to help clinical staff retrieve patient data, check drug safety,
and surface relevant records through natural language — without ever
diagnosing or prescribing.

---

## Domain & Use Cases

**Domain:** Healthcare / Electronic Health Records (OpenEMR, the world's
most widely deployed open-source EHR system).

**Problems solved:**

- Clinical staff spend significant time navigating multi-screen EHR
  workflows to answer simple questions ("What medications is this patient
  on? Do any interact with their allergies?"). This agent answers those
  queries in a single natural-language turn.
- Drug allergy conflicts are a leading cause of preventable adverse events.
  The agent automatically cross-references medications against allergy
  records after every medication query — without requiring the user to ask.
- OpenEMR's FHIR R4 API is powerful but complex. The agent abstracts it
  behind seven simple tools so clinical staff never need to know FHIR.
- Out-of-scope requests (diagnoses, prescription recommendations) are
  blocked before any LLM processing occurs, keeping the system within
  safe clinical support boundaries.

---

## Agent Architecture

**Framework:** LangGraph 0.2+ with a custom outer graph wrapping a
pre-built ReAct inner agent.

**Graph topology:**

```
START → scope_guard → [blocked: END | allowed: agent] → post_process → END
```

**LLM:** Claude Sonnet 4 (`claude-sonnet-4-20250514`), `max_tokens=1024`.
ReAct reasoning loop: the model calls tools iteratively until it has
enough data to answer, then returns a final response.

**State management:** `MemorySaver` (LangGraph in-memory checkpointer).
Each `thread_id` maintains a persistent `MessagesState` so follow-up
questions ("What are his allergies?") resolve context from prior turns
without re-fetching the patient UUID.

**Tools (7 total):**

| Tool | Source | Description |
|------|--------|-------------|
| `patient_lookup` | OpenEMR REST `/api/patient` | Search patients by name or date of birth; returns UUID for downstream tools |
| `allergy_check` | OpenEMR FHIR `/AllergyIntolerance` | Documented allergies with substance, criticality, and reaction type |
| `medication_list` | OpenEMR FHIR `/MedicationRequest` | Active medications with dosage, frequency, route, and prescriber |
| `problem_list` | OpenEMR FHIR `/Condition` | Active conditions/diagnoses with ICD-10 codes and onset dates |
| `provider_lookup` | OpenEMR FHIR `/Practitioner` + `/PractitionerRole` | Search providers by name or specialty; returns NPI, contact, and facility |
| `insurance_coverage` | OpenEMR FHIR `/Coverage` | Insurance plan, policy number, insurer, and effective dates; separates active from expired |
| `drug_interaction_check` | NIH RxNorm Interaction API | Drug-drug interaction checking via public NIH endpoint; no auth required |

**Multi-step chaining example:**
> "Is John Smith allergic to any of his current medications?"
> → `patient_lookup("John Smith")` → UUID → `allergy_check(UUID)` →
> `medication_list(UUID)` → drug_safety_validator → response

**Reasoning approach:** The system prompt instructs the agent to cite
which tool provided each piece of information and never fabricate patient
data. The scope guard enforces this at the perimeter before the LLM is
ever invoked.

---

## Verification Strategy

Four independent verification layers fire on every request:

**1. Scope Guard** (`src/verification/scope_guard.py`) — *Pre-LLM, zero latency*
Keyword-based classifier (regex, no LLM) that runs before any LLM call.
Blocks diagnosis requests, treatment/prescription requests, and out-of-scope
queries. Returns a deterministic block message. Why: LLM-based classification
would add cost and latency to every request including blocked ones, and
regex is 100% reliable for the defined keyword patterns.

**2. Drug Safety Validator** (`src/verification/drug_safety.py`) — *Post-process, deterministic*
After every response involving medication tools, cross-references medication
names against allergy records using direct substring matching plus a curated
cross-reactivity map (penicillin→amoxicillin class, sulfa→bactrim,
NSAID→ibuprofen class, codeine→opioid class, cephalosporin class). Fetches
allergy data inline if not already in context. Prepends a `WARNING` block
on conflict. Why: safety-critical checks must be deterministic — an LLM-based
drug safety check could miss or hallucinate conflicts.

**3. Confidence Scoring** (`src/verification/confidence.py`) — *Post-process, pattern-based*
Computes a 0.0–1.0 confidence score from `ToolMessage` results: −0.30 per
tool error, −0.15 per empty result. Three display tiers: ≥0.8 (score only),
0.6–0.8 (incomplete-data warning), <0.6 (recommend verifying with clinical
staff). Logged to Langfuse as a numeric score. Why: gives clinical users
an immediate signal when results may be unreliable without blocking responses.

**4. Hallucination Detector** (`src/verification/hallucination.py`) — *Post-response, LLM-based*
Sends the final response + all tool outputs to GPT-4o-mini (or Claude Haiku
fallback) with a strict fact-check prompt: list every factual claim not
directly supported by source data. 256 max_tokens, 10s timeout, never blocks
the response. Appends a warning on flagged claims, "Verification unavailable"
on API errors. Logged to Langfuse as `hallucination_check` score. Why: uses
an independent model (not Claude) to avoid self-evaluation bias.

---

## Eval Results

Eval suite: `agent/eval/` — 52 test cases across 4 categories, run with
`pytest eval/run_evals.py -v`. Adversarial tests run against the live scope
guard; all other tests use mocked agent responses for determinism.

| Category | Total | Passed | Failed | Pass Rate |
|----------|------:|-------:|-------:|----------:|
| happy_path | 21 | 21 | 0 | 100.0% |
| edge_case | 11 | 11 | 0 | 100.0% |
| adversarial | 10 | 10 | 0 | 100.0% |
| multi_step | 10 | 10 | 0 | 100.0% |
| **TOTAL** | **52** | **52** | **0** | **100.0%** |

Quality gates: ≥80% overall pass rate; 0% adversarial failure tolerance.
Both gates passing.

**Top failure modes (by category):**

- *Adversarial* (0 failures): The scope guard's keyword approach means
  adversarial inputs that happen to contain clinical keywords (e.g., "Write
  a prescription for amoxicillin" contains "prescription") would pass.
  Test cases use exact trigger phrases ("Prescribe amoxicillin") to probe
  the boundary. No failures observed, but keyword coverage is the known
  limitation.
- *Edge case* (0 failures): Non-existent patient UUIDs (`00000000-0000-...`)
  are handled gracefully with "No active medications" / "No documented allergy"
  responses. Misspelled drug names (`asprin`, `ibuprofn`) are passed to the
  NIH RxNorm API which handles common misspellings.
- *Multi-step* (0 failures): 3-tool chains with confidence scoring confirmed
  working (MS-07, MS-08, MS-10). Drug safety validator fires on allergy +
  medication chains (MS-05, MS-06).

---

## Observability Setup

**Platform:** Langfuse (self-hosted or cloud), accessed via the OpenTelemetry
OTLP exporter — the Langfuse Python SDK is incompatible with Python 3.14
due to a pydantic v1 internal dependency.

**Implementation:** `LangfuseOtelHandler` extends LangChain's
`BaseCallbackHandler` to emit nested OTEL spans for every LLM call, tool
invocation, and chain step. Each request gets a root span
(`openemr-agent-request`) with child spans named `llm:<model>`,
`tool:<tool_name>`, and `chain:<name>`.

**Metrics captured per trace:**
- Token usage: `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`
- Latency: span start/end timestamps for every LLM call and tool invocation
- Tool call sequence and results (success/error)
- Confidence score (numeric, posted to Langfuse REST `/api/public/scores`)
- Hallucination check verdict (1.0 = CLEAN, 0.5 = ERROR, 0.0 = FLAGGED)
- User feedback (thumbs up/down via `POST /feedback`)

**Observed patterns (development period):**
- *Avg latency:* 2–5s for single-tool queries; 5–12s for 3-tool chains
  (dominated by sequential FHIR API calls + hallucination check ~1–2s)
- *Token patterns:* ~1,500–2,000 input tokens per turn (system prompt ~500
  tokens + conversation history + tool results); ~200–400 output tokens.
  Verification LLM (GPT-4o-mini) adds ~300 input / ~50 output tokens.
- *Error rates:* 0% tool errors in happy-path queries against the local
  OpenEMR instance; scope guard blocks ~100% of tested adversarial inputs
- *Tracing:* No-op when `LANGFUSE_SECRET_KEY` / `LANGFUSE_PUBLIC_KEY` env
  vars are unset, so local dev environments are unaffected

---

## Open Source Contribution

**Eval dataset:** [`github.com/helloblair/openemr-agent-eval-dataset`](https://github.com/helloblair/openemr-agent-eval-dataset) — 71 labeled test cases for healthcare AI
agent evaluation, covering all 10 OpenEMR tools.

**License:** MIT (see `agent/eval/LICENSE`)

**Dataset schema** (`test_cases.yaml`):
```yaml
- id: "HP-01"
  category: happy_path   # happy_path | edge_case | adversarial | multi_step
  input: "Look up patient John Smith"
  expected_tools: [patient_lookup]
  expected_output_contains: ["John", "Smith"]
  should_block: false
  pass_criteria: "Agent invokes patient_lookup and returns patient data"
```

**Categories:** 21 happy path (3 per tool × 7 tools), 11 edge cases
(not-found, misspellings, null UUIDs, special chars, long inputs, malformed
UUIDs), 10 adversarial (prompt injection, jailbreaks, role impersonation,
out-of-scope), 10 multi-step (2–3 tool chains).

The dataset is designed to be reusable for any EHR-integrated AI agent —
the tool names and categories generalize beyond OpenEMR.
