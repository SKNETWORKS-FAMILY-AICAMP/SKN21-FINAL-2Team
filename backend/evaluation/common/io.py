from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pandas as pd


def load_and_validate_csv(input_csv: str | Path, required_columns: list[str]) -> pd.DataFrame:
    """CSV 로드 후 필수 컬럼 존재를 검증한다."""
    path = Path(input_csv)
    if not path.exists():
        raise FileNotFoundError(f"입력 CSV 파일을 찾을 수 없습니다: {path}")

    df = pd.read_csv(path)
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {missing}")
    return df


def _safe_parse_literal(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            return ast.literal_eval(text)
        except Exception:
            return value
    return value


def parse_structured_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """리스트/딕셔너리 문자열 컬럼을 파싱한다."""
    parsed = df.copy()
    for col in columns:
        if col in parsed.columns:
            parsed[col] = parsed[col].apply(_safe_parse_literal)
    return parsed


def normalize_eval_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """평가 레코드를 공통 포맷으로 정규화한다."""
    normalized: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        item = row.to_dict()
        question = str(item.get("question") or item.get("user_input") or "").strip()
        item["question"] = question

        for list_col in [
            "relevant_ids",
            "selected_ids",
            "retrieved_candidates",
            "retrieved_contexts",
            "reference_contexts",
        ]:
            value = item.get(list_col)
            if value is None or (isinstance(value, float) and pd.isna(value)):
                item[list_col] = []
            elif not isinstance(value, list):
                # 파싱되지 않은 문자열이면 빈 리스트로 처리
                item[list_col] = []

        item["reference"] = str(item.get("reference") or "").strip()
        item["response"] = str(item.get("response") or "").strip()
        normalized.append(item)

    return normalized
