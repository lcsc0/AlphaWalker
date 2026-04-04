#!/usr/bin/env bash
# AlphaWalker — start backend + frontend with a single command
# Usage: ./start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load nvm so node/npm are available
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

PYTHON=/opt/homebrew/Caskroom/miniconda/base/bin/python3
UVICORN=/opt/homebrew/Caskroom/miniconda/base/bin/uvicorn

# Fallback to whatever python3/uvicorn is on PATH
command -v "$UVICORN" &>/dev/null || UVICORN=uvicorn
command -v "$PYTHON" &>/dev/null || PYTHON=python3

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}Starting AlphaWalker...${NC}"
echo -e "  ${BLUE}Backend${NC}  → http://localhost:8000"
echo -e "  ${BLUE}Frontend${NC} → http://localhost:3000"
echo ""

# Start backend
"$UVICORN" api.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
(cd "$SCRIPT_DIR/frontend" && npm run dev -- --port 3000) &
FRONTEND_PID=$!

# Kill both on Ctrl+C
cleanup() {
    echo ""
    echo "Shutting down..."
    kill "$BACKEND_PID" 2>/dev/null
    kill "$FRONTEND_PID" 2>/dev/null
    wait "$BACKEND_PID" 2>/dev/null
    wait "$FRONTEND_PID" 2>/dev/null
    echo "Done."
}
trap cleanup INT TERM

wait "$BACKEND_PID" "$FRONTEND_PID"
