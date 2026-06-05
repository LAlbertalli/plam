#!/usr/bin/env bash

set -euo pipefail

# Default Configuration
MODE="dev"
FRONTEND_PORT="3000"
BACKEND_PORT="8000"
CLEAN_DB=false
CONFIG_DIR=""
LOG_DIR="log"
ALLOWED_ORIGINS=""


# PID Tracking File
PID_FILE=".plam.pids"

# Usage helper
usage() {
  echo "PLAM (Personal Local Agent Manager) Setup and Runner Script"
  echo ""
  echo "Usage: ./setup.sh [command] [options]"
  echo ""
  echo "Commands:"
  echo "  (no command)            Build, configure, and start the frontend and backend servers."
  echo "  stop                    Stop running backend and frontend background processes."
  echo ""
  echo "Options:"
  echo "  --mode dev|release      Start mode for servers. Dev uses reload/dev, release builds and starts. Default: dev."
  echo "  --frontend-port PORT    Port to run the Next.js frontend on. Default: 3000."
  echo "  --backend-port PORT     Port to run the FastAPI backend on. Default: 8000."
  echo "  --clean-db              Stop, remove, and recreate the plam-postgres container."
  echo "  --config-dir PATH       Path to a configuration directory containing JSON files to seed database."
  echo "  --log-dir PATH          Directory to write server logs. Default: log."
  echo "  --allowed-origins IPS   Comma-separated list of additional origins/IPs to allow in dev mode."
  echo "  -h, --help              Show this help message."
  exit 0
}

# Resolve command
COMMAND="start"
if [ "${1:-}" = "stop" ]; then
  COMMAND="stop"
  shift
fi

# Parse Options
while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode)
      if [ "$2" != "dev" ] && [ "$2" != "release" ]; then
        echo "Error: Invalid mode '$2'. Mode must be 'dev' or 'release'."
        exit 1
      fi
      MODE="$2"
      shift 2
      ;;
    --frontend-port)
      FRONTEND_PORT="$2"
      shift 2
      ;;
    --backend-port)
      BACKEND_PORT="$2"
      shift 2
      ;;
    --clean-db)
      CLEAN_DB=true
      shift
      ;;
    --config-dir)
      CONFIG_DIR="$2"
      shift 2
      ;;
    --log-dir)
      LOG_DIR="$2"
      shift 2
      ;;
    --allowed-origins)
      ALLOWED_ORIGINS="$2"
      shift 2
      ;;

    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Helper function to check if port is available
check_port() {
  local port=$1
  if python3 -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', $port))" >/dev/null 2>&1; then
    return 0 # Free
  else
    return 1 # In use
  fi
}

# Recursive process group termination function
kill_descendants() {
  local target_pid=$1
  if [ -z "$target_pid" ]; then return; fi
  
  # Get child pids
  local child_pids
  child_pids=$(pgrep -P "$target_pid" 2>/dev/null) || true
  for child in $child_pids; do
    kill_descendants "$child"
  done
  
  if kill -0 "$target_pid" 2>/dev/null; then
    kill -TERM "$target_pid" 2>/dev/null
    sleep 0.5
    if kill -0 "$target_pid" 2>/dev/null; then
      kill -KILL "$target_pid" 2>/dev/null
    fi
  fi
}

# STOP COMMAND EXECUTION
if [ "$COMMAND" = "stop" ]; then
  echo "Stopping PLAM Stack processes..."
  
  if [ -f "$PID_FILE" ]; then
    # Read PIDs
    BACKEND_PID=$(grep BACKEND_PID "$PID_FILE" | cut -d= -f2 || true)
    FRONTEND_PID=$(grep FRONTEND_PID "$PID_FILE" | cut -d= -f2 || true)
    
    if [ -n "$BACKEND_PID" ]; then
      echo "Terminating Backend processes (PID: $BACKEND_PID)..."
      kill_descendants "$BACKEND_PID"
    fi
    
    if [ -n "$FRONTEND_PID" ]; then
      echo "Terminating Frontend processes (PID: $FRONTEND_PID)..."
      kill_descendants "$FRONTEND_PID"
    fi
    
    rm -f "$PID_FILE"
    echo "Processes terminated."
  else
    echo "No $PID_FILE file found. Stack might not be running in the background."
  fi
  
  # Double check checkouts on ports and free them if possible
  if command -v lsof >/dev/null 2>&1; then
    # Attempt to locate and kill remaining processes on the ports
    for p in "$BACKEND_PORT" "$FRONTEND_PORT"; do
      p_pids=$(lsof -t -i :"$p" 2>/dev/null) || true
      if [ -n "$p_pids" ]; then
        echo "Port $p still occupied, cleaning up..."
        kill -9 $p_pids 2>/dev/null || true
      fi
    done
  fi
  
  echo "PLAM Stack successfully stopped."
  exit 0
fi

# START COMMAND EXECUTION
echo "=========================================="
echo "    PLAM - Starting Application Stack     "
echo "=========================================="
echo ""

# 1. Dependency Validation Checks (Graceful Failure)
echo "Checking system dependencies..."

MISSING_DEPS=0

if ! command -v python3 >/dev/null 2>&1; then
  echo "[-] Error: python3 is not installed on this system." >&2
  MISSING_DEPS=1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "[-] Error: node (Node.js) is not installed on this system." >&2
  MISSING_DEPS=1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[-] Error: npm is not installed on this system." >&2
  MISSING_DEPS=1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[-] Error: docker is not installed on this system." >&2
  MISSING_DEPS=1
fi

if [ $MISSING_DEPS -ne 0 ]; then
  echo "" >&2
  echo "Please install all missing system dependencies and try again." >&2
  exit 1
fi

# Check if Docker Daemon is running
if ! docker info >/dev/null 2>&1; then
  echo "[-] Error: Docker daemon is not running. Please start the Docker service." >&2
  exit 1
fi

echo "[+] All system dependencies verified successfully."
echo ""

# 2. Local Dependencies Validation and Setup
echo "Checking and setting up local dependencies..."

# Python virtual environment setup
if [ ! -d "backend/venv" ]; then
  echo "Creating Python virtual environment in backend/venv..."
  python3 -m venv backend/venv
fi

echo "Installing/updating Python requirements..."
backend/venv/bin/pip install --upgrade pip
backend/venv/bin/pip install -r backend/requirements.txt

# Node local modules setup
if [ ! -d "frontend/node_modules" ]; then
  echo "Installing frontend local npm packages..."
  cd frontend && npm install && cd ..
else
  # Quick npm package install check/refresh
  echo "Checking/updating frontend npm packages..."
  cd frontend && npm install && cd ..
fi

echo "[+] Local dependencies configured successfully."
echo ""

# 3. Port Occupancy Checks
echo "Checking port availability..."
if ! check_port "$BACKEND_PORT"; then
  echo "[-] Error: Backend port $BACKEND_PORT is already in use." >&2
  echo "    Please stop the occupying process or run setup.sh with --backend-port <PORT>" >&2
  exit 1
fi

if ! check_port "$FRONTEND_PORT"; then
  echo "[-] Error: Frontend port $FRONTEND_PORT is already in use." >&2
  echo "    Please stop the occupying process or run setup.sh with --frontend-port <PORT>" >&2
  exit 1
fi
echo "[+] Ports $BACKEND_PORT and $FRONTEND_PORT are available."
echo ""

# 4. Database Setup & Checks
if [ "$CLEAN_DB" = true ]; then
  echo "Cleaning up database container plam-postgres..."
  docker stop plam-postgres >/dev/null 2>&1 || true
  docker rm plam-postgres >/dev/null 2>&1 || true
  echo "[+] Existing plam-postgres container removed."
fi

# Check database container state and start if necessary
PG_CONTAINER_STATE=$(docker ps -a --filter name=plam-postgres --format "{{.State}}" || true)

if [ -z "$PG_CONTAINER_STATE" ]; then
  echo "Creating and starting new plam-postgres container..."
  docker run -d \
    --name plam-postgres \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=plam \
    -p 15432:5432 \
    ankane/pgvector:latest
elif [ "$PG_CONTAINER_STATE" != "running" ]; then
  echo "Starting stopped plam-postgres container..."
  docker start plam-postgres
else
  echo "Database container plam-postgres is already running."
fi

# Wait for PostgreSQL to be ready to accept connections
echo "Waiting for PostgreSQL database connection..."
PG_READY=false
for i in {1..30}; do
  if backend/venv/bin/python -c "import psycopg2; psycopg2.connect('postgresql://postgres:postgres@localhost:15432/plam')" >/dev/null 2>&1; then
    PG_READY=true
    break
  fi
  sleep 1
done

if [ "$PG_READY" != true ]; then
  echo "[-] Error: PostgreSQL container did not start/respond within 30 seconds." >&2
  exit 1
fi
echo "[+] Database container is ready."
echo ""

# 5. Database Migrations (Always run)
echo "Running database migrations..."
cd backend
venv/bin/alembic upgrade head
cd ..
echo "[+] Database migrations completed."
echo ""

# 6. Database Seeding
if [ -n "$CONFIG_DIR" ]; then
  echo "Seeding database configuration..."
  PYTHONPATH=backend backend/venv/bin/python utilities/seed.py --config-dir "$CONFIG_DIR"
  echo "[+] Seeding completed."
  echo ""
fi

# 7. Environment Injection and Preparation
echo "Writing environment settings..."
mkdir -p "$LOG_DIR"
echo "POSTGRES_PORT=15432" > backend/.env
echo "PORT=$FRONTEND_PORT" > frontend/.env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:$BACKEND_PORT" >> frontend/.env.local
if [ -n "$ALLOWED_ORIGINS" ]; then
  echo "ALLOWED_DEV_ORIGINS=$ALLOWED_ORIGINS" >> frontend/.env.local
fi
echo "[+] Settings loaded to backend/.env and frontend/.env.local"

echo ""

# 8. Building and Launching Servers
echo "Starting backend and frontend servers in $MODE mode..."
echo "Logs will be written to: $LOG_DIR/backend.log & $LOG_DIR/frontend.log"

if [ "$MODE" = "dev" ]; then
  # Launch FastAPI backend (Reload mode)
  cd backend
  nohup env PYTHONPATH=. venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" > "../$LOG_DIR/backend.log" 2>&1 &
  BACKEND_PID=$!
  cd ..

  # Launch Next.js frontend (Dev mode)
  cd frontend
  nohup env NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT" PORT="$FRONTEND_PORT" npm run dev -- -p "$FRONTEND_PORT" -H 0.0.0.0 > "../$LOG_DIR/frontend.log" 2>&1 &
  FRONTEND_PID=$!
  cd ..
else
  # Release mode (No reload)
  cd backend
  nohup env PYTHONPATH=. venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" > "../$LOG_DIR/backend.log" 2>&1 &
  BACKEND_PID=$!
  cd ..

  # Build Next.js frontend first
  echo "Building Next.js frontend for release... (this may take a minute)"
  cd frontend
  NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT" npm run build
  
  # Launch Next.js frontend (Release mode)
  nohup env PORT="$FRONTEND_PORT" npm run start -- -p "$FRONTEND_PORT" -H 0.0.0.0 > "../$LOG_DIR/frontend.log" 2>&1 &
  FRONTEND_PID=$!
  cd ..
fi

# Save PIDs for stop command
echo "BACKEND_PID=$BACKEND_PID" > "$PID_FILE"
echo "FRONTEND_PID=$FRONTEND_PID" >> "$PID_FILE"

# Wait a moment to verify they are running
echo "Verifying server startup..."
sleep 3

BACKEND_OK=true
FRONTEND_OK=true

if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  BACKEND_OK=false
fi

if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
  FRONTEND_OK=false
fi

if [ "$BACKEND_OK" = true ] && [ "$FRONTEND_OK" = true ]; then
  echo ""
  echo "=========================================="
  echo "    PLAM Application Stack is RUNNING     "
  echo "=========================================="
  echo ""
  echo "  Frontend URL : http://localhost:$FRONTEND_PORT"
  echo "  Backend API  : http://localhost:$BACKEND_PORT"
  echo "  Backend Logs : tail -f $LOG_DIR/backend.log"
  echo "  Frontend Logs: tail -f $LOG_DIR/frontend.log"
  echo ""
  echo "To stop the running application, run: ./setup.sh stop"
  echo "=========================================="
else
  echo "[-] Error: One or both servers failed to start." >&2
  if [ "$BACKEND_OK" != true ]; then
    echo "    Backend failed to start. Last few log lines ($LOG_DIR/backend.log):" >&2
    if [ -f "$LOG_DIR/backend.log" ]; then
      tail -n 10 "$LOG_DIR/backend.log" >&2
    else
      echo "    (Log file not found)" >&2
    fi
  fi
  if [ "$FRONTEND_OK" != true ]; then
    echo "    Frontend failed to start. Last few log lines ($LOG_DIR/frontend.log):" >&2
    if [ -f "$LOG_DIR/frontend.log" ]; then
      tail -n 10 "$LOG_DIR/frontend.log" >&2
    else
      echo "    (Log file not found)" >&2
    fi
  fi
  # Stop whatever started
  ./setup.sh stop --backend-port "$BACKEND_PORT" --frontend-port "$FRONTEND_PORT" >/dev/null 2>&1 || true
  exit 1
fi
