[![PLAM CI/CD Pipeline](https://github.com/LAlbertalli/plam/actions/workflows/test.yml/badge.svg)](https://github.com/LAlbertalli/plam/actions/workflows/test.yml)
# Personal Local Agent Manager (PLAM)

This is an AI project I'm building for myself to help me think deeper about agents and agents architecture. The inspiration comes from the idea of OpenClaw but I wanted to create something more in line with my beliefs and ideas.
PLAM is a powerful, local-first multi-agent system designed to orchestrate local LLMs (via `llama.cpp`), manage hierarchical agents with complex memory systems, and execute code safely within isolated sandboxes.

## Key Features

> **Note:** The `llama.cpp` Docker configuration used in this project is optimized for running on a **NVIDIA DGX Spark**, leveraging `nvcr.io/nvidia/cuda` as the base image for maximum CUDA acceleration.

- **Local-First AI**: Runs models completely locally using Dockerized `llama.cpp` containers.
- **Intelligent Resource Management**: Monitors system RAM to dynamically spin up and evict model containers, ensuring at least 10GB of RAM is always free.
- **Dual Proxy Architecture**: Employs a System Injection proxy for personas/tools and a Regex Rewriting proxy to normalize input/output formats across different LLM architectures.
- **Hybrid Agent Communication**: Orchestrator-driven delegation combined with a shared "Blackboard" long-term memory.
- **Robust Memory Subsystem**: 
  - *Short-Term*: High-speed JSONB storage capturing full conversational flows and "thinking" traces.
  - *Long-Term*: `pgvector` RAG database with scopes (Public/Private) and background consolidation.
- **Secure Code Execution**: Automatically spins up ephemeral, pre-configured Docker containers to safely execute LLM-generated Bash and Python scripts.

## Tech Stack

- **Frontend**: Next.js 15 (React), strictly styled with a custom Vanilla CSS design system.
- **Backend**: Python 3.12, FastAPI, Pydantic, and SQLAlchemy (with Alembic for migrations).
- **Database**: PostgreSQL with `pgvector` running in Docker.
- **Infrastructure Management**: Python Docker SDK for dynamic container orchestration.

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+ & npm
- Docker Engine (with API access configured)

### Installation

1. **Clone the repository** (if applicable) and navigate to the root directory.

2. **Initialize Backend**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Initialize Frontend**:
   ```bash
   cd frontend
   npm install
   ```

4. **Database Setup**:
   The backend's Docker Manager will automatically pull and start the `ankane/pgvector` container on port `15432` when you launch the application.

### Running the Application

The easiest way to run the full stack is via **VS Code**. 
1. Open the `/plam` directory in VS Code.
2. Go to the "Run and Debug" panel (`Ctrl+Shift+D`).
3. Select **"Start PLAM (Full Stack)"** from the dropdown and hit play.
   - The FastAPI backend will run on `http://localhost:8000`
   - The Next.js frontend will run on `http://localhost:3000`

## Documentation

Comprehensive design documents can be found in the `doc/design` directory:
- [Design Overview](doc/design/overview.md)
- [Feature List](doc/design/features.md)
- [Database Schema](doc/design/database_schema.md)
- [Implementation Plan](doc/design/implementation_plan.md)
