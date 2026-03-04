"""평가 스크립트 공통 유틸리티 모듈."""

from .io import load_and_validate_csv, parse_structured_columns, normalize_eval_records
from .metrics import (
    precision_at_k,
    recall_at_k,
    average_precision_at_k,
    mrr_at_k,
    ndcg_at_k,
    ild_at_n,
    category_coverage,
    district_diversity,
)
from .reporting import build_evaluation_summary, write_evaluation_outputs

__all__ = [
    "load_and_validate_csv",
    "parse_structured_columns",
    "normalize_eval_records",
    "precision_at_k",
    "recall_at_k",
    "average_precision_at_k",
    "mrr_at_k",
    "ndcg_at_k",
    "ild_at_n",
    "category_coverage",
    "district_diversity",
    "build_evaluation_summary",
    "write_evaluation_outputs",
]
