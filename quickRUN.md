# To directory
cd /Users/sky/projects/ensemble

# Activate python venv
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env and settings
cp .env.example .env
cp config/settings.example.yaml config/settings.yaml

# Configure settings.yaml
cache.backend: redis for Redis, otherwise use file-backed default via cache.file_path
cache.redis_url: redis://localhost:6379/0
cost.per_token_usd, groq_per_token_usd, aistudio_per_token_usd
cms.license_token_ttl_seconds, retry/backoff settings
If you want real LLM / CMS access, set API keys in .env:
GROQ_API_KEY
AI_STUDIO_API_KEY
(OpenAI support is in config if you add it)
Note: out of the box, the repo runs with the mock LLM provider and deterministic fixture fallback, so it is runnable even without external API keys.

# RUN:
python -m src.agent.cli --input /Users/sky/projects/ensemble/tests/fixtures/denial_letters/basic_denial.txt
OR
python -m src.agent.cli --input tests/fixtures/denial_letters/basic_denial.txt --output output.json

# Test suite RUN
pytest -q

# The fixture is already created:
python -m src.agent.cli --input tests/fixtures/denial_letters/sample_eob_denial.pdf

# Or use your own text-layer PDF (not scanned):
python -m src.agent.cli --input /path/to/your_eob.pdf

# Run on the synthetic PDF:
python -m src.agent.cli --input tests/fixtures/denial_letters/sample_eob_denial.pdf

# Run on any real text-layer PDF (not scanned):
python -m src.agent.cli --input /path/to/your_eob_denial.pdf

# Still works on text too:
python -m src.agent.cli --input tests/fixtures/denial_letters/basic_denial.txt