# Triver (트리버) - LLM 연동 K-Culture 여행 추천 웹 애플리케이션

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [기술 스택](#3-기술-스택)
4. [코드 구현](#4-코드-구현)
5. [프롬프트 최적화](#5-프롬프트-최적화)
6. [성능 최적화](#6-성능-최적화)

---

## 1. 시스템 개요

### 1.1 프로젝트 소개

Triver는 LLM 기반의 한국 여행 추천 AI 에이전트 웹 애플리케이션입니다. 단순한 정보 검색을 넘어, 사용자의 선호도와 대화 맥락을 이해하여 개인화된 여행 추천과 일정 생성을 제공합니다.

### 1.2 주요 기능

| 기능 | 설명 |
|------|------|
| **대화형 여행 계획** | 멀티턴 대화를 통해 사용자의 선호도와 맥락을 이해하고 개인화된 여행 추천 제공 |
| **장소 추천** | 9,827개 이상의 검증된 한국 여행지에서 RAG 기반 의미적 검색 수행 |
| **자동 일정 생성** | 시간대, 교통수단, 식사를 고려한 최적화된 여행 일정 자동 생성 |
| **이미지 기반 검색** | CLIP 모델을 활용한 이미지 유사도 기반 장소 검색 |
| **실시간 트렌드 반영** | 팝업 스토어, 축제, 전시회 등 시의성 있는 정보 추적 |
| **다국어 지원** | 한국어, 영어, 일본어, 중국어 4개 언어 네이티브 응답 지원 |
| **날씨 연동 추천** | 실시간 날씨 데이터를 활용한 실내/실외 추천 자동 전환 |

### 1.3 데이터 소스

총 9,827건의 장소 데이터를 다양한 소스에서 수집하여 활용합니다.

| 소스 | 수집 방법 | 건수 | 용도 |
|------|-----------|------|------|
| Visit Korea API | API | 1,632 | 관광지 |
| Visit Korea API | API | 2,259 | 음식점 |
| Visit Korea API | API | 345 | 숙박 |
| 리테일 사이트 | 크롤링 | 82 | 쇼핑 |
| Visit Korea | 크롤링 | 386 | 투어 |
| 서울문화포털 | 크롤링/API | 250 | 이벤트 |
| Poply | 크롤링 | 9 | 팝업 스토어 |
| 기타 소스 | 크롤링 | 4,864 | 이미지 |

---

## 2. 시스템 아키텍처

### 2.1 전체 시스템 구조

```
┌──────────────────────────────────────────────────────┐
│                    Frontend (Next.js 15)              │
│          React 19 + TypeScript + TailwindCSS          │
│                  i18next (4개 언어)                    │
└──────────────────┬───────────────────────────────────┘
                   │ SSE (Server-Sent Events)
                   ▼
┌──────────────────────────────────────────────────────┐
│                   Nginx (Reverse Proxy)               │
└──────────────────┬───────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────┐
│              Backend (FastAPI + LangGraph)             │
│  ┌─────────────────────────────────────────────────┐ │
│  │          LangGraph State Machine (6 Nodes)       │ │
│  │  Intent → Planner → Geocoder → Retriever →      │ │
│  │  WebSearch → Executor                            │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ LLM Factory │  │  PlaceRetriever│  │ GeoCoder   │  │
│  │ (GPT-4o-mini)│  │ (4-Channel)  │  │(Naver Maps)│  │
│  └─────────────┘  └──────────────┘  └────────────┘  │
└────────┬──────────────────┬──────────────────────────┘
         ▼                  ▼
┌─────────────┐    ┌──────────────┐
│   MySQL 8.0  │    │  Qdrant VDB  │
│(사용자/대화) │    │ (벡터 검색)   │
└─────────────┘    └──────────────┘
```

### 2.2 LangGraph 에이전트 그래프

시스템의 핵심은 **LangGraph 기반 6노드 상태 머신**입니다. 단순한 prompt-response가 아닌, 조건부 라우팅을 통해 사용자 의도에 따라 최적 경로로 처리합니다.

```
                     ┌─────────┐
                     │  Intent  │ (의도 분석)
                     └────┬────┘
                          │
              ┌───────────┼──────────────┐
              ▼           ▼              ▼
        ┌─────────┐  ┌─────────┐  ┌──────────────┐
        │ Planner │  │Geocoder │  │Executor      │
        │(일정생성)│  │(위치확인)│  │General(일반) │
        └────┬────┘  └────┬────┘  └──────────────┘
             │            │
     ┌───────┼────┐       ▼
     ▼            ▼  ┌──────────┐
┌─────────┐  ┌────┐ │Retriever │ (장소 검색)
│Executor │  │Geo-│ └────┬─────┘
│Missing  │  │coder│      │
│(재질문)  │  └────┘  ┌───┼────────┐
└─────────┘          ▼   ▼        ▼
                ┌────────┐  ┌──────────┐
                │Executor│  │WebSearch │
                │(응답)  │  │(Tavily)  │
                └────────┘  └─────┬────┘
                                  ▼
                            ┌────────┐
                            │Executor│
                            └────────┘
```

**라우팅 규칙:**

| 시작 노드 | 조건 | 다음 노드 |
|-----------|------|-----------|
| Intent | `primary_intent == GENERAL` | Executor General |
| Intent | `TRIP_PLANNING in intents` | Planner |
| Intent | 그 외 (장소 관련) | Geocoder |
| Planner | `missing_slots` 있음 | Executor Missing |
| Planner | `missing_slots` 없음 | Geocoder |
| Geocoder | `is_auto_start == True` | Executor |
| Geocoder | 그 외 | Retriever |
| Retriever | 후보 있음 | Executor |
| Retriever | 후보 없음 & 재시도 가능 | Retriever (재시도) |
| Retriever | 후보 없음 & 재시도 완료 | WebSearch |

### 2.3 멀티 컨테이너 배포 구조

Docker Compose를 통해 6개 컨테이너로 구성됩니다.

| 컨테이너 | 포트 | 역할 |
|----------|------|------|
| Backend | 8000 | FastAPI + Uvicorn |
| Frontend | 3000 | Next.js |
| MySQL | 3306 | 관계형 데이터 |
| Qdrant | 6333 | 벡터 검색 |
| Nginx | 80 | 리버스 프록시 |
| Adminer | 8080 | DB 관리 UI (개발용) |

---

## 3. 기술 스택

### 3.1 Frontend

| 항목 | 기술 |
|------|------|
| 프레임워크 | Next.js 15, React 19 |
| 언어 | TypeScript |
| 스타일링 | TailwindCSS 4 |
| 다국어 | i18next |
| 인증 | Google OAuth 2.0 |
| 차트 | Recharts |
| 마크다운 렌더링 | react-markdown + remark-gfm |
| 애니메이션 | Framer Motion |

### 3.2 Backend

| 항목 | 기술 |
|------|------|
| 프레임워크 | FastAPI (Python 3.13) |
| ORM | SQLAlchemy + Alembic |
| 인증 | JWT (python-jose) + Google OAuth |
| LLM 프레임워크 | LangChain + LangGraph |
| 모니터링 | LangSmith |

### 3.3 AI/ML 모델

| 용도 | 모델 |
|------|------|
| 대화 LLM | OpenAI GPT-4o-mini |
| 텍스트 임베딩 | BAAI/bge-m3 (1024차원, 다국어) |
| 비전 임베딩 | CLIP ViT-L-14 (768차원) |
| 리랭커 | cross-encoder/mmarco-mMiniLMv2-L12 |
| 이미지 분석 | Google Vision API + GPT-4o-mini |
| 웹 검색 | Tavily API (DB 결과 없을 시 폴백) |

### 3.4 데이터베이스

| DB | 용도 |
|----|------|
| MySQL 8.0 | 사용자 정보, 대화 기록, 세션, 북마크, 예약, 일기 |
| Qdrant | 고차원 벡터 임베딩 저장 (2개 컬렉션: `places`, `photos`) |

### 3.5 외부 API

| 서비스 | 용도 |
|--------|------|
| Naver Maps/Geocoding | 지도 표시, 좌표 변환, 역 지오코딩 |
| OpenWeather / Weather API | 실시간 날씨, 3일 예보 |
| Visit Seoul API | 공식 관광 데이터 |
| ODsay API | 대중교통 경로 검색 |
| Tavily API | 웹 검색 폴백 |

---

## 4. 코드 구현

### 4.1 LangGraph 워크플로우 정의

시스템의 에이전트 그래프는 `graph.py`에서 정의됩니다. 6개의 노드와 조건부 엣지를 통해 사용자 의도에 따른 동적 라우팅을 구현합니다.

```python
# backend/app/agents/graph.py
from langgraph.graph import StateGraph, END

def workflow():
    graph = StateGraph(TravelState)

    # 노드 등록
    graph.add_node("intent", intent_node)         # 의도 분석
    graph.add_node("planner", planner_node)       # 일정 생성
    graph.add_node("geocoder", geocoder_node)     # 위치 확인
    graph.add_node("retriever", retriever_node)   # 장소 검색
    graph.add_node("web_search", web_search_node) # 웹 검색 폴백
    graph.add_node("executor", executor_node)     # 최종 응답

    # 조건부 라우팅 엣지
    graph.set_entry_point("intent")
    graph.add_conditional_edges("intent", route_by_intent)
    graph.add_conditional_edges("planner", route_by_missing)
    graph.add_conditional_edges("geocoder", route_after_geocoder)
    graph.add_conditional_edges("retriever", route_after_retriever)
    graph.add_edge("web_search", "executor")
    graph.add_edge("executor", END)

    return graph
```

**설계 의도:** 단순한 chain이 아닌 StateGraph를 사용함으로써, 사용자 의도에 따라 필요한 노드만 실행하여 불필요한 처리를 줄이고, 재시도/폴백 로직을 그래프 레벨에서 관리합니다.

### 4.2 조건부 라우팅 로직

```python
# backend/app/agents/grapy_route.py

def route_by_intent(state: TravelState):
    """intent 노드 이후 라우팅"""
    primary_intent = state["primary_intent"]
    intents = state.get("intents") or []

    if primary_intent == IntentType.GENERAL:
        return "executor_general"

    # 복합 의도: TRIP_PLANNING이 포함되면 planner로 우선 라우팅
    if IntentType.TRIP_PLANNING in intents:
        return "planner"

    return "geocoder"


def route_after_retriever(state: TravelState):
    """retriever 실행 후 라우팅 — 재시도 및 폴백 로직"""
    candidates = state.get("candidates") or []
    retry_count = int(state.get("retriever_retry_count") or 0)

    if candidates:
        return "executor"

    if retry_count <= 1:
        # 검색 반경을 확장하여 재시도
        return "retriever"

    # 재시도 후에도 결과 없음 → 웹 검색 폴백
    return "web_search"
```

**설계 의도:** 복합 의도(예: "카페 찾아서 일정에 넣어줘")를 처리하기 위해 `intents` 리스트를 함께 검사합니다. Retriever는 최대 2회 시도(초회 + 반경 확장 재시도) 후 Tavily 웹 검색으로 폴백하여, 어떤 입력에서도 응답이 반환되도록 보장합니다.

### 4.3 Intent 분석 노드

사용자 의도를 분석하고, 슬롯(위치, 카테고리, 날짜 등)을 추출하며, 대화 요약을 업데이트하는 핵심 노드입니다.

```python
# backend/app/agents/intent.py

async def intent_node(state: TravelState):
    # 이미지가 있으면 가장 먼저 분석
    if image_path and not semantic_input_image:
        semantic_input_image = await _analyze_image(image_path)

    # LLM Structured Output 설정
    llm = LLMFactory.get_llm()
    intent_llm = llm.with_structured_output(IntentCoreOutput)
    summary_llm = llm.with_structured_output(SummaryOutput)

    # 1차 gather: 날씨 + GPS 역지오코딩 (빠른 API 호출, ~200ms)
    fast_results = dict(zip(
        fast_coro_keys,
        await asyncio.gather(*fast_coros)
    ))

    # 2차 gather: Intent LLM + Summary LLM 병렬 실행 (~2s)
    result, summary_result = await asyncio.gather(
        intent_chain.ainvoke({...}),
        summary_chain.ainvoke({...}),
    )

    # 범죄 관련 입력 강제 차단 (Python-level 이중 방어)
    if _CRIME_PATTERN.search(check_input):
        primary_intent = IntentType.GENERAL

    # 표준 장소 후처리: LLM 반환 location을 서버에서 최종 정규화
    if slots and slots.location and slots.location.name:
        norm = NormalizedLocation.normalize_location(slots.location.name)
        if norm.canonical_matched:
            slots.location.lat = norm.lat
            slots.location.lon = norm.lon
```

**핵심 설계:**
- **2단계 병렬 실행**: 빠른 API(날씨, GPS)를 먼저 완료한 후, Intent/Summary LLM을 동시에 실행하여 지연을 최소화
- **Structured Output**: `with_structured_output()`을 사용하여 LLM 출력을 Pydantic 모델로 강제, 파싱 오류 방지
- **이중 방어 안전장치**: 프롬프트 레벨 + Python regex로 유해 입력 차단
- **랜드마크 사전 정규화**: LLM이 반환한 위치명을 서버 측 사전과 대조하여 좌표 환각(hallucination) 방지

### 4.4 태그 확장 시스템

사용자의 추상적 표현을 구체적인 검색 키워드로 확장합니다.

```python
# backend/app/agents/intent.py

_TAG_EXPANSION: dict[str, list[str]] = {
    "한국적인":  ["한옥", "전통", "전통차", "고즈넉한"],
    "힙한":      ["감성카페", "인더스트리얼", "트렌디한"],
    "감성적인":  ["감성카페", "빈티지소품", "인스타감성"],
    "레트로":    ["빈티지", "복고", "근대건축"],
    "아늑한":    ["조용한", "소규모", "따뜻한"],
}

def _expand_input_tags(tags: list[str]) -> list[str]:
    expanded = list(tags)
    for tag in tags:
        for key, additions in _TAG_EXPANSION.items():
            if key in tag:
                expanded.extend(additions)
    return list(dict.fromkeys(expanded))  # 순서 유지 + 중복 제거
```

**효과:** "감성적인 카페"라는 입력이 ["감성카페", "빈티지소품", "인스타감성"] 키워드로 확장되어, 벡터 검색의 recall을 크게 향상시킵니다.

### 4.5 4-Layer 하이브리드 멀티채널 검색기

단일 쿼리가 아닌 4개의 병렬 검색 채널을 운영하여 다양한 관점에서 후보를 수집합니다.

```python
# backend/app/core/retrieval/place.py

class PlaceRetriever(PlaceScorer):
    """싱글톤 패턴의 하이브리드 검색 엔진"""

    _instance = None

    def __init__(self):
        self.client = QdrantClient(host=host, port=port)
        self.text_model = SentenceTransformer(TEXT_MODEL, device=DEVICE)    # BGE-M3
        self.vision_model = SentenceTransformer(VISION_MODEL, device=DEVICE) # CLIP

    async def search_hybrid(self, query, image_url, ...):
        # Channel A: Text-Semantic (BGE-M3 → places 컬렉션)
        # Channel B: Image-Visual (CLIP 이미지 임베딩 → photos 컬렉션)
        # Channel C: Text-to-Image (CLIP 텍스트 → photos 컬렉션)
        # Channel D: Web Fallback (Tavily API)
        # → Reciprocal Rank Fusion + CrossEncoder Reranking + Geo-Proximity Blending
```

**4개 검색 채널:**

| 채널 | 모델 | 컬렉션 | 용도 |
|------|------|--------|------|
| A (Text-Semantic) | BGE-M3 | places | 텍스트 의미 기반 검색 |
| B (Image-Visual) | CLIP | photos | 사용자 업로드 이미지와 유사 장소 검색 |
| C (Text-to-Image) | CLIP | photos | 시각적 묘사 텍스트로 이미지 매칭 |
| D (Web Fallback) | Tavily | 외부 | DB에 없는 정보 웹 검색 |

**융합 전략:** Reciprocal Rank Fusion (RRF)으로 채널별 순위를 통합한 후, CrossEncoder로 쿼리-문서 관련성을 재평가하고, 지리적 근접도를 가중치로 블렌딩합니다.

### 4.6 후보 다양성 확보 알고리즘

검색 결과의 카테고리 편중을 방지하는 다양화 알고리즘을 구현합니다.

```python
# backend/app/agents/retriever.py

def _pick_diverse_candidates_deterministic(candidates, final_k, top_pool):
    """결정론 모드: 점수 우선 + 카테고리 분산 tie-break"""
    selected = []
    used_categories = set()
    used_name_signatures = set()

    # 1차: 카테고리 중복 최소화, 동일 장소명 완전 제외
    for c in pool:
        cat = _candidate_category(c)
        name_sig = _candidate_name_signature(c)
        if name_sig in used_name_signatures:
            continue
        if cat not in used_categories:
            selected.append(c)
            used_categories.add(cat)
            used_name_signatures.add(name_sig)

    # 2차: 같은 카테고리여도 장소명이 다르면 추가
    # 3차: 남은 슬롯은 점수 순으로 채움
    return selected


def _pick_diverse_candidates_explore(candidates, final_k, top_pool, seed):
    """탐색 모드: 시드 기반 랜덤 다양화 (매 턴마다 다른 결과)"""
    rng = random.Random(seed)
    while pool and len(selected) < final_k:
        unseen_pool = [c for c in pool if _candidate_category(c) not in used_categories]
        source = unseen_pool if unseen_pool else pool
        weights = [_candidate_score(c) for c in source]
        picked = rng.choices(source, weights=weights, k=1)[0]
        selected.append(picked)
```

**설계 의도:** `deterministic` 모드는 일관된 결과를, `explore` 모드는 `room_id + turn_count` 기반 시드로 매 턴마다 새로운 추천을 제공합니다. 3단계 선택(카테고리 분산 → 장소명 분산 → 점수 순)으로 다양성과 품질을 동시에 확보합니다.

### 4.7 LLM Factory (싱글톤 캐시 패턴)

```python
# backend/app/core/llm_factory.py

class LLMFactory:
    """(model, temperature, llm_type) 조합별 인스턴스 캐싱"""
    _llm_instances: dict[tuple[str, float, str, str], BaseLanguageModel] = {}

    @classmethod
    def get_llm(cls, model=LLM_MODEL, temperature=0, llm_type=LLM_TYPE):
        key = (model, float(temperature), llm_type, base_url)
        if key not in cls._llm_instances:
            if llm_type.lower() == "huggingface":
                endpoint = HuggingFaceEndpoint(repo_id=model, ...)
                cls._llm_instances[key] = ChatHuggingFace(llm=endpoint)
            else:
                cls._llm_instances[key] = ChatOpenAI(model=model, temperature=temperature)
        return cls._llm_instances[key]
```

**설계 의도:** 동일 설정의 LLM 인스턴스를 재생성하지 않고 캐시하여 메모리와 초기화 비용을 절약합니다. OpenAI와 HuggingFace 양쪽을 지원하여 모델 전환이 용이합니다.

### 4.8 Executor 노드 (최종 응답 생성)

검색된 장소 정보를 기반으로 자연스러운 대화형 응답을 스트리밍 방식으로 생성합니다.

```python
# backend/app/agents/executor.py

async def executor_node(state: TravelState, config: RunnableConfig | None = None):
    # 장소 컨텍스트 구성 (Qdrant 결과 → 사람이 읽기 쉬운 텍스트)
    candidate_places, place_context, candidate_names = _build_place_context(candidates)

    # TRIP_PLANNING vs 일반 추천에 따라 다른 프롬프트 사용
    if primary_intent == IntentType.TRIP_PLANNING:
        system_prompt = EXECUTOR_TRIP_PLANNING_PROMPT.format(...)
    else:
        system_prompt = EXECUTOR_PROMPT.format(...)

    # SSE 스트리밍으로 토큰 단위 응답 전송
    full_content = await collect_streamed_text(
        temperature=0.2,
        prompt_value=prompt_messages,
        config=config,
    )

    # 답변에 실제로 언급된 장소만 필터링 (환각 방지)
    place_info_list = _collect_recommended_places(cleaned_answer, candidate_places)

    # 노출된 장소 ID 누적 (다음 턴에서 중복 제거용)
    shown_place_ids = list(state.get("shown_place_ids") or [])
    for p in place_info_list:
        if p.contenttypeid not in shown_set:
            shown_place_ids.append(p.contenttypeid)
```

**핵심 설계:**
- **응답 후 검증**: LLM이 생성한 답변에서 마크다운 링크를 파싱하여, 실제 검색 결과에 존재하는 장소만 반환 (환각 장소 필터링)
- **노출 이력 관리**: `shown_place_ids`로 이전 턴에 추천한 장소를 추적하여 중복 추천 방지
- **SSE 스트리밍**: `collect_streamed_text()`로 토큰 단위 실시간 전송하여 사용자 체감 응답 시간 단축

### 4.9 다국어 지원 시스템

```python
# backend/app/agents/prompts/prompts.py

_LANGUAGE_REMINDER: dict[LanguageType, str] = {
    LanguageType.en: "[IMPORTANT] Your response MUST be written entirely in English.",
    LanguageType.ja: "[重要] 必ず全て日本語で回答してください。",
    LanguageType.zh: "[重要] 请务必全部使用中文回答。",
}

_NAME_INSTRUCTION: dict[LanguageType, str] = {
    LanguageType.en: "Keep Korean place names in original Hangul when they are the canonical name.",
    LanguageType.ja: "場所名など固有名詞は、韓国語表記を維持しても構いません。",
    LanguageType.zh: "地点名等专有名词可保留韩文原文表记。",
}
```

**전략:**
- System 프롬프트에 언어 지시문 주입 (`get_language_instruction`)
- HumanMessage 앞에 리마인더 삽입 (`get_language_reminder`)
- 장소명은 원어(한국어) 표기 유지 지시 (고유명사 번역 오류 방지)

---

## 5. 프롬프트 최적화

### 5.1 노드별 Temperature 전략

각 노드의 역할에 맞게 LLM의 temperature를 차등 설정하여 결정론적 분석과 창의적 응답 사이의 균형을 잡았습니다.

| 노드 | Temperature | 근거 |
|------|------------|------|
| Intent (의도 분석) | 0.0 | 의도 분류와 슬롯 추출은 정확성이 최우선 |
| Planner (일정 생성) | 0.3 | 구조적이면서도 약간의 창의성 허용 |
| Executor (응답 생성) | 0.2 | 정보 전달의 정확성 우선, 자연스러운 표현 |
| Executor General (일반 대화) | 0.7 | 친근하고 다양한 대화 스타일 |
| Executor Missing (재질문) | 0.5 | 자연스러운 질문 생성 |

### 5.2 Structured Output 활용

LLM 출력을 Pydantic 모델로 강제하여 파싱 오류를 원천 차단합니다.

```python
# Intent 분석 결과 구조
class IntentCoreOutput(BaseModel):
    intents: list[IntentType]         # 복수 의도 분류
    primary_intent: IntentType        # 주 의도
    slots: IntentSlots               # 추출된 슬롯 (위치, 날짜, 카테고리 등)
    update_user_input: str           # 재구성된 사용자 입력 (단답 → 완전한 문장)
    input_tags: list[str]            # 검색용 키워드 태그

class SummaryOutput(BaseModel):
    summary_title: str               # 대화 요약 제목
    summary_message: str             # 누적 대화 요약
```

### 5.3 컨텍스트 주입 전략

LLM에 전달하는 컨텍스트를 체계적으로 구성하여 응답 품질을 향상시킵니다.

**장소 컨텍스트 포맷 (JSON → 구조화 텍스트):**

```
## 검색된 장소 정보

### 1. 경복궁
- 주소: 서울특별시 종로구 사직로 161
- 지도: https://map.naver.com/...
- 소개: 조선 왕조의 법궁으로...
- 태그: 전통, 궁궐, 역사
- 이용시간: 09:00~18:00
- 휴무일: 매주 화요일
```

**설계 근거:** JSON 대신 마크다운 형태의 구조화 텍스트를 사용하면, LLM이 JSON을 그대로 출력하는 현상을 방지하고, 필요한 정보를 자연스러운 문장으로 변환하여 전달하는 품질이 향상됩니다.

### 5.4 대화 요약 패턴 (Summary Chain)

멀티턴 대화에서 컨텍스트 윈도우 초과를 방지하면서도 핵심 정보를 유지합니다.

- Intent 노드에서 매 턴마다 `SummaryOutput` 생성
- 최근 6개 메시지만 원문 유지, 나머지는 `summary_message`로 압축
- 요약에 사용자 선호도, 일정 정보, 이전 추천 내역이 누적 포함
- 이후 모든 노드가 이 요약을 참조하여 일관된 맥락 유지

### 5.5 안전 가드 레일

```python
# 프롬프트 레벨 + Python 레벨 이중 방어
_CRIME_PATTERN = re.compile(
    r"살해|살인|살육|살상|시신|시체|"
    r"성폭행|강간|추행|몰카|불법촬영|"
    r"테러|폭탄|폭발물|간첩|기밀유출"
)

# 탐지 시 장소 검색 차단
if _CRIME_PATTERN.search(check_input):
    primary_intent = IntentType.GENERAL  # 일반 대화로 강제 전환
    update_user_input += "\n범죄 관련 내용이 포함되어있으니 장소 추천을 하지 말아줘"
```

프롬프트 지시문으로 1차 차단하고, Python 정규표현식으로 2차 검증하는 이중 방어 전략을 사용합니다.

### 5.6 입력 재구성 (update_user_input)

사용자의 단답이나 불완전한 입력을 완전한 문장으로 재구성하여 하위 노드의 처리 품질을 향상시킵니다.

```
사용자: "거기 맛집도 알려줘"
  ↓ (이전 대화: 홍대 카페 추천 중)
update_user_input: "홍대 근처의 맛집을 추천해주세요"
```

이를 통해 Retriever와 Executor가 "거기"가 "홍대"를 의미한다는 맥락을 정확히 전달받습니다.

---

## 6. 성능 최적화

### 6.1 응답 지연 최적화 전략

전체 파이프라인의 응답 지연을 줄이기 위해 6가지 전략을 적용했습니다.

| # | 전략 | 효과 |
|---|------|------|
| 1 | Reranker 경량 모델 사용 | Cross-encoder 추론 시간 감소 |
| 2 | Intent 노드 비동기화 | 이미지 분석 + 날씨 조회 + LLM 호출을 2단계 병렬 실행 |
| 3 | 멀티채널 병렬 검색 | 4개 검색 채널(Text/Image/Text-to-Image/Web) 동시 실행 |
| 4 | 후보 풀 축소 | 20개 후보 → 5개 최종 추천으로 Executor 토큰 소비 절감 |
| 5 | 프롬프트 토큰 최소화 | 불필요한 예시/프리앰블 제거, 컨텍스트 길이 압축 |
| 6 | Executor 단순화 | 복수 옵션 대신 단일 최적 일정만 생성 |

**결과:** 전체 파이프라인 기준 약 20~30% 지연 감소

### 6.2 RAGAS + LLM-as-Judge 기반 RAG 품질 평가

RAGAS 프레임워크를 활용하여 검색 및 응답 품질을 정량적으로 측정하고, 단계별로 개선했습니다. 모든 평가 메트릭은 **GPT-4o-mini를 Judge LLM으로 사용**하여 자동 평가합니다.

**LLM-as-Judge 평가 메트릭:**

| 메트릭 | 목표 | 설명 |
|--------|------|------|
| Faithfulness | 0.9+ | 응답이 검색된 컨텍스트에 근거하는 정도 |
| Answer Relevancy | 0.9+ | 응답이 질문 의도에 부합하는 정도 |
| LLM Context Recall | - | LLM이 판단한 컨텍스트 재현율 |
| LLM Context Precision | - | LLM이 판단한 컨텍스트 정밀도 |

**검색 단계 평가 메트릭 (규칙 기반):**

| 메트릭 | 설명 |
|--------|------|
| Precision@K | 상위 K개 중 정답 비율 |
| Recall@K | 전체 정답 중 상위 K개에 포함된 비율 |
| NDCG@K | 순위를 고려한 검색 품질 |
| MRR@K | 첫 번째 정답이 나타나는 순위 |

**3단계 평가 프로세스:**

| 단계 | 구성 | 목적 |
|------|------|------|
| Phase 1 | BGE-M3 텍스트 단일 채널 | Baseline 성능 측정 |
| Phase 2 | 멀티채널 융합 (텍스트 + 이미지 + 웹) | 채널 추가에 따른 품질 변화 측정 |
| Phase 3 | Reranker + Geo-blending 적용 | 후처리 최적화 효과 검증 |
