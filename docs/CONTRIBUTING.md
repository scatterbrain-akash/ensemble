# Contributing

Thank you for contributing to the claims denial & appeal intelligence agent.

## Getting started

1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy config files:
   ```bash
   cp .env.example .env
   cp config/settings.example.yaml config/settings.yaml
   ```
3. Run the project:
   ```bash
   python -m src.agent.cli --input tests/fixtures/denial_letters/basic_denial.txt
   ```

## Recommended workflow

- Use branches for new work.
- Keep changes small and focused.
- Add tests for new functionality.
- Run formatting and linting before committing.

## Testing

Run the test suite:
```bash
pytest -q
```

## Coding conventions

- Use `snake_case` for functions and variables.
- Use `PascalCase` for classes and Pydantic models.
- Keep prompts in `src/agent/prompts/` as Markdown files.
- Keep configuration in `config/` and never hardcode secrets.
