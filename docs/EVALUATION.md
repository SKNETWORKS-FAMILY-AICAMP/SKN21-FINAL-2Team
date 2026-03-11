# Evaluation 가이드

## 1) 한눈에 보는 평가 단계

여행 추천 챗봇 평가는 아래 3단계를 분리해서 봅니다.

1. Retrieval / Rerank
- 질문에 맞는 후보를 찾고, 순서를 적절히 재정렬했는지 확인합니다.

2. Recommendation
- 최종 추천된 장소 집합이 정확하고 다양한지 확인합니다.

3. Generation
- 추천 이유와 설명이 컨텍스트에 근거해 자연스럽게 생성되는지 확인합니다.

---

## 2) 평가 스크립트

- `backend/evaluation/evaluate_ragas.py`
  - 합성 데이터 생성 및 enriched CSV 준비
- `backend/evaluation/evaluate_prepare_enriched.py`
  - 평가 입력 CSV에 enriched 컬럼을 보강
- `backend/evaluation/evaluate_retrieval.py`
  - Retrieval / Rerank 평가
- `backend/evaluation/evaluate_recommendation.py`
  - Recommendation 평가
- `backend/evaluation/evaluate_generation.py`
  - Generation 평가
- `backend/evaluation/evaluate_all.py`
  - 단계별 평가 통합 실행

공통 모듈:

- `backend/evaluation/common/io.py`
- `backend/evaluation/common/metrics.py`
- `backend/evaluation/common/reporting.py`

---

## 3) 입력 데이터

기본 입력 파일:

- `backend/evaluation/evaluate_testdata.csv`
- `backend/evaluation/evaluate_testdata_enriched.csv`

필수 컬럼(통합 평가 기준):

- `question` 또는 `user_input`
- `reference`
- `response`
- `retrieved_contexts`
- `relevant_ids`
- `selected_ids`
- `retrieved_candidates`

주의:

- 컬럼이 부족한 단계는 실패 대신 `skipped`로 기록될 수 있습니다.

---

## 4) 단계별 주요 지표

### 4.1 Retrieval / Rerank

- `Recall@K`
- `Precision@K`
- `MAP@K`
- `MRR@K`
- `nDCG@K`
- `delta_ndcg@k`
- `delta_mrr@k`

### 4.2 Recommendation

- `Precision@N`
- `Recall@N`
- `nDCG@N`
- `ILD@N`
- `Category Coverage`
- `District Diversity`
- `Entity Existence Rate`

### 4.3 Generation

- `faithfulness`
- `answer_relevancy`
- `context_precision`
- `context_recall`

---

## 5) 실행 예시

### Docker 우선

합성 데이터/보강:

```bash
docker compose run --rm backend python evaluation/evaluate_ragas.py
```

Retrieval / Rerank:

```bash
docker compose run --rm backend python evaluation/evaluate_retrieval.py --input-csv evaluation/evaluate_testdata.csv --stage all --top-k 30
```

Recommendation:

```bash
docker compose run --rm backend python evaluation/evaluate_recommendation.py --input-csv evaluation/evaluate_testdata.csv --top-n 5
```

Generation:

```bash
docker compose run --rm backend python evaluation/evaluate_generation.py --input-csv evaluation/evaluate_testdata.csv --context-k 30
```

통합 실행:

```bash
docker compose run --rm backend python evaluation/evaluate_all.py --mode all --input-csv evaluation/evaluate_testdata.csv --compare-rerank
```

### 로컬(`uv`) 실행

```bash
cd backend
uv sync
uv run python evaluation/evaluate_all.py --mode all --input-csv evaluation/evaluate_testdata.csv --compare-rerank
```

---

## 6) `evaluate_all.py` 주요 옵션

- `--input-csv`: 평가 입력 파일
- `--mode`: `all | retrieval | recommendation | generation`
- `--retrieval-k`: Retrieval 평가 Top-K
- `--recommendation-n`: Recommendation Top-N
- `--generation-context-k`: Generation 컨텍스트 개수
- `--compare-rerank`: Retrieval 단계에서 재정렬 전/후 비교 수행
- `--output-prefix`: 결과 파일 접두어

---

## 7) 결과 파일

주요 결과 경로:

- `backend/evaluation/result/evaluation_retrieval_report.csv`
- `backend/evaluation/result/evaluation_retrieval_summary.json`
- `backend/evaluation/result/evaluation_recommendation_report.csv`
- `backend/evaluation/result/evaluation_recommendation_summary.json`
- `backend/evaluation/result/evaluation_generation_report.csv`
- `backend/evaluation/result/evaluation_generation_summary.json`
- `backend/evaluation/result/evaluation_all_report.csv`
- `backend/evaluation/result/evaluation_all_summary.json`
- `backend/evaluation/result/*_summary.txt`

---

## 8) 해석 기준

### Retrieval / Rerank

- Recall이 높고 Precision이 낮으면 후보는 넓게 찾지만 노이즈가 많다는 의미입니다.
- `delta_ndcg@k`, `delta_mrr@k`가 낮으면 rerank가 체감 개선을 거의 못 만들고 있을 수 있습니다.

### Recommendation

- Precision/Recall/nDCG가 높아도 `ILD@N`이 낮으면 비슷한 장소만 반복 추천할 가능성이 있습니다.
- `Entity Existence Rate`는 선택된 ID의 유효성을 확인하는 안전장치입니다.

### Generation

- `faithfulness`, `context_precision`, `context_recall`이 낮으면 설명의 근거성이 약하다는 뜻입니다.
- 추천 정확도가 괜찮아도 생성 지표가 낮으면 사용자 신뢰도는 떨어질 수 있습니다.

---

## 9) 운영 메모

- 평가 결과는 `result/` 하위에 누적되므로 리포트 비교 시 입력 파일과 옵션을 함께 기록해야 합니다.
- 생성 평가는 외부 LLM 키 유무에 따라 fallback 동작이 들어갈 수 있습니다.
- Retrieval 성능 점검 시에는 후보 수와 rerank 상한을 함께 확인하는 것이 좋습니다.
