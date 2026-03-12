# 여행 챗봇 에이전트 시퀀스 다이어그램

> LangGraph 기반 멀티 에이전트 파이프라인의 동작 흐름을 시퀀스 다이어그램으로 정리한 문서입니다.

---

## 목차

0. [시스템 인프라 컴포넌트 다이어그램](#0-시스템-인프라-컴포넌트-다이어그램)
1. [아키텍처 개요](#1-아키텍처-개요)
2. [전체 흐름 (Graph Workflow)](#2-전체-흐름-graph-workflow)
3. [Intent Agent](#3-intent-agent)
4. [Planner Agent](#4-planner-agent)
5. [Retriever Agent](#5-retriever-agent)
6. [Executor Agent](#6-executor-agent)
7. [Executor Missing Agent](#7-executor-missing-agent)
8. [Executor General Agent](#8-executor-general-agent)
9. [구성요소 설명](#9-구성요소-설명)
10. [액티비티 다이어그램](#10-액티비티-다이어그램)

---

## 0. 시스템 인프라 컴포넌트 다이어그램

전체 시스템의 배포 아키텍처와 각 컴포넌트 간 통신 흐름입니다.

```mermaid
graph LR
    Users["👥 Users"]

    subgraph VPC
        subgraph EC2["EC2 Instance (Docker)"]
            Nginx["🌐 Nginx Gateway"]
            subgraph Frontend["Frontend Container"]
                NextJS["Next.js"]
                React["React"]
            end
            subgraph Backend["Backend Container"]
                FastAPI["⚡ FastAPI (Uvicorn)"]
            end
            Qdrant["🗄️ Qdrant VectorDB"]
        end
        RDS["🛢️ MySQL (RDS)"]
    end

    Users -->|HTTP/HTTPS| Nginx
    Nginx -->|프록시 패스| NextJS
    NextJS -.->|SSR/CSR| React
    NextJS -->|API 요청| FastAPI
    Nginx -->|/api 프록시| FastAPI
    FastAPI -->|SQL| RDS
    FastAPI -->|벡터 검색| Qdrant
```

### 컴포넌트 설명

| 컴포넌트 | 기술 스택 | 역할 | 비고 |
|----------|----------|------|------|
| **Users** | 웹 브라우저 | 서비스 사용자 | 채팅, 장소 검색, 여행 계획 |
| **Nginx Gateway** | Nginx (Docker) | 리버스 프록시 / 정적 파일 서빙 | `/api/*` → FastAPI, 나머지 → Next.js |
| **Next.js + React** | Next.js 14, React 18 (Docker) | 프론트엔드 SPA | SSR/CSR 하이브리드, SSE 스트리밍 수신 |
| **FastAPI** | Python, FastAPI, Uvicorn (Docker) | 백엔드 API 서버 | LangGraph 에이전트 실행, REST API, SSE 스트리밍 |
| **Qdrant VectorDB** | Qdrant (Docker) | 벡터 데이터베이스 | 장소/사진 임베딩 저장, 하이브리드 검색 (Dense + BM25 + Rerank) |
| **MySQL (RDS)** | AWS RDS MySQL | 관계형 데이터베이스 | 사용자, 채팅방, 메시지, 장소 북마크, 체크포인터 데이터 |

### 네트워크 흐름

| 경로 | 프로토콜 | 설명 |
|------|---------|------|
| Users → Nginx | HTTP/HTTPS | 외부 트래픽 진입점 |
| Nginx → Next.js | HTTP (내부) | 프론트엔드 페이지 렌더링 |
| Nginx → FastAPI | HTTP (내부) | `/api/*` 경로 프록시 (Uvicorn) |
| Next.js → FastAPI | HTTP (내부) | 클라이언트 사이드 API 호출 |
| FastAPI → RDS | TCP (3306) | SQL 쿼리 (SQLAlchemy) |
| FastAPI → Qdrant | HTTP (6333) | 벡터 검색 API |

---

## 1. 아키텍처 개요

이 프로젝트는 **LangGraph StateGraph**를 사용하여 여행 추천 챗봇의 에이전트 파이프라인을 구성합니다.  
사용자 메시지가 들어오면 의도 분석 → 조건부 라우팅 → 검색/계획 → 최종 답변 생성 순서로 처리됩니다.

### 핵심 노드 구성

| 노드 | 파일 | 역할 |
|------|------|------|
| `intent` | `agents/intent.py` | 사용자 의도 분석 (GENERAL / PLACE_INQUIRY / TRIP_PLANNING 등) |
| `planner` | `agents/planner.py` | 여행 일정 초안 생성 및 필수 정보 누락 감지 |
| `retriever` | `agents/retriever.py` | Qdrant 벡터DB 하이브리드 검색 + 리랭킹 |
| `executor` | `agents/executor.py` | 검색 결과 기반 최종 답변 생성 (스트리밍) |
| `executor_missing` | `agents/executor.py` | 누락 정보 재질문 답변 생성 |
| `executor_general` | `agents/executor.py` | 일상 대화 답변 생성 |

### 라우팅 함수

| 함수 | 파일 | 역할 |
|------|------|------|
| `route_by_intent` | `agents/grapy_route.py` | Intent 결과에 따라 다음 노드 결정 |
| `route_by_missing` | `agents/grapy_route.py` | Planner 결과에서 누락 슬롯 여부로 분기 |

---

## 2. 전체 흐름 (Graph Workflow)

사용자 메시지 입력부터 최종 응답까지의 전체 에이전트 파이프라인 흐름입니다.

```mermaid
sequenceDiagram
    actor User as 사용자
    participant FE as Frontend (Next.js)
    participant API as ChatAPI (FastAPI)
    participant Graph as LangGraph StateGraph
    participant Intent as Intent Agent
    participant Router as Route Functions
    participant Planner as Planner Agent
    participant Retriever as Retriever Agent
    participant Executor as Executor Agent
    participant ExecMissing as Executor Missing
    participant ExecGeneral as Executor General
    participant DB as MySQL / Checkpointer

    User->>FE: 메시지 입력
    FE->>API: POST /api/chat/rooms/{id}/ask/stream
    API->>DB: 사용자 메시지 저장 (ChatMessage)
    API->>API: _build_graph_inputs() - TravelState 구성
    API->>Graph: astream_events(inputs, config)

    Graph->>Intent: intent_node(state)

    Note over Intent: 의도 분석 결과에 따라 분기

    alt primary_intent == TRIP_PLANNING
        Intent->>Router: route_by_intent → "planner"
        Router->>Planner: planner_node(state)
        alt missing_slots 존재
            Planner->>Router: route_by_missing → "executor_missing"
            Router->>ExecMissing: executor_missing_node(state)
            ExecMissing-->>Graph: 재질문 답변 반환
        else missing_slots 없음
            Planner->>Router: route_by_missing → "retriever"
            Router->>Retriever: retriever_node(state)
            Retriever->>Executor: executor_node(state)
            Executor-->>Graph: 최종 답변 반환
        end
    else primary_intent == GENERAL
        Intent->>Router: route_by_intent → "executor_general"
        Router->>ExecGeneral: executor_general_node(state)
        ExecGeneral-->>Graph: 일반 대화 답변 반환
    else 그 외 (PLACE_INQUIRY, IMAGE_SIMILAR 등)
        Intent->>Router: route_by_intent → "retriever"
        Router->>Retriever: retriever_node(state)
        Retriever->>Executor: executor_node(state)
        Executor-->>Graph: 최종 답변 반환
    end

    Graph-->>API: SSE 토큰 스트리밍
    API->>DB: AI 메시지 + ChatPlace 저장
    API-->>FE: SSE 응답 (토큰 + places + done)
    FE-->>User: 실시간 답변 표시
```

---

## 3. Intent Agent

사용자 입력의 의도를 분석하고 슬롯(장소, 카테고리, 날짜 등)을 추출합니다.

```mermaid
sequenceDiagram
    participant Graph as LangGraph
    participant Intent as Intent Agent
    participant LLM as LLM (OpenAI)
    participant State as TravelState

    Graph->>Intent: intent_node(state)
    Intent->>State: user_input, prefs_info, messages 읽기

    alt user_input 없음 + image_path 존재
        Intent-->>Graph: IntentType.IMAGE_SIMILAR 즉시 반환
    else user_input 존재
        Intent->>LLM: INTENT_PROMPT + messages + user_input
        Note over LLM: Structured Output → IntentOutput
        LLM-->>Intent: IntentOutput (intents, slots, summary)
        Intent-->>Graph: State 업데이트<br/>(primary_intent, slots, summary_title, summary_message)
    end
```

**IntentOutput 구조:**
- `intents`: 감지된 의도 목록 (List[IntentType])
- `primary_intent`: 주 의도 (GENERAL / PLACE_INQUIRY / TRIP_PLANNING / IMAGE_SIMILAR 등)
- `slots`: 추출된 정보 (location, category, dates, duration, party_size, budget_level 등)
- `summary_title`: 채팅방 제목용 요약 (10자 이내)
- `summary_message`: 대화 요약

---

## 4. Planner Agent

여행 계획형 요청에 대해 일정 초안을 생성하고 필수 정보 누락 여부를 판단합니다.

```mermaid
sequenceDiagram
    participant Router as route_by_intent
    participant Planner as Planner Agent
    participant LLM as LLM (OpenAI)
    participant State as TravelState

    Router->>Planner: planner_node(state)
    Planner->>State: user_input, slots, prefs_info 읽기
    Planner->>Planner: slots → 텍스트 변환 (slots_info)
    Planner->>LLM: PLANNER_PROMPT + messages + user_input
    Note over LLM: Structured Output → PlannerOutput
    LLM-->>Planner: PlannerOutput

    alt missing_slots 존재 (여행 날짜/인원 누락)
        Planner-->>State: itinerary + missing_slots + followup_question
        Note over State: route_by_missing → executor_missing
    else 필수 정보 충분
        Planner-->>State: itinerary (일정 목록)
        Note over State: route_by_missing → retriever
    end
```

**PlannerOutput 구조:**
- `itinerary`: 일차/시간대별 여행 일정 항목 리스트
  - `day`, `time_slot` (morning/afternoon/evening), `activity`, `search_query`, `category`
- `missing_slots`: 누락된 필수 정보 (여행 날짜, 여행 인원)
- `followup_question`: 후속 질문 문장

---

## 5. Retriever Agent

Qdrant 벡터DB에서 하이브리드 검색(텍스트 + 이미지 + BM25 + Rerank)을 수행합니다.

```mermaid
sequenceDiagram
    participant Prev as 이전 노드 (Intent/Planner)
    participant Retriever as Retriever Agent
    participant Vision as Vision (이미지 분석)
    participant PlaceDB as PlaceRetriever (Qdrant)
    participant GeoCoder as GeoCoder (역지오코딩)
    participant State as TravelState

    Prev->>Retriever: retriever_node(state)
    Retriever->>State: user_input, image_path, slots, itinerary 읽기

    opt image_path 존재
        Retriever->>Vision: describe_image(image_path)
        Vision-->>Retriever: emotional_text (이미지 설명)
    end

    Retriever->>Retriever: _resolve_search_scope() → place_only / photo_only

    alt primary_intent == TRIP_PLANNING
        Retriever->>PlaceDB: _search_for_general() (일반 검색)
        PlaceDB-->>Retriever: general_pool
        loop itinerary 항목별 (Semaphore=3 병렬)
            Retriever->>PlaceDB: search_hybrid(search_query, category)
            PlaceDB-->>Retriever: trip_candidates
        end
        Retriever->>Retriever: general_pool + trip_candidates 병합
    else 일반 검색
        opt 위도/경도 존재
            Retriever->>GeoCoder: reverse_geocoder(lat, lng)
            GeoCoder-->>Retriever: 도로명 주소
        end
        Retriever->>PlaceDB: search_hybrid(query, image, category, location)
        PlaceDB-->>Retriever: candidate_pool
    end

    Retriever->>Retriever: 중복 제거 + 점수 정렬
    Retriever->>Retriever: _pick_candidates() (카테고리 다양화)
    Retriever-->>State: candidate_pool, candidates, retrieval_diagnostics
```

**검색 파라미터:**
- `candidate_k`: 초기 후보 풀 크기
- `final_k`: 최종 노출 후보 수
- `rerank_max_k`: 리랭킹 대상 최대 수
- `selection_mode`: `deterministic` (점수 우선) / `explore` (랜덤 다양화)

---

## 6. Executor Agent

검색된 장소 후보를 기반으로 최종 추천 답변을 스트리밍 생성합니다.

```mermaid
sequenceDiagram
    participant Retriever as Retriever Agent
    participant Executor as Executor Agent
    participant LLM as LLM (OpenAI)
    participant Tavily as Tavily (웹 검색)
    participant State as TravelState

    Retriever->>Executor: executor_node(state)
    Executor->>State: candidates, user_input, image_path, prefs_info 읽기

    alt candidates 없음
        Executor->>Tavily: 웹 검색 Fallback (타임아웃 3초)
        Tavily-->>Executor: web_context
    else candidates 존재
        Executor->>Executor: _build_place_context() → 장소 정보 + 네이버 지도 링크
        opt TRIP_PLANNING
            Executor->>Executor: _build_itinerary_context() → 일정별 정리
        end
    end

    opt image_path 존재
        Executor->>Executor: _get_image_data_url() → base64 변환
        Executor->>LLM: 멀티모달 메시지 (텍스트 + 이미지)
    end

    Executor->>LLM: EXECUTOR_PROMPT + context + messages
    Note over LLM: 스트리밍 응답 (토큰 단위)
    LLM-->>Executor: 토큰 스트리밍 → full_content

    Executor->>Executor: [IDs: ...] 태그에서 selected_ids 추출
    opt 태그 매칭 실패
        Executor->>Executor: _infer_selected_ids_from_answer() (텍스트 기반 추론)
    end

    Executor-->>State: answer, selected_ids, AIMessage
```

**주요 기능:**
- **Tavily Fallback**: 검색 결과가 없을 때 웹 검색으로 보완 (3초 타임아웃)
- **멀티모달**: 이미지가 있으면 base64 인코딩하여 LLM에 전달
- **ID 추출**: 답변에서 `[IDs: id1, id2]` 태그 → 없으면 텍스트 매칭으로 장소 ID 추론

---

## 7. Executor Missing Agent

Planner에서 필수 정보(여행 날짜, 인원)가 누락되었을 때 자연스러운 재질문을 생성합니다.

```mermaid
sequenceDiagram
    participant Planner as Planner Agent
    participant ExecMissing as Executor Missing Agent
    participant LLM as LLM (OpenAI)
    participant State as TravelState

    Planner->>ExecMissing: executor_missing_node(state)
    ExecMissing->>State: missing_slots, follow_up_questions, messages 읽기
    ExecMissing->>ExecMissing: _build_missing_context(missing_slots)
    ExecMissing->>LLM: EXECUTOR_MISSING_INFO_PROMPT + missing_info + messages
    Note over LLM: 스트리밍 응답
    LLM-->>ExecMissing: 재질문 답변
    ExecMissing-->>State: answer, AIMessage
```

---

## 8. Executor General Agent

여행과 무관한 일반 대화(인사, 잡담 등)에 대한 응답을 생성합니다.

```mermaid
sequenceDiagram
    participant Intent as Intent Agent
    participant ExecGeneral as Executor General Agent
    participant LLM as LLM (OpenAI)
    participant State as TravelState

    Intent->>ExecGeneral: executor_general_node(state)
    ExecGeneral->>State: user_input, messages, prefs_info 읽기
    ExecGeneral->>LLM: EXECUTOR_GENERAL_PROMPT + user_input + prefs_info
    Note over LLM: 스트리밍 응답
    LLM-->>ExecGeneral: 일반 대화 답변
    ExecGeneral-->>State: answer, AIMessage
```

---

## 9. 구성요소 설명

### TravelState (상태 관리)

LangGraph의 `TypedDict` 기반 상태 객체로, 모든 에이전트 노드 간 데이터를 공유합니다.

| 분류 | 필드 | 설명 |
|------|------|------|
| **입력** | `user_input` | 사용자 메시지 텍스트 |
| | `user_id`, `room_id` | 사용자/채팅방 식별자 |
| | `latitude`, `longitude` | 사용자 현재 위치 |
| | `image_path` | 업로드 이미지 경로 |
| **대화** | `messages` | 대화 히스토리 (add_messages 리듀서) |
| | `prefs_info` | 사용자 여행 선호도 문자열 |
| **Intent** | `primary_intent` | 주 의도 (IntentType enum) |
| | `slots` | 추출된 슬롯 정보 (IntentSlots) |
| | `summary_title/message` | 대화 요약 |
| **Planner** | `itinerary` | 일정 계획 리스트 |
| | `missing_slots` | 누락 필수 정보 |
| **Retriever** | `candidate_pool` | 전체 검색 후보 풀 |
| | `candidates` | 최종 노출 후보 |
| **출력** | `answer` | 최종 답변 텍스트 |
| | `selected_ids` | 선택된 장소 ID 목록 |

### IntentType (의도 분류)

| 값 | 설명 | 라우팅 |
|----|------|--------|
| `GENERAL` | 일상 대화, 인사 | → `executor_general` |
| `PLACE_INQUIRY` | 장소 검색/추천 | → `retriever` → `executor` |
| `TRIP_PLANNING` | 여행 계획 수립 | → `planner` → (분기) |
| `IMAGE_SIMILAR` | 이미지 유사 장소 검색 | → `retriever` → `executor` |
| `BOOKING` | 예약 관련 | → `retriever` → `executor` |
| `REVIEWS` | 리뷰 관련 | → `retriever` → `executor` |
| `BUDGET` | 예산 관련 | → `retriever` → `executor` |
| `INFO_QA` | 정보 검색 | → `retriever` → `executor` |

### SSE 스트리밍 이벤트 흐름

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as ChatAPI
    participant Graph as LangGraph

    API->>FE: SSE padding (2KB)
    
    loop 각 노드 실행
        Graph->>API: on_chain_start (노드명)
        API->>FE: {step: "intent", status: "start"}
        
        opt executor 계열 노드
            loop 토큰 생성
                Graph->>API: on_custom_event "token"
                API->>API: compute_visible_delta()
                API->>FE: {token: "답변 텍스트..."}
            end
        end

        Graph->>API: on_chain_end (노드명)
        API->>FE: {step: "intent", status: "done"}
        
        opt intent 노드 완료 시
            API->>FE: {room_title: "새 제목"}
        end
    end

    API->>FE: {done: true, full_message, message_id, places}
```

### 주요 외부 의존성

| 컴포넌트 | 역할 |
|----------|------|
| **Qdrant** | 벡터 데이터베이스 (장소/사진 임베딩 저장 및 검색) |
| **OpenAI** | LLM (의도 분석, 계획 생성, 답변 생성) |
| **Tavily** | 웹 검색 API (검색 결과 없을 때 Fallback) |
| **MySQL** | 사용자/채팅방/메시지/장소 데이터 저장 |
| **Naver Map** | 지도 링크 생성 |
| **LangGraph Checkpointer** | 대화 상태 체크포인팅 (AsyncMySaver) |

---

## 10. 액티비티 다이어그램

사용자 메시지 입력부터 최종 응답까지의 전체 처리 흐름을 액티비티 다이어그램으로 표현합니다.

```mermaid
flowchart LR
    %% ── 1. 입력 ──
    subgraph INPUT["📥 입력 처리"]
        direction TB
        Start(["🟢 메시지 입력"]) --> SaveMsg["DB 저장"]
        SaveMsg --> BuildState["TravelState 구성"]
    end

    %% ── 2. 의도 분석 ──
    subgraph INTENT["🧠 의도 분석"]
        direction TB
        IntentAgent["Intent Agent"]
        IntentAgent --> CheckInput{"입력 타입"}
        CheckInput -->|"이미지만"| ImgIntent["IMAGE_SIMILAR"]
        CheckInput -->|"텍스트"| LLMIntent["LLM 분석"]
        LLMIntent --> IntentOut["IntentOutput"]
        ImgIntent --> Route{"의도 분기"}
        IntentOut --> Route
    end

    %% ── 3. 계획 / 검색 ──
    subgraph PROCESS["📋 계획 & 검색"]
        direction TB
        Planner["Planner Agent"] --> CheckMiss{"정보 누락?"}
        CheckMiss -->|"누락"| ExecMissing["❓ 재질문 생성"]
        CheckMiss -->|"충분"| Retriever

        Retriever["🔍 Retriever Agent"]
        Retriever --> CheckImg{"이미지?"}
        CheckImg -->|"있음"| Vision["Vision 분석"]
        Vision --> Search["Qdrant 검색"]
        CheckImg -->|"없음"| Search
        Search --> Dedup["중복제거 + 다양화"]
    end

    %% ── 4. 실행 ──
    subgraph EXEC["⚡ 답변 생성"]
        direction TB
        Executor["Executor Agent"]
        Executor --> CheckCand{"후보 유무"}
        CheckCand -->|"없음"| Tavily["Tavily Fallback"]
        CheckCand -->|"있음"| Context["컨텍스트 구성"]
        Tavily --> Context
        Context --> LLMExec["LLM 스트리밍"]
        LLMExec --> ExtractID["장소 ID 추출"]

        ExecGeneral["💬 일반 대화"]
    end

    %% ── 5. 출력 ──
    subgraph OUTPUT["📤 출력 처리"]
        direction TB
        SaveAI["AI 메시지 저장"] --> SavePlace["ChatPlace 저장"]
        SavePlace --> Done(["🔴 응답 완료"])
    end

    %% ── 연결 ──
    INPUT --> INTENT
    Route -->|"GENERAL"| ExecGeneral
    Route -->|"TRIP_PLANNING"| Planner
    Route -->|"PLACE_INQUIRY 등"| Retriever
    ExecMissing --> SaveAI
    Dedup --> Executor
    ExtractID --> SaveAI
    ExecGeneral --> SaveAI

    %% 스타일
    style Start fill:#4CAF50,color:#fff
    style Done fill:#f44336,color:#fff
    style IntentAgent fill:#2196F3,color:#fff
    style Planner fill:#FF9800,color:#fff
    style Retriever fill:#9C27B0,color:#fff
    style Executor fill:#00BCD4,color:#fff
    style ExecMissing fill:#FFC107,color:#333
    style ExecGeneral fill:#8BC34A,color:#fff
```

### 액티비티 구성요소 설명

#### 주요 액티비티 (노드)

| 액티비티 | 색상 | 설명 |
|----------|------|------|
| **사용자 메시지 입력** | 🟢 초록 | 시작점. 사용자가 텍스트/이미지를 전송 |
| **Intent Agent** | 🔵 파랑 | LLM으로 사용자 의도 분류 및 슬롯(장소, 날짜 등) 추출 |
| **Planner Agent** | 🟠 주황 | 여행 일정 초안 생성, 필수 정보 누락 감지 |
| **Retriever Agent** | 🟣 보라 | Qdrant 벡터DB 하이브리드 검색 + 카테고리 다양화 |
| **Executor Agent** | 🔷 청록 | 검색 결과 기반 최종 추천 답변 스트리밍 생성 |
| **Executor Missing** | 🟡 노랑 | 필수 정보 누락 시 자연스러운 재질문 생성 |
| **Executor General** | 🟢 연두 | 일상 대화(인사, 잡담) 응답 생성 |
| **응답 완료** | 🔴 빨강 | 종료점. SSE done 이벤트 전송 완료 |

#### 분기 조건 (Decision)

| 분기 | 조건 | 분기 결과 |
|------|------|-----------|
| **user_input 존재 여부** | 텍스트 입력 유무 | 텍스트 있음 → LLM 의도 분석 / 텍스트 없음+이미지 → IMAGE_SIMILAR |
| **primary_intent 분기** | Intent Agent 결과 | GENERAL → 일반 대화 / TRIP_PLANNING → Planner / 그 외 → Retriever |
| **필수 정보 누락 여부** | Planner 분석 결과 | 누락 있음 → 재질문 / 정보 충분 → Retriever 검색 진행 |
| **이미지 존재 여부** | image_path 유무 | 있음 → Vision API 분석 후 검색 / 없음 → 텍스트만 검색 |
| **TRIP_PLANNING 여부** | intent 타입 확인 | Yes → itinerary별 병렬 검색 추가 / No → 일반 검색만 |
| **candidates 존재 여부** | Retriever 검색 결과 | 있음 → 장소 컨텍스트 구성 / 없음 → Tavily 웹 검색 Fallback |

#### 데이터 처리 단계

| 단계 | 설명 |
|------|------|
| **TravelState 구성** | 사용자 선호도, 위치, 이미지 등을 state에 주입 |
| **Qdrant 하이브리드 검색** | Dense 벡터 + BM25 + Cross-encoder Rerank |
| **카테고리 다양화 선택** | 상위 후보에서 카테고리 중복 최소화하여 최종 노출 후보 선택 |
| **선택 장소 ID 추출** | LLM 답변에서 `[IDs: ...]` 태그 파싱 또는 텍스트 매칭으로 추론 |
| **ChatPlace 저장** | 추천 장소 최대 3개를 DB에 저장 (이름, 주소, 좌표, 이미지) |
| **SSE done 이벤트** | 전체 답변 + 메시지 ID + 장소 정보를 프론트엔드에 최종 전송 |
