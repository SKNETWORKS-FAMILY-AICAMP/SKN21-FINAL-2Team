import os

import pandas as pd

from evaluation.evaluate_generation import extract_generation_inputs, run_generation_metrics


def test_extract_generation_inputs_uses_candidates_as_context_topk():
    df = pd.DataFrame(
        [
            {
                "user_input": "성수 카페 추천",
                "response": "답변",
                "reference": "정답",
                "retrieved_contexts": ["기존1", "기존2"],
                "retrieved_candidates": [
                    {"id": "1", "payload": {"title": "A", "contenttypeid": "음식점", "addr": "서울"}},
                    {"id": "2", "payload": {"title": "B", "contenttypeid": "음식점", "addr": "서울"}},
                ],
            }
        ]
    )

    out = extract_generation_inputs(df, context_k=1)
    contexts = out.iloc[0]["retrieved_contexts"]

    assert len(contexts) == 1
    assert "\"title\": \"A\"" in contexts[0]


def test_run_generation_metrics_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    eval_df = pd.DataFrame(
        [
            {
                "user_input": "질문",
                "response": "응답",
                "reference": "정답",
                "retrieved_contexts": ["ctx"],
            }
        ]
    )

    result = run_generation_metrics(eval_df)
    assert "faithfulness" in result.columns
    assert float(result.iloc[0]["answer_relevancy"]) >= 0.0
