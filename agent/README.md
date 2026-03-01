# Veris Agent — OpenEMR Clinical Intelligence

LangGraph-based AI agent providing clinical decision support on top of OpenEMR.

## Frontends

| Directory | Stack | Status |
|-----------|-------|--------|
| `frontend-next/` | Next.js 16, TypeScript, Tailwind CSS | **Production** — deployed to Vercel |
| `frontend/` | Streamlit | **Deprecated** — will be removed in a future release |

> **Note:** `frontend-next/` is the production frontend. See its
> [README](frontend-next/README.md) for setup and deployment instructions.
> The Streamlit frontend in `frontend/` is deprecated and should not be used
> for new development.

## Project Structure

```
agent/
├── src/                # FastAPI backend + LangGraph agent
│   ├── main.py         # FastAPI entry point
│   ├── tools/          # 7 clinical tools (patient, allergy, medication, etc.)
│   ├── verification/   # Safety systems (scope guard, drug safety, confidence, hallucination)
│   └── observability/  # Langfuse tracing
├── eval/               # Evaluation framework (52 test cases)
├── tests/              # Unit and integration tests
├── frontend-next/      # Production Next.js frontend
├── frontend/           # Deprecated Streamlit frontend
├── scripts/            # Utility scripts
├── Dockerfile          # Agent API Docker build
├── fly.toml            # Fly.io deployment config
└── pyproject.toml      # Python dependencies
```

## Quick Start

See [frontend-next/README.md](frontend-next/README.md) for the frontend, and
[frontend-next/DEPLOYMENT.md](frontend-next/DEPLOYMENT.md) for full deployment
instructions.
