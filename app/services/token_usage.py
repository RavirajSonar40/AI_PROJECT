"""Cheap token estimation helpers.

Real providers expose usage metadata, but the platform talks to them through
several abstractions. Estimating from characters keeps the observability
dashboard useful without coupling it to a specific provider response shape.
The UI labels these numbers as estimates.
"""

from __future__ import annotations


def estimate_tokens(text: str | None) -> int:
    if not text:
        return 0

    return max(1, (len(text) + 3) // 4)


def estimate_prompt_tokens(
    *parts: str | None,
) -> int:
    return sum(
        estimate_tokens(part)
        for part in parts
    )
