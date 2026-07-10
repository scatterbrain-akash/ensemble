from __future__ import annotations

from src.agent.config import Settings


def validate_input_text(input_text: str) -> None:
    if not input_text or not isinstance(input_text, str):
        raise ValueError("Input text must be a non-empty string.")
    if len(input_text) > 20000:
        raise ValueError("Input text exceeds maximum allowed length of 20,000 characters.")
