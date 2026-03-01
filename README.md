# OpenEMR Healthcare AI Agent

A LangGraph-powered clinical support agent integrated with OpenEMR — lets clinical staff look up patient records, check drug interactions, and review allergies using natural language, with 4 safety verification layers and full Langfuse observability.

---

## Architecture

```
User
 |
 v
Next.js UI  ──POST /chat──>  FastAPI Backend
                                    |
                                    v
                              LangGraph Graph
                              ┌─────────────────────────────┐
                              │  scope_guard (pre-LLM block) │
                              │         |                    │
                              │         v                    │
                              │   ReAct Agent (Claude Sonnet)│
                              │   ┌──────────────────────┐  │
                              │   │  patient_lookup       │  │
                              │   │  allergy_check        │──┼──> OpenEMR FHIR API
                              │   │  medication_list      │  │
                              │   │  problem_list         │  │
                              │   │  provider_lookup      │  │
                              │   │  insurance_coverage   │  │
                              │   │  drug_interaction_check│─┼──> NIH RxNorm API
                              │   └──────────────────────┘  │
                              │         |                    │
                              │         v                    │
                              │   post_process               │
                              │   (drug safety + disclaimers)│
                              └─────────────────────────────┘
                                    |
                                    v
                              Langfuse (observability)
                              traces, scores, feedback
```

---

## Setup

### Prerequisites

- Python 3.11+
- Docker + Docker Compose (for OpenEMR)
- Anthropic API key (Claude Sonnet 4)
- OpenAI API key (optional — GPT-4o-mini hallucination verification)
- Langfuse account (optional — observability)

### 1. Start OpenEMR

```bash
cd docker/development-easy
docker compose up --detach --wait
# App: http://localhost:8300  Login: admin / pass
```

### 2. Environment Variables

Copy and fill in `agent/.env`:

```bash
cp agent/.env.example agent/.env
```

Required variables:

```bash
OPENEMR_BASE_URL=http://localhost:8300
OPENEMR_CLIENT_ID=<oauth2-client-id>
OPENEMR_CLIENT_SECRET=<oauth2-client-secret>
ANTHROPIC_API_KEY=sk-ant-...

# Optional — verification and observability
OPENAI_API_KEY=sk-...
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

### 3. Install Dependencies

```bash
cd agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 4. Run

```bash
# FastAPI backend (port 8400)
cd agent
uvicorn src.main:app --reload --port 8400

# Streamlit frontend (port 8501) — new terminal
cd agent
streamlit run frontend/streamlit_app.py
```

Open http://localhost:8501

### Deployed Links

> **Frontend (Vercel):** https://veris-teal.vercel.app
> **Agent API (Fly.io):** https://openemr-agent-api.fly.dev

---

## Tools

| Tool | Source | Description |
|------|--------|-------------|
| `patient_lookup` | OpenEMR REST | Search patients by name or date of birth |
| `allergy_check` | OpenEMR FHIR | Documented allergies with substance, criticality, and reactions |
| `medication_list` | OpenEMR FHIR | Active medications with dosage, frequency, and prescriber |
| `problem_list` | OpenEMR FHIR | Active conditions/diagnoses with ICD-10 codes |
| `provider_lookup` | OpenEMR FHIR | Search providers by name or specialty |
| `insurance_coverage` | OpenEMR FHIR | Insurance plan, policy number, and coverage dates |
| `drug_interaction_check` | NIH RxNorm | Drug-drug interaction checking (no auth required) |

---

## Running the Eval Suite

52 test cases across 4 categories (happy path, edge cases, adversarial, multi-step).

```bash
cd agent

# Run with pytest (recommended — parallel, verbose)
python -m pytest eval/run_evals.py -v

# Run standalone (prints summary table)
python eval/run_evals.py
```

Quality gates enforced automatically:
- Overall pass rate >= 80%
- Adversarial (safety) failures: 0 tolerance

---

## Open Source Eval Dataset

The eval dataset is MIT-licensed and designed to be reusable for any
EHR-integrated AI agent evaluation.

**Public dataset:** [github.com/helloblair/AGENTFORGE-openemr/tree/master/agent/eval](https://github.com/helloblair/AGENTFORGE-openemr/tree/master/agent/eval)

- **52 labeled test cases** covering all 7 tools
- **4 categories:** happy_path, edge_case, adversarial, multi_step
- **Schema:** `id`, `category`, `input`, `expected_tools`,
  `expected_output_contains`, `should_block`, `pass_criteria`
- **License:** [MIT](agent/eval/LICENSE)

See [`agent/eval/README.md`](agent/eval/README.md) for full documentation.

---

## Architecture & Cost Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — full system design, verification strategy, eval results, observability
- [COST_ANALYSIS.md](COST_ANALYSIS.md) — dev costs, production projections, optimization strategies

---

---

[![Syntax Status](https://github.com/openemr/openemr/actions/workflows/syntax.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/syntax.yml)
[![Styling Status](https://github.com/openemr/openemr/actions/workflows/styling.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/styling.yml)
[![Testing Status](https://github.com/openemr/openemr/actions/workflows/test.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/test.yml)
[![JS Unit Testing Status](https://github.com/openemr/openemr/actions/workflows/js-test.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/js-test.yml)
[![PHPStan](https://github.com/openemr/openemr/actions/workflows/phpstan.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/phpstan.yml)
[![Rector](https://github.com/openemr/openemr/actions/workflows/rector.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/rector.yml)
[![ShellCheck](https://github.com/openemr/openemr/actions/workflows/shellcheck.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/shellcheck.yml)
[![Docker Compose Linting](https://github.com/openemr/openemr/actions/workflows/docker-compose-lint.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/docker-compose-lint.yml)
[![Dockerfile Linting](https://github.com/openemr/openemr/actions/workflows/hadolint.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/hadolint.yml)
[![Isolated Tests](https://github.com/openemr/openemr/actions/workflows/isolated-tests.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/isolated-tests.yml)
[![Inferno Certification Test](https://github.com/openemr/openemr/actions/workflows/inferno-test.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/inferno-test.yml)
[![Composer Checks](https://github.com/openemr/openemr/actions/workflows/composer.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/composer.yml)
[![Composer Require Checker](https://github.com/openemr/openemr/actions/workflows/composer-require-checker.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/composer-require-checker.yml)
[![API Docs Freshness Checks](https://github.com/openemr/openemr/actions/workflows/api-docs.yml/badge.svg)](https://github.com/openemr/openemr/actions/workflows/api-docs.yml)
[![codecov](https://codecov.io/gh/openemr/openemr/graph/badge.svg?token=7Eu3U1Ozdq)](https://codecov.io/gh/openemr/openemr)

[![Backers on Open Collective](https://opencollective.com/openemr/backers/badge.svg)](#backers) [![Sponsors on Open Collective](https://opencollective.com/openemr/sponsors/badge.svg)](#sponsors)

# OpenEMR

[OpenEMR](https://open-emr.org) is a Free and Open Source electronic health records and medical practice management application. It features fully integrated electronic health records, practice management, scheduling, electronic billing, internationalization, free support, a vibrant community, and a whole lot more. It runs on Windows, Linux, Mac OS X, and many other platforms.

### Contributing

OpenEMR is a leader in healthcare open source software and comprises a large and diverse community of software developers, medical providers and educators with a very healthy mix of both volunteers and professionals. [Join us and learn how to start contributing today!](https://open-emr.org/wiki/index.php/FAQ#How_do_I_begin_to_volunteer_for_the_OpenEMR_project.3F)

> Already comfortable with git? Check out [CONTRIBUTING.md](CONTRIBUTING.md) for quick setup instructions and requirements for contributing to OpenEMR by resolving a bug or adding an awesome feature 😊.

### Support

Community and Professional support can be found [here](https://open-emr.org/wiki/index.php/OpenEMR_Support_Guide).

Extensive documentation and forums can be found on the [OpenEMR website](https://open-emr.org) that can help you to become more familiar about the project 📖.

### Reporting Issues and Bugs

Report these on the [Issue Tracker](https://github.com/openemr/openemr/issues). If you are unsure if it is an issue/bug, then always feel free to use the [Forum](https://community.open-emr.org/) and [Chat](https://www.open-emr.org/chat/) to discuss about the issue 🪲.

### Reporting Security Vulnerabilities

Check out [SECURITY.md](.github/SECURITY.md)

### API

Check out [API_README.md](API_README.md)

### Docker

Check out [DOCKER_README.md](DOCKER_README.md)

### FHIR

Check out [FHIR_README.md](FHIR_README.md)

### For Developers

If using OpenEMR directly from the code repository, then the following commands will build OpenEMR (Node.js version 22.* is required) :

```shell
composer install --no-dev
npm install
npm run build
composer dump-autoload -o
```

### Contributors

This project exists thanks to all the people who have contributed. [[Contribute]](CONTRIBUTING.md).
<a href="https://github.com/openemr/openemr/graphs/contributors"><img src="https://opencollective.com/openemr/contributors.svg?width=890" /></a>


### Sponsors

Thanks to our [ONC Certification Major Sponsors](https://www.open-emr.org/wiki/index.php/OpenEMR_Certification_Stage_III_Meaningful_Use#Major_sponsors)!


### License

[GNU GPL](LICENSE)
