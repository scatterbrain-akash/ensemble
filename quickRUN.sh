#!/usr/bin/env bash
set -euo pipefail

# Quick start for the Ensemble claims denial agent.
# Run this from the repository root.

echo "== Entering repository root =="
cd "$(dirname "$0")"

echo "== Creating virtual environment =="
python -m venv .venv
source .venv/bin/activate

echo "== Installing dependencies =="
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "== Copying environment and settings templates =="
cp -n .env.example .env || true
cp -n config/settings.example.yaml config/settings.yaml || true

cat <<'EOF'

Setup complete.

Next:
- Edit config/settings.yaml and .env as needed.
- For Redis, set cache.backend=redis and cache.redis_url=redis://localhost:6379/0.
- Set GROQ_API_KEY or AI_STUDIO_API_KEY in .env if using a real provider.

Run the sample command:
  python -m src.agent.cli --input tests/fixtures/denial_letters/basic_denial.txt --output output.json

Run tests:
  pytest -q
EOF
