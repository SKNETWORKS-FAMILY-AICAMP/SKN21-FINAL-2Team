"""LLM-as-Judge 점수를 0~1 범위로 정규화한다."""

from __future__ import annotations


def normalize_judge_score(value: float | int | str) -> float:
    """0~1 또는 legacy 1~5 점수를 0~1 범위로 맞춘다."""
    score = float(value)
    if score > 1.0:
        score /= 5.0
    return round(min(max(score, 0.0), 1.0), 4)
