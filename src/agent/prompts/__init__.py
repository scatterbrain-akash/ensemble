from __future__ import annotations

from pathlib import Path


def load_system_prompt(role: str) -> str:
    prompt_path = Path(__file__).parent / f"{role}_system.md"
    return prompt_path.read_text(encoding="utf-8")
