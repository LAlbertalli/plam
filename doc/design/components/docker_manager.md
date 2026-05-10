# Docker & Resource Manager

## Overview
This component is responsible for all interactions with the host's Docker Engine via the `docker` Python SDK. It ensures PLAM stays within the resource limits of the host machine.

## Responsibilities
- **Automated Startup**: Ensure the PostgreSQL container is running before the backend fully initializes.
- **Model Lifecycle**: Spin up `llama.cpp` containers for active models. Shut down least-used models when system RAM drops below the 10GB free threshold (monitored via `psutil`).
- **Model Downloader**: Pull `GGUF` files from Hugging Face Hub, store them in a shared local Docker volume, and persist configurations in PostgreSQL.

## Internal Interfaces
- `DockerManager.start_db()`: Initializes the PostgreSQL DB container.
- `DockerManager.start_model(model_config)`: Starts a model container, enforcing RAM limits.
- `DockerManager.run_sandboxed_code(image, code, options)`: Executes code in an ephemeral container.
