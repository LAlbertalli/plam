# Memory Subsystem

## Overview
The memory subsystem manages both short-term conversational context and long-term knowledge retrieval using PostgreSQL.

## Architecture
- **Short-Term Memory**: Stored as JSONB in PostgreSQL. Captures the active conversation trace, including intermediate internal agent reasoning ("thinking" traces) and tool execution outputs.
- **Long-Term Memory**: Uses the `pgvector` extension for PostgreSQL.
  - Documents, consolidated memories, and verified code snippets are embedded and stored as vectors.
  - *Scopes*: Vectors are tagged with ownership (specific Agent ID or "Public").
- **Memory Consolidation Agent**: A specialized background agent that runs on a schedule (via APScheduler). It reads older short-term memory traces, summarizes them, extracts key entities/facts, and inserts them into the long-term memory vector store.
