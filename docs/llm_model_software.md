# LLM 모델 및 소프트웨어 구성 요약

이 문서는 현재 프로젝트에서 사용하는 LLM, 임베딩, 검색 소프트웨어 조합만 요약한다.  
시스템 구조는 [BACKEND_STRUCTURE.md](/Users/kim/SKN21-FINAL-2Team/docs/BACKEND_STRUCTURE.md),  
에이전트 흐름은 [agent_sequence_diagrams.md](/Users/kim/SKN21-FINAL-2Team/docs/agent_sequence_diagrams.md),  
실행 상태는 [PROJECT_ANALYSIS.md](/Users/kim/SKN21-FINAL-2Team/docs/PROJECT_ANALYSIS.md)에서 관리한다.

---

## 1. 핵심 모델 구성

| 구분 | 현재 사용 모델/소프트웨어 | 역할 |
|------|---------------------------|------|
| 생성 LLM | `gpt-4o-mini` | 의도 분석, 일정 생성, 최종 응답 생성 |
| 텍스트 임베딩 | `BAAI/bge-m3` | 장소 텍스트 임베딩 |
| 이미지 임베딩 | `CLIP-ViT-L-14` | 이미지 유사도 검색 |
| 리랭커 | `BAAI/bge-reranker-base` | 후보 재정렬 |
| 벡터 DB | `Qdrant` | 장소/사진 벡터 저장 및 검색 |
| 웹 보조 검색 | `Tavily` | 실시간 웹 검색 폴백 |

---

## 2. 검색 조합

현재 검색은 아래 조합을 중심으로 구성된다.

- Dense text retrieval
- 이미지 기반 retrieval
- BM25 계열 보조 검색
- reranker 기반 순위 재정렬
- 필요 시 Tavily 웹 검색 폴백

---

## 3. 소프트웨어 스택 요약

| 계층 | 소프트웨어 |
|------|------------|
| 프론트엔드 | Next.js, React |
| 백엔드 | FastAPI, Uvicorn |
| 에이전트 오케스트레이션 | LangGraph |
| LLM 연동 | LangChain, langchain-openai |
| 관계형 DB | MySQL |
| 벡터 검색 | Qdrant |
| 배포 | Docker, Docker Compose, Nginx |

---

## 4. 문서 관리 메모

- 모델 교체나 검색 전략 변경 시 이 문서를 갱신
- 구조 설명이나 시퀀스 설명은 이 문서에 중복 작성하지 않음
