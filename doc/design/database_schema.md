# Database Schema

This document details the PostgreSQL relational schema used as the foundation for PLAM.

## Core Entities

### 1. `models`
**Description**: Stores the configuration, metadata, and state of the local LLMs (managed via `llama.cpp`).
- `id` (UUID, Primary Key): Unique identifier.
- `name` (String, Unique, Not Null): Human-readable name (e.g., "Llama-3-8B-Instruct").
- `hf_repo_id` (String, Not Null): Hugging Face repository ID (e.g., "QuantFactory/Meta-Llama-3-8B-Instruct-GGUF").
- `gguf_filename` (String, Not Null): The specific file to download.
- `local_path` (String, Nullable): The absolute path to the GGUF file within the local shared Docker volume. Used to skip re-downloading.
- `status` (Enum, Not Null, Default: "stopped"): Current state of the model. Values: `['stopped', 'running', 'downloading', 'error']`. *Note: The database only durably tracks transient states (`downloading`, `error`). The `running` and `stopped` states are dynamically resolved at runtime by the API querying the Docker daemon to prevent split-brain issues.*
- `ram_required_mb` (Integer, Not Null): Estimated system RAM needed for the model. Used by the Resource Manager for eviction and scheduling.
- `context_size` (Integer, Not Null): Maximum token context.
- `llamacpp_args` (JSONB, Nullable): Custom starting parameters passed to the llama.cpp server (e.g., `{"n_gpu_layers": -1, "n_predict": 1024}`).
- `parameter_count` (String, Nullable): Metadata (e.g., "8B", "70B").
- `quantization` (String, Nullable): Metadata (e.g., "Q4_K_M", "Q8_0").
- `recommended_tasks` (Array of Strings, Nullable): Metadata indicating what this model is best suited for (e.g., `["coding", "summarization"]`).
- `created_at` / `updated_at` (DateTime, Not Null): Timestamps.

### 2. `agents`
**Description**: Defines the persona and core instructions for a specific agent. Each agent is tied to a model.
- `id` (UUID, Primary Key): Unique identifier.
- `name` (String, Unique, Not Null): Name of the agent.
- `description` (String, Nullable): Purpose of the agent.
- `model_id` (UUID, Foreign Key referencing `models.id`, Not Null): The underlying LLM backing this agent.
- `system_prompt` (Text, Not Null): The core `AGENT.md` persona instructions injected into the prompt.
- `is_orchestrator` (Boolean, Not Null, Default: False): True for the main, always-on routing agent.
- `parent_agent_id` (UUID, Foreign Key referencing `agents.id`, Nullable): Traces inheritance. Packages are inherited from the parent by reference, so the new agent will have access to the same packages.
- `is_abstract` (Boolean, Not Null, Default: False): True if this agent is a base agent that should not be instantiated directly.
- `created_at` / `updated_at` (DateTime, Not Null).


### 3. `packages`
**Description**: Logical groupings (like OOP interfaces) that bundle related Skills and MCP Tools together so they can be assigned to Agents in bulk.
- `id` (UUID, Primary Key).
- `name` (String, Unique, Not Null): (e.g., "Web Operations", "Local Code Execution").
- `description` (Text, Nullable).

### 4. `agent_packages`
**Description**: Mapping table linking Agents to the Packages they possess.
- `agent_id` (UUID, Foreign Key referencing `agents.id`, Not Null, PK part 1).
- `package_id` (UUID, Foreign Key referencing `packages.id`, Not Null, PK part 2).

### 5. `skills`
**Description**: Executable Bash or Python snippets that run in the ephemeral Docker sandbox.
- `id` (UUID, Primary Key).
- `package_id` (UUID, Foreign Key referencing `packages.id`, Not Null): The package this skill belongs to.
- `name` (String, Unique, Not Null): The name of the skill (e.g., "scan_directory").
- `front_matter` (JSONB, Not Null): The front matter of the skill file, which contains metadata about the skill.
- `description` (Text, Not Null): The instruction provided to the LLM explaining how and when to use this skill.

### 6. `mcp_tools`
**Description**: Tools that conform to the Model Context Protocol (external API endpoints, browsing).
- `id` (UUID, Primary Key).
- `package_id` (UUID, Foreign Key referencing `packages.id`, Not Null).
- `name` (String, Unique, Not Null).
- `description` (Text, Not Null).
- `mcp_schema` (JSONB, Not Null): The JSON schema defining the inputs required for this tool.
- `endpoint_url` (String, Nullable): Internal routing endpoint for the Orchestrator to trigger this tool.

## Memory Models

### 7. `sessions`
**Description**: A continuous conversation or task thread.
- `id` (UUID, Primary Key).
- `title` (String, Nullable).
- `created_at` / `updated_at` (DateTime, Not Null).

### 8. `short_term_memory`
**Description**: Stores the chronological trace of messages within a session.
- `id` (UUID, Primary Key).
- `session_id` (UUID, Foreign Key referencing `sessions.id`, Not Null).
- `agent_id` (UUID, Foreign Key referencing `agents.id`, Nullable): Which agent generated the response (null for user input).
- `sequence_id` (Integer, Not Null): The order in which the message was sent.
- `role` (Enum, Not Null): Values: `['user', 'assistant', 'system', 'tool']`.
- `content` (Text, Nullable): Main message content.
- `thinking_trace` (Text, Nullable): Internal reasoning output generated by the model before the final answer (e.g., output between `<thought>` tags).
- `tool_calls` (JSONB, Nullable): Structured data of invoked skills/tools.
- `tool_outputs` (JSONB, Nullable): Results of skill/tool executions.
- `timestamp` (DateTime, Not Null, Default: CurrentTime).

#### How Short Term Memory Works:
The short term memory operates as a chronological, append-only log for a `session`. 
1. When a user sends a message, it is logged with `role='user'`. 
2. The Orchestrator agent processes the request. Its response is logged with its `agent_id`, including its `thinking_trace` and any `tool_calls` it decides to make.
3. If the Orchestrator delegates a task to a specialized Agent (e.g., a "Coder Agent"), the prompt sent to the sub-agent is logged, followed by the sub-agent's response (with its specific `agent_id`).
4. When a skill is executed in the sandbox, the result is appended with `role='tool'` and stored in `tool_outputs`.

This structure captures the full hierarchical conversational flow. It allows the Next.js UI to visually reconstruct the exact sequence of events, letting the user trace exactly how a conclusion was reached (e.g., User Request -> Orchestrator thoughts -> Orchestrator delegates to Sub-Agent -> Sub-Agent thoughts -> Sub-Agent runs Python skill -> Result).
