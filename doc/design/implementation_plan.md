# Implementation Plan

To ensure high quality, each phase begins with a **Design Refinement** step dedicated to finalizing data models, API contracts, and UI mockups before writing code. UI and Backend implementation will occur concurrently. 
**Testing & Coverage**: Every phase must conclude with writing unit and integration tests (`pytest` with `pytest-cov` for backend, `Jest` with `--coverage` for frontend) for all newly developed features before moving to the next phase. Coverage should be rigorously checked and must never fall below 70%.

## Phase 1: Foundation & Project Setup
- **Design Refinement**: Finalize the core database schema (Agents, Models, Memory) and REST API contracts. Wireframe the base UI layout.
- **Backend Implementation**: 
  - Initialize FastAPI backend, Alembic migrations, and SQLAlchemy.
  - Implement Docker SDK logic to auto-start PostgreSQL.
- **Frontend Implementation**:
  - Initialize Next.js project with a styling framework.
  - Set up base layout, routing, and API client layer.

## Phase 2: Model & Resource Management
- **Design Refinement**: Detail the Hugging Face download strategy, RAM calculation formula, and model configuration JSON structure.
- **Backend Implementation**: 
  - Build Model Downloader (GGUF fetcher).
  - Build Container Manager (RAM monitoring via `psutil` and dynamic Docker container start/stop).
- **Frontend Implementation**:
  - Build Model Management Dashboard (download models, view status).
  - Build System Resource Monitor (live RAM usage graphs).

## Phase 3: Proxy & Agent Core
- **Design Refinement**: Detail the System Injection prompt format and the Regex rule schema. Define the inter-agent communication payload.
- **Backend Implementation**: 
  - Build the Injection and Rewriting proxy pipelines.
  - Implement the core execution loop for the Orchestrator Agent.
- **Frontend Implementation**:
  - Build the main Chat Interface (rendering thinking traces and markdown).
  - Build the Visual Regex Proxy Editor.
  - Build the Agent Builder (assigning packages, editing `AGENT.md`).

## Phase 4: Tools & Security
- **Design Refinement**: Define the Docker parameters for ephemeral containers (network, mounts) and the exact rules for the Security Review Agent.
- **Backend Implementation**: 
  - Build the Docker Sandboxing execution engine using pre-configured images.
  - Build the Security Review Agent and human-approval API endpoints.
- **Frontend Implementation**:
  - Build the Security Settings UI.
  - Implement the Approval Workflow popup/pane within the Chat interface.

## Phase 5: Memory Subsystem
- **Design Refinement**: Design the `pgvector` embeddings schema, RAG search logic, and the consolidation agent's scheduling config.
- **Backend Implementation**: 
  - Implement RAG queries via `pgvector`.
  - Implement the Memory Consolidation Agent using APScheduler.
- **Frontend Implementation**:
  - Build the Memory Explorer Dashboard.
  - Build the Document Upload interface for RAG insertion.
