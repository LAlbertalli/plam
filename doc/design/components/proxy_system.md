# Proxy System

## Overview
The Proxy System modifies inputs and outputs between the agents and the underlying `llama.cpp` models. Both proxies are fully configurable via the Web UI and stored in PostgreSQL.

## Components
1. **System Injection Proxy**:
   - Responsible for prompt construction.
   - Injects the `AGENT.md` persona instructions.
   - Dynamically appends definitions of available MCP tools and skills based on the agent's assigned packages.
2. **Rewriting Proxy**:
   - A configurable chain of Regex rules.
   - *Input Chain*: Modifies the prompt format before it reaches the model (e.g., adapting ChatML tags to Llama-3 or Mistral instruction formats).
   - *Output Chain*: Fixes common model hallucinations, formatting errors, or broken JSON before the Orchestrator parses tool calls.
