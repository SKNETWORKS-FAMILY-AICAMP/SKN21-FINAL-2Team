import pandas as pd

from evaluation.evaluate_recommendation import run_recommendation_evaluation


def test_recommendation_eval_runs_with_minimum_columns(tmp_path):
    csv_path = tmp_path / "recommend.csv"
    df = pd.DataFrame(
        [
            {
                "user_input": "강남 맛집 추천",
                "response": "추천 드립니다",
                "relevant_ids": "['1','2']",
                "selected_ids": "['1','3']",
                "retrieved_candidates": "[{'id':'1','payload':{'contenttypeid':'음식점','addr':'서울특별시 강남구'}},{'id':'3','payload':{'contenttypeid':'음식점','addr':'서울특별시 서초구'}}]",
            }
        ]
    )
    df.to_csv(csv_path, index=False)

    summary = run_recommendation_evaluation(str(csv_path), top_n=2, output_prefix="test_recommendation")

    assert summary["executed"] is True
    assert summary["sample_count"] == 1
    assert "precision@n" in summary
