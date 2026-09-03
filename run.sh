#!/usr/bin/env bash
set -e

# Change to repository root directory
cd "$(dirname "$0")"

# Setup virtual environment if not already present
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    ./.venv/bin/pip install --upgrade pip
fi

# Check if PyQt6 and pymobiledevice3 are installed in .venv
if ! ./.venv/bin/python3 -c "import PyQt6, pymobiledevice3" >/dev/null 2>&1; then
    echo "Installing required dependencies from requirements.txt..."
    ./.venv/bin/pip install -r requirements.txt
fi

# Launch Location Spoofer GUI
echo "Starting iOS 17+ Location Spoofer..."
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"
exec ./.venv/bin/python3 app/main.py "$@"
