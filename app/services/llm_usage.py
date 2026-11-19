"""Provider usage metadata normalized across LangChain providers."""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    source: str = "estimated"


def usage_from_response(response: Any) -> LLMUsage | None:
    """Extract usage from common LangChain response metadata shapes."""
    metadata = getattr(response, "usage_metadata", None) or {}
    response_metadata = getattr(response, "response_metadata", None) or {}
    usage = metadata or response_metadata.get("token_usage") or response_metadata.get("usage") or {}
    if not isinstance(usage, dict):
        return None

    prompt = usage.get("input_tokens", usage.get("prompt_tokens", usage.get("prompt_eval_count")))
    completion = usage.get("output_tokens", usage.get("completion_tokens", usage.get("eval_count")))
    total = usage.get("total_tokens")
    if prompt is None and completion is None and total is None:
        return None

    prompt = int(prompt or 0)
    completion = int(completion or 0)
    return LLMUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=int(total if total is not None else prompt + completion),
        source="provider",
    )
