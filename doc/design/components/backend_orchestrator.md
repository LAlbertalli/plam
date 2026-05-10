# Backend Orchestrator

## Overview
The Backend Orchestrator is the central brain of PLAM. Built with FastAPI and Pydantic, it provides the REST API for the frontend, manages the event loop, handles scheduling, and coordinates inter-agent communication.

## Responsibilities
- Serve the REST and WebSocket API for the Web UI.
- Manage database connections and run Alembic migrations at startup.
- Handle background tasks (using APScheduler) like Memory Consolidation.
- Listen to internal events or webhooks to trigger automatic agent workflows.
- Manage the execution loop for the Orchestrator Agent.

## Key API Design (Draft)
- `POST /api/chat`: Send a message to the Orchestrator Agent.
- `GET /api/models`: List available and running models.
- `POST /api/agents/{agent_id}/invoke`: Invoke a specific agent programmatically.
- `GET /api/metrics`: Retrieve system metrics for the dashboard.
