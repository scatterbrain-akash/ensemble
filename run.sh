#!/usr/bin/env bash
# run.sh — single entrypoint for setup, CLI runs, and Docker packaging
# Usage:  ./run.sh <command> [options]
# Commands:
#   setup           Create venv and install all dependencies
#   run-txt         Run the CLI on the sample text denial letter
#   run-pdf         Run the CLI on the sample PDF denial letter
#   run-custom      Run on a custom file: ./run.sh run-custom /path/to/file.pdf
#   run-web         Start the FastAPI web UI (http://localhost:8000)
#   test            Run the full pytest suite
#   evaluate        Run the scenario evaluator
#   docker-build    Build the Docker image
#   docker-up       Start with docker-compose (detached)
#   docker-down     Stop the docker-compose stack
#   docker-run      One-shot docker run without compose

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# ── Colours ──────────────────────────────────────────────────────────────────
BOLD='\033[1m'; CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RESET='\033[0m'
info()    { echo -e "${CYAN}▶ $*${RESET}"; }
success() { echo -e "${GREEN}✔ $*${RESET}"; }
warn()    { echo -e "${YELLOW}⚠ $*${RESET}"; }

CMD="${1:-help}"

# ── setup ─────────────────────────────────────────────────────────────────────
setup() {
  info "Creating Python virtual environment (.venv)…"
  python3 -m venv .venv
  source .venv/bin/activate

  info "Upgrading pip…"
  pip install --upgrade pip -q

  info "Installing core dependencies…"
  pip install -r requirements.txt -q

  info "Installing web dependencies (FastAPI / uvicorn)…"
  pip install -r requirements-web.txt -q

  # Check Redis connectivity (optional — app falls back to file cache if unavailable)
  if python3 -c "import redis; redis.from_url('redis://localhost:6379/0').ping()" 2>/dev/null; then
    success "Redis is reachable at localhost:6379 — cache.backend=redis will be used."
  else
    warn "Redis not reachable. The app will use file-backed cache (cache/cache_store.json)."
    warn "To enable Redis: run 'redis-server' in another terminal, then set cache.backend: redis in config/settings.yaml"
  fi
  if [ ! -f .env ]; then
    info "Copying .env.example → .env"
    cp .env.example .env
    warn "Edit .env and add your GROQ_API_KEY and/or AI_STUDIO_API_KEY before running."
  fi

  if [ ! -f config/settings.yaml ]; then
    info "Copying config/settings.example.yaml → config/settings.yaml"
    cp config/settings.example.yaml config/settings.yaml
  fi

  success "Setup complete. Activate the environment with:  source .venv/bin/activate"
}

# ── CLI helpers ───────────────────────────────────────────────────────────────
run_txt() {
  info "Running on sample text denial letter…"
  python -m src.agent.cli \
    --input tests/fixtures/denial_letters/basic_denial.txt \
    --output output_txt.json
  success "Done. Result written to output_txt.json"
}

run_pdf() {
  info "Running on sample PDF denial letter…"
  python -m src.agent.cli \
    --input tests/fixtures/denial_letters/sample_eob_denial.pdf \
    --output output_pdf.json
  success "Done. Result written to output_pdf.json"
}

run_custom() {
  local INPUT="${2:-}"
  if [ -z "$INPUT" ]; then
    echo "Usage: ./run.sh run-custom /path/to/file.pdf"
    exit 1
  fi
  info "Running on: $INPUT"
  python -m src.agent.cli --input "$INPUT"
}

# ── Web UI ────────────────────────────────────────────────────────────────────
run_web() {
  info "Starting FastAPI web UI on http://localhost:8000 …"
  uvicorn src.agent.api.app:app --host 0.0.0.0 --port 8000 --reload
}

# ── Tests & evaluation ────────────────────────────────────────────────────────
run_tests() {
  info "Running test suite…"
  python -m pytest -q
  success "All tests passed."
}

run_evaluate() {
  info "Running scenario evaluator…"
  python -c "
from pathlib import Path
from src.agent.config import Settings
from src.agent.evaluation.evaluator import Evaluator
result = Evaluator(Settings(env='personal')).run_scenarios(Path('tests/fixtures/scenarios.json'))
print(result)
"
}

# ── Docker ────────────────────────────────────────────────────────────────────
docker_build() {
  info "Building Docker image (ensemble-agent)…"
  docker build -t ensemble-agent .
  success "Image built: ensemble-agent"
}

docker_up() {
  info "Starting with docker-compose (detached)…"
  docker compose up --build -d
  success "Running. Visit http://localhost:8000"
}

docker_down() {
  info "Stopping docker-compose stack…"
  docker compose down
  success "Stopped."
}

docker_run() {
  info "Running container (one-shot, port 8000)…"
  docker run --rm -p 8000:8000 --env-file .env ensemble-agent
}

# ── Dispatch ──────────────────────────────────────────────────────────────────
case "$CMD" in
  setup)        setup ;;
  run-txt)      run_txt ;;
  run-pdf)      run_pdf ;;
  run-custom)   run_custom "$@" ;;
  run-web)      run_web ;;
  test)         run_tests ;;
  evaluate)     run_evaluate ;;
  docker-build) docker_build ;;
  docker-up)    docker_up ;;
  docker-down)  docker_down ;;
  docker-run)   docker_run ;;
  help|*)
    echo ""
    echo -e "${BOLD}Claims Denial Appeal Intelligence Agent — run.sh${RESET}"
    echo ""
    echo "  ./run.sh setup           Install dependencies and create .env / settings.yaml"
    echo "  ./run.sh run-txt         Process the sample text denial letter"
    echo "  ./run.sh run-pdf         Process the sample PDF denial letter"
    echo "  ./run.sh run-custom FILE Process a custom denial letter (txt or pdf)"
    echo "  ./run.sh run-web         Start the web UI at http://localhost:8000"
    echo "  ./run.sh test            Run the full pytest suite"
    echo "  ./run.sh evaluate        Run the scenario evaluator"
    echo "  ./run.sh docker-build    Build the Docker image"
    echo "  ./run.sh docker-up       Start with docker-compose"
    echo "  ./run.sh docker-down     Stop the docker-compose stack"
    echo "  ./run.sh docker-run      One-shot docker run (no compose)"
    echo ""
    ;;
esac
