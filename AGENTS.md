# Personal Local Agent Manager (PLAM) - Agent Guidelines

Welcome, AI Agent! This document is your primary entry point for understanding the PLAM codebase, developer workflow, and strict rules of engagement. Read this carefully before editing or writing any code.

---

## 1. Project Overview & Context
PLAM is a local-first, multi-agent management system designed to orchestrate local LLMs (via dockerized `llama.cpp` instances), manage hierarchical agent memory structures (short-term JSONB and long-term `pgvector` RAG), and execute untrusted model-generated code safely inside isolated containers.
- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL with `pgvector`.
- **Frontend**: Next.js 15, React 19, Vanilla CSS (strictly tailored design system, no Tailwind unless requested).
- **Core Platform**: Tailored for NVIDIA DGX Spark CUDA acceleration, but uses Docker for local orchestration.

---

## 2. Codebase Layout

Below is the directory layout of the PLAM repository:

```
plam/
├── AGENTS.md                   # This file (master instructions for AI agents)
├── CLAUDE.md                   # IDE/Claude-specific developer card (points to AGENTS.md)
├── GEMINI.md                   # IDE/Gemini-specific developer card (points to AGENTS.md)
├── README.md                   # Main project introduction & user guide
├── TODO.md                     # Roadmap and tasks
├── setup.sh                    # Orchestrates system dependency checks, database startup, migrations, and starting dev/release servers
├── backend/                    # FastAPI backend codebase
│   ├── app/                    # FastAPI source files
│   │   ├── main.py             # Entrypoint and app initialization
│   │   ├── api/                # V1 REST API route controllers
│   │   ├── core/               # Configuration settings and security definitions
│   │   ├── db/                 # DB connection and session setups
│   │   ├── models/             # SQLAlchemy DB schemas and Pydantic validation models
│   │   └── services/           # Business logic (Docker, caching, memory, proxying, orchestrator)
│   ├── tests/                  # Pytest suite
│   ├── alembic/                # DB migrations
│   ├── pytest.ini              # Pytest configurations & coverage rule constraints
│   ├── requirements.txt        # Python package requirements
│   └── venv/                   # Local virtual environment
├── frontend/                   # Next.js 15 frontend codebase
│   ├── src/                    # Frontend source files
│   │   ├── app/                # Next.js Page Router directory
│   │   ├── components/         # Reusable React components (Sidebar, Monitor, Modals)
│   │   └── lib/                # API client helper and state managers
│   ├── __tests__/              # Jest component and unit tests
│   ├── package.json            # Script definitions and dependencies
│   └── jest.config.ts          # Jest configurations & coverage rule constraints
├── doc/                        # Saved documentation directory
│   └── design/                 # High-level architecture, schemas, and components design
│       ├── components/         # Detailed service/component sub-docs
│       └── ...                 # System overview, RAG, tool execution docs
├── utilities/                  # Seeding scripts and utilities
├── data/                       # PostgreSQL database volume storage
└── log/                        # Dev environment logs
```

---

## 3. Documentation Registry

All primary system documentation is stored inside the [doc/design/](file:///home/luca/plam/doc/design) directory. Before working on a subsystem, review its respective design file:
- **Core Architecture**: [overview.md](file:///home/luca/plam/doc/design/overview.md)
- **Features List**: [features.md](file:///home/luca/plam/doc/design/features.md)
- **Database Schema & Vector Database**: [database_schema.md](file:///home/luca/plam/doc/design/database_schema.md)
- **Testing Design**: [testing_strategy.md](file:///home/luca/plam/doc/design/testing_strategy.md)
- **Hierarchical Agents Flow**: [multi_agent_delegation_architecture.md](file:///home/luca/plam/doc/design/multi_agent_delegation_architecture.md)
- **Docker Manager & Security Sandboxing**: [tools_and_security.md](file:///home/luca/plam/doc/design/tools_and_security.md)
- **Model Loading & RAM Eviction Logic**: [active_model_caching_analysis.md](file:///home/luca/plam/doc/design/active_model_caching_analysis.md)
- **Component Sub-docs**:
  - Web UI: [web_ui.md](file:///home/luca/plam/doc/design/components/web_ui.md)
  - Security Sandbox: [security_sandboxing.md](file:///home/luca/plam/doc/design/components/security_sandboxing.md)
  - Docker Manager: [docker_manager.md](file:///home/luca/plam/doc/design/components/docker_manager.md)
  - Memory Subsystem: [memory_subsystem.md](file:///home/luca/plam/doc/design/components/memory_subsystem.md)
  - Reverse Proxy System: [proxy_system.md](file:///home/luca/plam/doc/design/components/proxy_system.md)
  - Backend Orchestrator: [backend_orchestrator.md](file:///home/luca/plam/doc/design/components/backend_orchestrator.md)

---

## 4. Strict Rules of Development

You MUST adhere to these rules for any code modification:

### A. The Code Coverage Rules
*   **Coverage Thresholds**: Both the backend and frontend enforce strict coverage constraints.
*   **Backend Enforcement (Per-File)**:
    *   The backend enforces coverage **per file** instead of a global average.
    *   No file under `backend/app/` can have less than **70%** coverage unless explicitly exempted.
    *   Critical security files (like [crypto_helper.py](file:///home/luca/plam/backend/app/core/crypto_helper.py)) have a higher minimum of **80%** coverage.
    *   Enforced by running `pytest --cov-report=json` followed by the custom check script:
        ```bash
        cd backend
        env PYTHONPATH=. venv/bin/pytest && venv/bin/python utilities/check_coverage.py
        ```
*   **Frontend Enforcement (Per-File)**:
    *   The frontend enforces coverage **per file** instead of a global average.
    *   No file under `frontend/src/` (excluding server layout `src/app/layout.tsx`) can have less than **70%** coverage for statements, branches, functions, and lines.
    *   Enforced by running `npm run test:coverage` which executes jest and runs the custom checker:
        ```bash
        cd frontend
        npm run test:coverage
        ```
*   **Action Required**: If your changes add or modify source files under `backend/app/` or `frontend/src/`, you **MUST** write corresponding tests so that the individual file meets or exceeds its required coverage threshold.

### B. Run Tests Before Finishing
*   **Always Run Tests**: You must run the tests to verify correctness and coverage **before** finalizing your implementation and declaring success.
*   **No Exceptions**: Always confirm all tests pass successfully.

### C. Testing & Mocking Standards
*   **Mock Real Infrastructure**: When writing backend tests, you MUST mock the `DockerManager` and actual `llama.cpp` HTTP/HuggingFace API calls to avoid creating Docker containers or making network requests during test runs.
*   **Frontend Mocking**: Mock the API client (`src/lib/api.ts`) in Jest tests to supply deterministic JSON endpoints, keeping tests fast and fully independent of a running backend.

---

## 5. Development & Testing Commands

Use the following commands to test, lint, and run the applications.

### Backend (Python)
- Run backend tests and check per-file coverage:
  ```bash
  cd backend
  env PYTHONPATH=. venv/bin/pytest && venv/bin/python utilities/check_coverage.py
  ```
- Generate database migrations:
  ```bash
  cd backend
  venv/bin/alembic revision --autogenerate -m "Description of changes"
  ```
- Apply migrations:
  ```bash
  cd backend
  venv/bin/alembic upgrade head
  ```

### Frontend (Next.js)
- Run frontend unit and component tests:
  ```bash
  cd frontend
  npm run test
  ```
- Run frontend tests with coverage:
  ```bash
  cd frontend
  npm run test:coverage
  ```
- Lint frontend code:
  ```bash
  cd frontend
  npm run lint
  ```