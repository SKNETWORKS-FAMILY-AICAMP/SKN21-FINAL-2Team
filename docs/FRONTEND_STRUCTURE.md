# Frontend 디렉토리 구조 분석

> Next.js App Router 기반 프론트엔드 구조와 현재 실행 상태를 정리한 문서

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
│   ├── features/
│   ├── hooks/
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
- UI/유틸: `framer-motion`, `lucide-react`, `react-markdown`, `remark-gfm`, `jose`
- 테스트: `jest`, `@testing-library/*`, `jest-environment-jsdom`
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

- `src/app/layout.tsx`: 전역 폰트, `GoogleOAuthProvider`, 메타데이터
- `src/app/globals.css`: 전역 스타일
- `src/app/api/chat/route.ts`: Next 서버 측 채팅 프록시 엔드포인트

---

## 5. 컴포넌트 구조

### `src/app/components/`

랜딩 및 공통 화면 조각이 위치한다.

- `Hero.tsx`, `Features.tsx`, `Destinations.tsx`, `ReviewSection.tsx`, `CTA.tsx`
- `Header.tsx`, `Footer.tsx`
- `IncompleteSignupModal.tsx`

### `src/components/`

라우트 바깥 공통 컴포넌트 영역이다.

- `GoogleLoginBtn.tsx`
- `common/Logo.tsx`
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

---

## 6. 서비스 및 유틸리티

### `src/services/`

- `api.ts`
  - 인증/사용자/채팅/북마크/자동시작 API 래퍼
  - 스트리밍 요청은 브라우저에서 `/api` rewrite를 우선 사용
  - 토큰 검증 및 refresh 처리 포함
- `autoStart.ts`: 자동시작 관련 보조 로직
- `authError.ts`, `errorHandler.ts`: 인증 및 공통 에러 처리

### `src/hooks/`

- `common/useSpeechRecognition.ts`: 음성 인식 훅

### `src/lib/`

- `utils.ts`: 공통 유틸리티

### `src/types/`

- 브라우저 음성 인식 타입 정의 등 전역 타입 보완

---

## 7. 정적 자산

`public/` 아래에 랜딩/설문/브랜드 이미지가 배치되어 있다.

- `public/image/*`
- 기본 SVG 자산

---

## 8. 문서 역할 및 연계

- 이 문서는 프론트엔드 구조와 파일 배치를 설명하는 문서다.
- 실행 가능 여부, 테스트 통과 여부, 현재 이슈 목록은 [PROJECT_ANALYSIS.md](/Users/kim/SKN21-FINAL-2Team/docs/PROJECT_ANALYSIS.md)에서만 관리한다.

---

## 9. 문서 관리 메모

- 라우트 추가/삭제 시 이 문서를 먼저 갱신
- `src/features/chat`가 현재 챗봇 핵심 로직의 중심
- 빌드 상태는 코드 변경 여부와 별개로 로컬 의존성 상태 영향을 크게 받으므로 테스트 결과와 빌드 결과를 분리해 기록
