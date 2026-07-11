import argparse
from pathlib import Path
from typing import Any

from src.agent.config import Settings
from src.agent.core.orchestrator import Orchestrator


def _format_summary(summary: dict[str, Any]) -> str:
    if not summary:
        return "No execution summary available."

    headers = ["Step", "Status", "Duration(s)", "LLM Calls", "Cache Hits", "Tokens In", "Tokens Out", "Cost (USD)", "Result"]
    rows = []
    for step in summary.get("steps", []):
        rows.append([
            step.get("step", ""),
            step.get("status", ""),
            f"{step.get('duration', 0.0):.3f}",
            str(step.get("llm_calls", 0)),
            str(step.get("cache_hits", 0)),
            str(step.get("tokens_in", 0)),
            str(step.get("tokens_out", 0)),
            f"{step.get('cost_usd', 0.0):.6f}",
            step.get("result", ""),
        ])

    widths = [max(len(str(cell)) for cell in column) for column in zip(headers, *rows)]
    separator = "  ".join("=" * width for width in widths)

    lines = ["EXECUTION SUMMARY", separator]
    header_line = "  ".join(header.ljust(width) for header, width in zip(headers, widths))
    lines.append(header_line)
    lines.append(separator.replace("=", "-"))
    for row in rows:
        lines.append("  ".join(str(cell).ljust(width) for cell, width in zip(row, widths)))
    lines.append(separator)

    overall = summary.get("overall_status", "unknown")
    escalation = summary.get("escalation_reason")
    input_len = summary.get("input_length", 0)
    total_llm_calls = summary.get("total_llm_calls", 0)
    total_cache_hits = summary.get("total_cache_hits", 0)
    total_tokens_in = summary.get("total_tokens_in", 0)
    total_tokens_out = summary.get("total_tokens_out", 0)
    total_cost = summary.get("total_cost_usd", 0.0)
    lines.append(f"Overall status: {overall}")
    lines.append(f"Input length: {input_len}")
    lines.append(f"Total LLM calls: {total_llm_calls}")
    lines.append(f"Total cache hits: {total_cache_hits}")
    lines.append(f"Total tokens in: {total_tokens_in}")
    lines.append(f"Total tokens out: {total_tokens_out}")
    lines.append(f"Total cost (USD): {total_cost:.6f}")
    if escalation:
        lines.append(f"Escalation reason: {escalation}")
    return "\n".join(lines)


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
    summary = result.metadata.get("execution_summary", {})

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(_format_summary(summary))
    else:
        print(result.model_dump_json(indent=2))
        print()
        print(_format_summary(summary))


if __name__ == "__main__":
    main()
