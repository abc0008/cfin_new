#!/bin/bash
# CFIN local dev launcher — starts backend (FastAPI :8000) + frontend (Next.js :3000).
# Usage: ./dev-up.sh [backend|frontend|all|status|stop]
# The Anthropic key is read from cfin_new/backend/.env, falling back to the
# legacy cfin/backend/.env (which uses "KEY = value" formatting).

set -u
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPO_DIR/backend"
FRONTEND_DIR="$REPO_DIR/nextjs-fdas"
LEGACY_ENV="$(dirname "$REPO_DIR")/cfin/backend/.env"
BACKEND_LOG="/tmp/cfin-backend.log"
FRONTEND_LOG="/tmp/cfin-frontend.log"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

read_key() {
  local f="$1"
  [ -f "$f" ] || return 1
  sed -n 's/^ANTHROPIC_API_KEY[[:space:]]*=[[:space:]]*//p' "$f" | head -1 | tr -d '[:space:]'
}

resolve_key() {
  local key=""
  key="$(read_key "$BACKEND_DIR/.env" || true)"
  [ -z "$key" ] && key="$(read_key "$LEGACY_ENV" || true)"
  echo "$key"
}

start_backend() {
  if curl -s -o /dev/null --max-time 2 http://localhost:8000/docs; then
    echo "backend: already running"
    return 0
  fi
  local key
  key="$(resolve_key)"
  if [ -z "$key" ]; then
    echo "backend: WARNING — no ANTHROPIC_API_KEY found; chat will not work" >&2
  fi
  cd "$BACKEND_DIR" || exit 1
  ANTHROPIC_API_KEY="$key" nohup python3 -m uvicorn app.main:app --port 8000 \
    > "$BACKEND_LOG" 2>&1 &
  echo "backend: starting (pid $!) — log: $BACKEND_LOG"
}

start_frontend() {
  if curl -s -o /dev/null --max-time 2 http://localhost:3000; then
    echo "frontend: already running"
    return 0
  fi
  cd "$FRONTEND_DIR" || exit 1
  NEXT_PUBLIC_API_URL="http://localhost:8000" nohup npx next dev -p 3000 \
    > "$FRONTEND_LOG" 2>&1 &
  echo "frontend: starting (pid $!) — log: $FRONTEND_LOG"
}

status() {
  curl -s -o /dev/null -w "backend  :8000 -> HTTP %{http_code}\n" --max-time 3 "http://localhost:8000/api/conversation?limit=1" || true
  curl -s -o /dev/null -w "frontend :3000 -> HTTP %{http_code}\n" --max-time 3 "http://localhost:3000" || true
}

stop_all() {
  pkill -f "uvicorn app.main:app" 2>/dev/null && echo "backend: stopped" || echo "backend: not running"
  pkill -f "next dev -p 3000" 2>/dev/null && echo "frontend: stopped" || echo "frontend: not running"
}

case "${1:-all}" in
  backend) start_backend ;;
  frontend) start_frontend ;;
  status) status ;;
  stop) stop_all ;;
  all) start_backend; start_frontend ;;
  *) echo "usage: $0 [backend|frontend|all|status|stop]"; exit 1 ;;
esac
