import pandas as pd

from evaluation.evaluate_retrieval import run_csv_stage_evaluation


def test_retrieval_stage_all_runs(tmp_path):
    csv_path = tmp_path / "retrieval.csv"
    df = pd.DataFrame(
        [
            {
                "user_input": "강남 맛집",
                "reference": "정답",
                "retrieved_contexts": "['a']",
                "relevant_ids": "['p2']",
                "retrieved_candidates": "[{'id':'p1','first_stage_rank':1,'final_rank':2},{'id':'p2','first_stage_rank':2,'final_rank':1}]",
            }
        ]
    )
    df.to_csv(csv_path, index=False)

    summary = run_csv_stage_evaluation(str(csv_path), stage="all", top_k=2, output_prefix="test_retrieval")

    assert summary["executed"] is True
    assert summary["sample_count"] == 1
    assert "delta_ndcg@k" in summary
