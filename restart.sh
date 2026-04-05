#!/usr/bin/env bash
# AlphaWalker — kill any running backend/frontend and restart both
# Usage: ./restart.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load nvm so node/npm are available
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

PYTHON=/opt/homebrew/Caskroom/miniconda/base/bin/python3
UVICORN=/opt/homebrew/Caskroom/miniconda/base/bin/uvicorn
command -v "$UVICORN" &>/dev/null || UVICORN=uvicorn
command -v "$PYTHON"  &>/dev/null || PYTHON=python3

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Load environment variables from .env ──────────────────────

if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
    echo -e "${GREEN}Loaded .env${NC}"
else
    echo -e "${YELLOW}Warning: no .env file found — LLM API key may be missing${NC}"
fi

# ── Kill existing processes ────────────────────────────────────

echo -e "${YELLOW}Stopping existing processes...${NC}"

# Backend: uvicorn on port 8000
pkill -f "uvicorn api.main:app" 2>/dev/null && echo "  killed backend" || true

# Frontend: vite / npm run dev on port 3000
pkill -f "vite.*3000"           2>/dev/null && echo "  killed frontend (vite)" || true
pkill -f "npm run dev"          2>/dev/null && echo "  killed frontend (npm)"  || true

# Free ports in case something else grabbed them
for PORT in 8000 3000; do
    PIDS=$(lsof -ti tcp:"$PORT" 2>/dev/null)
    if [ -n "$PIDS" ]; then
        echo "  freeing port $PORT (pids: $PIDS)"
        echo "$PIDS" | xargs kill -9 2>/dev/null || true
    fi
done

sleep 1
echo ""

# ── Start backend ──────────────────────────────────────────────

echo -e "${BLUE}Starting backend${NC}  → http://localhost:8000"
"$UVICORN" api.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready (up to 15s)
for i in $(seq 1 15); do
    if curl -sf http://localhost:8000/health &>/dev/null; then
        echo -e "  ${GREEN}backend ready${NC}"
        break
    fi
    sleep 1
done

# ── Start frontend ─────────────────────────────────────────────

echo -e "${BLUE}Starting frontend${NC} → http://localhost:3000"
(cd "$SCRIPT_DIR/frontend" && npm run dev -- --port 3000) &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}AlphaWalker running.${NC} Press Ctrl+C to stop."
echo ""

# ── Cleanup on exit ────────────────────────────────────────────

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill "$BACKEND_PID"  2>/dev/null
    kill "$FRONTEND_PID" 2>/dev/null
    wait "$BACKEND_PID"  2>/dev/null
    wait "$FRONTEND_PID" 2>/dev/null
    echo "Done."
}
trap cleanup INT TERM

wait "$BACKEND_PID" "$FRONTEND_PID"
