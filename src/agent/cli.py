import argparse
from pathlib import Path

from src.agent.config import Settings
from src.agent.core.orchestrator import Orchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="Claims denial to appeal package agent")
    parser.add_argument("--input", type=str, help="Path to denial letter text file")
    parser.add_argument("--output", type=str, default=None, help="Optional output JSON file path")
    parser.add_argument("--environment", type=str, choices=["personal", "work"], default=None)
    args = parser.parse_args()

    settings = Settings(env=args.environment or "personal")
    orchestrator = Orchestrator(settings=settings)

    input_path = Path(args.input)
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    text = input_path.read_text(encoding="utf-8")
    result = orchestrator.run(text)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    else:
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
