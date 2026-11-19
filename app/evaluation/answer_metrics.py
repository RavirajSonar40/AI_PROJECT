"""Deterministic, offline-friendly answer quality metrics.

These are lexical and embedding-based proxies, not an LLM judge. They are
cheap, reproducible and good enough to show regressions between retrieval
configurations on the demo corpus. The dashboard labels them as proxies.
"""

from __future__ import annotations

import re
from math import sqrt

STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "also",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "each",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "may",
    "more",
    "most",
    "must",
    "no",
    "not",
    "of",
    "on",
    "or",
    "other",
    "our",
    "out",
    "over",
    "same",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "to",
    "up",
    "use",
    "used",
    "using",
    "was",
    "we",
    "were",
    "what",
    "when",
    "which",
    "who",
    "will",
    "with",
    "would",
    "you",
    "your",
}

ABSTENTION_MARKERS = (
    "not have enough information",
    "not enough information",
    "insufficient information",
    "do not have information",
    "no information available",
    "cannot answer",
    "can not answer",
    "no tengo informacion",
    "no tengo información",
    "no hay informacion",
    "no hay información",
    "informacion insuficiente",
    "información insuficiente",
)

WORD_PATTERN = re.compile(r"[a-záéíóúñ0-9]+")
SENTENCE_PATTERN = re.compile(r"[^.!?\n]+[.!?]?")


def normalize_words(text: str) -> list[str]:
    return WORD_PATTERN.findall(
        (text or "").lower()
    )


def content_words(text: str) -> list[str]:
    return [
        word
        for word in normalize_words(text)
        if word not in STOPWORDS and len(word) > 2
    ]


def abstained(answer: str | None) -> bool:
    if not answer:
        return False

    normalized = answer.lower()

    return any(
        marker in normalized
        for marker in ABSTENTION_MARKERS
    )


def lexical_faithfulness(
    answer: str | None,
    context: str | None,
) -> float:
    """Share of answer sentences supported by retrieved context.

    A sentence counts as supported when at least half of its content words
    appear in the context. Crude, but it catches invented facts.
    """

    if not answer:
        return 0.0

    context_terms = set(
        content_words(context or "")
    )

    if not context_terms:
        return 0.0

    considered = 0
    supported = 0

    for raw_sentence in SENTENCE_PATTERN.findall(
        answer
    ):
        words = content_words(raw_sentence)

        if len(words) < 3:
            continue

        considered += 1

        overlap = sum(
            1
            for word in words
            if word in context_terms
        ) / len(words)

        if overlap >= 0.5:
            supported += 1

    if considered == 0:
        return 0.0

    return supported / considered


def context_precision(
    retrieved_document_ids: list[int],
    expected_document_ids: list[int],
) -> float:
    retrieved = set(retrieved_document_ids)
    expected = set(expected_document_ids)

    if not retrieved:
        return 1.0 if not expected else 0.0

    if not expected:
        # Retrieval for an unanswerable question is noise.
        return 0.0

    return len(retrieved & expected) / len(
        retrieved
    )


def context_recall(
    retrieved_document_ids: list[int],
    expected_document_ids: list[int],
    did_abstain: bool,
) -> float:
    expected = set(expected_document_ids)

    if not expected:
        return 1.0 if did_abstain else 0.0

    retrieved = set(retrieved_document_ids)

    if not retrieved:
        return 0.0

    return len(retrieved & expected) / len(
        expected
    )


def cosine_similarity(
    left: list[float],
    right: list[float],
) -> float:
    if not left or not right:
        return 0.0

    dot = sum(
        a * b for a, b in zip(left, right)
    )

    left_norm = sqrt(
        sum(a * a for a in left)
    )

    right_norm = sqrt(
        sum(b * b for b in right)
    )

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot / (left_norm * right_norm)


def did_pass(
    expected_document_ids: list[int],
    did_abstain: bool,
    faithfulness: float,
    recall: float,
) -> bool:
    if not expected_document_ids:
        return did_abstain

    return (
        recall >= 0.5
        and faithfulness >= 0.4
    )
