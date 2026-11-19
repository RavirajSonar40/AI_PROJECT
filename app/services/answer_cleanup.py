import re


# Some models (for example gpt-oss) emit internal citation markers such as
# "【7†L1-L9】" or "[1†L1-L5]" inside the generated text. Sources are already
# returned as structured data, so these markers are noise for the end user.
_CITATION_MARKERS = (
    re.compile(r"\s*【[^】]*】"),
    re.compile(r"\s*\[\d+†[^\]]*\]"),
)


def clean_model_answer(text: str) -> str:
    """Remove model-specific citation markers from a generated answer."""

    if not isinstance(text, str):
        return text

    cleaned = text

    for pattern in _CITATION_MARKERS:
        cleaned = pattern.sub("", cleaned)

    # Tidy the gaps left behind: "days ." -> "days."
    cleaned = re.sub(r"[ \t]+([.,;:!?%)\]])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)

    return cleaned.strip()
