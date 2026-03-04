import numpy as np
import pytest

from evaluation import evaluate_retrieval as er


class DummyScorer:
    def batch_similarity(self, query, docs):
        if not docs:
            return []
        return [0.8 for _ in docs]


def test_candidate_to_text_handles_missing_fields():
    candidate = {"payload": {"title": "가나돈까스"}}
    text = er._candidate_to_text(candidate)
    assert "가나돈까스" in text
    assert "|" not in text[-1:]


def test_normalized_cosine_range_0_to_1():
    v1 = np.array([1.0, 0.0], dtype=np.float32)
    v2 = np.array([0.0, 1.0], dtype=np.float32)
    value = er._normalized_cosine(v1, v2)
    assert 0.0 <= value <= 1.0


def test_ranking_metrics_hit_mrr_ndcg():
    rank = er._find_gold_rank("가나돈까스", ["가담", "가나돈까스", "성하"], top_k=5)
    assert rank == 2
    assert pytest.approx(0.5, rel=1e-6) == (1.0 / rank)
    assert er._ndcg_at_k(rank, 5) > 0


@pytest.mark.asyncio
async def test_unsupervised_works_without_reference():
    async def fake_retrieve(question, top_k, category):
        return [
            {
                "payload": {
                    "title": "가나돈까스",
                    "contenttypeid": "음식점",
                    "addr": "서울특별시 강남구 언주로 608",
                    "llm_text": "바삭한 돈까스",
                }
            }
        ]

    rows = await er.evaluate_records(
        records=[{"question": "서울 강남구 맛집 추천해줘"}],
        mode="unsupervised",
        top_k=5,
        scorer=DummyScorer(),
        retrieve_fn=fake_retrieve,
    )

    assert len(rows) == 1
    assert rows[0]["unsup_evaluable"] is True
    assert rows[0]["labeled_evaluable"] is False
    assert rows[0]["sim@1"] == 0.8


@pytest.mark.asyncio
async def test_empty_candidates_do_not_crash():
    async def fake_retrieve(question, top_k, category):
        return []

    rows = await er.evaluate_records(
        records=[{"question": "서울 종로구 전시 추천"}],
        mode="all",
        top_k=5,
        scorer=DummyScorer(),
        retrieve_fn=fake_retrieve,
    )

    assert len(rows) == 1
    assert rows[0]["retrieved_count"] == 0
    assert rows[0]["sim@1"] == 0.0
    assert rows[0]["mrr@k"] == 0.0


def test_summary_uses_evaluable_denominator():
    rows = [
        {
            "retrieval_failed": False,
            "unsup_evaluable": True,
            "labeled_evaluable": True,
            "sim@1": 0.7,
            "sim@k_mean": 0.6,
            "sim@k_min": 0.5,
            "query_coverage": 0.4,
            "category_consistency@k": 0.8,
            "district_consistency@k": 0.9,
            "hit@1": 1.0,
            "hit@3": 1.0,
            "hit@5": 1.0,
            "mrr@k": 1.0,
            "ndcg@k": 1.0,
        },
        {
            "retrieval_failed": True,
            "unsup_evaluable": False,
            "labeled_evaluable": False,
            "sim@1": 0.0,
            "sim@k_mean": 0.0,
            "sim@k_min": 0.0,
            "query_coverage": 0.0,
            "category_consistency@k": None,
            "district_consistency@k": None,
            "hit@1": 0.0,
            "hit@3": 0.0,
            "hit@5": 0.0,
            "mrr@k": 0.0,
            "ndcg@k": 0.0,
        },
    ]
    summary = er._build_summary(mode="all", rows=rows, top_k=5, data_file="rag_eval_data.json", enriched_count=0)

    assert summary["sample_count"] == 2
    assert summary["unsupervised_evaluable_count"] == 1
    assert summary["labeled_evaluable_count"] == 1
    assert summary["sim@1"] == 0.7
    assert summary["hit@1"] == 1.0
