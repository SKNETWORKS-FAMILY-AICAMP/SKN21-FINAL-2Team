# 1. 시스템 개요
본 소프트웨어는 벡터 데이터베이스(Vector DB) 및 LLM(Language Model) 을 연동하여 사용자 질문에 문서 기반 답변을 제공하는 RAG (Retrieval-Augmented Generation) 구조를 사용합니다.
 LLM API Key 등 민감 정보는 환경 변수로 관리되며, 프롬프트 최적화를 통해 빠른 응답 속도와 품질을 보장합니다.

# 2. 시스템 구성 요소
User
 │
 ▼
[Frontend or CLI]
 │
 ▼
[Backend - RAG Pipeline]
     ├── 1. Embed Question        ← (Embedding LLM)
     ├── 2. Vector Search         ← (Vector DB: FAISS / Pinecone)
     ├── 3. Prompt Construction   ← (with retrieved docs)
     ├── 4. LLM Call              ← (Instruction-following LLM)
     └── 5. Return Response

# 3. 코드 구조 (모듈화, 주석 포함)

rag_project/
├── main.py                     # Entry point
├── rag_pipeline/
│   ├── __init__.py
│   ├── embedder.py             # Embedding 관련 함수
│   ├── vector_store.py         # 벡터DB 검색
│   ├── prompt_builder.py       # 프롬프트 최적화 로직
│   ├── llm_client.py           # LLM 호출 및 예외 처리
│   └── utils.py                # 공통 유틸
├── .env                        # 환경 변수 저장
├── requirements.txt
└── README.md

# 4. 주요 코드 (요약 + 평가요소 적용)

## 4.1 예외 처리 포함

## 4.2 .env & 환경변수 설정

# 5. 프롬프트 최적화 

# 6. 보안 고려 사항

API Key는 절대 코드에 하드코딩하지 않고, .env 파일 또는 시스템 환경 변수에서 로드합니다.
.env는 반드시 .gitignore에 추가합니다.

# 7. 테스트 시나리오
질문: 
응답 예시: 

# 8. 평가요소표
|평가 항목|대응 내용|
|벡터 DB와 LLM이 목적에 맞는 프롬프트로 효율적 연동|프롬프트 생성 함수 + 검색된 문서 기반|
|예상치 못한 상황 예외 처리 포함|try/except로 LLM 호출 오류 처리|
|코드 모듈화 및 주석 작성|각 기능별 파일 분리 + 설명 포함|
|보안 정보 노출 방지|.env 파일 + 환경변수 활용|
|빠른 응답을 위한 프롬프트 최적화|중복 제거 및 길이 제한 전략|