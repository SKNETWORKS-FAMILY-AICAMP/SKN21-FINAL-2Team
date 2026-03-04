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

from evaluation.common import build_evaluation_summary, write_evaluation_outputs  # noqa: E402
from evaluation.evaluate_generation import run_generation_evaluation  # noqa: E402
from evaluation.evaluate_recommendation import run_recommendation_evaluation  # noqa: E402
from evaluation.evaluate_retrieval import run_csv_stage_evaluation  # noqa: E402


def run_stage_evaluations(
    input_csv: str,
    mode: str,
    retrieval_k: int,
    recommendation_n: int,
    generation_context_k: int,
    compare_rerank: bool,
) -> dict[str, Any]:
    """요청 모드에 맞춰 단계별 평가를 실행한다."""
    outputs: dict[str, Any] = {}

    if mode in ("retrieval", "all"):
        stage = "all" if compare_rerank else "first"
        outputs["retrieval"] = run_csv_stage_evaluation(
            input_csv=input_csv,
            stage=stage,
            top_k=retrieval_k,
            output_prefix="evaluation_retrieval",
        )

    if mode in ("recommendation", "all"):
        outputs["recommendation"] = run_recommendation_evaluation(
            input_csv=input_csv,
            top_n=recommendation_n,
            output_prefix="evaluation_recommendation",
        )

    if mode in ("generation", "all"):
        outputs["generation"] = run_generation_evaluation(
            input_csv=input_csv,
            context_k=generation_context_k,
            output_prefix="evaluation_generation",
        )

    return outputs


def build_integrated_summary(outputs: dict[str, Any], mode: str, input_csv: str, compare_rerank: bool) -> dict[str, Any]:
    """단계별 결과를 통합 요약 포맷으로 묶는다."""
    return {
        "mode": mode,
        "input_csv": input_csv,
        "compare_rerank": compare_rerank,
        "stages": outputs,
    }


def run_all(
    input_csv: str,
    mode: str,
    retrieval_k: int,
    recommendation_n: int,
    generation_context_k: int,
    compare_rerank: bool,
    output_prefix: str,
) -> dict[str, Any]:
    """통합 평가 실행 + 통합 summary 파일 저장을 수행한다."""
    outputs = run_stage_evaluations(
        input_csv=input_csv,
        mode=mode,
        retrieval_k=retrieval_k,
        recommendation_n=recommendation_n,
        generation_context_k=generation_context_k,
        compare_rerank=compare_rerank,
    )
    summary = build_integrated_summary(outputs, mode, input_csv, compare_rerank)
    wrapper_summary = build_evaluation_summary(
        stage="all",
        sample_count=len(outputs),
        executed=True,
        metrics=summary,
    )
    write_evaluation_outputs([], wrapper_summary, output_prefix, RESULT_DIR)
    return wrapper_summary


def build_parser() -> argparse.ArgumentParser:
    """통합 평가 CLI 인자를 정의한다."""
    parser = argparse.ArgumentParser(description="3단계 통합 평가 실행기")
    parser.add_argument("--input-csv", default="evaluation/evaluate_testdata.csv")
    parser.add_argument("--mode", default="all", choices=["all", "retrieval", "recommendation", "generation"])
    parser.add_argument("--retrieval-k", type=int, default=30)
    parser.add_argument("--recommendation-n", type=int, default=5)
    parser.add_argument("--generation-context-k", type=int, default=30)
    parser.add_argument("--compare-rerank", action="store_true")
    parser.add_argument("--output-prefix", default="evaluation_all")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    summary = run_all(
        input_csv=args.input_csv,
        mode=args.mode,
        retrieval_k=args.retrieval_k,
        recommendation_n=args.recommendation_n,
        generation_context_k=args.generation_context_k,
        compare_rerank=args.compare_rerank,
        output_prefix=args.output_prefix,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
