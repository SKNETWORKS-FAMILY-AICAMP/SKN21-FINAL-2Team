"""
RAGAS 비의존 리트리버 평가 스크립트.

현재 프로젝트(places/photos 컬렉션, 관광지 추천 도메인)에 맞춰
query + retrieved candidates 기반으로 검색 품질을 측정한다.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = Path(__file__).resolve().parent
RESULT_DIR = EVAL_DIR / "result"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

CATEGORIES = ["관광지", "문화시설", "축제공연행사", "레포츠", "숙박", "음식점"]
CATEGORY_ALIASES = {
    "명소": "관광지",
    "볼거리": "관광지",
    "박물관": "문화시설",
    "미술관": "문화시설",
    "전시": "문화시설",
    "축제": "축제공연행사",
    "공연": "축제공연행사",
    "액티비티": "레포츠",
    "체험": "레포츠",
    "숙소": "숙박",
    "호텔": "숙박",
    "맛집": "음식점",
    "식당": "음식점",
    "레스토랑": "음식점",
    "카페": "음식점",
}

TOKEN_STOPWORDS = {
    "추천",
    "추천해줘",
    "추천해",
    "알려줘",
    "알려줘요",
    "기준",
    "근처",
    "에서",
    "같은",
    "느낌",
    "분위기",
    "장소",
    "서울",
    "서울특별시",
}


@dataclass
class Reference:
    title: str = ""
    category: str = ""
    district: str = ""


def _resolve_eval_path(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (EVAL_DIR / p)


def _normalize_text(value: str) -> str:
    return re.sub(r"[\s\W_]+", "", (value or "")).lower()


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _normalized_cosine(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return 0.0
    an = float(np.linalg.norm(a))
    bn = float(np.linalg.norm(b))
    if an == 0.0 or bn == 0.0:
        return 0.0
    cos = float(np.dot(a, b) / (an * bn))
    return _clip01((cos + 1.0) / 2.0)


def _extract_gold_title(ground_truth: str) -> str:
    if not ground_truth:
        return ""
    left = ground_truth.split("을 포함", 1)[0].strip()
    if ". " in left:
        left = left.split(". ")[-1].strip()
    m = re.search(r"([^\s]+)\s*$", left)
    if m:
        return m.group(1).strip(".,")
    fallback = ground_truth.split(" - ", 1)[0].strip()
    return fallback.split(" (", 1)[0].strip()


def _extract_category(text: str) -> str:
    if not text:
        return ""
    for cat in CATEGORIES:
        if cat in text:
            return cat
    for alias, cat in CATEGORY_ALIASES.items():
        if alias in text:
            return cat
    return ""


def _extract_district(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"(서울특별시\s+[가-힣]+구)", text)
    if m:
        return m.group(1)
    m = re.search(r"([가-힣]+구)", text)
    return f"서울특별시 {m.group(1)}" if m else ""


def _tokenize_query(query: str) -> list[str]:
    tokens = re.findall(r"[가-힣A-Za-z0-9]+", query or "")
    return [t for t in tokens if len(t) >= 2 and t not in TOKEN_STOPWORDS]


def _query_coverage(query: str, docs: list[str]) -> float:
    tokens = list(dict.fromkeys(_tokenize_query(query)))
    if not tokens:
        return 0.0
    corpus = " ".join(docs)
    matched = sum(1 for t in tokens if t in corpus)
    return _clip01(matched / len(tokens))


def _keyword_overlap_score(query: str, doc_text: str) -> float:
    q_tokens = set(_tokenize_query(query))
    d_tokens = set(_tokenize_query(doc_text))
    if not q_tokens or not d_tokens:
        return 0.0
    return _clip01(len(q_tokens & d_tokens) / len(q_tokens))


def _bm25_like_score(query: str, doc_text: str) -> float:
    # 간단한 BM25 유사 근사치 (TF 기반), 평가용 보조 점수로 사용
    tokens = _tokenize_query(query)
    if not tokens:
        return 0.0
    doc_tokens = re.findall(r"[가-힣A-Za-z0-9]+", doc_text or "")
    if not doc_tokens:
        return 0.0
    doc_len = len(doc_tokens)
    freq = {}
    for tok in doc_tokens:
        freq[tok] = freq.get(tok, 0) + 1

    k1 = 1.2
    b = 0.75
    avgdl = 120.0
    score = 0.0
    for t in tokens:
        tf = freq.get(t, 0)
        if tf <= 0:
            continue
        denom = tf + k1 * (1 - b + b * (doc_len / avgdl))
        score += ((k1 + 1) * tf) / denom
    # 포화 함수로 0~1 정규화
    return _clip01(1 - math.exp(-score))


def _candidate_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    payload = candidate.get("payload") if isinstance(candidate, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _candidate_title(candidate: dict[str, Any]) -> str:
    payload = _candidate_payload(candidate)
    return str(payload.get("title") or payload.get("name") or candidate.get("title") or "").strip()


def _candidate_category(candidate: dict[str, Any]) -> str:
    payload = _candidate_payload(candidate)
    raw = str(payload.get("contenttypeid") or payload.get("category") or "").strip()
    return _extract_category(raw) or raw


def _candidate_addr(candidate: dict[str, Any]) -> str:
    payload = _candidate_payload(candidate)
    return str(payload.get("addr") or payload.get("address") or "").strip()


def _candidate_vector_score(candidate: dict[str, Any]) -> float:
    try:
        return float(candidate.get("score", 0.0))
    except Exception:
        return 0.0


def _candidate_to_text(candidate: dict[str, Any]) -> str:
    payload = _candidate_payload(candidate)
    parts = [
        str(payload.get("title") or payload.get("name") or candidate.get("title") or ""),
        str(payload.get("contenttypeid") or payload.get("category") or ""),
        str(payload.get("addr") or payload.get("address") or ""),
        str(payload.get("llm_text") or payload.get("description") or candidate.get("description") or ""),
        str(payload.get("usetime") or ""),
        str(payload.get("restdate") or ""),
    ]
    text = " | ".join([p.strip() for p in parts if p and str(p).strip()])
    return text[:1200]


def _find_gold_rank(gold_title: str, retrieved_titles: list[str], top_k: int) -> int:
    if not gold_title:
        return 0
    g = _normalize_text(gold_title)
    for idx, title in enumerate(retrieved_titles[:top_k], start=1):
        t = _normalize_text(title)
        if t and (t in g or g in t):
            return idx
    return 0


def _ndcg_at_k(rank: int, top_k: int) -> float:
    if rank <= 0 or rank > top_k:
        return 0.0
    return float(1.0 / math.log2(rank + 1))


class SimilarityScorer:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
        self._model = None
        self._model_load_failed = False
        self._cache: dict[str, np.ndarray] = {}

    def _ensure_model(self):
        if self._model is not None or self._model_load_failed:
            return
        try:
            from sentence_transformers import SentenceTransformer
            from app.utils.config import DEVICE, TEXT_MODEL

            chosen = self.model_name or TEXT_MODEL
            self._model = SentenceTransformer(chosen, device=DEVICE)
            self.model_name = chosen
        except Exception:
            self._model_load_failed = True

    def _embed(self, text: str) -> np.ndarray:
        key = text or ""
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        self._ensure_model()
        if self._model is None:
            vec = np.array([len(set(_tokenize_query(key)))], dtype=np.float32)
            self._cache[key] = vec
            return vec
        vec = np.asarray(self._model.encode(key), dtype=np.float32)
        self._cache[key] = vec
        return vec

    def similarity(self, query: str, doc: str) -> float:
        self._ensure_model()
        if self._model is None:
            return _keyword_overlap_score(query, doc)
        return _normalized_cosine(self._embed(query), self._embed(doc))

    def batch_similarity(self, query: str, docs: list[str]) -> list[float]:
        return [self.similarity(query, d) for d in docs]


def _load_records(data_file: str, limit: Optional[int] = None) -> list[dict[str, Any]]:
    data_path = _resolve_eval_path(data_file)
    if not data_path.exists():
        raise FileNotFoundError(f"Test data file not found: {data_path}")
    with data_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Test data must be a list")
    for i, row in enumerate(data):
        if not isinstance(row, dict) or not str(row.get("question", "")).strip():
            raise ValueError(f"Invalid sample at index={i}: 'question' is required")
    if limit is not None and limit > 0:
        data = data[:limit]
    return data


def _ensure_reference(item: dict[str, Any]) -> Reference:
    ref = item.get("reference") if isinstance(item.get("reference"), dict) else {}
    title = str(ref.get("title") or "").strip()
    category = str(ref.get("category") or "").strip()
    district = str(ref.get("district") or "").strip()
    return Reference(
        title=title or _extract_gold_title(str(item.get("ground_truth") or "")),
        category=category or _extract_category(str(item.get("question") or "")),
        district=district or _extract_district(str(item.get("question") or "")),
    )


def enrich_references_inplace(records: list[dict[str, Any]]) -> int:
    changed = 0
    for item in records:
        cur = item.get("reference") if isinstance(item.get("reference"), dict) else {}
        ensured = _ensure_reference(item)
        new_ref = {
            "title": ensured.title,
            "category": ensured.category,
            "district": ensured.district,
        }
        if cur != new_ref:
            item["reference"] = new_ref
            changed += 1
    return changed


def save_records(data_file: str, records: list[dict[str, Any]]):
    path = _resolve_eval_path(data_file)
    with path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)


def _safe_mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def _safe_category_bucket(category: str) -> str:
    c = _extract_category(category)
    return c if c else "unknown"


def _build_summary(
    mode: str,
    rows: list[dict[str, Any]],
    top_k: int,
    data_file: str,
    enriched_count: int,
) -> dict[str, Any]:
    total = len(rows)
    unsup_rows = [r for r in rows if r.get("unsup_evaluable")]
    labeled_rows = [r for r in rows if r.get("labeled_evaluable")]

    summary: dict[str, Any] = {
        "mode": mode,
        "top_k": top_k,
        "data_file": data_file,
        "sample_count": total,
        "retrieval_failed_count": sum(1 for r in rows if r.get("retrieval_failed")),
        "reference_enriched_count": enriched_count,
    }

    if mode in ("unsupervised", "all"):
        summary.update(
            {
                "unsupervised_evaluable_count": len(unsup_rows),
                "sim@1": _safe_mean([float(r["sim@1"]) for r in unsup_rows]),
                "sim@k_mean": _safe_mean([float(r["sim@k_mean"]) for r in unsup_rows]),
                "sim@k_min": _safe_mean([float(r["sim@k_min"]) for r in unsup_rows]),
                "query_coverage": _safe_mean([float(r["query_coverage"]) for r in unsup_rows]),
                "vector_score@1": _safe_mean([float(r.get("vector_score@1", 0.0)) for r in unsup_rows]),
                "keyword_score@k": _safe_mean([float(r.get("keyword_score@k", 0.0)) for r in unsup_rows]),
                "bm25_score@k": _safe_mean([float(r.get("bm25_score@k", 0.0)) for r in unsup_rows]),
                "category_consistency@k": _safe_mean(
                    [float(r["category_consistency@k"]) for r in rows if r.get("category_consistency@k") is not None]
                ),
                "district_consistency@k": _safe_mean(
                    [float(r["district_consistency@k"]) for r in rows if r.get("district_consistency@k") is not None]
                ),
            }
        )

    if mode in ("labeled", "all"):
        summary.update(
            {
                "labeled_evaluable_count": len(labeled_rows),
                "hit@1": _safe_mean([float(r["hit@1"]) for r in labeled_rows]),
                "hit@3": _safe_mean([float(r["hit@3"]) for r in labeled_rows]),
                "hit@5": _safe_mean([float(r["hit@5"]) for r in labeled_rows]),
                "mrr@k": _safe_mean([float(r["mrr@k"]) for r in labeled_rows]),
                "ndcg@k": _safe_mean([float(r["ndcg@k"]) for r in labeled_rows]),
            }
        )

    # 카테고리별 집계(unsupervised 기준)
    by_category: dict[str, list[dict[str, Any]]] = {}
    for row in unsup_rows:
        cat = _safe_category_bucket(row.get("inferred_category", ""))
        by_category.setdefault(cat, []).append(row)

    summary["category_breakdown"] = {
        cat: {
            "count": len(items),
            "sim@k_mean": _safe_mean([float(i["sim@k_mean"]) for i in items]),
            "query_coverage": _safe_mean([float(i["query_coverage"]) for i in items]),
        }
        for cat, items in sorted(by_category.items())
    }

    return summary


def _write_report(rows: list[dict[str, Any]], output_prefix: str) -> Path:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULT_DIR / f"{output_prefix}_report.csv"
    if not rows:
        with out.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["question"])
        return out

    fieldnames = list(rows[0].keys())
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            record = dict(row)
            for key in ("retrieved_titles", "retrieved_categories"):
                if isinstance(record.get(key), list):
                    record[key] = json.dumps(record[key], ensure_ascii=False)
            writer.writerow(record)
    return out


def _write_summary(summary: dict[str, Any], output_prefix: str) -> tuple[Path, Path]:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESULT_DIR / f"{output_prefix}_summary.json"
    txt_path = RESULT_DIR / f"{output_prefix}_summary.txt"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    lines = ["--- Retrieval Evaluation Summary ---"]
    for key, value in summary.items():
        if isinstance(value, float):
            lines.append(f"{key}: {value:.4f}")
        else:
            lines.append(f"{key}: {value}")
    with txt_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return json_path, txt_path


RetrieveFn = Callable[[str, int, Optional[str]], Awaitable[list[dict[str, Any]]]]


async def _default_retrieve_fn(question: str, top_k: int, category: Optional[str]) -> list[dict[str, Any]]:
    from app.retrieval.place import PlaceRetriever

    retriever = PlaceRetriever.get_instance()
    return await retriever.search_hybrid(query=question, limit=top_k, category=category)


async def evaluate_records(
    records: list[dict[str, Any]],
    mode: str,
    top_k: int,
    scorer: SimilarityScorer,
    retrieve_fn: RetrieveFn,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for idx, item in enumerate(records):
        question = str(item.get("question", "")).strip()
        reference = _ensure_reference(item)
        inferred_category = _extract_category(question) or reference.category
        inferred_district = _extract_district(question) or reference.district

        retrieval_failed = False
        error_message = ""
        try:
            candidates = await retrieve_fn(question, top_k, inferred_category or None)
        except Exception as e:
            retrieval_failed = True
            error_message = str(e)
            candidates = []

        top_candidates = candidates[:top_k]
        candidate_texts = [_candidate_to_text(c) for c in top_candidates]
        candidate_titles = [_candidate_title(c) for c in top_candidates]
        candidate_categories = [_candidate_category(c) for c in top_candidates]
        candidate_addrs = [_candidate_addr(c) for c in top_candidates]
        vector_scores = [_candidate_vector_score(c) for c in top_candidates]

        similarities = scorer.batch_similarity(question, candidate_texts) if candidate_texts else []
        keyword_scores = [_keyword_overlap_score(question, t) for t in candidate_texts]
        bm25_scores = [_bm25_like_score(question, t) for t in candidate_texts]

        sim_at_1 = float(similarities[0]) if similarities else 0.0
        sim_k_mean = _safe_mean(similarities)
        sim_k_min = min(similarities) if similarities else 0.0
        query_coverage = _query_coverage(question, candidate_texts)

        category_consistency = None
        if inferred_category and candidate_categories:
            matched = sum(1 for c in candidate_categories if _extract_category(c) == inferred_category)
            category_consistency = _clip01(matched / len(candidate_categories))

        district_consistency = None
        if inferred_district and candidate_addrs:
            matched = sum(1 for addr in candidate_addrs if inferred_district in addr)
            district_consistency = _clip01(matched / len(candidate_addrs))

        gold_rank = _find_gold_rank(reference.title, candidate_titles, top_k)
        hit1 = 1.0 if gold_rank == 1 else 0.0
        hit3 = 1.0 if 1 <= gold_rank <= 3 else 0.0
        hit5 = 1.0 if 1 <= gold_rank <= 5 else 0.0
        mrr = (1.0 / gold_rank) if gold_rank > 0 else 0.0
        ndcg = _ndcg_at_k(gold_rank, top_k)

        unsup_evaluable = bool(candidate_texts)
        labeled_evaluable = bool(reference.title)

        rows.append(
            {
                "idx": idx,
                "question": question,
                "inferred_category": inferred_category,
                "inferred_district": inferred_district,
                "reference_title": reference.title,
                "reference_category": reference.category,
                "reference_district": reference.district,
                "retrieved_count": len(candidates),
                "retrieved_titles": candidate_titles,
                "retrieved_categories": candidate_categories,
                "retrieval_failed": retrieval_failed,
                "error": error_message,
                "unsup_evaluable": unsup_evaluable,
                "sim@1": sim_at_1 if mode in ("unsupervised", "all") else 0.0,
                "sim@k_mean": sim_k_mean if mode in ("unsupervised", "all") else 0.0,
                "sim@k_min": sim_k_min if mode in ("unsupervised", "all") else 0.0,
                "query_coverage": query_coverage if mode in ("unsupervised", "all") else 0.0,
                "vector_score@1": (vector_scores[0] if vector_scores else 0.0) if mode in ("unsupervised", "all") else 0.0,
                "keyword_score@k": _safe_mean(keyword_scores) if mode in ("unsupervised", "all") else 0.0,
                "bm25_score@k": _safe_mean(bm25_scores) if mode in ("unsupervised", "all") else 0.0,
                "category_consistency@k": category_consistency if mode in ("unsupervised", "all") else None,
                "district_consistency@k": district_consistency if mode in ("unsupervised", "all") else None,
                "labeled_evaluable": labeled_evaluable,
                "gold_rank": gold_rank if mode in ("labeled", "all") else None,
                "hit@1": hit1 if mode in ("labeled", "all") and labeled_evaluable else 0.0,
                "hit@3": hit3 if mode in ("labeled", "all") and labeled_evaluable else 0.0,
                "hit@5": hit5 if mode in ("labeled", "all") and labeled_evaluable else 0.0,
                "mrr@k": mrr if mode in ("labeled", "all") and labeled_evaluable else 0.0,
                "ndcg@k": ndcg if mode in ("labeled", "all") and labeled_evaluable else 0.0,
            }
        )

    return rows


async def run(
    data_file: str,
    mode: str,
    top_k: int,
    limit: Optional[int],
    output_prefix: str,
    embedding_model: Optional[str],
    enrich_reference: bool,
) -> dict[str, Any]:
    records = _load_records(data_file, limit=limit)

    enriched_count = 0
    if enrich_reference:
        enriched_count = enrich_references_inplace(records)
        save_records(data_file, records)
        print(f"[INFO] reference 보강 완료: {enriched_count}건")

    scorer = SimilarityScorer(model_name=embedding_model)
    rows = await evaluate_records(
        records=records,
        mode=mode,
        top_k=top_k,
        scorer=scorer,
        retrieve_fn=_default_retrieve_fn,
    )

    summary = _build_summary(
        mode=mode,
        rows=rows,
        top_k=top_k,
        data_file=data_file,
        enriched_count=enriched_count,
    )
    report_path = _write_report(rows, output_prefix)
    summary_json, summary_txt = _write_summary(summary, output_prefix)

    print(f"[INFO] Report saved: {report_path}")
    print(f"[INFO] Summary saved: {summary_json}")
    print(f"[INFO] Summary saved: {summary_txt}")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RAGAS 비의존 리트리버 평가")
    parser.add_argument("--data-file", default="rag_eval_data.json")
    parser.add_argument("--mode", default="all", choices=["unsupervised", "labeled", "all"])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--output-prefix", default="evaluation_retrieval")
    parser.add_argument("--seed", type=int, default=42)  # 인터페이스 호환용
    parser.add_argument("--enrich-reference", action="store_true")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    asyncio.run(
        run(
            data_file=args.data_file,
            mode=args.mode,
            top_k=args.top_k,
            limit=args.limit,
            output_prefix=args.output_prefix,
            embedding_model=args.embedding_model,
            enrich_reference=args.enrich_reference,
        )
    )
