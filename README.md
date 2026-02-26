# SKN21-FINAL-2Team
# ✈️ Triver (트리버)

### LLM 기반 초개인화 K-Culture 여행 에이전트  
> 당신이 원하는 한국 여행의 모든 것

---

## 📌 About The Project

**Triver**는 단순 정보 나열형 여행 플랫폼을 넘어,  
사용자의 취향과 대화 맥락을 이해하여 **실행 가능한 여행 일정**을 설계하는  
LLM 기반 대화형 여행 추천 서비스입니다.

📅 **프로젝트 기간**  
2026.02.02. ~ 2026.03.31.

---

## 👥 Team TRIVERS

| 이름 | 역할 |
|------|------|
| 전우영 | Service Planner |
| 김가람 | Multimodal AI Engineer |
| 박민정 | Frontend Developer |
| 손현우 | UI/UX Designer |
| 장이선 | Data Engineer |

---

## 🎯 Project Goal

기존 여행 서비스는 정보 제공 중심 구조에 머물러 있습니다.  
Triver는 다음을 해결합니다:

- 검색 결과를 **실행 가능한 여정**으로 자동 변환
- 사용자 취향 기반 **초개인화 일정 설계**
- 정보, 지도, 예약 기능의 **통합 경험 제공**

---

## 🚀 Key Features

### 1️⃣ 파편화된 여정의 통합
- RAG 기반 검증된 정보 추천
- API 연동을 통한 즉각적인 예약 가능
- 대화형 커머스 환경 제공

### 2️⃣ 여행 계획 피로도 감소
- 사전 설문 기반 사용자 맞춤 인터페이스
- AI가 핵심 정보만 큐레이션

### 3️⃣ 동선 최적화 엔진 구축
- VRP 기반 최적 경로 계산
- 이동 수단, 예상 소요 시간 포함
- 식사 및 휴식 시간까지 고려한 정교한 타임라인 생성

### 4️⃣ 멀티모달 & 다국어 지원
- 이미지 기반 검색 지원
- 텍스트 + 위치 + 이미지 통합 탐색
- 외국인 관광객 특화 접근성 확보

---

## 🧭 Background

### 1. 관광 수요의 역설
K-컬쳐 인기와 함께 방한 관광객은 증가하고 있으나  
체류 경험과 관광 수익의 질적 성장은 정체되어 있음.

여행 정보, 지도, 예약 서비스가 파편화되어  
사용자는 반복 검색과 이동을 경험함.

### 2. 기존 시장 구조의 한계
- 개인화 일정 설계 기능 부족
- 검증되지 않은 추천 알고리즘
- 실행 불가능한 일정 제안

---

## 🛠 Tech Stack

### Frontend
- Next.js (v16.1)
- React (v19.2)
- TypeScript
- Tailwind CSS (v4)
- Framer Motion
- Recharts
- Lucide React
- Jest
- React Testing Library

### Backend
- FastAPI
- Uvicorn
- Python (v3.13+)
- MySQL
- SQLAlchemy
- qdrant-client
- LangChain
- LangGraph
- OpenAI API
- Sentence-Transformers
- Pytest
- RAGAS

### Infrastructure
- Nginx
- Docker
- Docker Compose

---

## 🗂 Project Structure

```text
SKN21-FINAL-2Team/
├── backend/                  # FastAPI 기반 백엔드 애플리케이션
│   ├── app/                  # 비즈니스 로직, API 라우터, DB 모델
│   ├── data/                 # 데이터 수집 및 전처리
│   ├── tests/                # 백엔드 테스트 코드
│   └── uploads/              # 사용자 업로드 파일 저장소
├── frontend/                 # Next.js 기반 프론트엔드
│   ├── public/               # 정적 에셋
│   ├── src/                  # 리액트 컴포넌트 및 로직
│   └── tests/                # 프론트엔드 테스트 코드
├── nginx/                    # 웹 서버 및 리버스 프록시 설정
├── docker-compose-local.yml  # 로컬 실행 설정
└── README.md
```

---

## 📊 WBS

![WBS](WBS.png)

---

## 🗄 ERD

![ERD](RDB_ERD.png)

---

## ✨ Vision

> 검색에서 끝나는 여행이 아니라,  
> **실제로 떠날 수 있는 일정까지 완성하는 AI 여행 에이전트**

---
