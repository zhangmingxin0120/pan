#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
APP_NAME="Pan"
APP_URL="http://localhost:8080"
HEALTH_URL="http://localhost:8080/health"
FORCE_BUILD=false
[[ "${1:-}" == "--build" ]] && FORCE_BUILD=true

command -v docker >/dev/null 2>&1 || { echo "[ERROR] Docker is not installed or not in PATH."; exit 1; }
if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Trying to start it..."
  case "$(uname -s)" in
    Darwin) open -a Docker ;;
    Linux)
      if command -v systemctl >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then sudo -n systemctl start docker
      else echo "[ERROR] Start Docker Desktop or run: sudo systemctl start docker"; exit 1; fi ;;
    *) echo "[ERROR] Start Docker manually, then run this script again."; exit 1 ;;
  esac
  for ((attempt = 1; attempt <= 60; attempt++)); do docker info >/dev/null 2>&1 && break; sleep 2; done
  docker info >/dev/null 2>&1 || { echo "[ERROR] Docker did not become ready within two minutes."; exit 1; }
fi
[[ -f .env ]] || [[ ! -f .env.example ]] || cp .env.example .env
echo "[1/3] Validating Docker Compose..."; docker compose config >/dev/null
if [[ "$FORCE_BUILD" != true ]] && docker compose up -d --no-build; then
  wait_step="[3/3]"
else
  if [[ "$FORCE_BUILD" != true ]]; then echo "Existing images are unavailable. A build is required."; fi
  echo "[2/4] Building images (network failures will be retried)..."
  build_ok=false
  for attempt in 1 2 3; do
    if docker compose build; then build_ok=true; break; fi
    if [[ "$attempt" -lt 3 ]]; then echo "Build attempt $attempt failed. Retrying in 5 seconds..."; sleep 5; fi
  done
  if [[ "$build_ok" != true ]]; then
    echo "[ERROR] Image build failed after three attempts."
    echo "The configured mirror may be temporarily unavailable."
    echo "You can change PYTHON_IMAGE, NODE_IMAGE and NGINX_IMAGE in .env."
    exit 1
  fi
  echo "[3/4] Starting rebuilt images..."; docker compose up -d --no-build
  wait_step="[4/4]"
fi
echo "$wait_step Waiting for the application..."
healthy=false
for ((attempt = 1; attempt <= 40; attempt++)); do
  if command -v curl >/dev/null 2>&1 && curl -fsS --max-time 3 "$HEALTH_URL" >/dev/null; then healthy=true; break; fi
  if ! command -v curl >/dev/null 2>&1 && command -v wget >/dev/null 2>&1 && wget -q -T 3 -O /dev/null "$HEALTH_URL"; then healthy=true; break; fi
  sleep 2
done
if [[ "$healthy" != true ]]; then echo "[ERROR] Startup failed. Recent logs:"; docker compose logs --tail=100; exit 1; fi
echo "$APP_NAME is ready: $APP_URL"
if [[ "${PAN_NO_OPEN:-0}" != "1" ]]; then
  if [[ "$(uname -s)" == "Darwin" ]]; then open "$APP_URL" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$APP_URL" >/dev/null 2>&1 || true; fi
fi
