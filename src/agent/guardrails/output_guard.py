from __future__ import annotations

import re

from src.agent.schemas.io_models import AppealDraft

# Minimum argument length to filter out trivial/empty strings.
_MIN_ARG_LENGTH = 20

# Patterns that may indicate hallucinated or template placeholder content.
_PLACEHOLDER_PATTERNS = [
    re.compile(r"\[.*?\]"),        # [INSERT ...] style placeholders
    re.compile(r"<.*?>"),          # <placeholder> style
    re.compile(r"lorem ipsum", re.I),
    re.compile(r"TODO|FIXME|PLACEHOLDER", re.I),
]


def validate_appeal_draft(
    draft: AppealDraft,
    evidence_ids: list[str] | None = None,
) -> None:
    if draft is None:
        raise ValueError("Appeal draft is missing.")

    if not draft.summary or not draft.summary.strip():
        raise ValueError("Appeal draft summary is required.")

    if len(draft.summary.strip()) < 30:
        raise ValueError("Appeal draft summary is too short to be meaningful.")

    if not draft.appeal_arguments:
        raise ValueError("At least one appeal argument is required.")

    for i, arg in enumerate(draft.appeal_arguments):
        if not arg or len(arg.strip()) < _MIN_ARG_LENGTH:
            raise ValueError(
                f"Appeal argument {i + 1} is too short or empty: '{arg}'"
            )
        for pattern in _PLACEHOLDER_PATTERNS:
            if pattern.search(arg):
                raise ValueError(
                    f"Appeal argument {i + 1} appears to contain a placeholder: '{arg}'"
                )

    if not draft.evidence_references:
        raise ValueError("At least one evidence reference is required.")

    if evidence_ids is not None:
        # All cited references must exist in retrieved evidence.
        missing = [ref for ref in draft.evidence_references if ref not in evidence_ids]
        if missing:
            raise ValueError(
                f"Draft references evidence IDs not found in retrieved policy evidence: {missing}. "
                "This may indicate hallucinated citations."
            )

    # Check summary for obvious placeholder patterns.
    for pattern in _PLACEHOLDER_PATTERNS:
        if pattern.search(draft.summary):
            raise ValueError(
                f"Appeal draft summary appears to contain a placeholder value."
            )
