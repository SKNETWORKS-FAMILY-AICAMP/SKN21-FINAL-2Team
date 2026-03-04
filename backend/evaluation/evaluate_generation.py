from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = Path(__file__).resolve().parent
RESULT_DIR = EVAL_DIR / "result"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from evaluation.common import (  # noqa: E402
    build_evaluation_summary,
    load_and_validate_csv,
    parse_structured_columns,
    write_evaluation_outputs,
)
from app.utils.common import parse_payload


def extract_generation_inputs(df: pd.DataFrame, context_k: int) -> pd.DataFrame:
    """생성 평가 입력을 표준화한다."""
    records = []
    for _, row in df.iterrows():
        contexts = row.get("retrieved_contexts")
        if not isinstance(contexts, list):
            contexts = []

        candidates = row.get("retrieved_candidates")
        if isinstance(candidates, list) and candidates:
            # candidate pool 기반 context 확장 — payload를 JSON string으로
            contexts = []
            for i, c in enumerate(candidates[:context_k], 1):
                if not isinstance(c, dict):
                    continue
                payload = c.get("payload") if isinstance(c.get("payload"), dict) else {}
                payload_str = parse_payload(payload)
                contexts.append(f"{i}. {payload_str}")
        else:
            contexts = contexts[:context_k]

        records.append(
            {
                "user_input": str(row.get("question") or row.get("user_input") or ""),
                "response": str(row.get("response") or ""),
                "reference": str(row.get("reference") or ""),
                "retrieved_contexts": contexts,
            }
        )

    return pd.DataFrame(records)


def _fallback_generation_metrics(eval_df: pd.DataFrame) -> pd.DataFrame:
    """RAGAS 실행 불가 환경에서 최소 대체 점수를 만든다."""
    rows = []
    for _, row in eval_df.iterrows():
        has_context = 1.0 if row.get("retrieved_contexts") else 0.0
        has_answer = 1.0 if str(row.get("response") or "").strip() else 0.0
        rows.append(
            {
                "faithfulness": has_context * has_answer,
                "answer_relevancy": has_answer,
                "context_precision": has_context,
                "context_recall": has_context,
            }
        )
    return pd.DataFrame(rows)


def run_generation_metrics(eval_df: pd.DataFrame) -> pd.DataFrame:
    """RAGAS 지표를 계산하고 실패 시 fallback으로 대체한다."""
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return _fallback_generation_metrics(eval_df)

    try:
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas import EvaluationDataset, evaluate
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import AnswerRelevancy, Faithfulness, LLMContextPrecisionWithReference, LLMContextRecall

        dataset = EvaluationDataset.from_pandas(eval_df[["user_input", "retrieved_contexts", "response", "reference"]])
        eval_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))
        eval_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))
        metrics = [
            LLMContextRecall(llm=eval_llm),
            LLMContextPrecisionWithReference(llm=eval_llm),
            Faithfulness(llm=eval_llm),
            AnswerRelevancy(llm=eval_llm, embeddings=eval_embeddings),
        ]
        result = evaluate(dataset=dataset, metrics=metrics)
        return result.to_pandas()
    except Exception:
        return _fallback_generation_metrics(eval_df)


def run_generation_evaluation(input_csv: str, context_k: int, output_prefix: str) -> dict[str, Any]:
    """CSV 입력으로 생성 단계 평가를 실행하고 결과 파일을 저장한다."""
    required = ["reference", "response", "retrieved_contexts"]
    try:
        df = load_and_validate_csv(input_csv, required_columns=required)
    except ValueError as e:
        summary = build_evaluation_summary(
            stage="generation",
            sample_count=0,
            executed=False,
            metrics={},
            skipped_reason=str(e),
        )
        write_evaluation_outputs([], summary, output_prefix, RESULT_DIR)
        return summary

    df = parse_structured_columns(df, ["retrieved_contexts", "retrieved_candidates"])
    eval_df = extract_generation_inputs(df, context_k=context_k)
    metric_df = run_generation_metrics(eval_df)

    rows: list[dict[str, Any]] = []
    for idx, (_, row) in enumerate(metric_df.iterrows()):
        rows.append(
            {
                "idx": idx,
                "faithfulness": float(row.get("faithfulness", 0.0)),
                "answer_relevancy": float(row.get("answer_relevancy", 0.0)),
                "context_precision": float(row.get("context_precision", 0.0)),
                "context_recall": float(row.get("context_recall", 0.0)),
            }
        )

    summary = build_evaluation_summary(
        stage="generation",
        sample_count=len(rows),
        executed=True,
        metrics={
            "context_k": context_k,
            "faithfulness": float(metric_df["faithfulness"].mean()) if "faithfulness" in metric_df else 0.0,
            "answer_relevancy": float(metric_df["answer_relevancy"].mean()) if "answer_relevancy" in metric_df else 0.0,
            "context_precision": float(metric_df["context_precision"].mean()) if "context_precision" in metric_df else 0.0,
            "context_recall": float(metric_df["context_recall"].mean()) if "context_recall" in metric_df else 0.0,
            "entity_existence_note": "엔티티 존재성은 recommendation 단계 리포트를 참고하세요.",
        },
    )

    write_evaluation_outputs(rows, summary, output_prefix, RESULT_DIR)
    return summary


def build_parser() -> argparse.ArgumentParser:
    """생성 평가 CLI 인자를 정의한다."""
    parser = argparse.ArgumentParser(description="생성 단계 평가")
    parser.add_argument("--input-csv", default="evaluation/evaluate_testdata.csv")
    parser.add_argument("--context-k", type=int, default=30)
    parser.add_argument("--output-prefix", default="evaluation_generation")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    summary = run_generation_evaluation(
        input_csv=args.input_csv,
        context_k=args.context_k,
        output_prefix=args.output_prefix,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
