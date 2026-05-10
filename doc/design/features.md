# PLAM Feature List

This document serves as a reference for all the features discussed and planned for the Personal Local Agent Manager (PLAM).

## 1. Core Orchestration & Execution
- **Local LLMs via llama.cpp**: Run local models in isolated Docker containers.
- **Model Downloader**: Connect to Hugging Face Hub, download GGUF models, and manage local storage and configurations.
- **Resource Management**: Monitor system RAM via `psutil` and dynamically spin up/down model containers to keep at least 10GB of RAM free at all times. 
  - The manager should have a configuration for how much memory each model needs so it can actively manage how much memory will be available.
  - The manager should maintain the list of model running and evict models based on last utilization (except for the model running the orchestrator agent)
- **Pre-Configured Sandboxing**: Execute generated Bash and Python scripts securely using the Docker Engine SDK inside ephemeral, network-isolated containers. These containers use pre-configured base images containing necessary dependencies (avoiding real-time network downloads).
  - The container configuration and build process should be fully configurable via the Web UI.
- **PostgreSQL Foundation**: Use PostgreSQL (running in Docker) as the single source of truth for all configurations, state, and metrics. Managed via Alembic migrations.
- **Scheduled & Event-Driven Tasks**: Trigger agents via external/internal events (webhooks) or on a schedule (e.g., cron jobs via APScheduler).

## 2. Proxy System
- **Dual Proxy Architecture**: Separate the prompt augmentation and formatting into two stages, entirely configurable via the Web UI.
- **System Injection Proxy**: Injects `AGENT.md` personas and relevant MCP tool definitions into the prompt.
- **Regex Rewriting Proxy**: Input chain (modifying user prompt to fit model tags) and Output chain (fixing model hallucinations/malformed JSON before processing).

## 3. Agent Framework
- **Always-On Orchestrator**: A central agent that receives user input and delegates tasks to specialized sub-agents.
- **Hierarchical Configuration**: Define a Base Agent template. Attach "Skill/Tool Packages" (like interfaces) to agents.
- **1-to-1 Model Mapping**: Each agent definition is tied directly to a specific model instance, though multiple agents can reuse a running model container.
- **Hybrid Communication**: Orchestrator delegates tasks (Hub-and-Spoke), and agents share complex findings via Long-Term Memory (Blackboard pattern).

## 4. Memory Subsystem
- **Short-Term Memory**: Store conversation history and internal "thinking traces" in fast PostgreSQL JSONB columns.
- **Long-Term Memory (RAG)**: Store embeddings via the `pgvector` extension.
  - *Scopes*: Tag vectors as Private (agent-specific) or Public (shared).
  - *Knowledge Base*: Allow user document uploads for retrieval.
  - *Snippet Library*: Automatically save successful Python/Bash scripts for reuse.
- **Memory Consolidation Agent**: A scheduled background agent that summarizes short-term memory, extracts entities, and writes them to the Long-Term vector store.

## 5. Security Model
- **Security Review Agent**: A specialized lightweight agent that pre-screens generated code for destructive actions.
- **Human-in-the-Loop Approvals**: Pause execution and trigger an alert in the Web UI if the Review Agent flags a command or if a command requests elevated privileges (network, volumes).

## 6. External Tooling
- **Web Browsing**: Integration with headless browsers like LightPanda to allow agents to interact with web pages dynamically.

## 7. Next.js Web UI
- **Chat Interface**: Interact with the Orchestrator and visualize agent reasoning/tool execution.
- **System Dashboard**: View live RAM usage, container metrics, and token generation speed.
- **Configuration Panes**:
  - Model & Resource Config.
  - Agent Builder & Persona Editor.
  - Visual Regex Proxy Editor.
  - Memory Explorer & Document Uploader.
  - Security Approvals pane.
