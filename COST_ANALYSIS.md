# Cost Analysis — OpenEMR Healthcare AI Agent

Pricing as of February 2026. Claude Sonnet 4: **$3.00/M input tokens,
$15.00/M output tokens**. GPT-4o-mini (verification): **$0.15/M input,
$0.60/M output**.

---

## Development Costs

Estimated from sprint activity (integration testing, eval runs, debugging
sessions logged in `docs/CHANGELOG_SHOWCASE_SPRINT.md`):

| Item | Estimate | Tokens | Cost |
|------|----------|--------|------|
| Integration testing (6 end-to-end runs × ~10 turns) | ~60 queries | 60 × 2,000 input / 400 output | $0.36 in / $0.36 out |
| Eval suite runs (3 full runs × 42 non-blocked cases) | ~126 agent calls | 126 × 2,000 in / 300 out | $0.76 in / $0.57 out |
| Ad-hoc debugging & development queries | ~200 queries | 200 × 2,000 in / 350 out | $1.20 in / $1.05 out |
| GPT-4o-mini verification (all above, ~386 queries) | 386 calls | 386 × 300 in / 50 out | $0.017 in / $0.012 out |
| **Total development** | **~386 queries** | **~1.13M in / ~255K out** | **~$5.95** |

**Key token assumptions:**
- Input: ~500 tokens system prompt + ~800 tokens conversation/tool results
  + ~700 tokens tool call overhead = ~2,000 tokens avg per turn
- Output: ~300–400 tokens final response avg
- Verification (GPT-4o-mini): ~300 input (response + tool outputs, truncated)
  + ~50 output tokens per call

**Actual development cost: approximately $5–8** depending on exact query
volume and tool chain depth. The hallucination check adds <$0.05 to total
dev costs due to GPT-4o-mini's low pricing.

---

## Production Projections

Assumes: 2 queries/user/day, single-turn average, Claude Sonnet 4 pricing,
~$0.015/query fully loaded (Claude primary + GPT-4o-mini verification).

| Scale | Queries/day | Monthly Cost | Assumptions |
|-------|------------:|-------------:|-------------|
| 100 users | 200 | ~$90 | 2 q/user/day, $0.015/q |
| 1,000 users | 2,000 | ~$900 | same |
| 10,000 users | 20,000 | ~$9,000 | same |
| 100,000 users | 200,000 | ~$90,000 | same |

**Per-query cost breakdown (~$0.015):**
- Claude Sonnet 4 primary: ~2,000 input × $3/M = $0.006 + ~350 output ×
  $15/M = $0.005 → **$0.011**
- GPT-4o-mini verification: ~300 input × $0.15/M + ~50 output × $0.60/M
  → **$0.00008** (negligible)
- Infrastructure (FastAPI + Streamlit on Railway): ~$5–20/month fixed
- **Total per query: ~$0.012–0.015**

**Multi-step chain cost (3-tool queries):** ~2–3× single-turn cost due to
longer conversation context fed back to the model. 3-tool queries cost
~$0.025–0.035 each.

---

## Optimization Strategies

### 1. Cache Drug Interaction Results
The NIH RxNorm interaction API is stateless and deterministic — the same
drug pair always returns the same interactions. A Redis or in-memory cache
keyed on sorted drug name pairs (e.g., `aspirin+warfarin`) would eliminate
repeated API calls. Drug interaction data changes infrequently; a 24-hour
TTL is safe for clinical reference use.

**Estimated saving:** 30–50% reduction in drug_interaction_check tool call
latency; no direct LLM cost impact but faster responses improve UX.

### 2. Route Simple Queries to Cheaper Models
Queries classified as `DATA_RETRIEVAL` by the scope guard (patient lookup,
provider search) are simpler than clinical multi-step chains. These could
be routed to Claude Haiku 4.5 (~$0.80/M input, $4/M output — ~4× cheaper)
without meaningful quality loss.

**Estimated saving:** If 60% of queries are pure data retrieval:
`0.6 × 0.75 × $0.011 = ~$0.005/query` → **~33% LLM cost reduction**

Implementation: add a `model_tier` field to the scope guard output and
select LLM in the graph factory function.

### 3. Batch Verification Calls
Currently the hallucination check fires individually per request. At high
volume, batching 10–20 fact-check requests into a single GPT-4o-mini call
(separated by delimiters) would reduce per-call overhead. Already negligible
at current pricing, but meaningful at 100K+ queries/day.

### 4. Scope Guard Pre-emption (Already Implemented)
The keyword-based scope guard blocks invalid requests before any LLM call.
At the 100-user scale, if ~20% of inputs are out-of-scope (adversarial,
OOB queries), this saves ~$18/month. At 100K users, ~$18,000/month saved.

### 5. Conversation Context Pruning
`MemorySaver` accumulates all messages per thread. Long sessions grow token
counts significantly. Implementing a sliding window (last N turns) or
summarization step would cap per-turn input tokens and reduce cost for
power users with many follow-up queries in a single session.

---

## Cost Comparison: Current Architecture vs Alternatives

| Approach | Cost/Query | Trade-off |
|----------|-----------:|-----------|
| Claude Sonnet 4 + GPT-4o-mini verification (current) | ~$0.015 | Best quality, independent verification |
| Claude Sonnet 4 only (no verification) | ~$0.011 | Cheaper, no hallucination check |
| Claude Haiku 4.5 for all queries | ~$0.003 | 5× cheaper, lower reasoning quality for complex chains |
| GPT-4o for primary LLM | ~$0.025 | More expensive, similar quality to Sonnet 4 |
| Fine-tuned smaller model (future) | ~$0.002 | Lowest cost, requires significant training investment |
