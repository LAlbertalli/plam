# PLAM - Technical Debt & Future Improvements

This document tracks identified issues, technical debt, and architectural improvements that should be addressed in the future, but are not currently blocking active development.

## Security & Configuration
- [ ] **Database Credentials**: The PostgreSQL database configuration and credentials should not be hardcoded (e.g., in `config.py` or the `docker run` command). Ensure passwords are not the default "postgres" and use `.env` files or a secret manager.

## Reliability & Execution
- [ ] **Robust Container Health Checks**: The `DockerManager.start_db` method currently relies on a simple `time.sleep(3)` to wait for the container. It should be refactored to implement a proper polling loop that checks for database readiness (e.g., repeatedly trying to open a connection until successful). Furthermore, this "wait for readiness" strategy should be generalized for all container spin-ups (such as the `llama.cpp` model instances).
