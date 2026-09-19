#!/usr/bin/env bash
# ==============================================================================
#  M.A.R.K.E.T. AI Systems - Production & Local Launch Script
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo " [M.A.R.K.E.T AI Core] Starting Engine..."
echo "=================================================================="

# Check for .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "  .env file not found. Creating default from .env.example..."
        cp .env.example .env
        echo " Created .env! Make sure to update your API keys in .env."
    fi
fi

# Set up Python virtual environment if not present
if [ ! -d "venv" ]; then
    echo " Creating Python virtual environment (venv)..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install / update requirements
echo " Checking and installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Default host and port
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8000"}

echo "──────────────────────────────────────────────────────────────────"
echo " Everything ready! Starting FastAPI server on http://${HOST}:${PORT}"
echo " Observability & Diagnostics: http://localhost:${PORT}"
echo " Swagger API Docs:           http://localhost:${PORT}/docs"
echo "──────────────────────────────────────────────────────────────────"

exec uvicorn main:app --host "$HOST" --port "$PORT" --workers 1 --proxy-headers
