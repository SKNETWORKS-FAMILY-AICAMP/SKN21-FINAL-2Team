# 사용자 흐름도 (User Flow Diagrams)

> 랜딩 페이지부터 챗봇을 통한 여행 계획, 탐색 및 기록까지의 전체 사용자 여정과 시스템 간의 상호작용을 나타내는 시퀀스 다이어그램입니다.

---

## 1. 인증 및 온보딩 흐름 (Auth & Onboarding Flow)

사용자가 처음 서비스에 접속하여 Google 로그인을 거치고 프로필 설정 및 취향 설문을 완료하는 흐름입니다.

```mermaid
sequenceDiagram
    actor User as 사용자
    participant FE as Frontend (Next.js)
    participant Google as Google OAuth API
    participant BE as Backend (FastAPI)
    participant DB as MySQL

    User->>FE: 서비스 접속 (/)
    User->>FE: Google 로그인 클릭
    FE->>Google: OAuth 인증 요청
    Google-->>FE: Google 인증 완료 (Token)
    FE->>BE: POST /api/auth/google (토큰 전달)
    
    alt 신규 사용자
        BE->>DB: 사용자 생성
        BE-->>FE: JWT 토큰 발급 및 신규 사용자 알림
        FE->>User: 프로필 기입 페이지 (/signup/profile) 표시
        User->>FE: 프로필 입력 완료
        FE->>BE: 프로필 업데이트
        FE->>User: 취향 설문 페이지 (/survey) 표시
        User->>FE: 여행 취향 선택 (동반자, 스타일 등)
        FE->>BE: 선호도 업데이트 (POST /api/prefer)
        FE->>User: 챗봇 메인 화면 (/chatbot)으로 리다이렉트
    else 기존 사용자
        BE-->>FE: JWT 토큰 발급
        FE->>User: 챗봇 메인 화면 (/chatbot)으로 리다이렉트
    end
```

---

## 2. 메인 챗봇 대화 흐름 (Chatbot Processing Flow)

사용자가 채팅을 통해 여행 일정을 짜거나 장소를 추천받는 메인 흐름입니다.

```mermaid
sequenceDiagram
    actor User as 사용자
    participant FE as Frontend (/chatbot)
    participant BE as Backend API
    participant LangGraph as LangGraph Agent
    participant Map as Place Map Panel (UI)

    User->>FE: 메시지 입력 (또는 음성입력)
    FE->>BE: SSE 스트림 요청 (POST /api/chat/rooms/{id}/ask/stream)
    
    BE->>LangGraph: 상태 그래프 실행 시작
    LangGraph-->>FE: [SSE] pipeline start 이벤트
    
    LangGraph->>LangGraph: 의도 추론 (Intent) & 일정 계획 (Planner)
    LangGraph->>LangGraph: 위치 확인 (Geocoder) & 데이터 검색 (Retriever)
    
    LangGraph-->>FE: [SSE] 파이프라인 진행 상태 업데이트 UI 렌더링
    
    LangGraph->>LangGraph: 응답 생성 (Executor)
    loop 응답 스트리밍
        LangGraph-->>FE: [SSE] chunk (문자 스트리밍)
        FE->>User: 실시간 타이핑 효과 출력
    end

    LangGraph-->>FE: [SSE] step_done & 장소 정보 (PlaceInfo) 전달
    
    FE->>Map: 추천 장소가 포함된 경우 지도 마커 업데이트
    Map->>User: 지도 및 장소 카드 표시
    
    User->>FE: 추천 장소 북마크 클릭
    FE->>BE: POST /api/chat/bookmarks
    BE-->>FE: 성공 응답
```

---

## 3. 탐색 화면 연계 흐름 (Explore to Chat Flow)

사용자가 탐색 페이지(`/explore`)에서 핫플레이스나 관광지를 살펴보고 해당 데이터를 챗봇으로 넘겨 일정을 짜달라고 요청하는 흐름입니다.

```mermaid
sequenceDiagram
    actor User as 사용자
    participant Explore as Frontend (/explore)
    participant ChatUI as Frontend (/chatbot)
    participant BE as Backend

    User->>Explore: 탐색 페이지 진입
    User->>Explore: 랜덤/핫플/관광지 추천 조회
    Explore->>BE: GET 장소 목록 요청
    BE-->>Explore: 장소 데이터 (이미지, 카테고리 포함)
    
    User->>Explore: 마음에 드는 장소 선택 후 "채팅방으로 이동" 클릭
    Explore->>ChatUI: 선택 장소 메타데이터(장소명, 이미지, 카테고리)와 함께 라우팅
    
    ChatUI->>User: 챗봇 창에 초기 프롬프트 텍스트 세팅 (ex. "이 장소로 일정 짜줘")
    User->>ChatUI: 전송 버튼 클릭
    
    ChatUI->>BE: SSE 메세지 발송 (메타정보 포함) 
    BE->>BE: Intent Agent가 메타 정보(이미지, 주소)를 인식해 흐름 처리
    BE-->>ChatUI: 선택 장소 기반 여행 추천 결과 스트리밍
```

---

## 4. 여행 기록 및 다이어리 흐름 (Moments Flow)

챗봇으로 완료한 일정을 확인하고 다이어리에 여행의 순간을 기록하는 흐름입니다.

```mermaid
sequenceDiagram
    actor User as 사용자
    participant UI as Frontend (/moments)
    participant BE as Backend
    participant DB as MySQL / Cloud Storage

    User->>UI: 여행 기록 페이지 접속
    UI->>BE: 다이어리 목록 요청
    BE-->>UI: 지난 여행 & 작성된 다이어리 리스트
    
    User->>UI: "새 기록 작성" 클릭 및 사진 파일 선택
    
    alt 사진 업로드
        UI->>BE: 이미지 업로드 API (공통)
        BE->>DB: Storage 업로드 & URL 반환
        BE-->>UI: 이미지 URL
    end

    User->>UI: 일기 본문 및 위치정보(장소연동) 작성 완료
    UI->>BE: POST /api/diaries (다이어리 데이터 생성)
    BE->>DB: DB Insert
    BE-->>UI: 생성 완료 응답
    
    UI->>User: 작성된 다이어리 화면으로 이동
```
