# Testing Strategy

This document outlines the testing frameworks and strategies to ensure the reliability and stability of both the frontend and backend components of PLAM.

## 1. Backend Testing (FastAPI)

### Frameworks
- **Test Runner**: `pytest`
- **API Testing**: `fastapi.testclient.TestClient` (based on `httpx`)
- **Mocking**: `unittest.mock` and `pytest-mock`

### Strategy
1. **Unit Testing**:
   - Focus on core business logic (e.g., RAM threshold calculations, Regex proxy chain logic, Prompt assembly).
   - **Crucially**, all `DockerManager` functions and `llama.cpp` HTTP calls must be deeply mocked during unit tests to prevent spinning up real Docker containers or making network requests.
2. **Integration Testing**:
   - Test the FastAPI endpoints from request to database.
   - Use a separate test database schema (e.g., `plam_test` in PostgreSQL) to prevent wiping out local development data.
   - Use pytest fixtures to handle test database creation, running Alembic migrations before the test suite, and tearing down the database afterward.

## 2. Frontend Testing (Next.js)

### Frameworks
- **Test Runner**: `Jest`
- **Component Testing**: React Testing Library (`@testing-library/react`)
- **End-to-End (E2E)**: `Playwright`

### Strategy
1. **Unit & Component Testing**:
   - Test individual isolated UI components (e.g., ensuring the Chat bubble renders markdown correctly, or the Regex visual editor correctly updates local state).
   - Mock the `src/lib/api.ts` client to return controlled JSON responses, allowing frontend tests to run rapidly without the backend.
2. **E2E Testing (Playwright)**:
   - Run against a fully spun-up instance of Next.js + FastAPI (with mocked LLM responses).
   - Test critical user journeys: e.g., creating a new Agent, sending a message, and verifying the "Human-in-the-loop" security approval popup blocks execution correctly.

## 3. Continuous Integration
All tests (`pytest`, `Jest`, and `Playwright`) should be integrated into a GitHub Action (or similar CI/CD pipeline) to run automatically on every pull request, ensuring no regressions are introduced into the local manager.

## 4. Code Coverage Requirements
We enforce strict branch + statement coverage metrics:
* **Backend**: Coverage is validated **per file** (minimum 70% for standard modules, 80% for security modules like [crypto_helper.py](file:///home/luca/plam/backend/app/core/crypto_helper.py), and custom exemptions for infrastructure components). This is validated by running the custom checking script `utilities/check_coverage.py` on the generated `coverage.json` report.
* **Frontend**: Validated **per file** (minimum 70% for TS/TSX modules under `src/`, excluding server layout `src/app/layout.tsx`). This is validated by running `npm run test:coverage` which generates a `coverage-summary.json` report and executes the custom checker script `utilities/check_coverage.js`.
