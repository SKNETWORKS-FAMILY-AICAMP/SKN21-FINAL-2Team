import pandas as pd

from evaluation.evaluate_prepare_enriched import run_prepare_enriched


def test_prepare_enriched_adds_required_columns(tmp_path):
    input_csv = tmp_path / "raw.csv"
    output_csv = tmp_path / "enriched.csv"

    df = pd.DataFrame(
        [
            {
                "user_input": "강남 맛집 추천",
                "reference": "서울특별시 강남구에 있는 가나돈까스를 추천합니다.",
                "response": "[가나돈까스](https://example.com) 추천드립니다.",
                "reference_contexts": "['이름:가나돈까스 | 분류:음식점 | 주소:서울특별시 강남구']",
                "retrieved_contexts": "['이름:가나돈까스 | 분류:음식점 | 주소:서울특별시 강남구', '이름:다른가게 | 분류:음식점 | 주소:서울특별시 서초구']",
            }
        ]
    )
    df.to_csv(input_csv, index=False)

    summary = run_prepare_enriched(str(input_csv), str(output_csv), top_k=5, top_n=3)

    enriched = pd.read_csv(output_csv)
    assert summary["sample_count"] == 1
    assert "retrieved_candidates" in enriched.columns
    assert "selected_ids" in enriched.columns
    assert "relevant_ids" in enriched.columns
