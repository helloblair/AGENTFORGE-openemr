# Migration Audit: Railway/Fly.io/Vercel → Vultr VPS

**Latest update:** 2026-03-20
**Scope:** Full migration history — from Railway to Fly.io+Vercel, then to single Vultr VPS.

---

## Phase 3: Vultr VPS Consolidation (2026-03-20)

**Goal:** Eliminate all platform dependencies (Railway, Fly.io, Vercel) and consolidate onto a single Vultr VPS.

**What changed:**
- Created `docker-compose.prod.yml` — all 5 services (MariaDB, OpenEMR, Agent, Frontend, Nginx)
- Created `docker/nginx/nginx.conf` — reverse proxy (`:443` for frontend+agent, `:8443` for OpenEMR)
- Created `.env.production.example` — complete env var template
- Created `scripts/deploy-vultr.sh` — one-command VPS setup
- Created `scripts/bootstrap-oauth.sh` — automated OAuth2 client registration
- Made CORS origins configurable via `CORS_ALLOWED_ORIGINS` env var
- Made CSP frame-ancestors permissive (`*`) for changing IPs
- Added `NEXT_PUBLIC_AGENT_API_URL` as Docker build arg to frontend Dockerfile
- Deleted `railway.toml`, `agent/railway.toml`, `agent/fly.toml`
- Updated all documentation

**Cost savings:** ~$10-25/month → ~$1.50/month (snapshot approach for portfolio use)

**Architecture:**
```
Vultr VPS → Nginx (:443/:8443)
               ├── /* → Next.js frontend (:3000)
               ├── /api/* → FastAPI agent (:8080)
               └── :8443/* → OpenEMR (:80) + MariaDB (:3306)
```

---

## Phase 1-2: Original Migration History (2026-03-02)

**Original date:** 2026-03-02
**Original scope:** Forensic analysis of the Railway-to-Fly.io migration for the agent FastAPI backend.

---

## Architecture Summary (Current State)

| Component | Platform | URL | Status |
|-----------|----------|-----|--------|
| Next.js Frontend | Vercel | `https://veris-teal.vercel.app` | LIVE |
| Agent FastAPI | Fly.io | `https://openemr-agent-api.fly.dev` | LIVE |
| OpenEMR Backend | Railway | `https://openemr-production-7df2.up.railway.app` | LIVE (intentionally still on Railway) |

**Key insight:** The OpenEMR backend was **never migrated** off Railway — only the agent FastAPI backend moved to Fly.io. Railway is still the correct platform for the OpenEMR EHR. This means Railway config for OpenEMR (`railway.toml`, `Dockerfile.openemr`, `docker/railway-entrypoint.sh`) is **still active and needed**.

---

## PHASE 1: Forensic Diagnosis — What's Broken?

### 1.1 Probable Root Causes (Ranked by Likelihood)

#### #1 — `OPENEMR_BASE_URL` on Fly.io may point to localhost (HIGH)

**Evidence:**
- `agent/src/config.py:14` defaults `OPENEMR_BASE_URL` to `http://localhost:8300`
- `agent/.env:3` (local file, git-ignored) sets `OPENEMR_BASE_URL="http://localhost:8300"`
- Root `.env:3` (local file, git-ignored) sets `OPENEMR_BASE_URL="https://openemr-production-7df2.up.railway.app"`
- The **Fly.io secret** must be set to the Railway URL. If it's missing or wrong, the health check at `main.py:94` will report `openemr_connected: false` and all tools will fail.

**Verification:**
```bash
fly ssh console -a openemr-agent-api -C "printenv OPENEMR_BASE_URL"
```

**Expected value:** `https://openemr-production-7df2.up.railway.app`

#### #2 — OAuth2 Client Credentials Mismatch (HIGH)

**Evidence:**
- `agent/src/config.py:15-16`: `OPENEMR_CLIENT_ID` and `OPENEMR_CLIENT_SECRET` default to empty strings
- MEMORY.md explicitly warns: "OAuth2 client credentials are per-OpenEMR-installation. Local Docker and production Railway have separate registries."
- `agent/.env:4-5` has credentials for the **local Docker** OpenEMR instance
- Root `.env:4-5` has **different** credentials for the Railway production instance
- Fly.io must have the **Railway production** credentials set as secrets

**Verification:**
```bash
fly ssh console -a openemr-agent-api -C "printenv OPENEMR_CLIENT_ID"
fly ssh console -a openemr-agent-api -C "printenv OPENEMR_CLIENT_SECRET"
```

**These must match the OAuth2 client registered on the Railway OpenEMR instance.**

#### #3 — SSL Verification Disabled but Railway Uses HTTPS (MEDIUM)

**Evidence:**
- `agent/src/auth/oauth2.py` uses `verify=False` in httpx.AsyncClient
- This actually **prevents** SSL errors but masks certificate issues
- Not a blocker, but worth noting — production should ideally verify SSL

#### #4 — CORS Allows Railway OpenEMR URL but NOT for Fly.io Domain (LOW)

**Evidence:**
- `agent/src/main.py:18-24` — CORS origins include:
  - `https://veris-teal.vercel.app` — correct for Vercel frontend
  - `https://openemr-production-7df2.up.railway.app` — correct for Railway OpenEMR widget
  - `http://localhost:3000` — correct for local dev
  - `http://localhost:8300` and `https://localhost:9300` — correct for local dev
- The CORS list looks **correct** for the current architecture. The Vercel frontend needs to talk to the Fly.io agent, and `veris-teal.vercel.app` is in the list.

**Verdict: CORS is correctly configured.** No issue here.

#### #5 — Health Check is Correct (NO ISSUE)

**Evidence:**
- `fly.toml:23-28` health checks `GET /health` every 15s with 5s timeout
- `main.py:89-98` implements `/health` that always returns `{"status": "healthy"}` — it does NOT fail if OpenEMR is unreachable (returns `openemr_connected: false` but status is still `healthy`)
- This means Fly.io will keep the machine running even if OpenEMR connectivity is broken

**Verdict: Health check design is correct.**

#### #6 — `.env.example` Port Discrepancy (LOW)

**Evidence:**
- `agent/frontend-next/.env.example:1` says `NEXT_PUBLIC_AGENT_API_URL=http://localhost:8400`
- But the agent runs on port `8080` (fly.toml, Dockerfile)
- `agent/frontend-next/.env.local:1` correctly says `http://localhost:8080`
- `agent/frontend-next/lib/api.ts:4` defaults to `http://localhost:8080`

**Impact:** Confusing for developers, but not breaking production. The `.env.example` is stale from an older config.

### 1.2 What's Working Correctly

| Component | Status | Evidence |
|-----------|--------|----------|
| Fly.io fly.toml | Correct | Port 8080, health check `/health`, 1 min machine, force HTTPS |
| Agent Dockerfile | Correct | Builds from pyproject.toml, runs uvicorn on `${PORT:-8080}` |
| CORS origins | Correct | Vercel frontend + Railway OpenEMR + localhost variants all present |
| Health check endpoint | Correct | Always returns healthy, reports OpenEMR connectivity separately |
| Next.js API client | Correct | Uses `NEXT_PUBLIC_AGENT_API_URL` env var with localhost fallback |
| Vercel deployment | Correct | `vercel.json` is minimal, `output: "standalone"` in next.config.ts |
| CSP header | Correct | Allows framing from Railway OpenEMR (needed for embedded widget) |

---

## PHASE 2: Railway Artifact Catalog

### Files Found with Railway References

| # | File | Type | Classification |
|---|------|------|---------------|
| 1 | `agent/railway.toml` | Config | 🟡 STALE — Agent is on Fly.io now |
| 2 | `railway.toml` | Config | 🟢 ACTIVE — Still used by Railway for OpenEMR backend |
| 3 | `Dockerfile.openemr` | Docker | 🟢 ACTIVE — Still used by Railway for OpenEMR backend |
| 4 | `docker/railway-entrypoint.sh` | Script | 🟢 ACTIVE — Still used by Railway for OpenEMR backend |
| 5 | `.dockerignore` | Config | 🟢 ACTIVE — References railway-entrypoint.sh for OpenEMR build |
| 6 | `agent/src/main.py:23` | Code | 🟢 ACTIVE — Railway OpenEMR URL in CORS (needed for widget) |
| 7 | `agent/frontend-next/next.config.ts:14` | Code | 🟢 ACTIVE — Railway OpenEMR URL in CSP (needed for widget framing) |
| 8 | `agent/scripts/seed_clinical_data.py` | Script | 🟡 STALE — Contains Railway CLI hint in print() |
| 9 | `agent/frontend-next/README.md` | Docs | 🟡 STALE — Architecture diagram mentions Railway alongside correct info |
| 10 | `agent/frontend-next/DEPLOYMENT.md` | Docs | 🟡 STALE — Section header "Fly.io / Railway" |
| 11 | `docs/CHANGELOG_SHOWCASE_SPRINT.md` | Docs | 🟢 SAFE — Historical log, should remain |
| 12 | `docs/CODEBASE_AUDIT.md` | Docs | 🟡 STALE — Some references to deprecated Railway agent domains |
| 13 | `COST_ANALYSIS.md` | Docs | 🟡 STALE — References "FastAPI + Streamlit on Railway" |
| 14 | `DEMO_SCRIPT.md` | Docs | 🟡 STALE — References Railway deployment |
| 15 | `docs/TRANSPLANT_SCREENING_PLAN.md` | Docs | 🟡 STALE — Deployment checklist references Railway MySQL |
| 16 | `docs/TRANSPLANT_SCREENING_IMPLEMENTATION.md` | Docs | 🟡 STALE — Same deployment checklist |
| 17 | `docs/PRE_SEARCH_DOCUMENT.md` | Docs | 🟢 SAFE — General mention of Railway experience |

### Classification Summary

- **🔴 BREAKING: 0 files** — Nothing is actively breaking due to Railway references
- **🟡 STALE: 8 files** — Dead config or outdated docs that should be cleaned up
- **🟢 ACTIVE/SAFE: 9 files** — Either still needed (OpenEMR backend) or historical

### Critical Distinction: What MUST Stay

The OpenEMR backend is **still deployed on Railway**. These files are ACTIVE and must NOT be removed:

1. `railway.toml` (root) — Railway build config for OpenEMR
2. `Dockerfile.openemr` — Custom OpenEMR image for Railway
3. `docker/railway-entrypoint.sh` — Railway startup script
4. `.dockerignore` (root) — Includes railway-entrypoint.sh
5. Railway OpenEMR URL in CORS (`main.py:23`) — Needed for cross-origin requests from widget
6. Railway OpenEMR URL in CSP (`next.config.ts:14`) — Needed for iframe embedding

---

## PHASE 3: Fix & Cleanup Plan

### Priority 1: Verify Fly.io Secrets (No Code Changes)

These are the secrets that MUST be set on Fly.io. Run these commands to verify:

```bash
# Check all required secrets exist
fly secrets list -a openemr-agent-api
```

**Required secrets:**

| Secret | Expected Value | Notes |
|--------|----------------|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Claude API key |
| `OPENEMR_BASE_URL` | `https://openemr-production-7df2.up.railway.app` | Must be Railway URL, NOT localhost |
| `OPENEMR_CLIENT_ID` | *(Railway OAuth2 client)* | Must match Railway OpenEMR registration |
| `OPENEMR_CLIENT_SECRET` | *(Railway OAuth2 secret)* | Must match Railway OpenEMR registration |
| `OPENAI_API_KEY` | `sk-proj-...` | For hallucination check (optional) |
| `LANGFUSE_SECRET_KEY` | `sk-lf-...` | Observability (optional) |
| `LANGFUSE_PUBLIC_KEY` | `pk-lf-...` | Observability (optional) |
| `LANGFUSE_HOST` | `https://us.cloud.langfuse.com` | Observability (optional) |

**If `OPENEMR_BASE_URL` is missing or set to localhost, set it:**
```bash
fly secrets set OPENEMR_BASE_URL="https://openemr-production-7df2.up.railway.app" -a openemr-agent-api
```

### Priority 2: Verify Vercel Environment Variable

On Vercel dashboard (or via CLI):
```bash
vercel env ls
```

**Required:**

| Variable | Expected Value |
|----------|----------------|
| `NEXT_PUBLIC_AGENT_API_URL` | `https://openemr-agent-api.fly.dev` |

The local `.env.local` has this set correctly for local dev. Vercel needs it set in the project settings.

### Priority 3: Remove `agent/railway.toml` (Dead Config)

This file is no longer used — the agent is deployed on Fly.io now.

**File:** `agent/railway.toml`
```toml
# DELETE THIS ENTIRE FILE
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

**Action:** `rm agent/railway.toml`

### Priority 4: Fix `.env.example` Port Discrepancy

**File:** `agent/frontend-next/.env.example`

**Current:**
```
NEXT_PUBLIC_AGENT_API_URL=http://localhost:8400
```

**Should be:**
```
NEXT_PUBLIC_AGENT_API_URL=http://localhost:8080
```

### Priority 5: Clean Up Seed Script Railway Reference

**File:** `agent/scripts/seed_clinical_data.py` (lines ~1358-1359)

**Current:**
```python
print("  Or via Railway:")
print("    railway run mysql -u root -p openemr < seed_transplant_labs.sql")
```

**Should be:**
```python
print("  Or via Railway (production OpenEMR):")
print("    railway run -s openemr mysql -u root -p openemr < seed_transplant_labs.sql")
```

Or remove entirely if Railway CLI is no longer used for database operations.

### Priority 6: Update COST_ANALYSIS.md

**File:** `COST_ANALYSIS.md` (line ~53)

**Current:**
```
Infrastructure (FastAPI + Streamlit on Railway): ~$5–20/month fixed
```

**Should reference Fly.io for FastAPI and Vercel for frontend.**

### Priority 7: Documentation Updates (Low Priority)

These docs have stale Railway agent references but are not breaking anything:

| File | What to Update |
|------|---------------|
| `DEMO_SCRIPT.md` | Update deployment references to reflect Fly.io for agent |
| `docs/CODEBASE_AUDIT.md` | Remove deprecated Railway agent domain references |
| `docs/TRANSPLANT_SCREENING_PLAN.md` | Update deployment checklist |
| `docs/TRANSPLANT_SCREENING_IMPLEMENTATION.md` | Update deployment checklist |
| `agent/frontend-next/README.md` | Update architecture diagram |
| `agent/frontend-next/DEPLOYMENT.md` | Clarify Fly.io is primary for agent |

---

## PHASE 4: Verification Checklist

### After Applying Fixes

#### 1. Fly.io Agent API Health

```bash
# Check the agent is running
fly status -a openemr-agent-api

# Check secrets are set (should list all required)
fly secrets list -a openemr-agent-api

# Verify OPENEMR_BASE_URL inside the container
fly ssh console -a openemr-agent-api -C "printenv OPENEMR_BASE_URL"
# Expected: https://openemr-production-7df2.up.railway.app

# Verify OAuth2 credentials are set
fly ssh console -a openemr-agent-api -C "printenv OPENEMR_CLIENT_ID"
# Expected: non-empty string

# Hit the health endpoint
curl -s https://openemr-agent-api.fly.dev/health | python3 -m json.tool
# Expected: {"status": "healthy", "openemr_connected": true}
```

**If `openemr_connected: false`:**
- Check OPENEMR_BASE_URL is the Railway URL
- Check Railway OpenEMR is actually running: `curl -s https://openemr-production-7df2.up.railway.app/apis/default/fhir/metadata | head -c 200`
- Check OAuth2 credentials are correct and the client is enabled in Railway OpenEMR admin

#### 2. Vercel Frontend Health

```bash
# Hit the frontend
curl -sI https://veris-teal.vercel.app
# Expected: HTTP 200

# Check CSP header
curl -sI https://veris-teal.vercel.app | grep -i content-security-policy
# Expected: frame-ancestors 'self' ... https://openemr-production-7df2.up.railway.app
```

#### 3. End-to-End Chat Test

```bash
# Send a test message through the agent
curl -s -X POST https://openemr-agent-api.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, what can you help me with?", "thread_id": "test-1"}' \
  | python3 -m json.tool
# Expected: JSON with response, thread_id, tools_used, confidence_score
```

#### 4. Railway OpenEMR Backend

```bash
# Verify OpenEMR is accessible
curl -s https://openemr-production-7df2.up.railway.app/apis/default/fhir/metadata | head -c 300
# Expected: FHIR CapabilityStatement JSON

# Verify OAuth2 registration endpoint
curl -s https://openemr-production-7df2.up.railway.app/oauth2/default/.well-known/openid-configuration | python3 -m json.tool
# Expected: OpenID Connect discovery document
```

#### 5. Widget Embedding (Manual Browser Test)

1. Log into OpenEMR at `https://openemr-production-7df2.up.railway.app`
2. Look for the "V" floating button in the bottom-right corner
3. Click it — the Veris Agent panel should slide open
4. The iframe should load `https://veris-teal.vercel.app/?embedded=true&...`
5. Send a message — it should reach `https://openemr-agent-api.fly.dev/chat`

#### 6. Fly.io Logs

```bash
# Stream live logs
fly logs -a openemr-agent-api

# What to look for:
# - Uvicorn startup: "Uvicorn running on http://0.0.0.0:8080"
# - Health check hits: "GET /health" every 15 seconds
# - OpenEMR auth errors: "OAuth2" / "401" / "token" failures
# - Chat requests: "POST /chat" entries
```

#### 7. DNS and Domains

| Domain | Expected Target |
|--------|----------------|
| `openemr-agent-api.fly.dev` | Fly.io (auto-managed, no custom DNS needed) |
| `veris-teal.vercel.app` | Vercel (auto-managed, no custom DNS needed) |
| `openemr-production-7df2.up.railway.app` | Railway (auto-managed) |

No custom domain DNS records to verify — all three services use platform-provided subdomains.

---

## Security Notes

### Critical: API Keys in Git-Tracked `.env.example` (Root)

The root `.env.example` file (tracked in git) is fine — it has placeholder values. But:

1. `agent/.env` contains **live API keys** (Anthropic, OpenAI, Langfuse, OpenEMR OAuth2)
2. This file IS git-ignored (`.gitignore` has `.env`)
3. However, MEMORY.md warns it was previously committed — **git history contains the keys**
4. Before making the repo public, run: `git filter-branch` or `bfg` to purge `.env` from history
5. Rotate all keys after purging

### Root `.env.local` Contains Vercel OIDC Token

The file `.env.local` (git-ignored) was created by `vercel link` and contains a Vercel OIDC token. This is expected and local-only.

---

## Summary

**The migration from Railway to Fly.io for the agent FastAPI backend appears structurally complete.** The most likely issues are:

1. **Missing or wrong Fly.io secrets** — especially `OPENEMR_BASE_URL` (must be the Railway URL, not localhost)
2. **OAuth2 credential mismatch** — Fly.io needs the Railway-registered OAuth2 client, not the local Docker one
3. **Stale `agent/railway.toml`** — Dead config that should be deleted
4. **`.env.example` port mismatch** — Says 8400 but should say 8080

Everything else (CORS, CSP, health checks, Dockerfile, fly.toml) is correctly configured. The OpenEMR backend on Railway with its `railway.toml`, `Dockerfile.openemr`, and `railway-entrypoint.sh` should all remain — they're still actively used.
