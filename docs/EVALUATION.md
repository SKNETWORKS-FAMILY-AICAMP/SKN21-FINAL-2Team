# Evaluation 가이드

## 목적
이 문서는 현재 프로젝트의 평가 방식을 하나로 통합한 기준 문서입니다.

- 리트리버 품질 평가 (RAGAS 비의존)
- End-to-End RAG 평가 (RAGAS 기반)
- 평가 데이터(`rag_eval_data.json`) 보강/운영

## 평가 스크립트
- `backend/evaluation/evaluate_retrieval.py`
- `backend/evaluation/evaluate_rag.py`
- `backend/evaluation/evaluate_testdata.py`
- `backend/evaluation/create_dataset.py` — Ragas TestsetGenerator 기반 합성 데이터셋 생성

## 평가 데이터셋
기본 파일: `backend/evaluation/rag_eval_data.json`

기본 호환 포맷:

```json
[
  {
    "question": "서울 강남구 맛집 추천해줘",
    "ground_truth": "서울특별시 강남구 음식점 추천 답변 ...",
    "reference": {
      "title": "가담",
      "category": "음식점",
      "district": "서울특별시 강남구"
    }
  }
]
```

- `question`: 필수
- `ground_truth`: RAGAS/e2e 평가 시 사용
- `reference`: 선택 (`evaluate_retrieval.py --enrich-reference`로 자동 보강 가능)

## 1) 리트리버 평가 (RAGAS 비의존)
### 개요
`question` + 리트리버 반환 문서만으로 검색 품질을 측정합니다.

### 모드
1. `unsupervised`
- `sim@1`, `sim@k_mean`, `sim@k_min`
- `query_coverage`
- `vector_score@1`, `keyword_score@k`, `bm25_score@k`
- `category_consistency@k`, `district_consistency@k`

2. `labeled`
- `hit@1`, `hit@3`, `hit@5`
- `mrr@k`
- `ndcg@k`
- `gold_rank`

3. `all`
- `unsupervised` + `labeled` 동시 수행

### 실행
#### Docker 우선
```bash
docker compose run --rm backend python evaluation/evaluate_retrieval.py --mode all --top-k 5
```

### Reference 자동 보강
```bash
docker compose run --rm backend python evaluation/evaluate_retrieval.py --mode labeled --top-k 5 --enrich-reference
```

또는 보강 유틸만 별도 실행:

```bash
docker compose run --rm backend python evaluation/evaluate_testdata.py --data-file rag_eval_data.json
```

### 결과 파일
- `backend/evaluation/result/evaluation_retrieval_report.csv`
- `backend/evaluation/result/evaluation_retrieval_summary.json`
- `backend/evaluation/result/evaluation_retrieval_summary.txt`

## 2) End-to-End RAG 평가 (RAGAS 기반)
### 개요
LangGraph 실행 결과(`answer`, `contexts`)를 기반으로 RAGAS 메트릭을 계산합니다.

### 주요 메트릭
- `faithfulness`
- `answer_relevancy`
- `context_precision`
- `context_recall`

### 실행
#### Docker 우선
```bash
docker compose run --rm backend python evaluation/evaluate_rag.py --mode e2e --limit 20
```

#### 모드별 실행 예시
```bash
docker compose run --rm backend python evaluation/evaluate_rag.py --mode intent --limit 20
docker compose run --rm backend python evaluation/evaluate_rag.py --mode retriever --limit 20
docker compose run --rm backend python evaluation/evaluate_rag.py --mode executor --limit 20
docker compose run --rm backend python evaluation/evaluate_rag.py --mode all --limit 20
```

### 결과 파일
- `backend/evaluation/result/evaluation_report.csv`
- `backend/evaluation/result/evaluation_summary.txt`
- `backend/evaluation/result/evaluation_*_summary.(txt|json)`
- `backend/evaluation/result/evaluation_*_report.csv`

## 3) 운영 권장 순서
1. `evaluate_retrieval.py --mode unsupervised`
- 인프라/리트리버 기본 상태 점검

2. `evaluate_retrieval.py --mode labeled --enrich-reference`
- 랭킹 품질(Hit/MRR/nDCG) 확인

3. `evaluate_rag.py --mode e2e`
- 최종 답변 품질까지 종합 점검

## 4) 해석 가이드
- `sim@k`가 높아도 `hit@k`가 낮을 수 있습니다. 유사도와 정답 순위를 같이 보세요.
- `category_consistency@k`가 낮으면 intent/category 필터 로직부터 점검하세요.
- `district_consistency@k`가 낮으면 지역 파싱/주소 정규화 로직을 우선 점검하세요.
- `retrieval_failed_count > 0`이면 Qdrant 연결/모델 로딩/환경변수를 먼저 확인하세요.

## 5) 주의사항
- `--enrich-reference`는 `rag_eval_data.json` 파일을 직접 갱신합니다.
- 대규모 실행 시 임베딩 모델 로딩 시간이 길 수 있습니다.
- Docker 실행 시 `qdrant` 컨테이너 상태를 먼저 확인하세요.

## 6) 합성 데이터셋 생성 (TestsetGenerator)

### 개요
Ragas `TestsetGenerator`를 사용해 Qdrant `places` 컬렉션 문서로부터
다양한 유형의 질문-답변 쌍을 자동 생성합니다.

### 실행
#### Docker 우선
```bash
docker compose run --rm backend python evaluation/create_dataset.py --num-samples 20 --limit 200
```

#### 주요 옵션
| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--num-samples` | 20 | 생성할 테스트 샘플 수 |
| `--limit` | 200 | Qdrant에서 가져올 소스 문서 수 |
| `--output` | `rag_eval_data_synthetic.json` | 출력 파일 경로 |
| `--seed` | 42 | 재현성을 위한 시드 값 |

### 출력
- `backend/evaluation/rag_eval_data_synthetic.json` (기존 `rag_eval_data.json`과 동일 포맷)

### 생성된 데이터로 평가 실행
```bash
docker compose run --rm backend python evaluation/evaluate_retrieval.py --data-file evaluation/rag_eval_data_synthetic.json --mode all --top-k 5
```

