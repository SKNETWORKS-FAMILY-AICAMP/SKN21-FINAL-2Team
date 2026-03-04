from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from evaluation.common import load_and_validate_csv, parse_structured_columns  # noqa: E402


def parse_place_context_line(line: str) -> dict[str, str]:
    """`이름:...|분류:...|주소:...` 형태 컨텍스트를 장소 필드로 파싱한다."""
    text = str(line or "")
    parts = [p.strip() for p in text.split("|") if p.strip()]
    parsed = {"title": "", "category": "", "addr": "", "description": ""}

    for part in parts:
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key == "이름":
            parsed["title"] = value
        elif key == "분류":
            parsed["category"] = value
        elif key == "주소":
            parsed["addr"] = value
        elif key == "설명":
            parsed["description"] = value

    return parsed


def _stable_id(title: str, addr: str) -> str:
    base = f"{title}|{addr}".encode("utf-8")
    return hashlib.md5(base).hexdigest()[:12]


def build_candidates_from_contexts(contexts: list[str], top_k: int) -> list[dict[str, Any]]:
    """retrieved_contexts에서 후보 리스트(`retrieved_candidates`)를 생성한다."""
    candidates: list[dict[str, Any]] = []
    for idx, line in enumerate(contexts[:top_k], start=1):
        parsed = parse_place_context_line(line)
        title = parsed["title"] or f"unknown-{idx}"
        addr = parsed["addr"]
        cid = _stable_id(title, addr)
        score = 1.0 / idx

        candidates.append(
            {
                "id": cid,
                "payload": {
                    "title": title,
                    "contenttypeid": parsed["category"],
                    "addr": addr,
                    "description": parsed["description"],
                },
                "first_stage_source": "hybrid",
                "first_stage_score": score,
                "first_stage_rank": idx,
                "rerank_score": None,
                "final_rank": idx,
            }
        )

    return candidates


def infer_selected_ids_from_response(response: str, candidates: list[dict[str, Any]], top_n: int) -> list[str]:
    """응답 본문에서 추천된 장소명을 찾아 selected_ids를 추정한다."""
    if not response or not candidates:
        return []

    selected: list[str] = []
    normalized_response = re.sub(r"\s+", "", response).lower()

    # 1) 마크다운 링크 텍스트 매칭
    link_names = re.findall(r"\[([^\]]+)\]\(https?://[^)]+\)", response)
    for name in link_names:
        key = re.sub(r"\s+", "", name).lower()
        for c in candidates:
            title = str(c.get("payload", {}).get("title") or "")
            title_key = re.sub(r"\s+", "", title).lower()
            if title_key and (title_key in key or key in title_key):
                cid = str(c.get("id") or "").strip()
                if cid and cid not in selected:
                    selected.append(cid)
                    if len(selected) >= top_n:
                        return selected

    # 2) 본문 포함 매칭
    if len(selected) < top_n:
        for c in candidates:
            title = str(c.get("payload", {}).get("title") or "")
            title_key = re.sub(r"\s+", "", title).lower()
            if title_key and title_key in normalized_response:
                cid = str(c.get("id") or "").strip()
                if cid and cid not in selected:
                    selected.append(cid)
                    if len(selected) >= top_n:
                        break

    return selected


def infer_relevant_ids(reference: str, reference_contexts: list[str], candidates: list[dict[str, Any]]) -> list[str]:
    """reference/reference_contexts와 후보명을 비교해 relevant_ids를 추정한다."""
    if not candidates:
        return []

    corpus_parts = [str(reference or "")]
    corpus_parts.extend([str(x) for x in reference_contexts])
    corpus = re.sub(r"\s+", "", " ".join(corpus_parts)).lower()

    relevant: list[str] = []
    for c in candidates:
        title = str(c.get("payload", {}).get("title") or "")
        title_key = re.sub(r"\s+", "", title).lower()
        if title_key and title_key in corpus:
            cid = str(c.get("id") or "").strip()
            if cid and cid not in relevant:
                relevant.append(cid)

    return relevant


def enrich_records(df: pd.DataFrame, top_k: int, top_n: int) -> pd.DataFrame:
    """원본 평가 CSV를 enriched 스키마로 확장한다."""
    rows = []
    for _, row in df.iterrows():
        user_input = str(row.get("question") or row.get("user_input") or "")
        response = str(row.get("response") or "")
        reference = str(row.get("reference") or "")
        retrieved_contexts = row.get("retrieved_contexts") if isinstance(row.get("retrieved_contexts"), list) else []
        reference_contexts = row.get("reference_contexts") if isinstance(row.get("reference_contexts"), list) else []

        candidates = build_candidates_from_contexts(retrieved_contexts, top_k=top_k)
        selected_ids = infer_selected_ids_from_response(response, candidates, top_n=top_n)
        relevant_ids = infer_relevant_ids(reference, reference_contexts, candidates)

        out = row.to_dict()
        out["question"] = user_input
        out["retrieved_candidates"] = candidates
        out["selected_ids"] = selected_ids
        out["relevant_ids"] = relevant_ids
        rows.append(out)

    return pd.DataFrame(rows)


def run_prepare_enriched(input_csv: str, output_csv: str, top_k: int, top_n: int) -> dict[str, Any]:
    """CSV를 enriched 형태로 변환하고 저장한다."""
    required = ["response", "reference", "retrieved_contexts", "reference_contexts"]
    df = load_and_validate_csv(input_csv, required_columns=required)
    df = parse_structured_columns(df, ["retrieved_contexts", "reference_contexts"])

    enriched = enrich_records(df, top_k=top_k, top_n=top_n)

    out_path = Path(output_csv)
    if not out_path.is_absolute():
        output_text = str(output_csv).strip()
        if output_text.startswith("evaluation/"):
            out_path = ROOT_DIR / output_text
        else:
            out_path = EVAL_DIR / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(out_path, index=False, encoding="utf-8-sig")

    return {
        "input_csv": input_csv,
        "output_csv": str(out_path),
        "sample_count": int(len(enriched)),
        "top_k": top_k,
        "top_n": top_n,
        "columns_added": ["question", "retrieved_candidates", "selected_ids", "relevant_ids"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="평가 CSV enriched 데이터 생성기")
    parser.add_argument("--input-csv", default="evaluation/evaluate_testdata.csv")
    parser.add_argument("--output-csv", default="evaluation/evaluate_testdata_enriched.csv")
    parser.add_argument("--top-k", type=int, default=30)
    parser.add_argument("--top-n", type=int, default=5)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    summary = run_prepare_enriched(
        input_csv=args.input_csv,
        output_csv=args.output_csv,
        top_k=args.top_k,
        top_n=args.top_n,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
