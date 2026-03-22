# Veris Demo Script — AgentForge + $500 Bounty

**Total runtime target:** 4:00–4:30 (well within 3–5 minute window)
**App name:** Veris | Clinical Intelligence
**URLs (Vultr VPS — restore snapshot before demo):**
- Frontend: https://YOUR_VPS_IP/
- Agent API: https://YOUR_VPS_IP/api/health
- OpenEMR: https://YOUR_VPS_IP:8443/
- Langfuse: https://us.cloud.langfuse.com
- GitHub: https://github.com/helloblair/AGENTFORGE-openemr
- Eval dataset: https://github.com/helloblair/openemr-agent-eval-dataset

> **IMPORTANT — Patient name corrections:**
> The 5 seeded patients are: **Clara Reeves**, **Marcus Blake** (not Marcus Johnson), **Diana Patel**, **Robert Chen-Ramirez** (not Robert Chen), **Angela Torres**. Use the exact names below during recording.

---

## PRE-RECORDING CHECKLIST

- [ ] Restore Vultr snapshot and SSH in to verify services are running
- [ ] Open Veris frontend in browser (https://YOUR_VPS_IP/)
- [ ] Confirm sidebar shows green dots for API + OpenEMR
- [ ] Open Langfuse dashboard in a second browser tab
- [ ] Open terminal with eval runner ready (`cd agent && python eval/run_evals.py`)
- [ ] Open GitHub repo page in a third tab
- [ ] Clear any previous chat threads (click "New Chat")
- [ ] Screen recording software capturing full screen at 1080p+
- [ ] Microphone tested and levels set

---

## SCENE 1: OPENING — "What This Is"
**Duration:** 15–20 seconds
**Screen:** Veris frontend landing page (https://veris-teal.vercel.app) — empty chat state with sidebar visible

**Action:**
1. Show the full Veris interface — header ("Veris | Clinical Intelligence"), sidebar with example queries, health status dots (green), clinical disclaimer footer
2. Hover briefly over the example queries in the sidebar

**Narration:**
> "This is Veris, a healthcare AI agent I built on top of OpenEMR — the most widely deployed open-source electronic health records system. Veris helps clinical staff retrieve patient data, check drug safety, and now screen organ transplant candidates — all through natural language conversation."

**Tags:** [MVP-9] [DEL-8]

---

## SCENE 2: ARCHITECTURE FLASH — "How It's Built"
**Duration:** 20–25 seconds
**Screen:** Quick flash of GitHub repo structure, then back to the app

**Action:**
1. Switch to GitHub repo tab — show the repo README briefly (2–3 seconds)
2. Scroll to show directory structure or the architecture diagram if pinned
3. Switch back to Veris — do NOT linger on slides

**Narration:**
> "Under the hood: LangGraph ReAct agent powered by Claude Sonnet 4, with 10 tools that query OpenEMR's FHIR and REST APIs. The agent has a three-node graph — scope guard for safety, the ReAct reasoning loop, then post-processing with drug safety checks, confidence scoring, and hallucination detection via GPT-4o-mini. Deployed on Fly.io with observability through Langfuse."

**Tags:** [ARCH-1] [ARCH-2] [ARCH-3] [ARCH-4] [ARCH-5] [ARCH-6] [DEL-1] [DEL-4]

---

## SCENE 3: HAPPY PATH — Clara Reeves, Kidney Qualifier
**Duration:** 50–60 seconds
**Screen:** Veris chat interface

**Action:**
1. Click into the chat input
2. Type: **"Is Clara Reeves a candidate for a kidney transplant?"**
3. Press Enter — wait for response to stream in
4. As the response appears, narrate over the key sections
5. Point out (mouse hover or scroll to): the tool calls panel, the clinical score section, ICD-10 code reference, confidence bar

**Narration:**
> "Let's start with Clara Reeves — a 50-year-old patient on dialysis. I'm asking the agent to evaluate her kidney transplant candidacy."
>
> *(wait for response to appear)*
>
> "Notice what's happening: the agent first looked up Clara by name, then ran a full transplant screening. It pulled her labs — eGFR of 12, creatinine 6.8 — checked her diagnoses against OPTN criteria, and found ICD-10 code N18.6, end-stage renal disease. That eGFR of 12 is well under the 20 threshold, so she meets criteria."
>
> *(point to tool calls panel)* "You can see it called patient_lookup and transplant_screening."
>
> *(point to confidence bar)* "Confidence score is high because all tools returned data successfully."
>
> "No contraindications found — no substance abuse, no active malignancy. Clara is eligible."

**What to highlight:**
- Multi-tool chaining (patient_lookup → transplant_screening)
- ICD-10 N18.6 cross-reference in the response
- eGFR < 20 threshold evaluation
- Structured report format with clinical score, contraindications, next steps
- Confidence bar (should be green/high)
- Clinical disclaimer at bottom of response

**Tags:** [MVP-1] [MVP-2] [MVP-3] [MVP-4] [ARCH-1] [ARCH-4] [TOOL-3] [TOOL-4] [VER-3] [BOUNTY-1] [BOUNTY-2] [BOUNTY-5] [BOUNTY-6]

---

## SCENE 4: CONTRAINDICATION CATCH — Marcus Blake, Heart Ineligible
**Duration:** 35–45 seconds
**Screen:** Veris chat (same thread or new chat — either works)

**Action:**
1. Type: **"Evaluate Marcus Blake for heart transplant candidacy"**
2. Press Enter — wait for response
3. Point out the contraindication flags as they appear

**Narration:**
> "Now Marcus Blake — a 46-year-old with heart failure. Let's see if he qualifies for a heart transplant."
>
> *(wait for response)*
>
> "The agent found two red flags. First, an absolute contraindication: active alcohol dependence — ICD-10 code F10.20. That's an automatic disqualifier under OPTN guidelines. Second, a relative contraindication: morbid obesity, E66.01 — his BMI is 41.6, well above the 35 threshold for heart transplant."
>
> "But notice the agent doesn't just say 'no' — it explains WHY. His NYHA class is only II, which doesn't meet the Class III threshold, and his ejection fraction is 30%, above the 25% cutoff. The agent is enforcing real clinical criteria, not guessing."

**What to highlight:**
- Agent reasoning about WHY factors are disqualifying
- Absolute vs. relative contraindication distinction
- Domain constraint enforcement (BMI > 35, NYHA < III, EF > 25%)
- ICD-10 prefix matching (F10 = substance abuse range)
- This is where the bounty data source proves its value

**Tags:** [MVP-4] [VER-1] [VER-4] [ARCH-5] [EVAL-1] [BOUNTY-2] [BOUNTY-3] [BOUNTY-6]

---

## SCENE 5: MISSING EVALUATIONS — Diana Patel, Liver Incomplete
**Duration:** 30–40 seconds
**Screen:** Veris chat

**Action:**
1. Type: **"What's the transplant screening status for Diana Patel?"**
2. Press Enter — wait for response
3. Highlight the distinction between "meets MELD threshold" and "evaluation incomplete"

**Narration:**
> "Diana Patel has liver cirrhosis. The agent computes her MELD score — around 22 — which exceeds the 15-point threshold. So medically, she qualifies."
>
> "But look at this: the agent also identifies five missing evaluations — psychiatric eval, cardiac clearance, HLA typing, substance screening, and insurance confirmation. Her status is 'incomplete' because meeting the lab threshold is only part of the picture."
>
> "This is the real clinical value — the agent doesn't just check a box. It tells the coordinator exactly what's still needed before a referral can go through."

**What to highlight:**
- MELD score computation (formula using creatinine, bilirubin, INR, sodium)
- Distinction between "medically qualifies" and "evaluation incomplete"
- Specific missing items listed
- Real clinical workflow value — actionable output

**Tags:** [MVP-4] [TOOL-4] [EVAL-6] [VER-4] [VER-5] [BOUNTY-3] [BOUNTY-5]

---

## SCENE 6: CONVERSATION CONTINUITY — Follow-up on Diana Patel
**Duration:** 20–25 seconds
**Screen:** Veris chat (SAME thread — do NOT click "New Chat")

**Action:**
1. WITHOUT starting a new chat, type: **"Update her screening — mark the psychiatric evaluation as completed and passed"**
2. Press Enter — wait for response
3. Point out that the agent knows "her" = Diana Patel

**Narration:**
> "Now without starting a new chat, I ask the agent to update Diana's screening. Notice I just said 'her' — the agent remembers from context that we're talking about Diana Patel."
>
> *(wait for response)*
>
> "It updated the screening record through the REST API — that's a real CRUD update operation on the transplant_screenings table in OpenEMR's database. Conversation memory is working, and the data is persistent."

**What to highlight:**
- Conversation history maintained ("her" resolves to Diana Patel)
- CRUD Update operation on screening record
- State persistence across turns (thread_id-based MemorySaver)

**Tags:** [MVP-5] [ARCH-3] [BOUNTY-3]

---

## SCENE 7: COMPLEX REASONING — Robert Chen-Ramirez, Multi-Organ
**Duration:** 25–30 seconds
**Screen:** Veris chat (new chat)

**Action:**
1. Click "New Chat"
2. Type: **"Assess Robert Chen-Ramirez for transplant — he has both kidney and heart concerns"**
3. Press Enter — wait for response
4. Point out the dual evaluation and confidence nuance

**Narration:**
> "Robert Chen-Ramirez is the complex case — CKD stage 5 plus heart failure. I'm asking the agent to evaluate both organ systems."
>
> *(wait for response)*
>
> "For kidney, it's clear-cut: eGFR of 18, under the 20 threshold, NYHA Class III heart failure is documented. But for heart, his ejection fraction is 32% — above the 25% cutoff — even though NYHA III does meet criteria."
>
> "The agent doesn't force a binary answer. It flags the heart as needing multidisciplinary review. That's the kind of nuanced clinical reasoning that makes this useful."

**What to highlight:**
- Multi-step reasoning across organ systems
- Confidence variation (high for kidney, nuanced for heart)
- Agent NOT giving a false binary — recommending review instead
- Multi-organ complexity as a "wow" moment

**Tags:** [ARCH-1] [ARCH-4] [TOOL-4] [VER-3] [PERF-2] [BOUNTY-5]

---

## SCENE 8: TEMPORAL REASONING — Angela Torres, Resolved History
**Duration:** 20–30 seconds
**Screen:** Veris chat

**Action:**
1. Type: **"Is Angela Torres eligible for a lung transplant despite her smoking history?"**
2. Press Enter — wait for response
3. Highlight the temporal reasoning about resolved substance use

**Narration:**
> "Angela Torres has pulmonary fibrosis and a former smoking history. The naive approach would flag nicotine dependence as a contraindication and stop there."
>
> *(wait for response)*
>
> "But the agent checks the clinical status — her nicotine dependence code F17.210 is marked as resolved since March 2024. She's been clean over 24 months, which exceeds the 6-month OPTN requirement. Her FEV1 is 22% predicted, well under the 25% threshold. The agent correctly determines she's eligible."

**What to highlight:**
- Agent NOT naively flagging substance abuse as disqualifying
- Temporal reasoning — checking dates and resolved status, not just presence
- Citing specific sobriety requirement from OPTN criteria
- FEV1 scoring (22% < 25% threshold)

**Tags:** [EVAL-6] [VER-1] [VER-4] [BOUNTY-2] [BOUNTY-6]

---

## SCENE 9: ERROR HANDLING + SAFETY
**Duration:** 15–20 seconds
**Screen:** Veris chat

**Action:**
1. Type: **"Prescribe immunosuppressants for Clara Reeves"**
2. Press Enter — observe the scope guard blocking the request
3. Optionally, follow with: **"Look up patient ZZZZZ McFakename"** to show graceful empty result

**Narration:**
> "What happens when someone asks the agent to prescribe medications?"
>
> *(wait for block response)*
>
> "The scope guard catches this immediately — before it even reaches the LLM. The agent refuses to prescribe or recommend treatments. It stays within its clinical decision support lane."
>
> *(optionally show the non-existent patient query)*
>
> "And for data that doesn't exist, no crash — just a clear message that no patient was found."

**What to highlight:**
- Scope guard pre-LLM blocking (no tokens wasted on dangerous requests)
- Graceful failure on missing data
- Safety guardrails — agent won't cross clinical boundaries
- Human-in-the-loop escalation language in responses

**Tags:** [MVP-6] [EVAL-4] [VER-2] [VER-6] [ARCH-5] [PERF-1]

---

## SCENE 10: OBSERVABILITY DASHBOARD
**Duration:** 25–30 seconds
**Screen:** Langfuse dashboard (https://us.cloud.langfuse.com)

**Action:**
1. Switch to Langfuse tab
2. Show the traces list — click into one of the traces from the queries you just ran
3. Expand the waterfall/span view to show: LLM call → tool calls → response
4. Point out token usage, latency numbers, and scores

**Narration:**
> "Every request is traced end-to-end through Langfuse via OpenTelemetry."
>
> *(click into a trace)*
>
> "Here's the Clara Reeves query. You can see the full span waterfall — the LLM reasoning call, each tool invocation with its latency, and the final response. Token usage is tracked per call for cost analysis."
>
> *(point to scores section)*
>
> "Confidence and hallucination scores are logged as numeric metrics. This trace scored 1.0 confidence and passed hallucination detection — meaning GPT-4o-mini verified every claim against the source tool data."
>
> "PHI is automatically redacted before any data leaves the system."

**What to highlight:**
- Full request trace (input → reasoning → tool calls → output)
- Span waterfall visualization
- Latency breakdown per step
- Token usage and cost tracking
- Confidence and hallucination scores as logged metrics
- PHI redaction mention

**Tags:** [OBS-1] [OBS-2] [OBS-3] [OBS-4] [OBS-5] [OBS-6] [DEL-5] [PERF-1]

---

## SCENE 11: EVAL RESULTS
**Duration:** 15–20 seconds
**Screen:** Terminal running evals

**Action:**
1. Switch to terminal
2. Run: `python eval/run_evals.py`
3. Show the summary table as it prints

**Narration:**
> "The eval suite has 71 test cases across four categories: 29 happy path, 16 edge cases, 10 adversarial, and 16 multi-step chains."
>
> *(wait for results to print)*
>
> "71 out of 71 passing — 100% pass rate. The adversarial tests verify that the scope guard blocks prompt injection, jailbreak attempts, and out-of-scope requests with zero failures. And there's a 5-percentage-point regression threshold so any new changes that break tests get caught automatically."

**What to highlight:**
- 71 total test cases (exceeds the 50+ requirement)
- 100% pass rate (exceeds the 80% target)
- Category breakdown (happy path, edge, adversarial, multi-step)
- Regression detection threshold
- Bounty-specific transplant test cases included (19 of the 71)

**Tags:** [EVAL-1] [EVAL-2] [EVAL-3] [EVAL-4] [EVAL-5] [EVAL-6] [EVAL-7] [EVAL-8] [PERF-3] [PERF-4] [DEL-6] [BOUNTY-7]

---

## SCENE 12: BOUNTY FEATURE SUMMARY
**Duration:** 15–20 seconds
**Screen:** GitHub showing BOUNTY.md or quick scroll of the file

**Action:**
1. Switch to GitHub — open BOUNTY.md
2. Quick scroll through the sections (don't read the whole thing)

**Narration:**
> "For the bounty: I integrated the CMS ICD-10-CM FY2026 diagnostic code set — 2,475 transplant-relevant codes pulled from the official CMS ZIP file. These are loaded into OpenEMR's database and queried through the REST API by the agent."
>
> "The agent performs full CRUD operations on transplant screening records — we created screenings for Clara and updated Diana's in the demo. Five seeded patients each demonstrate a different clinical scenario: eligible, ineligible with contraindications, incomplete evaluations, multi-organ complexity, and resolved history with temporal reasoning."

**What to highlight:**
- External data source: CMS ICD-10-CM FY2026
- 2,475 codes loaded via OpenEMR's API
- CRUD operations demonstrated live (Create in Scene 3, Read in Scene 5, Update in Scene 6)
- 5 patients = 5 distinct clinical scenarios
- Full BOUNTY.md documentation

**Tags:** [BOUNTY-1] [BOUNTY-2] [BOUNTY-3] [BOUNTY-4] [BOUNTY-5] [BOUNTY-6] [BOUNTY-7]

---

## SCENE 13: CLOSE — Open Source + Links
**Duration:** 10–15 seconds
**Screen:** GitHub repo overview or README

**Action:**
1. Show GitHub repo one more time
2. Mention the open source contribution

**Narration:**
> "Everything is open source on GitHub. I published the 71-test evaluation dataset as a standalone MIT-licensed repo — it's reusable for any EHR-integrated AI agent. The app is live at veris-teal.vercel.app. Links in the description."

**Tags:** [DEL-1] [DEL-7] [DEL-8] [DEL-9]

---

## TIMING SUMMARY

| Scene | Topic | Target Duration | Cumulative |
|-------|-------|----------------|------------|
| 1 | Opening | 15–20s | 0:20 |
| 2 | Architecture | 20–25s | 0:45 |
| 3 | Clara Reeves (Kidney) | 50–60s | 1:45 |
| 4 | Marcus Blake (Heart) | 35–45s | 2:25 |
| 5 | Diana Patel (Liver) | 30–40s | 3:00 |
| 6 | Diana Follow-up | 20–25s | 3:25 |
| 7 | Robert Chen-Ramirez | 25–30s | 3:55 |
| 8 | Angela Torres (Lung) | 20–30s | 4:20 |
| 9 | Error Handling | 15–20s | 4:35 |
| 10 | Observability | 25–30s | 5:00 |
| 11 | Eval Results | 15–20s | 5:15 |
| 12 | Bounty Summary | 15–20s | 5:30 |
| 13 | Close | 10–15s | 5:40 |

**Total estimate: ~4:30–5:40**

### Scenes to trim if over 5 minutes:
1. **Combine Scenes 7+8** into a single "Advanced Reasoning" scene (~30s total instead of 50–60s): Ask about Robert, then quickly say "Angela Torres demonstrates temporal reasoning — resolved smoking history correctly evaluated as non-disqualifying." Save 20–30 seconds.
2. **Tighten Scene 3** — the longest scene. Cut narration about tool calls panel (the viewer can see it). Target 45s instead of 60s.
3. **Combine Scenes 12+13** — mention BOUNTY.md and open source in the same closing breath.

**With trims: ~4:00–4:30** (ideal range)

---

## REQUIREMENTS COVERAGE MATRIX

### MVP Requirements

| Requirement | Code | Demo Scene(s) | Status |
|-------------|------|---------------|--------|
| Agent responds to NL queries | MVP-1 | Scene 3 | Covered |
| At least 3 functional tools | MVP-2 | Scene 3 (patient_lookup + transplant_screening) | Covered (10 tools total) |
| Tool calls execute with structured results | MVP-3 | Scenes 3, 4, 5 | Covered |
| Agent synthesizes tool results into coherent responses | MVP-4 | Scenes 3, 4, 5, 7 | Covered |
| Conversation history maintained across turns | MVP-5 | Scene 6 | Covered |
| Basic error handling | MVP-6 | Scene 9 | Covered |
| At least one domain-specific verification check | MVP-7 | Scenes 4, 9 (scope guard, drug safety, contraindications) | Covered (4 systems) |
| 5+ test cases with expected outcomes | MVP-8 | Scene 11 | Covered (71 test cases) |
| Deployed and publicly accessible | MVP-9 | Scene 1 | Covered |

### Architecture Requirements

| Requirement | Code | Demo Scene(s) | Status |
|-------------|------|---------------|--------|
| Reasoning Engine: LLM with structured output | ARCH-1 | Scenes 2, 3, 7 | Covered |
| Tool Registry: defined tools with schemas | ARCH-2 | Scene 2 | Covered |
| Memory System: conversation history, state | ARCH-3 | Scene 6 | Covered |
| Orchestrator: decides when to use tools | ARCH-4 | Scenes 3, 7 | Covered |
| Verification Layer: domain-specific checks | ARCH-5 | Scenes 4, 9 | Covered |
| Output Formatter: structured responses, confidence | ARCH-6 | Scene 2 (mention), Scene 3 (shown) | Covered |

### Tool Requirements

| Requirement | Code | Demo Scene(s) | Status |
|-------------|------|---------------|--------|
| Minimum 5 tools | TOOL-1 | Scene 2 (stated: 10 tools) | Covered |
| Tools have clear schemas and structured outputs | TOOL-2 | Scenes 3–8 (visible in responses) | Covered |
| Agent chooses the right tool for each query | TOOL-3 | Scenes 3, 4, 5 | Covered |
| Agent chains tools for multi-step reasoning | TOOL-4 | Scenes 3, 5, 7 | Covered |

### Evaluation Framework

| Requirement | Code | Demo Scene(s) | Status |
|-------------|------|---------------|--------|
| Correctness testing | EVAL-1 | Scene 11 (happy path cases) | Covered |
| Tool selection testing | EVAL-2 | Scene 11 (expected_tools field) | Covered |
| Tool execution testing | EVAL-3 | Scene 11 | Covered |
| Safety testing | EVAL-4 | Scenes 9, 11 (adversarial cases) | Covered |
| Consistency testing | EVAL-5 | Scene 11 (deterministic mocked mode) | Covered |
| Edge case testing | EVAL-6 | Scenes 5, 8, 11 (16 edge cases) | Covered |
| Latency testing | EVAL-7 | Scene 11 (mention) + Scene 10 (shown) | Covered |
| 50+ test cases | EVAL-8 | Scene 11 (71 cases) | Covered |

### Observability

| Requirement | Code | Demo Scene(s) | Status |
|-------------|------|---------------|--------|
| Trace logging | OBS-1 | Scene 10 | Covered |
| Latency tracking | OBS-2 | Scene 10 | Covered |
| Error tracking | OBS-3 | Scene 10 | Covered |
| Token usage | OBS-4 | Scene 10 | Covered |
| Eval results | OBS-5 | Scene 10 (Langfuse scores) | Covered |
| User feedback mechanism | OBS-6 | Scene 10 (mention) + visible in UI (thumbs up/down) | Covered |

### Verification Systems

| Requirement | Code | Demo Scene(s) | Status |
|-------------|------|---------------|--------|
| Fact checking | VER-1 | Scenes 4, 8 (ICD-10 cross-reference) | Covered |
| Hallucination detection | VER-2 | Scene 9 (mention), Scene 10 (score shown) | Covered |
| Confidence scoring | VER-3 | Scenes 3, 7 (bar visible), Scene 10 (logged) | Covered |
| Domain constraints | VER-4 | Scenes 4, 5, 8 (clinical thresholds) | Covered |
| Output validation | VER-5 | Scene 5 (completeness check) | Covered |
| Human-in-the-loop escalation | VER-6 | Scene 9 (escalation language) | Covered |

### Performance Targets

| Requirement | Code | Demo Scene(s) | Status |
|-------------|------|---------------|--------|
| E2E latency < 5s (single tool) | PERF-1 | Scene 9 (scope guard instant), Scene 10 (latency visible) | Covered |
| Multi-step < 15s (3+ tools) | PERF-2 | Scene 7 (visible response time) | Covered |
| Tool success rate > 95% | PERF-3 | Scene 11 (100% pass rate) | Covered |
| Eval pass rate > 80% | PERF-4 | Scene 11 (100% pass rate) | Covered |
| Hallucination rate < 5% | PERF-5 | Scene 10 (hallucination scores in Langfuse) | Covered |
| Verification accuracy > 90% | PERF-6 | Scene 11 (100% pass rate on verification tests) | Covered |

### Deliverables

| Requirement | Code | Demo Scene(s) | Status |
|-------------|------|---------------|--------|
| GitHub repo with setup guide | DEL-1 | Scenes 2, 13 | Covered |
| Demo video 3-5 minutes | DEL-2 | This script IS the demo | Covered (this recording) |
| Pre-Search document | DEL-3 | — | Offline deliverable — not in video |
| Agent Architecture Doc | DEL-4 | Scene 2 (flash ARCHITECTURE.md) | Covered |
| AI Cost Analysis | DEL-5 | Scene 10 (token usage visible) | Covered (COST_ANALYSIS.md exists) |
| Eval dataset (50+ cases) | DEL-6 | Scene 11 | Covered (71 cases) |
| Open source contribution | DEL-7 | Scene 13 | Covered (published eval dataset) |
| Deployed application | DEL-8 | Scene 1 | Covered |
| Social post (X or LinkedIn) | DEL-9 | Scene 13 (mention) | Offline deliverable — post after recording |

### Bounty Requirements

| Requirement | Code | Demo Scene(s) | Status |
|-------------|------|---------------|--------|
| New data source relevant to OpenEMR | BOUNTY-1 | Scenes 3, 12 (CMS ICD-10-CM) | Covered |
| Agent accesses data through project's API | BOUNTY-2 | Scenes 3, 4, 8, 12 (REST API calls) | Covered |
| Stateful data with CRUD operations | BOUNTY-3 | Scenes 4, 5, 6, 12 (screening records) | Covered |
| BOUNTY.md documentation | BOUNTY-4 | Scene 12 | Covered |
| Most impactful customer use case | BOUNTY-5 | Scenes 3, 5, 7, 12 | Covered |
| Real data source integrated into app | BOUNTY-6 | Scenes 3, 4, 8, 12 (2,475 ICD-10 codes) | Covered |
| Reliable agent with evals/obs/verification | BOUNTY-7 | Scenes 10, 11, 12 | Covered |

### UNCOVERED REQUIREMENTS (Offline Deliverables)

| Requirement | Code | Action Needed |
|-------------|------|---------------|
| Pre-Search document | DEL-3 | Write and submit separately — not demonstrable in video |
| Social post | DEL-9 | Post to X or LinkedIn after recording — mention in video closing |

**All other requirements (53 of 55) are covered in the demo video.**

---

## SHOT LIST

Tape this next to your monitor while recording.

| # | Screen | Duration | Action | Key thing to say |
|---|--------|----------|--------|-----------------|
| 1 | Veris landing page | 15s | Show UI, green health dots, sidebar examples | "This is Veris, a healthcare AI agent built on OpenEMR" |
| 2 | GitHub repo → back to app | 20s | Flash repo structure, switch back fast | "LangGraph + Claude Sonnet 4, 10 tools, 3-node graph with scope guard and post-processing" |
| 3 | Veris chat | 50s | Type: "Is Clara Reeves a candidate for a kidney transplant?" | "eGFR 12, N18.6 end-stage renal disease, meets OPTN criteria — she's eligible" |
| 4 | Veris chat | 35s | Type: "Evaluate Marcus Blake for heart transplant candidacy" | "Caught F10.20 alcohol dependence + E66.01 obesity — two contraindications, NYHA only Class II" |
| 5 | Veris chat | 30s | Type: "What's the transplant screening status for Diana Patel?" | "MELD 22 meets threshold, but five evaluations still missing — status incomplete" |
| 6 | Veris chat (SAME thread!) | 20s | Type: "Update her screening — mark psychiatric evaluation as completed and passed" | "Agent remembers 'her' = Diana Patel, CRUD update on the screening record" |
| 7 | Veris chat (new) | 25s | Type: "Assess Robert Chen-Ramirez for transplant — kidney and heart concerns" | "Kidney clear at eGFR 18, heart needs multidisciplinary review — no false binary" |
| 8 | Veris chat | 20s | Type: "Is Angela Torres eligible for lung transplant despite smoking history?" | "F17.210 resolved, 24 months clean exceeds 6-month requirement, FEV1 22% qualifies" |
| 9 | Veris chat | 15s | Type: "Prescribe immunosuppressants for Clara Reeves" | "Scope guard blocks it before the LLM — agent stays in its clinical support lane" |
| 10 | Langfuse dashboard | 25s | Click into a trace, show span waterfall, scores | "Full end-to-end traces, token usage, confidence and hallucination scores, PHI redacted" |
| 11 | Terminal | 15s | Run: `python eval/run_evals.py` | "71 out of 71 passing — 100% across happy path, edge cases, adversarial, and multi-step" |
| 12 | GitHub BOUNTY.md | 15s | Scroll through sections quickly | "CMS ICD-10-CM FY2026, 2,475 codes, CRUD screening records, 5 demo patients" |
| 13 | GitHub repo overview | 10s | Show repo + deployed link | "Open source, eval dataset published under MIT, app live at veris-teal.vercel.app" |

**Total: ~4:15–4:30**

---

## FEATURE FLAGS — What's Built vs. What Might Need Attention

### Fully Functional (Confirmed in Codebase)
- [x] 10 tools registered and exported in `__init__.py`
- [x] All 7 REST API endpoints for transplant criteria + screening
- [x] 3 MySQL tables (transplant_icd10_criteria, transplant_organ_criteria, transplant_screenings)
- [x] 2,475 ICD-10 codes in CSV/JSON data files
- [x] 4 verification systems (scope_guard, drug_safety, confidence, hallucination)
- [x] Langfuse OTEL observability with PHI redaction
- [x] 71 eval test cases (100% pass rate)
- [x] Feedback buttons (thumbs up/down) in frontend
- [x] Confidence bar and escalation warning in frontend
- [x] Tool calls panel in frontend
- [x] 5 seeded patient profiles in `seed_clinical_data.py`
- [x] MemorySaver conversation state persistence
- [x] BOUNTY.md documentation
- [x] ARCHITECTURE.md (2-page agent architecture doc)
- [x] COST_ANALYSIS.md
- [x] Deployed: Vercel + Fly.io + Railway
- [x] Published eval dataset repo

### Verify Before Recording
- [ ] **Production database has transplant tables created** — Run `mysql < agent/sql/transplant_schema.sql` on Railway if not done
- [ ] **Production database has ICD-10 data loaded** — Run `python agent/scripts/load_transplant_data.py` against production
- [ ] **5 demo patients are seeded in production** — Run `python -m scripts.seed_clinical_data` against production OpenEMR
- [ ] **Lab results seeded** — Run `seed_transplant_labs.sql` against production
- [ ] **OAuth2 client registered with transplant scopes** on production
- [ ] **Langfuse credentials set** as Fly.io secrets (for traces to appear in dashboard)
- [ ] **Agent API is live** — Check https://openemr-agent-api.fly.dev/health returns `{"status": "healthy", "openemr_connected": true}`

### Offline Deliverables (Not in Video)
- [ ] Pre-Search document (DEL-3)
- [ ] Social post on X or LinkedIn (DEL-9)
