# Architecture Overview

## Introduction
PLAM (Personal Local Agent Manager) is a multi-agent system designed to run entirely locally, orchestrating local LLMs via `llama.cpp`.

## High-Level Architecture
The system consists of the following macro-components:
1. **Next.js Web UI**: The frontend for interacting with agents and managing the system.
2. **Python FastAPI Backend**: The core orchestrator handling API requests, scheduling, and agent execution.
3. **PostgreSQL (pgvector)**: The single source of truth for configuration, short-term memory, long-term memory (RAG embeddings), and metrics.
4. **Docker Engine**: Used dynamically by the backend to manage `llama.cpp` model containers, the PostgreSQL database, and ephemeral execution sandboxes.

## Component Interactions
- **User -> Web UI**: User configures models, agents, and initiates chats.
- **Web UI -> Backend**: REST API and WebSockets for real-time interaction.
- **Backend -> Docker**: Uses the Python Docker SDK to start/stop models based on RAM constraints, and to launch ephemeral execution containers.
- **Backend -> PostgreSQL**: Uses SQLAlchemy and Alembic for schema management and CRUD operations.
- **Backend -> LLMs**: Interacts with the `llama.cpp` containers via HTTP after proxying the prompt.
