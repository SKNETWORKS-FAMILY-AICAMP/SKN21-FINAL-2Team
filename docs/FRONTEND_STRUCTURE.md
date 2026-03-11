# Frontend 디렉토리 구조 분석

> Next.js App Router 기반 한국 여행 추천 챗봇 프론트엔드

---

## 1) 전체 구조

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
├── next.config.ts
├── vite.config.ts
├── postcss.config.mjs
├── eslint.config.mjs
└── tsconfig.json
```

---

## 2) 루트 파일

### `package.json`

- 프레임워크: `next@16`, `react@19`, `react-dom@19`
- 스타일/렌더링: `framer-motion`, `lucide-react`, `react-markdown`, `remark-gfm`
- 유틸리티: `clsx`, `tailwind-merge`, `jose`
- 테스트: `jest`, `@testing-library/*`, `jest-environment-jsdom`
- 실행 스크립트
  - `npm run dev`
  - `npm run build`
  - `npm run start`
  - `npm run lint`
  - `npm run test`

### `Dockerfile`

- Node 기반 프론트엔드 컨테이너 설정
- 개발 환경에서 `npm run dev`를 기준으로 사용

### 테스트 설정

- `tests/jest.config.js`: Next.js 연동 Jest 설정
- `tests/jest.setup.js`: DOM 테스트 공통 설정

---

## 3) `src/app/` 라우트 구조

현재 확인되는 주요 페이지는 아래와 같습니다.

| 경로 | 설명 |
| --- | --- |
| `/` | 랜딩 페이지 |
| `/signup` | 회원가입 페이지 |
| `/signup/profile` | 프로필 입력 단계 |
| `/survey` | 사용자 취향 설문 |
| `/chatbot` | 메인 챗봇 인터페이스 |
| `/explore` | 여행지 탐색 |
| `/bookmark` | 북마크 목록 |
| `/collection` | 컬렉션 페이지 |
| `/mypage` | 마이페이지 |

공통 파일:

- `layout.tsx`: 전역 레이아웃
- `globals.css`: 전역 스타일
- `favicon.ico`: 파비콘

참고:

- 문서 작성 시점 기준 `src/app/login`, `src/app/onboarding` 페이지는 존재하지 않습니다.

---

## 4) `src/components/` 구성

- `chat/`: 챗봇 인터페이스 핵심 컴포넌트
  - `ChatHome.tsx`
  - `ChatMessageItem.tsx`
  - `PipelineProgress.tsx`
  - `PlaceMapPanel.tsx`
  - `PlaceMapSheet.tsx`
  - `TripContextModal.tsx`
  - `useNaverMap.ts`
- `landing/`: 랜딩 전용 섹션 컴포넌트
  - `Hero.tsx`, `Features.tsx`, `Destinations.tsx`, `ReviewSection.tsx`, `CTA.tsx`, `Header.tsx`, `Footer.tsx`
- `ui/`: 공통 UI 컴포넌트
  - `button.tsx`, `input.tsx`, `label.tsx`, `dialog.tsx`, `SimpleModal.tsx`
- 기타 공통 컴포넌트
  - `Sidebar.tsx`, `Logo.tsx`, `SettingsModal.tsx`, `GoogleLoginBtn.tsx`, `IntroGate.tsx`, `IntroOverlay.tsx`

---

## 5) `src/lib/`, `src/services/`, `src/hooks/`, `src/types/`

### `src/lib/`

- `utils.ts`: 공통 유틸리티 함수 (예: Tailwind 클래스 병합을 위한 `cn`)


### `src/services/`

- `api.ts`: 프론트-백엔드 API 통신 래퍼
- `authError.ts`: 인증 오류 처리
- `errorHandler.ts`: 공통 에러 처리 로직

### `src/hooks/`

- `useSpeechRecognition.ts`: 음성 인식 처리 훅

### `src/types/`

- `speech-recognition.d.ts`: 브라우저 음성 인식 타입 정의

---

## 6) `public/` 정적 자산

- 브랜드 로고: `public/brand/*`
- 랜딩/설문용 이미지: `public/image/*`
- 기본 SVG 아이콘: `globe.svg`, `next.svg`, `vercel.svg`, `window.svg`, `file.svg`

---

## 7) 테스트 구성

`frontend/tests/`에서 Jest + Testing Library 기반으로 주요 UI/상호작용을 검증합니다.

- `ChatbotPage.test.tsx`
- `ChatHome.stt-permission.test.tsx`
- `GoogleLoginBtn.test.tsx`
- `IntroGate.test.tsx`
- `authError.test.ts`

---

## 8) 데이터 흐름 요약

```text
[사용자 브라우저]
    │
    ▼
[src/app 페이지]
    │
    ▼
[src/components UI]
    │
    ▼
[src/services/api.ts]
    │
    ▼
[Backend API]
```

---

## 9) 문서 관리 메모

- 프론트 라우트가 추가/삭제되면 이 문서를 먼저 갱신
- 테스트 도구는 현재 `Vitest`가 아니라 `Jest` 기준
- 정적 자산 분류는 `public/brand`, `public/image` 구조를 기준으로 관리
