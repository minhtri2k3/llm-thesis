#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  Clothie — one-command launcher
#  Usage: ./start.sh [--stop | --logs | --status]
# ════════════════════════════════════════════════════════════════
set -euo pipefail

COMPOSE_DIR="$(cd "$(dirname "$0")/fashion_agent" && pwd)"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"
ENV_FILE="$COMPOSE_DIR/.env"

# ── Colours ─────────────────────────────────────────────────────
BOLD='\033[1m'; CYAN='\033[1;36m'; GREEN='\033[1;32m'
YELLOW='\033[1;33m'; RED='\033[1;31m'; RESET='\033[0m'

header() { echo -e "\n${CYAN}${BOLD}$1${RESET}"; }
ok()     { echo -e "${GREEN}✓ $1${RESET}"; }
info()   { echo -e "${YELLOW}➜ $1${RESET}"; }
err()    { echo -e "${RED}✗ $1${RESET}"; }

dc() { docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"; }

# ── Subcommands ──────────────────────────────────────────────────
case "${1:-up}" in
  --stop|stop)
    header "🛑  Stopping all services…"
    dc down
    ok "All services stopped."
    exit 0
    ;;
  --logs|logs)
    dc logs -f --tail=100
    exit 0
    ;;
  --status|status)
    dc ps
    exit 0
    ;;
  up|"")
    ;;  # continue to main launch flow
  *)
    echo "Usage: $0 [--stop | --logs | --status]"
    exit 1
    ;;
esac

# ── Resolve Docker on macOS (Desktop adds to interactive PATH only) ─
export PATH="/Applications/Docker.app/Contents/Resources/bin:$HOME/.docker/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"

# ── Pre-flight ───────────────────────────────────────────────────
header "🚀  Clothie Fashion RAG — Starting Stack"

if ! command -v docker &>/dev/null; then
  err "Docker not found. Install Docker Desktop first: https://www.docker.com/products/docker-desktop"
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  err ".env not found at $ENV_FILE"
  exit 1
fi

# ── Start databases first, wait for healthy ──────────────────────
info "Starting databases (postgres + qdrant)…"
dc up -d postgres qdrant

info "Waiting for databases to be healthy…"
for i in $(seq 1 30); do
  pg_ok=$(dc ps --format json postgres 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health','') if isinstance(d,dict) else [x.get('Health','') for x in d][0])" 2>/dev/null || echo "")
  qd_ok=$(dc ps --format json qdrant  2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health','') if isinstance(d,dict) else [x.get('Health','') for x in d][0])" 2>/dev/null || echo "")
  if [[ "$pg_ok" == "healthy" && "$qd_ok" == "healthy" ]]; then
    ok "Databases healthy."
    break
  fi
  printf "."
  sleep 2
done
echo ""

# ── Start the full stack ─────────────────────────────────────────
info "Building & starting all services (this may take a few minutes on first run)…"
dc up -d --build

ok "All containers started."

# ── Extract the trycloudflare.com URL ───────────────────────────
header "🌐  Waiting for public Cloudflare URL…"
info "Reading cloudflared logs (up to 60s)…"

TUNNEL_URL=""
for i in $(seq 1 60); do
  TUNNEL_URL=$(dc logs cloudflared-fe 2>/dev/null \
    | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' \
    | tail -1 || true)
  if [ -n "$TUNNEL_URL" ]; then
    break
  fi
  sleep 1
done

echo ""
if [ -n "$TUNNEL_URL" ]; then
  echo -e "${GREEN}${BOLD}"
  echo "  ╔══════════════════════════════════════════════════════╗"
  echo "  ║                                                      ║"
  printf "  ║   🎉 Public URL: %-35s ║\n" "$TUNNEL_URL"
  echo "  ║                                                      ║"
  echo "  ║   Local  URL:   http://localhost:3000                ║"
  echo "  ║   API    URL:   http://localhost:8000                ║"
  echo "  ║                                                      ║"
  echo "  ║   Run  ./start.sh --logs    to tail all logs         ║"
  echo "  ║   Run  ./start.sh --stop    to shut down             ║"
  echo "  ║   Run  ./start.sh --status  for container status     ║"
  echo "  ╚══════════════════════════════════════════════════════╝"
  echo -e "${RESET}"
else
  err "Could not detect Cloudflare URL within 60s."
  info "Check logs with:  ./start.sh --logs"
  info "Or manually:      docker logs fashion-cloudflared-fe"
  echo ""
  info "Local access still available at http://localhost:3000"
fi
