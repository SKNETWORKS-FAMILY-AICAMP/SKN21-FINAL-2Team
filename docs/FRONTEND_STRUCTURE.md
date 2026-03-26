# Frontend 디렉토리 구조 분석

> Next.js App Router 기반 프론트엔드 구조를 현재 코드 기준으로 정리한 문서

---

## 1. 개요

프론트엔드는 `frontend/` 아래에 구성되어 있으며, Next.js 16 + React 19 조합을 사용한다.  
주요 사용자 흐름은 랜딩, 회원가입, 취향 설문, 챗봇, 탐색, 북마크, 여행 기록, 마이페이지로 나뉜다.

---

## 2. 루트 구조

```text
frontend/
├── src/
│   ├── app/
│   ├── components/
│   ├── config/
│   ├── constants/
│   ├── features/
│   ├── hooks/
│   ├── i18n/
│   ├── lib/
│   ├── services/
│   └── types/
├── public/
├── tests/
├── Dockerfile
├── package.json
├── package-lock.json
├── next.config.ts
├── postcss.config.mjs
├── eslint.config.mjs
└── tsconfig.json
```

---

## 3. 핵심 설정 파일

### `package.json`

- 프레임워크: `next@16.1.6`, `react@19.2.3`
- 주요 의존성
  - `@react-oauth/google`
  - `framer-motion`
  - `i18next`, `react-i18next`
  - `lucide-react`
  - `react-markdown`, `remark-gfm`
  - `react-datepicker`
  - `recharts`
- 주요 스크립트
  - `npm run dev`
  - `npm run build`
  - `npm run start`
  - `npm run lint`
  - `npm run test`

### `next.config.ts`

- `@` alias를 `frontend/src`로 연결
- `/api/:path*` 요청을 백엔드로 rewrite
- `NEXT_PUBLIC_API_URL`이 절대 URL이 아니면 기본 목적지는 `http://backend:8000/api`
- Next route handler가 있으면 해당 handler가 우선 처리되고, 나머지만 fallback rewrite가 적용된다

### `Dockerfile`

- `dev`, `builder`, `production` 멀티 스테이지 구성
- 개발 컨테이너는 `npm run dev`
- 프로덕션 이미지는 `npm run build` 결과물 기반

---

## 4. `src/app/` 라우트 구조

현재 확인되는 주요 페이지는 다음과 같다.

| 경로 | 파일 | 설명 |
| --- | --- | --- |
| `/` | `src/app/page.tsx` | 랜딩 페이지 |
| `/signup` | `src/app/signup/page.tsx` | 회원가입 진입 |
| `/signup/profile` | `src/app/signup/profile/page.tsx` | 프로필 입력 |
| `/survey` | `src/app/survey/page.tsx` | 취향 설문 |
| `/chatbot` | `src/app/chatbot/page.tsx` | 메인 챗봇 |
| `/explore` | `src/app/explore/page.tsx` | 여행지 탐색 |
| `/bookmark` | `src/app/bookmark/page.tsx` | 북마크 |
| `/moments` | `src/app/moments/page.tsx` | 여행 기록/다이어리 |
| `/mypage` | `src/app/mypage/page.tsx` | 마이페이지 |

공통 파일:

- `src/app/layout.tsx`
  - Google OAuth Provider
  - `LanguageProvider`
  - 다국어 폰트 세팅
- `src/app/globals.css`
  - 전역 스타일
- `src/app/HomePage.tsx`
  - 랜딩 페이지 조립

### `src/app/api/`

Next 서버 측 프록시/스트리밍 route handler가 위치한다.

- `src/app/api/chat/route.ts`
  - 일반 채팅 프록시
- `src/app/api/chat/rooms/[roomId]/ask/stream/route.ts`
  - 스트리밍 채팅 프록시
- `src/app/api/chat/rooms/[roomId]/autostart/stream/route.ts`
  - 자동시작 스트리밍 프록시

---

## 5. 컴포넌트 구조

### `src/app/components/`

랜딩과 온보딩 중심의 화면 조각이 위치한다.

- `Hero.tsx`, `Features.tsx`, `Destinations.tsx`, `ReviewSection.tsx`, `CTA.tsx`
- `Header.tsx`, `Footer.tsx`
- `IncompleteSignupModal.tsx`

### `src/components/`

라우트 바깥 공통 컴포넌트 영역이다.

- `GoogleLoginBtn.tsx`
- `common/Logo.tsx`
- `common/LanguageBanner.tsx`
- `common/LanguageSwitcher.tsx`
- `navigation/Sidebar.tsx`

### `src/features/chat/`

챗봇 기능이 집중된 영역이다.

- `components/`
  - `ChatHome.tsx`
  - `ChatHeader.tsx`
  - `ChatInputArea.tsx`
  - `ChatMessageItem.tsx`
  - `PipelineProgress.tsx`
  - `PlaceMapPanel.tsx`
  - `PlaceMapSheet.tsx`
  - `TripContextModal.tsx`
- `hooks/`
  - `useChatMessages.ts`
  - `useChatRooms.ts`
  - `useChatMap.ts`
  - `useNaverMap.ts`

### 페이지별 하위 컴포넌트

- `src/app/moments/components/*`
  - 다이어리 편집, 위치 선택, 갤러리
- `src/app/mypage/components/*`
  - 예약/여정 상세 모달
- `src/app/signup/components/*`
  - 가입 버튼 등 회원가입 보조 UI

---

## 6. 서비스, i18n, 유틸리티

### `src/services/`

- `api.ts`
  - 인증/사용자/채팅/북마크/자동시작 API 래퍼
  - 브라우저에서는 `/api` rewrite를 우선 사용해 CORS preflight를 줄임
  - 토큰 검증 및 refresh 처리 포함
- `autoStart.ts`
  - 자동시작용 payload 보조 로직
- `authError.ts`, `errorHandler.ts`
  - 인증 및 공통 에러 처리

### `src/i18n/`

- `LanguageContext.tsx`
  - 앱 전역 언어 상태 공급
- `config.ts`, `index.ts`
  - i18next 초기화
- `useTranslation.ts`
  - 번역 훅 래퍼
- `languageCookie.ts`, `constants.ts`
  - 언어 쿠키 관리
- `locales/*.json`
  - `ko`, `en`, `ja`, `zh` 번역 리소스

### `src/hooks/`

- `common/useSpeechRecognition.ts`
  - 브라우저 음성 인식 훅

### `src/lib/`

- `utils.ts`
  - 공통 유틸
- `imageUrl.ts`
  - 이미지 URL 처리 보조

### `src/config/` / `src/constants/`

- 국가, 내비게이션, 상수 정의

---

## 7. 정적 자산

`public/` 아래에 브랜드/랜딩/설문 이미지가 배치되어 있다.

- `public/brand/*`
- `public/image/*`
- 기본 SVG 자산

---

## 8. 테스트

`frontend/tests/` 아래에 Jest 테스트가 위치한다.

- API/에러 처리 테스트
- 챗봇 페이지/메시지 렌더링 테스트
- 파이프라인 진행 UI 테스트
- Google 로그인 버튼 테스트

---

## 9. 문서 역할 및 연계

- 이 문서는 프론트엔드 구조와 파일 배치를 설명하는 문서다.
- 챗봇 파이프라인과 백엔드 연계 흐름은 [agent_sequence_diagrams.md](/Users/kim/SKN21-FINAL-2Team/docs/agent_sequence_diagrams.md)에서 관리한다.

---

## 10. 문서 관리 메모

- 라우트 추가/삭제 시 이 문서를 우선 갱신
- `src/features/chat`와 `src/app/api/chat/*`는 함께 보는 것이 맞다
- 다국어 리소스 구조 변경 시 이 문서와 사용자 플로우 문서를 함께 수정
