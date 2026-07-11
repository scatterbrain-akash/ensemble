from __future__ import annotations

import re


# Minimum characters required to contain actionable claim information.
_MIN_LENGTH = 50
_MAX_LENGTH = 20_000

# Patterns that suggest this is a real denial/EOB document.
_SIGNAL_PATTERNS = [
    re.compile(r"\b(claim|denial|denied|eob|explanation of benefits)\b", re.I),
    re.compile(r"\b(procedure|diagnosis|cpt|icd|hcpcs)\b", re.I),
    re.compile(r"\b(medicare|medicaid|insurance|payer|member)\b", re.I),
]
# Require at least this many signal patterns to match before processing.
_MIN_SIGNALS = 1


def validate_input_text(input_text: str) -> None:
    if not input_text or not isinstance(input_text, str):
        raise ValueError("Input text must be a non-empty string.")

    stripped = input_text.strip()

    if len(stripped) < _MIN_LENGTH:
        raise ValueError(
            f"Input text is too short ({len(stripped)} chars). "
            "Provide the full denial letter or EOB document."
        )

    if len(stripped) > _MAX_LENGTH:
        raise ValueError(
            f"Input text exceeds maximum allowed length of {_MAX_LENGTH:,} characters. "
            "Truncate or split the document before processing."
        )

    signals_matched = sum(1 for p in _SIGNAL_PATTERNS if p.search(stripped))
    if signals_matched < _MIN_SIGNALS:
        raise ValueError(
            "Input does not appear to be a claim denial or EOB document. "
            "Expected content related to claims, procedures, diagnoses, or insurance."
        )
