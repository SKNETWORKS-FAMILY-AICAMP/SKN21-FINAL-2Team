# Frontend 디렉토리 구조 분석

> Next.js 기반 한국 여행 추천 챗봇 프론트엔드 애플리케이션

---

## 📁 전체 디렉토리 구조

```
frontend/
├── src/                    # 소스 코드
│   ├── app/                # App Router (페이지 및 레이아웃)
│   ├── components/         # 재사용 가능한 UI 컴포넌트
│   ├── hooks/              # 커스텀 리액트 훅
│   ├── services/           # API 통신 및 에러 핸들링 로직
│   └── types/              # TypeScript 타입 정의
├── public/                 # 정적 자원 (이미지, 아이콘 등)
├── tests/                  # 테스트 코드
├── Dockerfile              # Docker 이미지 빌드 설정
├── next.config.ts          # Next.js 설정
├── package.json            # 프로젝트 의존성 및 스크립트
├── postcss.config.mjs      # PostCSS 설정
├── tailwind.config.ts      # Tailwind CSS 설정
└── tsconfig.json           # TypeScript 설정
```

---

## 🗂️ 루트 파일

### `package.json`
프로젝트의 의존성 관리 및 실행 스크립트를 정의합니다.

| 분류 | 라이브러리 |
| --- | --- |
| 프레임워크 | `next`, `react`, `react-dom` |
| 스타일링 | `tailwindcss`, `postcss`, `lucide-react`, `framer-motion` |
| 상태 관리/통신 | `axios` |
| 유틸리티 | `clsx`, `tailwind-merge` |
| 개발 도구 | `typescript`, `eslint`, `vitest` |

---

### `Dockerfile`
프론트엔드 어플리케이션을 빌드하고 실행하기 위한 설정입니다.

- 베이스 이미지: `node:20-slim`
- 패키지 매니저: `npm`
- 실행 모드: `npm run dev` (개발 환경 기준)

---

## 📦 `src/app/` — App Router

Next.js의 App Router 방식을 사용하여 URL 경로에 따른 페이지를 구성합니다.

| 경로 | 설명 |
| --- | --- |
| `/` | 랜딩 페이지 (`page.tsx`) |
| `/login` | 로그인 페이지 |
| `/signup` | 회원가입 페이지 |
| `/onboarding` | 초기 온보딩 스텝 |
| `/survey` | 사용자 취향 설문 페이지 |
| `/chatbot` | 메인 챗봇 인터페이스 |
| `/explore` | 여행지 탐색 페이지 |
| `/bookmark` | 북마크한 장소 목록 |
| `/mypage` | 사용자 프로필 및 개인 설정 |

---

## 📁 `src/components/` — UI 컴포넌트

공통으로 사용되거나 특정 도메인에 종속된 UI 컴포넌트들입니다.

- **`chat/`**: 챗봇 인터페이스 관련 컴포넌트 (메시지 버블, 입력창, 프로세스 인디케이터 등)
- **`landing/`**: 메인 랜딩 페이지 전용 컴포넌트
- **`ui/`**: 기본 UI 빌딩 블록 (버튼, 입력창, 모달 등 기본 요소)
- **독립 컴포넌트**: `Sidebar.tsx`, `Logo.tsx`, `SettingsModal.tsx`, `GoogleLoginBtn.tsx` 등

---

## 📁 `src/services/` — 비즈니스 로직 및 API

백엔드 서버와의 통신 및 데이터 처리를 담당합니다.

- **`api.ts`**: Axios 인스턴스 설정 및 백엔드 API 엔드포인트 호출 함수 정의
- **`errorHandler.ts`**: API 요청 시 발생하는 에러를 통합 관리하고 처리하는 로직

---

## 📁 `src/hooks/` & `src/types/` — 유틸리티

- **`hooks/`**: 다양한 컴포넌트에서 재사용되는 리액트 로직 (인증 상태 관리, 스크롤 처리 등)
- **`types/`**: 프로젝트 전역에서 사용되는 TypeScript 인터페이스 및 타입 정의

---

## 📁 `public/` — 정적 자원

- 벡터 이미지 (`.svg`): `next.svg`, `vercel.svg`, `globe.svg` 등 기본 아이콘 및 로고 포함

---

## 🔄 데이터 흐름 요약

```
[사용자 브라우저]
    │
    ▼
[src/app (Pages)] <───> [src/components (UI)]
    │                      │
    └────────┬─────────────┘
             │
             ▼
[src/services (API)] <───> [Backend API (8000)]
```
