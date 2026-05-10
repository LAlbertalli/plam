# Agent Framework

## Overview
Defines how agents are structured, inherited, configured, and how they communicate with one another.

## Core Concepts
- **Base Agent**: The foundational template defining the core agent execution loop. Cannot be instantiated directly.
- **Skill/Tool Packages**: Groupings of capabilities (e.g., "Web Browsing with LightPanda", "Python Code Execution"). These act like interfaces or traits that can be attached to any agent.
- **Agent Definitions**: Each agent has a 1-to-1 mapping with a specific model configuration. They inherit tools from packages. Upon creation, an agent can copy the `AGENT.md` persona from a parent.

## Inter-Agent Communication
Uses a **Hybrid Orchestrator-Blackboard Pattern**:
- **Direct Delegation**: The main Orchestrator delegates tasks by calling other agents as if they were tools (e.g., passing a prompt to a specialized coder agent).
- **The Blackboard**: Agents share complex state or findings by reading/writing to the Long-Term "Public" Memory, which acts as a shared blackboard accessible via RAG.
