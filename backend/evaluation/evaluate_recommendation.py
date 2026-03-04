from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = Path(__file__).resolve().parent
RESULT_DIR = EVAL_DIR / "result"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from evaluation.common import (  # noqa: E402
    build_evaluation_summary,
    category_coverage,
    district_diversity,
    ild_at_n,
    load_and_validate_csv,
    ndcg_at_k,
    parse_structured_columns,
    precision_at_k,
    recall_at_k,
    write_evaluation_outputs,
)


def _extract_relevant_ids(record: dict[str, Any]) -> set[str]:
    """평가 레코드에서 정답 ID 집합을 추출한다."""
    values = record.get("relevant_ids")
    if isinstance(values, list):
        return {str(v).strip() for v in values if str(v).strip()}
    return set()


def _extract_selected_ids(record: dict[str, Any], top_n: int) -> list[str]:
    """평가 레코드에서 최종 추천 ID 목록을 N개까지 추출한다."""
    values = record.get("selected_ids")
    if isinstance(values, list):
        return [str(v).strip() for v in values if str(v).strip()][:top_n]
    return []


def _extract_selected_items(record: dict[str, Any], top_n: int) -> list[dict[str, Any]]:
    """선택된 ID와 후보 풀을 조인해 다양성 계산용 아이템 목록을 만든다."""
    candidates = record.get("retrieved_candidates")
    selected_ids = set(_extract_selected_ids(record, top_n))
    if not isinstance(candidates, list) or not selected_ids:
        return []

    selected = []
    for c in candidates:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or c.get("contentid") or "").strip()
        if cid in selected_ids:
            payload = c.get("payload") if isinstance(c.get("payload"), dict) else {}
            selected.append({"id": cid, "payload": payload})
    return selected[:top_n]


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    """행 리스트의 특정 수치 컬럼 평균을 계산한다."""
    values = [float(r.get(key, 0.0)) for r in rows if r.get(key) is not None]
    return float(sum(values) / len(values)) if values else 0.0


def run_recommendation_evaluation(input_csv: str, top_n: int, output_prefix: str) -> dict[str, Any]:
    """추천 단계 정확도/다양성/존재성 지표를 계산해 리포트를 저장한다."""
    required = ["relevant_ids", "selected_ids", "retrieved_candidates", "response"]
    try:
        df = load_and_validate_csv(input_csv, required_columns=required)
    except ValueError as e:
        summary = build_evaluation_summary(
            stage="recommendation",
            sample_count=0,
            executed=False,
            metrics={},
            skipped_reason=str(e),
        )
        write_evaluation_outputs([], summary, output_prefix, RESULT_DIR)
        return summary

    df = parse_structured_columns(df, ["relevant_ids", "selected_ids", "retrieved_candidates"])

    rows: list[dict[str, Any]] = []
    total_selected = 0
    total_existing = 0

    for idx, (_, row) in enumerate(df.iterrows()):
        record = row.to_dict()
        question = str(record.get("question") or record.get("user_input") or "")
        relevant_ids = _extract_relevant_ids(record)
        selected_ids = _extract_selected_ids(record, top_n)
        selected_items = _extract_selected_items(record, top_n)

        precision = precision_at_k(selected_ids, relevant_ids, top_n)
        recall = recall_at_k(selected_ids, relevant_ids, top_n)
        ndcg = ndcg_at_k(selected_ids, relevant_ids, top_n)
        ild = ild_at_n(selected_items, top_n)
        cat_cov = category_coverage(selected_items, top_n)
        dist_div = district_diversity(selected_items, top_n)

        # selected_ids가 존재하면 엔티티 존재로 간주(오프라인 CSV 기준)
        existence_hits = sum(1 for sid in selected_ids if sid)
        total_selected += len(selected_ids)
        total_existing += existence_hits

        rows.append(
            {
                "idx": idx,
                "question": question,
                "selected_count": len(selected_ids),
                "relevant_count": len(relevant_ids),
                "precision@n": precision,
                "recall@n": recall,
                "ndcg@n": ndcg,
                "ild@n": ild,
                "category_coverage": cat_cov,
                "district_diversity": dist_div,
                "entity_existence_rate": float(existence_hits / len(selected_ids)) if selected_ids else 0.0,
                "selected_ids": selected_ids,
            }
        )

    summary = build_evaluation_summary(
        stage="recommendation",
        sample_count=len(rows),
        executed=True,
        metrics={
            "top_n": top_n,
            "precision@n": _mean(rows, "precision@n"),
            "recall@n": _mean(rows, "recall@n"),
            "ndcg@n": _mean(rows, "ndcg@n"),
            "ild@n": _mean(rows, "ild@n"),
            "category_coverage": _mean(rows, "category_coverage"),
            "district_diversity": _mean(rows, "district_diversity"),
            "entity_existence_rate": float(total_existing / total_selected) if total_selected else 0.0,
        },
    )

    write_evaluation_outputs(rows, summary, output_prefix, RESULT_DIR)
    return summary


def build_parser() -> argparse.ArgumentParser:
    """추천 평가 CLI 인자를 정의한다."""
    parser = argparse.ArgumentParser(description="추천 단계 평가")
    parser.add_argument("--input-csv", default="evaluation/evaluate_testdata.csv")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--output-prefix", default="evaluation_recommendation")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    summary = run_recommendation_evaluation(
        input_csv=args.input_csv,
        top_n=args.top_n,
        output_prefix=args.output_prefix,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
