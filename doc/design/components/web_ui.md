# Web UI (Next.js)

## Overview
The frontend management dashboard and primary chat interface for PLAM.

## Core Features
- **Chat Interface**: The main view to interact with the Orchestrator agent. Displays thinking traces, tool execution progress, and markdown-formatted responses.
- **System Dashboard**: View real-time RAM usage, active model containers, and performance metrics (tokens/sec).
- **Configuration Panes**:
  - **Agent Builder**: Create new agents, assign skill/tool packages, and edit `AGENT.md` instructions.
  - **Proxy Rules**: A UI to visually manage and edit the Regex chains for the rewriting proxy.
  - **Security Settings**: Approve or deny pending code execution requests flagged by the Security Review Agent.
  - **Memory Browser**: Inspect and search short-term JSONB traces and long-term `pgvector` entries.
