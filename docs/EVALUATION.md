# Evaluation 가이드

## 한눈에 보는 3단계 평가
여행 추천 챗봇 평가는 아래 3가지를 분리해서 봅니다.

1. Retrieval(검색): 질문에 맞는 후보를 잘 찾았는가?
- 왜 중요한가: 후보를 잘못 찾으면 뒤 단계가 좋아도 결과가 나빠집니다.
- 점수가 낮을 때 보이는 문제: 엉뚱한 장소가 많이 섞이거나, 맞는 장소가 후보에 아예 없음.
- 개선 모듈: 검색기(BM25/벡터 검색/하이브리드 검색).

2. Rerank(재정렬): 찾은 후보의 순서를 잘 세웠는가?
- 왜 중요한가: 같은 후보라도 순서가 좋아야 상위 추천 품질이 올라갑니다.
- 점수가 낮을 때 보이는 문제: 관련 장소가 뒤로 밀려 사용자 체감 품질 하락.
- 개선 모듈: Reranker, 점수 결합 로직.

3. Recommendation(최종 추천): 후보 중 최종 추천을 잘 골랐는가?
- 왜 중요한가: 사용자에게 실제로 노출되는 결과가 이 단계에서 결정됩니다.
- 점수가 낮을 때 보이는 문제: 추천이 부정확하거나 너무 비슷한 장소만 반복됨.
- 개선 모듈: 추천 선택 로직(`selected_ids` 생성 부분).

4. Generation(설명 생성): 추천 이유를 근거 있게 설명했는가?
- 왜 중요한가: 추천 이유가 어색하거나 근거가 약하면 신뢰도가 떨어집니다.
- 점수가 낮을 때 보이는 문제: 질문과 무관한 설명, 근거 부족, 환각성 문장.
- 개선 모듈: Executor 프롬프트/응답 생성 로직.

## 평가 스크립트
- `backend/evaluation/evaluate_ragas.py`: 합성 데이터 생성 + RAG 실행 → enriched CSV 직접 저장
- `backend/evaluation/evaluate_retrieval.py`: Retrieval + Rerank 평가
- `backend/evaluation/evaluate_recommendation.py`: Recommendation 평가
- `backend/evaluation/evaluate_generation.py`: Generation(RAGAS) 평가
- `backend/evaluation/evaluate_all.py`: 통합 실행

## CSV 입력 표준
입력 파일: `backend/evaluation/evaluate_testdata.csv`

`evaluate_ragas.py`를 실행하면 합성 데이터 생성 + RAG 파이프라인 실행 + enriched 컬럼 추가까지 한 번에 수행되어 이 파일에 저장됩니다.

필수 컬럼(통합 평가 기준):
- `question` 또는 `user_input`
- `reference`
- `response`
- `retrieved_contexts`
- `relevant_ids`
- `selected_ids`
- `retrieved_candidates`

## 단계별 주요 지표

### 1) Retrieval / Rerank
- 후보 생성(1단): `Recall@K`, `Precision@K`, `MAP@K`
- 재정렬(2단): `MRR@K`, `nDCG@K`, `MAP@K`
- 전후 비교: `delta_ndcg@k`, `delta_mrr@k`

### 2) Recommendation
- 정확도: `Precision@N`, `Recall@N`, `nDCG@N`
- 다양성: `ILD@N`, `Category Coverage`, `District Diversity`
- 안정성: `Entity Existence Rate`

### 3) Generation
- `faithfulness`
- `answer_relevancy`
- `context_precision`
- `context_recall`

운영 규칙:
- 생성 평가는 기본 컨텍스트 `Top30` 권장.
- 엔티티 존재성은 Recommendation 리포트와 분리해서 해석.
- 검색 지연이 증가하면 BM25 조건부 실행 여부(`vector_pool_size`, `top_vector_score`)와 `RETRIEVAL_PROFILE`/rerank 상한 설정을 먼저 점검.
- 평가 실행 시에는 `evaluation` 프로파일(후보/재정렬 확대)을 기본 사용하고, 필요하면 CLI로 오버라이드합니다.

## 실행 예시 (Docker 우선)

### 평가 데이터 생성 (합성 데이터 + RAG 실행 + enriched 컬럼)
```bash
docker compose run --rm backend python evaluation/evaluate_ragas.py
```

### Retrieval + Rerank
```bash
docker compose run --rm backend python evaluation/evaluate_retrieval.py --input-csv evaluation/evaluate_testdata.csv --stage all --top-k 30
```

평가용 검색 파라미터를 별도로 지정하려면:
```bash
docker compose run --rm backend python evaluation/evaluate_retrieval.py \
  --data-file evaluation/rag_eval_data.json \
  --mode all --top-k 10 \
  --retriever-candidate-k 60 \
  --retriever-rerank-max-k 30
```

### Recommendation
```bash
docker compose run --rm backend python evaluation/evaluate_recommendation.py --input-csv evaluation/evaluate_testdata.csv --top-n 5
```

### Generation
```bash
docker compose run --rm backend python evaluation/evaluate_generation.py --input-csv evaluation/evaluate_testdata.csv --context-k 30
```

### 통합 실행
```bash
docker compose run --rm backend python evaluation/evaluate_all.py --mode all --input-csv evaluation/evaluate_testdata.csv --compare-rerank
```

## 결과 파일
- `backend/evaluation/result/evaluation_retrieval_report.csv`
- `backend/evaluation/result/evaluation_recommendation_report.csv`
- `backend/evaluation/result/evaluation_generation_report.csv`
- `backend/evaluation/result/evaluation_all_summary.json`
- 각 스크립트별 `*_summary.json`, `*_summary.txt`

## 주의사항
- 입력 CSV에 필수 컬럼이 없으면 해당 단계는 실패 대신 `skipped`로 기록됩니다.
- `--compare-rerank`는 Retrieval 단계에서 재정렬 전/후 비교 요약을 함께 출력합니다.
- 외부 LLM 키가 없으면 Generation은 fallback 점수로 동작합니다.

## 최근 실행 결과 해석
기준 실행:
- `mode=all`
- `input_csv=evaluation/evaluate_testdata.csv`
- `compare_rerank=true`
- 샘플 수: 단계별 21건

### 1) Retrieval / Rerank
- `first_precision@k=0.2381`: Top30 후보 중 관련 항목 비율이 평균 약 23.8%
    - Precision@K: TopK 후보 중 관련 항목 비율
- `first_recall@k=0.8095`: 관련 항목의 약 80.9%를 Top30 안에서 회수
    - Recall@K: 관련 항목의 TopK 안에 포함된 비율
- `first_map@k=0.6782`: 관련 항목이 전반적으로 상위권에 배치됨
    - MAP@K: 관련 항목이 전반적으로 상위권에 배치됨
- `rerank_mrr@k=0.6786`, `rerank_ndcg@k=0.7156`, `rerank_map@k=0.6782`: 재정렬 후 순위 품질은 중상
    - MRR@K: 첫 타겟 속도
    - nDCG@K: 상위 순서 전체 품질
    - MAP@K: 여러 정답에 대한 평균 정밀도 품질
- `delta_ndcg@k=0.0`, `delta_mrr@k=0.0`: 현재 데이터에서는 재정렬 전/후 개선 효과가 없음

해석:
- 후보를 찾는 능력(Recall)은 충분히 높음
- 다만 Top30 내 노이즈가 많아 Precision은 낮은 편
- rerank delta가 0인 것은 `final_rank`가 사실상 first rank와 유사하게 구성되었기 때문일 가능성이 큼

### 2) Recommendation
- `precision@n=0.7778`, `recall@n=0.7857`, `ndcg@n=0.7911`: 최종 추천 정확도/순위 품질은 양호
    - Precision@N: TopN 후보 중 관련 항목 비율
    - Recall@N: 관련 항목의 TopN 안에 포함된 비율
    - nDCG@N: 상위 순서 전체 품질
- `ild@n=0.0794`: 추천 리스트 내 다양성은 낮음(유사 항목 반복 가능성)
    - ILD@N: 추천 리스트 내 다양성
- `category_coverage=0.6825`, `district_diversity=0.7937`: 카테고리/지역 분산은 중간 이상
    - Category Coverage: 카테고리 다양성
    - District Diversity: 지역 다양성
- `entity_existence_rate=1.0`: 추천 엔티티 존재성은 안정적
    - Entity Existence Rate: 추천 엔티티 존재성

해석:
- 추천 품질 자체는 괜찮지만, 체감 다양성(특히 ILD)은 개선 여지가 큼
    - 추천 리스트 내 다양성은 낮음(유사 항목 반복 가능성)
    - 카테고리/지역 분산은 중간 이상
    - 추천 엔티티 존재성은 안정적
    
### 3) Generation
- `faithfulness=0.1573`: 컨텍스트 근거 충실도 낮음
    - Faithfulness: 컨텍스트 근거 충실도
- `answer_relevancy=0.5385`: 질문 적합성은 중간 수준
    - Answer Relevancy: 질문 적합성
- `context_precision=0.0`, `context_recall=0.1417`: 컨텍스트 근거 품질이 낮음
    - Context Precision: 컨텍스트 근거 정밀도
    - Context Recall: 컨텍스트 근거 재현율
- `entity_existence_note`: 추천 엔티티 존재성은 recommendation 단계 리포트를 참고하세요.

해석:
- 현재 가장 큰 병목은 생성 단계의 근거성/정합성
- 추천 결과가 괜찮아도 설명 품질이 낮아 사용자 신뢰가 떨어질 수 있음
