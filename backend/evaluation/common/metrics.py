from __future__ import annotations

import math
import re
from itertools import combinations
from typing import Any


def _safe_div(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def precision_at_k(predicted_ids: list[str], relevant_ids: set[str], k: int) -> float:
    topk = predicted_ids[:k]
    if not topk:
        return 0.0
    hits = sum(1 for pid in topk if pid in relevant_ids)
    return _safe_div(hits, len(topk))


def recall_at_k(predicted_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    topk = predicted_ids[:k]
    hits = sum(1 for pid in topk if pid in relevant_ids)
    return _safe_div(hits, len(relevant_ids))


def average_precision_at_k(predicted_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0

    score = 0.0
    hit_count = 0
    for rank, pid in enumerate(predicted_ids[:k], start=1):
        if pid in relevant_ids:
            hit_count += 1
            score += hit_count / rank

    return _safe_div(score, min(len(relevant_ids), k))


def mrr_at_k(predicted_ids: list[str], relevant_ids: set[str], k: int) -> float:
    for rank, pid in enumerate(predicted_ids[:k], start=1):
        if pid in relevant_ids:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(predicted_ids: list[str], relevant_ids: set[str], k: int) -> float:
    dcg = 0.0
    for rank, pid in enumerate(predicted_ids[:k], start=1):
        rel = 1.0 if pid in relevant_ids else 0.0
        if rel > 0:
            dcg += rel / math.log2(rank + 1)

    ideal_count = min(len(relevant_ids), k)
    if ideal_count == 0:
        return 0.0

    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_count + 1))
    return _safe_div(dcg, idcg)


def ild_at_n(items: list[dict[str, Any]], n: int) -> float:
    """카테고리 불일치 비율 기반 간단 ILD."""
    topn = items[:n]
    if len(topn) < 2:
        return 0.0

    def category_of(item: dict[str, Any]) -> str:
        payload = item.get("payload", {}) if isinstance(item, dict) else {}
        return str(payload.get("contenttypeid") or payload.get("category") or "unknown").strip() or "unknown"

    distances = []
    for left, right in combinations(topn, 2):
        distances.append(0.0 if category_of(left) == category_of(right) else 1.0)

    return _safe_div(sum(distances), len(distances))


def category_coverage(items: list[dict[str, Any]], n: int) -> float:
    topn = items[:n]
    if not topn:
        return 0.0

    categories = set()
    for item in topn:
        payload = item.get("payload", {}) if isinstance(item, dict) else {}
        cat = str(payload.get("contenttypeid") or payload.get("category") or "unknown").strip() or "unknown"
        categories.add(cat)

    return _safe_div(len(categories), len(topn))


def _extract_district(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"([가-힣]+구)", text)
    return m.group(1) if m else ""


def district_diversity(items: list[dict[str, Any]], n: int) -> float:
    topn = items[:n]
    if not topn:
        return 0.0

    districts = set()
    for item in topn:
        payload = item.get("payload", {}) if isinstance(item, dict) else {}
        addr = str(payload.get("addr") or payload.get("address") or "")
        d = _extract_district(addr)
        if d:
            districts.add(d)

    return _safe_div(len(districts), len(topn))
