# Design Analysis: Stateful Active Model Caching & Stateless ProxyService

## Context & Background

In the current PLAM architecture:
1. `ProxyService` is a stateless global singleton (`proxy_service = ProxyService()`).
2. To remain thread-safe and concurrent-friendly within FastAPI (which uses asynchronous request handling), `ProxyService` methods do not store database sessions or model IDs as instance variables.
3. As a result, database sessions (`db`) and the active model context (`model_id`) must be passed as parameters to every method call (`apply_input_chain`, `apply_output_chain`, `build_system_prompt`).
4. This results in the database being queried on every single message turn to retrieve the active model's regex rules (`ModelRegexRule`).

While correct and robust, this approach couples model-specific database queries directly to chat orchestration and incurs a performance cost by hitting the database multiple times during each client interaction loop.

## Proposed Architectural Change

An alternative design is to introduce a stateful **`ActiveModel`** class that represents a running LLM model container. 
* A central **`ActiveModelRegistry`** would manage the lifecycle of these active models in memory.
* High-level services (like `OrchestratorService`) would request the `ActiveModel` object for a given `model_id` and invoke methods directly on it (e.g., `active_model.generate_stream(messages)`).
* `ProxyService` would be refactored into a pure, stateless string-replacement engine that is passed raw lists of rules, rather than querying the database itself.

---

## Detailed Analysis of Key Corner Cases

While this proposed refactor offers cleaner separation of concerns, it introduces several classic distributed state and cache invalidation challenges.

### 1. Cache Invalidation & Reload Triggers (Stale Memory Rules)
When a user updates, adds, or deletes a regex rule, or modifies model parameters in the DB, the running `ActiveModel` object in memory becomes stale.

* **The Challenge:** How does the in-memory cache representation know the DB has changed?
* **Design Options:**
  1. **Direct Event Dispatching:** The REST API endpoints that handle rule mutations (e.g., `POST /api/model-regex-rules`) must explicitly notify the registry to reload rules for the affected model (`active_model_registry.reload_rules(model_id, db)`).
  2. **Lazy Time-to-Live (TTL):** The `ActiveModel` could keep a timestamp of when it last fetched rules. Before applying rules, it checks if the cache is older than a threshold (e.g., 10 seconds) and automatically re-queries the DB if expired.

### 2. Multi-Worker & Multi-Process Memory Isolation
In production or scaling scenarios, FastAPI is often run with multiple worker processes (e.g., `uvicorn app.main:app --workers 4`). 

* **The Challenge:** Memory is isolated per worker process. If Worker A receives the HTTP request to update a regex rule, it updates the database and invalidates its own in-memory `ActiveModel` cache. However, Workers B, C, and D are still running in separate processes and will serve subsequent user requests using their stale cached rules.
* **Design Options:**
  1. **Single-Worker Constraint:** If PLAM is strictly a single-process/single-worker backend, this is not an issue, and a standard in-memory dictionary registry is sufficient.
  2. **Process Signaling (Pub/Sub):** Implement a lightweight pub/sub model to synchronize state. For instance, using PostgreSQL's native `LISTEN` and `NOTIFY` via the database connection driver (which requires no external infrastructure like Redis). When any worker writes a change to the database, it sends a notify command (`NOTIFY model_rule_change, 'model_id'`), and all worker processes listen for this event to invalidate their local caches.

### 3. Pipeline Consistency during Active Streaming
A chat generation takes time, streaming tokens over an HTTP connection. A user might modify a regex rule while a long generation is outputting tokens.

* **The Challenge:** If rules are reloaded in-memory *mid-generation*, the *input* chain will have been executed with Rule Version A, while the *output* chain (applied to the accumulated stream response) would execute with Rule Version B. This can lead to mismatch errors or half-sanitized output.
* **Design Option:**
  * To ensure consistency per chat turn, we should capture a snapshot of the active rules or the model configuration at the exact moment the turn starts and bind that configuration snapshot to the lifetime of the `generate_stream()` generator, protecting it from mid-turn reloads.

### 4. Container Health Sync (External Container Deaths)
LLM model containers run outside of the Python process under Docker. They can crash, get killed by the OS (e.g., due to Out-Of-Memory conditions), or be stopped manually by the user via the Docker CLI.

* **The Challenge:** The Python-bound `ActiveModel` object might still believe the container is healthy and keep trying to route HTTP traffic to a dead port.
* **Design Option:**
  * The `ActiveModel` should perform **lazy health checking**. The first time it gets a connection failure, or during a quick heartbeat check at the start of a turn, it should verify the container's status via `docker_manager`. If the container is dead, the registry should automatically drop the `ActiveModel` object, triggering a clean restart on the next message.

### 5. Re-architecting the Scope of `ProxyService`
With this refactor, `ProxyService` no longer needs to query the database. 

* **The Design:**
  * `ProxyService` should be transformed from a database-facing repository helper into a **pure, stateless utility engine**. It should just accept text and a raw list of rules, executing the string replacements:
  
  ```python
  class ProxyService:
      def apply_chain(self, text: str, rules: list[ModelRegexRule]) -> str:
          modified_text = text
          for rule in rules:
              try:
                  modified_text = re.sub(rule.pattern, rule.replacement, modified_text)
              except re.error:
                  continue
          return modified_text
  ```
  * The `ActiveModel` handles *storing* the list of rules in memory, and delegating the execution to `proxy_service.apply_chain(text, self.input_rules)`.

---

## Conclusion & Decision

While stateful `ActiveModel` caching provides clean decoupling and removes repetitive database queries on the hot path, the operational complexity (cache synchronization in multi-worker environments, lifecycle hook maintenance, lazy health checking) outweighs the benefits during the initial development phases. 

**Decision:** Retain the stateless singleton model for now to prioritize system reliability and ease of deployment. Reconsider this optimization once multi-worker scale or database overhead becomes a primary bottleneck.
