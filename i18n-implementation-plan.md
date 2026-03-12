# Triver 다국어(i18n) 시스템 구현 계획서

## 목차

1. [현재 상태 분석](#1-현재-상태-분석)
2. [지원 언어 및 아키텍처 설계](#2-지원-언어-및-아키텍처-설계)
3. [Phase 1: 백엔드 — 언어 설정 저장](#3-phase-1-백엔드--언어-설정-저장)
4. [Phase 2: 프론트엔드 — i18n 인프라 구축](#4-phase-2-프론트엔드--i18n-인프라-구축)
5. [Phase 3: 번역 파일(JSON) 작성](#5-phase-3-번역-파일json-작성)
6. [Phase 4: 회원가입 흐름 연동](#6-phase-4-회원가입-흐름-연동)
7. [Phase 5: 페이지별 적용](#7-phase-5-페이지별-적용)
8. [Phase 6: 설문조사(Survey) 다국어](#8-phase-6-설문조사survey-다국어)
9. [Phase 7: 폰트 및 날짜 포맷](#9-phase-7-폰트-및-날짜-포맷)
10. [Phase 8: AI 챗봇 응답 언어](#10-phase-8-ai-챗봇-응답-언어)
11. [번역 텍스트 전체 목록](#11-번역-텍스트-전체-목록)
12. [구현 순서 및 체크리스트](#12-구현-순서-및-체크리스트)

---

## 1. 현재 상태 분석

### 1.1 이미 있는 것

- **AppLanguage 타입**: `"en" | "ko" | "ja"` — `frontend/src/app/mypage/types/index.ts`에 정의됨
- **localStorage 키**: `"triver:language:v1"` — Sidebar에서 사용 중
- **Sidebar i18n 딕셔너리**: `SIDEBAR_I18N` — `Sidebar.tsx`에 en/ko/ja 3개 언어 번역 존재
- **언어 변경 이벤트**: `window.dispatchEvent(new CustomEvent("triver:language"))` 패턴 사용 중
- **회원가입 프로필 페이지 언어 드롭다운**: UI는 존재하나 기능 미연결 (onChange 없음, state 바인딩 없음)

### 1.2 없는 것 (구현 필요)

- **백엔드 User 모델에 `language` 필드**: 없음 — 언어 설정이 서버에 저장되지 않음
- **Pydantic 스키마에 `language` 필드**: `UserBase`, `UserUpdate`, `UserResponse` 모두 없음
- **LanguageType enum**: `enums.py`에 `GenderType`, `RoleType`만 있고 언어 enum 없음
- **전역 i18n Context/Provider**: 없음 — Sidebar만 자체적으로 localStorage 읽어 사용
- **번역 JSON 파일**: 없음 — 모든 텍스트가 컴포넌트에 하드코딩
- **useTranslation 훅**: 없음
- **CJK 폰트 지원**: `layout.tsx`에 `Geist`(라틴), `Noto Serif KR`(한국어 세리프)만 있고, 일본어/중국어 산세리프 폰트 없음

### 1.3 하드코딩된 텍스트 분포

| 카테고리 | 한국어 텍스트 수 | 영어 텍스트 수 | 주요 파일 |
|---------|---------------|-------------|---------|
| 회원가입/프로필 | ~5개 | ~10개 | `SignUpPage.tsx`, `SignUpProfilePage.tsx`, `validation.ts` |
| 설문조사 | ~7개 (선택지) | ~6개 (질문) | `SurveyPage.tsx`, `constants.ts` |
| 사이드바 | 3개 (기존 i18n) | 7개 (기존 i18n) | `Sidebar.tsx` |
| 탐색(Explore) | ~3개 | ~15개 | `ExplorePage.tsx` |
| 북마크 | ~5개 | ~15개 | `BookmarkPage.tsx` |
| 모먼츠(일기) | ~5개 | ~20개 | `MomentsPage.tsx`, 하위 컴포넌트 |
| 마이페이지 | ~2개 | ~8개 | `MyPagePage.tsx` |
| 랜딩페이지 | ~15개 | ~25개 | `Hero.tsx`, `Features.tsx`, `CTA.tsx` 등 |
| 공통 모달 | ~8개 | ~2개 | `IncompleteSignupModal.tsx`, Sidebar 삭제 모달 |
| **합계** | **~53개** | **~108개** | |

---

## 2. 지원 언어 및 아키텍처 설계

### 2.1 지원 언어

| 코드 | 언어 | 용도 |
|-----|------|------|
| `en` | English | 기본 언어 (fallback) |
| `ko` | 한국어 | |
| `ja` | 日本語 | |
| `zh` | 中文 (간체) | 추후 확장 대비 |

### 2.2 전체 아키텍처

```
┌─────────────────────────────────────────────────────┐
│  사용자 흐름                                          │
│                                                       │
│  1. 최초 접속 → navigator.language로 언어 자동 감지     │
│  2. 회원가입 프로필 → 언어 선택 드롭다운                  │
│  3. 프로필 저장 → PATCH /api/users/me (language 포함)   │
│  4. 이후 접속 → GET /api/users/me → language 복원       │
│  5. 마이페이지 → 언어 변경 가능                          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  데이터 흐름                                          │
│                                                       │
│  [User DB] ←→ [API: /api/users/me] ←→ [LanguageContext]│
│                                          ↕              │
│                                   [localStorage]        │
│                                          ↕              │
│                              [useTranslation() 훅]      │
│                                          ↕              │
│                              [번역 JSON 파일 참조]       │
│                                          ↕              │
│                              [컴포넌트 UI 렌더링]        │
└─────────────────────────────────────────────────────┘
```

### 2.3 언어 결정 우선순위

```
1순위: localStorage("triver:language:v1")  ← 가장 빠르게 접근 가능
2순위: API 응답 user.language               ← 서버에 저장된 설정
3순위: navigator.language 기반 자동 감지     ← 최초 방문자용
4순위: "en" (기본값)                         ← 최종 fallback
```

---

## 3. Phase 1: 백엔드 — 언어 설정 저장

### 3.1 LanguageType enum 추가

**파일**: `backend/app/models/enums.py`

```python
# 기존 코드 유지
import enum

class GenderType(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class RoleType(str, enum.Enum):
    human = "human"
    ai = "ai"

# ===== 새로 추가 =====
class LanguageType(str, enum.Enum):
    en = "en"
    ko = "ko"
    ja = "ja"
    # zh = "zh"  # 추후 확장 시 주석 해제
```

### 3.2 User 모델에 language 컬럼 추가

**파일**: `backend/app/models/user.py`

```python
from app.models.enums import GenderType, LanguageType  # LanguageType 임포트 추가

class User(BaseModel):
    __tablename__ = "users"

    # ... 기존 필드 유지 ...

    country_code = Column(String(10), nullable=True, comment="ISO Country Code")
    language = Column(Enum(LanguageType), default=LanguageType.en, nullable=False, comment="UI Language Preference")  # 새로 추가
    is_join = Column(Boolean, default=False)
    is_prefer = Column(Boolean, default=False)

    # ... 나머지 기존 코드 유지 ...
```

### 3.3 Pydantic 스키마 업데이트

**파일**: `backend/app/schemas/user.py`

```python
from app.models.enums import GenderType, LanguageType  # LanguageType 임포트 추가

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    nickname: Optional[str] = None
    # ... 기존 필드 유지 ...
    country_code: Optional[str] = None
    language: Optional[LanguageType] = None          # 새로 추가
    is_join: Optional[bool] = None
    is_prefer: Optional[bool] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    nickname: Optional[str] = None
    # ... 기존 필드 유지 ...
    country_code: Optional[str] = None
    language: Optional[LanguageType] = None          # 새로 추가
    is_join: Optional[bool] = None
    is_prefer: Optional[bool] = None
```

> `UserResponse`는 `UserBase`를 상속하므로 자동으로 `language` 필드가 포함됩니다.
> `PATCH /api/users/me` 엔드포인트는 `UserUpdate` 스키마를 사용하므로, 별도 수정 없이 language 업데이트가 가능합니다.

### 3.4 Alembic 마이그레이션

```bash
cd backend
alembic revision --autogenerate -m "add_language_to_user"
alembic upgrade head
```

생성된 마이그레이션 파일에서 기존 사용자의 기본값 처리를 확인합니다:

```python
# 마이그레이션 파일 내 upgrade 함수
def upgrade():
    op.add_column('users', sa.Column('language', sa.Enum('en', 'ko', 'ja', name='languagetype'),
                  nullable=False, server_default='en', comment='UI Language Preference'))
```

### 3.5 프론트엔드 API 타입 업데이트

**파일**: `frontend/src/services/api.ts`

`UserProfile` 인터페이스에 language 필드 추가:

```typescript
export interface UserProfile {
    id: number;
    email: string;
    // ... 기존 필드 유지 ...
    country_code?: string | null;
    language?: "en" | "ko" | "ja" | null;   // 새로 추가
    is_join?: boolean | null;
    is_prefer?: boolean | null;
}
```

---

## 4. Phase 2: 프론트엔드 — i18n 인프라 구축

### 4.1 디렉토리 구조

```
frontend/src/
  i18n/
    locales/
      en.json          # 영어 번역 (기준 언어)
      ko.json          # 한국어 번역
      ja.json          # 일본어 번역
    LanguageContext.tsx  # React Context Provider
    useTranslation.ts   # 커스텀 훅
    index.ts            # 유틸리티 함수
```

### 4.2 index.ts — 번역 로딩 유틸리티

**파일**: `frontend/src/i18n/index.ts`

```typescript
import type { AppLanguage } from "@/app/mypage/types";

import en from "./locales/en.json";
import ko from "./locales/ko.json";
import ja from "./locales/ja.json";

// 모든 번역 데이터를 static import (빌드 시 번들에 포함)
const translations: Record<AppLanguage, Record<string, string>> = { en, ko, ja };

/**
 * 점(dot) 표기법으로 중첩 키에 접근
 * 예: getTranslation("en", "signup.nickname") → "Nickname"
 */
export function getTranslation(lang: AppLanguage, key: string): string {
  const dict = translations[lang] ?? translations.en;
  const value = dict[key];

  if (value !== undefined) return value;

  // fallback: 영어에서 찾기
  const fallback = translations.en[key];
  if (fallback !== undefined) {
    if (process.env.NODE_ENV === "development") {
      console.warn(`[i18n] Missing "${lang}" translation for key: "${key}"`);
    }
    return fallback;
  }

  // 키 자체를 반환 (개발 중 누락 발견용)
  if (process.env.NODE_ENV === "development") {
    console.warn(`[i18n] Missing translation key: "${key}"`);
  }
  return key;
}

/**
 * 브라우저 언어를 AppLanguage로 변환
 */
export function detectBrowserLanguage(): AppLanguage {
  if (typeof navigator === "undefined") return "en";

  const browserLang = navigator.language.toLowerCase();
  if (browserLang.startsWith("ko")) return "ko";
  if (browserLang.startsWith("ja")) return "ja";
  // if (browserLang.startsWith("zh")) return "zh";  // 추후 확장 시
  return "en";
}

export const LANGUAGE_STORAGE_KEY = "triver:language:v1";
export const SUPPORTED_LANGUAGES: { code: AppLanguage; label: string }[] = [
  { code: "en", label: "English (US)" },
  { code: "ko", label: "한국어" },
  { code: "ja", label: "日本語" },
];
```

### 4.3 LanguageContext.tsx — 전역 상태 관리

**파일**: `frontend/src/i18n/LanguageContext.tsx`

```tsx
"use client";

import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import type { AppLanguage } from "@/app/mypage/types";
import { getTranslation, detectBrowserLanguage, LANGUAGE_STORAGE_KEY } from "./index";

interface LanguageContextValue {
  language: AppLanguage;
  setLanguage: (lang: AppLanguage) => void;
  t: (key: string) => string;
}

export const LanguageContext = createContext<LanguageContextValue>({
  language: "en",
  setLanguage: () => {},
  t: (key) => key,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<AppLanguage>(() => {
    if (typeof window === "undefined") return "en";

    // 1순위: localStorage
    const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (stored === "en" || stored === "ko" || stored === "ja") return stored;

    // 3순위: 브라우저 언어 감지 (2순위 API는 useEffect에서 처리)
    return detectBrowserLanguage();
  });

  // 언어 변경 함수
  const setLanguage = useCallback((lang: AppLanguage) => {
    setLanguageState(lang);
    localStorage.setItem(LANGUAGE_STORAGE_KEY, lang);

    // 다른 컴포넌트에 알림 (기존 Sidebar 호환)
    window.dispatchEvent(new CustomEvent("triver:language"));
  }, []);

  // 다른 탭/컴포넌트에서 언어 변경 시 동기화
  useEffect(() => {
    const handleLanguageChange = () => {
      const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
      if (stored === "en" || stored === "ko" || stored === "ja") {
        setLanguageState(stored);
      }
    };
    window.addEventListener("triver:language", handleLanguageChange);
    return () => window.removeEventListener("triver:language", handleLanguageChange);
  }, []);

  // 번역 함수
  const t = useCallback(
    (key: string) => getTranslation(language, key),
    [language]
  );

  const value = useMemo(() => ({ language, setLanguage, t }), [language, setLanguage, t]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}
```

### 4.4 useTranslation.ts — 커스텀 훅

**파일**: `frontend/src/i18n/useTranslation.ts`

```typescript
"use client";

import { useContext } from "react";
import { LanguageContext } from "./LanguageContext";

/**
 * 사용법:
 * const { t, language, setLanguage } = useTranslation();
 * <label>{t("signup.nickname")}</label>
 */
export function useTranslation() {
  return useContext(LanguageContext);
}
```

### 4.5 layout.tsx에 Provider 적용

**파일**: `frontend/src/app/layout.tsx`

```tsx
import { LanguageProvider } from "@/i18n/LanguageContext";

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">  {/* 추후 Phase 7에서 동적 lang 처리 */}
      <body className={`${geistSans.variable} ${geistMono.variable} ${notoSerifKr.variable} antialiased bg-slate-50 text-slate-900`}>
        <GoogleOAuthProvider clientId={CLIENT_ID}>
          <LanguageProvider>           {/* 새로 추가 */}
            {children}
          </LanguageProvider>
        </GoogleOAuthProvider>
      </body>
    </html>
  );
}
```

---

## 5. Phase 3: 번역 파일(JSON) 작성

### 5.1 JSON 파일 구조

**플랫 키 구조** 사용 (중첩 구조 대비 단순하고 검색이 쉬움):

```
"카테고리.세부항목" → "번역 텍스트"
```

### 5.2 en.json (영어 — 기준 언어)

**파일**: `frontend/src/i18n/locales/en.json`

> 참고: 실제 파일에서는 모든 키를 포함해야 합니다.
> 아래는 카테고리별 주요 키만 나열합니다. 전체 목록은 [Section 11](#11-번역-텍스트-전체-목록)을 참조하세요.

```json
{
  "_meta.language": "English",

  "common.save": "Save",
  "common.cancel": "Cancel",
  "common.delete": "Delete",
  "common.confirm": "Confirm",
  "common.next": "Next",
  "common.back": "Back",
  "common.loading": "Loading...",
  "common.yes": "Yes",
  "common.no": "No",
  "common.seeAll": "See all",
  "common.noImage": "No Image",

  "signup.title": "One last step, {name}",
  "signup.subtitle": "Help us personalize your travel experience.",
  "signup.nickname": "Nickname",
  "signup.nicknamePlaceholder": "How should we call you?",
  "signup.gender": "Gender",
  "signup.genderMale": "Male",
  "signup.genderFemale": "Female",
  "signup.genderOther": "Other",
  "signup.country": "Country",
  "signup.countryPlaceholder": "Select Country",
  "signup.language": "Language",
  "signup.continueWithGoogle": "Continue with Google",
  "signup.continueToPersona": "Continue to Persona Setup",
  "signup.privacyAgree": "I agree to the collection and use of personal information for service provision.",
  "signup.privacyDetail": "Your data is secured and will never be shared without consent.",
  "signup.switchAccount": "Sign in with a different Google account",
  "signup.loginRequired": "Login required.",
  "signup.profileSaveFailed": "Failed to save profile.",
  "signup.signupFailed": "Sign up failed. Please try again.",

  "validation.nicknameSpecialChar": "Only Korean, English letters, and numbers are allowed.",
  "validation.nicknameLength": "Nickname must be within 10 Korean or 16 English/number characters.",

  "survey.questionOf": "Question {current} of {total}",
  "survey.previous": "Previous",
  "survey.allSet": "You're all set!",
  "survey.completeMessage": "Your signup and preference analysis are complete. Start exploring personalized travel recommendations.",
  "survey.signUp": "Sign Up",
  "survey.saveFailed": "Failed to save preferences.",
  "survey.sessionExpired": "Login required or session expired. Please log in again.",

  "survey.planPrefer.title": "Travel Schedule",
  "survey.planPrefer.description": "How do you like to plan your trip?",
  "survey.planPrefer.packed": "Packed Schedule",
  "survey.planPrefer.relaxed": "Relaxed Schedule",
  "survey.vibePrefer.title": "Travel Vibe",
  "survey.vibePrefer.description": "What kind of destination do you prefer?",
  "survey.vibePrefer.city": "Bustling City",
  "survey.vibePrefer.nature": "Peaceful Nature",
  "survey.placesPrefer.title": "Interests",
  "survey.placesPrefer.description": "What are you most excited to explore?",
  "survey.placesPrefer.food": "Local Food",
  "survey.placesPrefer.historical": "Historical Sites",
  "survey.placesPrefer.kculture": "K-culture",

  "sidebar.home": "Home",
  "sidebar.moments": "Moments",
  "sidebar.bookmark": "Bookmark",
  "sidebar.newChat": "+ New Chat",
  "sidebar.recentChats": "Recent Chats",
  "sidebar.profile": "Profile",
  "sidebar.signOut": "Sign out",
  "sidebar.deleteRoom": "Delete chat room",
  "sidebar.deleteRoomTitle": "Delete Chat Room",
  "sidebar.deleteRoomMessage": "Delete \"{title}\"? Chat history and recommended places will also be removed.",
  "sidebar.deleting": "Deleting...",
  "sidebar.deleteFailed": "Failed to delete chat room.",

  "explore.yourChoices": "Your Choices",
  "explore.personalized": "Personalized",
  "explore.curatedDesc": "Curated recommendations based on your preferences",
  "explore.localEats": "Local Eats",
  "explore.mustVisit": "Must-Visit Spots",
  "explore.uniqueExperiences": "Unique Experiences",
  "explore.hotPlaces": "Hot Places",
  "explore.trendingDesc": "Trending neighborhoods",
  "explore.contents": "Contents",
  "explore.events": "Events & Exhibitions",
  "explore.popupStore": "POPUP STORE",
  "explore.ongoing": "Ongoing",
  "explore.noPopupInfo": "No popup store information available.",
  "explore.newTripPlan": "New trip plan",

  "bookmark.title": "Bookmarks",
  "bookmark.subtitle": "Saved Chats & Spots",
  "bookmark.sessions": "Sessions",
  "bookmark.places": "Places",
  "bookmark.deleteChat": "Delete Chat",
  "bookmark.deletePlace": "Delete Place",
  "bookmark.deleteSelected": "Delete Selected",
  "bookmark.planTripWithSelection": "Plan Trip with Selection",
  "bookmark.creatingRoom": "Creating Room...",
  "bookmark.confirmDeleteSession": "Are you sure you want to delete this selected session?",
  "bookmark.confirmDeleteSessions": "Are you sure you want to delete these selected sessions?",
  "bookmark.confirmDeletePlace": "Are you sure you want to delete this selected place?",
  "bookmark.confirmDeletePlaces": "Are you sure you want to delete these selected places?",
  "bookmark.loadFailed": "Failed to load bookmarks.",
  "bookmark.noSessions": "No bookmarked sessions.",
  "bookmark.noMessages": "No chat history.",
  "bookmark.noPlaces": "No bookmarked places.",
  "bookmark.deleteFailed": "Failed to delete.",
  "bookmark.createRoomFailed": "Failed to create new chat room.",

  "moments.title": "Moments",
  "moments.subtitle": "Captured places & memories",
  "moments.searchPlaceholder": "Search diary",
  "moments.addMemory": "Add Memory",
  "moments.startFirstMemory": "Start Your First Memory",
  "moments.startFirstMemoryDesc": "Capture a moment with a photo and a note.",
  "moments.create": "Create",
  "moments.unsavedDiary": "Unsaved Diary",
  "moments.unsavedWarning": "If you close now, your changes will not be saved. Press Save to keep them.",
  "moments.addCoverPhoto": "Add a cover photo",
  "moments.changePhoto": "Change Photo",
  "moments.noCoverPhoto": "No cover photo",
  "moments.titlePlaceholder": "Title your diary",
  "moments.noTitle": "No title",
  "moments.addLocation": "Add location",
  "moments.changeLocation": "Change location",
  "moments.linkedPlace": "Linked place",
  "moments.diary": "Diary",
  "moments.edit": "Edit",
  "moments.contentPlaceholder": "Write about your journey, emotions, and memorable scenes.",
  "moments.noContent": "No content",
  "moments.useThisLocation": "Use this location",
  "moments.locationPlaceholder": "Seoul City Hall, Seongsu, Jeju Airport",
  "moments.requiredFields": "Title, date, and content are required.",
  "moments.saveFailed": "Failed to save diary.",
  "moments.loadListFailed": "Failed to load diary list.",
  "moments.loadFailed": "Failed to load diary.",
  "moments.loadDetailFailed": "Failed to load diary details.",
  "moments.imageReadFailed": "Failed to read image.",

  "mypage.reservation": "Reservation",
  "mypage.savedReservation": "Saved Reservation",
  "mypage.reservationId": "Reservation ID",
  "mypage.category": "Category",
  "mypage.createdAt": "Created At",

  "incompleteSignup.profileNeeded": "Profile Information Required",
  "incompleteSignup.surveyNeeded": "Preference Survey Required",
  "incompleteSignup.profileDesc": "Please enter your basic profile information for Triver's personalized recommendations.",
  "incompleteSignup.surveyDesc": "Complete 3 short questions for more accurate travel recommendations.",
  "incompleteSignup.goToProfile": "Go to Profile Setup",
  "incompleteSignup.goToSurvey": "Go to Survey",
  "incompleteSignup.later": "Maybe Later",
  "incompleteSignup.switchAccount": "Sign in with a different Google account",

  "landing.heroTitle": "Discover Seoul with AI",
  "landing.heroSubtitle": "Travel smarter, not harder",
  "landing.heroDesc": "Experience hyper-personalized travel planning.",
  "landing.heroDesc2": "Let our AI curate your perfect Seoul itinerary in seconds.",
  "landing.searchPlaceholder": "Where is your next destination?",
  "landing.start": "Start",
  "landing.ctaTitle": "Your journey begins here.",
  "landing.ctaDesc": "Start planning your dream trip to Seoul today with our AI-powered travel assistant. No hidden fees, just pure exploration.",
  "landing.ctaButton": "Start for Free",
  "landing.features": "Features",
  "landing.destinations": "Destinations",
  "landing.reviews": "Reviews",
  "landing.getStarted": "Get Started"
}
```

### 5.3 ko.json (한국어)

```json
{
  "_meta.language": "한국어",

  "common.save": "저장",
  "common.cancel": "취소",
  "common.delete": "삭제",
  "common.confirm": "확인",
  "common.next": "다음",
  "common.back": "뒤로",
  "common.loading": "로딩 중...",
  "common.yes": "예",
  "common.no": "아니오",
  "common.seeAll": "모두 보기",
  "common.noImage": "이미지 없음",

  "signup.title": "마지막 단계입니다, {name}",
  "signup.subtitle": "맞춤형 여행 경험을 위해 정보를 입력해주세요.",
  "signup.nickname": "닉네임",
  "signup.nicknamePlaceholder": "어떻게 불러드릴까요?",
  "signup.gender": "성별",
  "signup.genderMale": "남성",
  "signup.genderFemale": "여성",
  "signup.genderOther": "기타",
  "signup.country": "국가",
  "signup.countryPlaceholder": "국가 선택",
  "signup.language": "언어",
  "signup.continueWithGoogle": "Google로 계속하기",
  "signup.continueToPersona": "취향 분석으로 계속하기",
  "signup.privacyAgree": "서비스 제공을 위한 개인정보 수집 및 이용에 동의합니다.",
  "signup.privacyDetail": "귀하의 데이터는 안전하게 보호되며, 동의 없이 공유되지 않습니다.",
  "signup.switchAccount": "다른 구글 계정으로 로그인하기",
  "signup.loginRequired": "로그인이 필요합니다.",
  "signup.profileSaveFailed": "프로필 저장에 실패했습니다.",
  "signup.signupFailed": "회원가입에 실패했습니다. 다시 시도해주세요.",

  "validation.nicknameSpecialChar": "닉네임은 한글, 영문, 숫자만 입력 가능합니다.",
  "validation.nicknameLength": "닉네임은 한글 10자, 영문/숫자 16자 이내로 입력해주세요.",

  "survey.questionOf": "{total}개 중 {current}번째 질문",
  "survey.previous": "이전",
  "survey.allSet": "모든 준비가 완료되었습니다!",
  "survey.completeMessage": "회원가입 및 취향 분석이 완료되었습니다. 이제 맞춤형 여행 추천을 시작해 보세요.",
  "survey.signUp": "시작하기",
  "survey.saveFailed": "선호도 저장에 실패했습니다.",
  "survey.sessionExpired": "로그인이 필요하거나 세션이 만료되었습니다. 다시 로그인해주세요.",

  "survey.planPrefer.title": "여행 일정",
  "survey.planPrefer.description": "여행 일정을 어떻게 계획하시나요?",
  "survey.planPrefer.packed": "빽빽한 일정",
  "survey.planPrefer.relaxed": "느슨한 일정",
  "survey.vibePrefer.title": "여행 분위기",
  "survey.vibePrefer.description": "어떤 여행지를 선호하시나요?",
  "survey.vibePrefer.city": "붐비는 도시",
  "survey.vibePrefer.nature": "한적한 자연",
  "survey.placesPrefer.title": "관심사",
  "survey.placesPrefer.description": "가장 탐험하고 싶은 것은?",
  "survey.placesPrefer.food": "맛집",
  "survey.placesPrefer.historical": "역사적 명소",
  "survey.placesPrefer.kculture": "K-culture"
}
```

> **참고**: `ja.json`도 동일한 키 구조로 일본어 번역을 작성합니다. 지면 관계상 생략하지만, 영어 JSON의 모든 키에 대해 일본어 번역을 제공해야 합니다.

---

## 6. Phase 4: 회원가입 흐름 연동

### 6.1 SignUpProfilePage 언어 드롭다운 연결

**파일**: `frontend/src/app/signup/profile/SignUpProfilePage.tsx`

**변경 사항**:

1. **state 추가**: `const [selectedLanguage, setSelectedLanguage] = useState<AppLanguage>("en");`
2. **useTranslation 훅 사용**: `const { t, setLanguage } = useTranslation();`
3. **드롭다운 onChange 연결**:

```tsx
// 변경 전 (현재 코드 — 190~194행)
<select className="w-full bg-white border ...">
    <option value="en">English (US)</option>
    <option value="ko">Korean</option>
    <option value="ja">Japanese</option>
</select>

// 변경 후
<select
    value={selectedLanguage}
    onChange={(e) => {
        const lang = e.target.value as AppLanguage;
        setSelectedLanguage(lang);
        setLanguage(lang);  // Context 업데이트 → 즉시 UI 반영
    }}
    className="w-full bg-white border ..."
>
    {SUPPORTED_LANGUAGES.map((l) => (
        <option key={l.code} value={l.code}>{l.label}</option>
    ))}
</select>
```

4. **프로필 저장 시 language 포함**:

```tsx
// 변경 전 (현재 코드 — 55~58행)
await updateCurrentUser({
    nickname,
    gender: genderValue,
    country_code: countryCode,
});

// 변경 후
await updateCurrentUser({
    nickname,
    gender: genderValue,
    country_code: countryCode,
    language: selectedLanguage,  // 언어 설정 서버 저장
});
```

5. **하드코딩 텍스트를 t() 호출로 교체**:

```tsx
// 변경 전
<h1>One last step, {userInfo.name.split(" ")[0]}</h1>

// 변경 후
<h1>{t("signup.title").replace("{name}", userInfo.name.split(" ")[0])}</h1>
```

### 6.2 validation.ts 다국어 처리

**파일**: `frontend/src/app/signup/profile/utils/validation.ts`

현재 에러 메시지가 한국어로 하드코딩되어 있습니다. 두 가지 접근법이 있습니다:

**방법 A (추천): 에러 코드를 반환하고, 컴포넌트에서 번역**

```typescript
// validation.ts — 에러 키만 반환
export function getNicknameValidationError(value: string): string {
  const hasSpecialChar = /[^ㄱ-ㅎㅏ-ㅣ가-힣a-zA-Z0-9]/.test(value);
  let length = 0;
  for (let i = 0; i < value.length; i += 1) {
    if (/[ㄱ-ㅎ|ㅏ-ㅣ|가-힣]/.test(value[i])) {
      length += 1.6;
    } else {
      length += 1;
    }
  }
  if (hasSpecialChar) return "validation.nicknameSpecialChar";   // 키 반환
  if (length > 16) return "validation.nicknameLength";            // 키 반환
  return "";
}

// SignUpProfilePage.tsx — 컴포넌트에서 번역
{nicknameError && (
    <p className="text-xs text-red-500 mt-1 pl-1">{t(nicknameError)}</p>
)}
```

### 6.3 초기 언어 자동 감지

회원가입 전(Google 로그인 화면)에서는 LanguageProvider가 `detectBrowserLanguage()`로 초기 언어를 추정합니다. 일본어 브라우저면 일본어, 한국어 브라우저면 한국어, 그 외 영어로 시작합니다.

### 6.4 로그인 후 언어 복원

사용자가 다시 로그인할 때, `GET /api/users/me` 응답에서 `language` 필드를 읽어 Context에 반영합니다.

**적용 위치**: 로그인 성공 후 라우팅하는 곳 (예: `SignUpPage.tsx`의 Google 콜백 처리)

```typescript
// 로그인 성공 후
const user = await fetchCurrentUser();
if (user.language) {
    setLanguage(user.language as AppLanguage);
}
```

---

## 7. Phase 5: 페이지별 적용

### 7.1 적용 패턴

모든 페이지에서 동일한 패턴으로 적용합니다:

```tsx
// 1. 훅 임포트
import { useTranslation } from "@/i18n/useTranslation";

// 2. 컴포넌트 내에서 사용
const { t } = useTranslation();

// 3. 하드코딩 텍스트를 t() 호출로 교체
<label>{t("signup.nickname")}</label>
```

### 7.2 페이지별 변경 파일 목록

#### 우선순위 1: 회원가입/인증 흐름

| 파일 | 변경 내용 |
|------|---------|
| `app/signup/SignUpPage.tsx` | "Continue with Google", alert 메시지 |
| `app/signup/profile/SignUpProfilePage.tsx` | 모든 라벨, 플레이스홀더, 에러 메시지, 버튼 텍스트 |
| `app/signup/profile/utils/validation.ts` | 에러 메시지 → 에러 키 반환으로 변경 |
| `app/survey/SurveyPage.tsx` | "Question X of Y", 버튼, 완료 메시지 |
| `app/survey/constants.ts` | 질문 메타데이터 (title, description) |

#### 우선순위 2: 메인 네비게이션

| 파일 | 변경 내용 |
|------|---------|
| `components/navigation/Sidebar.tsx` | 기존 `SIDEBAR_I18N` 제거 → `useTranslation` 사용으로 전환, 삭제 모달 텍스트 |

#### 우선순위 3: 주요 기능 페이지

| 파일 | 변경 내용 |
|------|---------|
| `app/explore/ExplorePage.tsx` | 섹션 제목, 설명, 에러 메시지 |
| `app/bookmark/BookmarkPage.tsx` | 탭 이름, 확인 다이얼로그, 에러 메시지 |
| `app/moments/MomentsPage.tsx` | 에러 메시지, 모달 텍스트 |
| `app/moments/components/MomentsHeader.tsx` | 페이지 제목, 검색 플레이스홀더 |
| `app/moments/components/DiaryEditorModal.tsx` | 폼 라벨, 플레이스홀더, 버튼 |
| `app/moments/components/EmptyDiaryState.tsx` | 안내 텍스트, 버튼 |
| `app/moments/components/DiaryLocationPickerModal.tsx` | 플레이스홀더, 버튼 |
| `app/mypage/MyPagePage.tsx` | 예약 관련 라벨 |

#### 우선순위 4: 랜딩페이지 & 공통

| 파일 | 변경 내용 |
|------|---------|
| `app/components/Hero.tsx` | 타이틀, 서브타이틀, CTA |
| `app/components/Features.tsx` | 섹션 제목, 기능 설명 (한국어 긴 텍스트 포함) |
| `app/components/Destinations.tsx` | 섹션 제목, 탭 이름 |
| `app/components/ReviewSection.tsx` | 섹션 제목, 서브타이틀 |
| `app/components/CTA.tsx` | 타이틀, 설명, 버튼 |
| `app/components/Header.tsx` | 네비게이션 메뉴 |
| `app/components/IncompleteSignupModal.tsx` | 모든 안내 텍스트 |

### 7.3 Sidebar 마이그레이션 상세

Sidebar는 이미 자체 i18n을 갖고 있으므로, 새 시스템으로 전환합니다:

```tsx
// 변경 전
const SIDEBAR_I18N = { ... };  // 컴포넌트 내부 딕셔너리
const dict = SIDEBAR_I18N[language] ?? SIDEBAR_I18N.en;
<span>{dict.home}</span>

// 변경 후
import { useTranslation } from "@/i18n/useTranslation";
const { t } = useTranslation();
<span>{t("sidebar.home")}</span>

// 제거 대상: SIDEBAR_I18N 상수, LANGUAGE_STORAGE_KEY(Sidebar 내부 것), language state
// 유지: LanguageContext가 동일한 localStorage 키를 사용하므로 기존 저장값 호환됨
```

---

## 8. Phase 6: 설문조사(Survey) 다국어

### 8.1 현재 문제

설문조사 선택지가 백엔드(`prefer.py`)에 한국어로 하드코딩되어 있습니다:

```python
SURVEY_DATA = [
    {"type": "plan_prefer", "value": "빽빽한 일정"},
    {"type": "plan_prefer", "value": "느슨한 일정"},
    ...
]
```

이 값은 DB의 `user.plan_prefer` 컬럼에 직접 저장되며, AI 에이전트의 프롬프트에서도 참조됩니다.

### 8.2 추천 접근법: 내부 키 + 프론트엔드 번역

**백엔드 변경**: 선택지의 value를 **언어 독립적인 키**로 변경

```python
# backend/app/api/prefer.py
SURVEY_DATA = [
    {"type": "plan_prefer", "value": "packed_schedule"},
    {"type": "plan_prefer", "value": "relaxed_schedule"},
    {"type": "vibe_prefer", "value": "bustling_city"},
    {"type": "vibe_prefer", "value": "peaceful_nature"},
    {"type": "places_prefer", "value": "local_food"},
    {"type": "places_prefer", "value": "historical_sites"},
    {"type": "places_prefer", "value": "k_culture"},
]
```

**프론트엔드에서 표시할 때 번역**:

```tsx
// SurveyPage.tsx
const displayValue = t(`survey.${option.type}.${option.value}`) || option.value;
```

번역 JSON에 매핑 추가:

```json
{
  "survey.plan_prefer.packed_schedule": "Packed Schedule",
  "survey.plan_prefer.relaxed_schedule": "Relaxed Schedule",
  "survey.vibe_prefer.bustling_city": "Bustling City",
  "survey.vibe_prefer.peaceful_nature": "Peaceful Nature",
  "survey.places_prefer.local_food": "Local Food",
  "survey.places_prefer.historical_sites": "Historical Sites",
  "survey.places_prefer.k_culture": "K-culture"
}
```

**질문 메타데이터도 동일하게**:

```tsx
// 변경 전 (constants.ts)
export const QUESTION_METADATA = {
  plan_prefer: { title: "Travel Schedule", description: "How do you like to plan your trip?" },
  ...
};

// 변경 후 — constants.ts에서 title/description 제거하고 번역 키 사용
// SurveyPage.tsx에서:
const title = t(`survey.${currentQuestion.id}.title`);
const description = t(`survey.${currentQuestion.id}.description`);
```

### 8.3 DB 마이그레이션 고려사항

기존 사용자의 `plan_prefer` 값이 `"빽빽한 일정"` 같은 한국어로 저장되어 있습니다.

**마이그레이션 SQL**:

```sql
UPDATE users SET plan_prefer = 'packed_schedule' WHERE plan_prefer = '빽빽한 일정';
UPDATE users SET plan_prefer = 'relaxed_schedule' WHERE plan_prefer = '느슨한 일정';
UPDATE users SET vibe_prefer = 'bustling_city' WHERE vibe_prefer = '붐비는 도시';
UPDATE users SET vibe_prefer = 'peaceful_nature' WHERE vibe_prefer = '한적한 자연';
UPDATE users SET places_prefer = 'local_food' WHERE places_prefer = '맛집';
UPDATE users SET places_prefer = 'historical_sites' WHERE places_prefer = '역사적 명소';
UPDATE users SET places_prefer = 'k_culture' WHERE places_prefer = 'K-culture';
```

### 8.4 AI 에이전트 프롬프트 수정

`User.build_preferences()` 메서드가 선호도를 텍스트로 변환합니다. 키 기반으로 변경 후, 영어 또는 사용자 언어로 변환하는 매핑을 추가합니다:

```python
# backend/app/models/user.py
PREFER_DISPLAY = {
    "packed_schedule": "Packed Schedule",
    "relaxed_schedule": "Relaxed Schedule",
    "bustling_city": "Bustling City",
    "peaceful_nature": "Peaceful Nature",
    "local_food": "Local Food",
    "historical_sites": "Historical Sites",
    "k_culture": "K-culture",
}

def build_preferences(self) -> str:
    lines = []
    if self.plan_prefer:
        display = PREFER_DISPLAY.get(self.plan_prefer, self.plan_prefer)
        lines.append(f"- Travel Schedule Style: **{display}**")
    # ... 나머지 동일 패턴 ...
```

### 8.5 IMAGE_MAP 수정

```typescript
// 변경 전 (한국어 키)
export const IMAGE_MAP: Record<string, string> = {
  "빽빽한 일정": "/image/planning.jpg",
  ...
};

// 변경 후 (영어 키)
export const IMAGE_MAP: Record<string, string> = {
  "packed_schedule": "/image/planning.jpg",
  "relaxed_schedule": "/image/noplan.png",
  "bustling_city": "/image/crowded.jpg",
  "peaceful_nature": "/image/lonely.jpg",
  "local_food": "/image/kfood.jpg",
  "historical_sites": "/image/khistorical.jpg",
  "k_culture": "/image/kculture.png",
};
```

---

## 9. Phase 7: 폰트 및 날짜 포맷

### 9.1 폰트 설정

현재 `layout.tsx`에 `Geist`(라틴), `Noto Serif KR`(한국어 세리프)이 있습니다. 다국어 지원을 위해 `Noto Sans` 계열을 추가합니다.

**파일**: `frontend/src/app/layout.tsx`

```tsx
import { Geist, Geist_Mono } from "next/font/google";
import { Noto_Sans_JP } from "next/font/google";  // 추가
import { Noto_Sans_KR } from "next/font/google";  // 기존 Noto_Serif_KR → Noto_Sans_KR로 변경 또는 추가

const notoSansKR = Noto_Sans_KR({
  variable: "--font-noto-sans-kr",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const notoSansJP = Noto_Sans_JP({
  variable: "--font-noto-sans-jp",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});
```

CSS에서 폰트 스택 설정:

```css
/* globals.css */
body {
  font-family: var(--font-geist-sans), var(--font-noto-sans-kr), var(--font-noto-sans-jp), sans-serif;
}
```

> Next.js의 `next/font`는 자동으로 사용하는 글자만 서브셋으로 로딩하므로 성능 영향이 최소화됩니다.

### 9.2 HTML lang 속성 동적 설정

`layout.tsx`는 서버 컴포넌트이므로 직접 Context를 사용할 수 없습니다. 클라이언트 컴포넌트로 `<html>` 태그의 `lang` 속성을 동적으로 업데이트합니다.

**LanguageContext.tsx에 추가**:

```tsx
// LanguageProvider 내부 useEffect에 추가
useEffect(() => {
  document.documentElement.lang = language;
}, [language]);
```

### 9.3 날짜/시간 포맷

`Intl.DateTimeFormat`을 활용하여 언어별 날짜 형식을 자동 적용합니다.

**유틸리티 함수** (i18n/index.ts에 추가):

```typescript
export function formatDate(lang: AppLanguage, date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return new Intl.DateTimeFormat(lang, {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(d);
}

// 결과 예시:
// en → "March 12, 2026"
// ko → "2026년 3월 12일"
// ja → "2026年3月12日"
```

---

## 10. Phase 8: AI 챗봇 응답 언어

사용자의 `language` 설정을 AI 에이전트의 시스템 프롬프트에 전달하여, AI가 해당 언어로 응답하도록 합니다.

### 10.1 백엔드 프롬프트에 언어 주입

AI 에이전트의 시스템 프롬프트를 구성하는 부분에서 사용자의 언어 설정을 포함합니다:

```python
# 에이전트 프롬프트 구성 시
user_language = current_user.language or "en"

LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in English.",
    "ko": "한국어로 응답해주세요.",
    "ja": "日本語で回答してください。",
}

system_prompt = f"""
...기존 프롬프트...

{LANGUAGE_INSTRUCTIONS.get(user_language, LANGUAGE_INSTRUCTIONS["en"])}
"""
```

### 10.2 스트리밍 응답 시 언어 전달

`sendChatMessageStream` API 호출 시 헤더로 언어 정보를 전달할 수 있습니다:

```typescript
// 프론트엔드에서 스트리밍 요청 시
headers: {
    'Content-Type': 'application/json',
    'Accept-Language': language,  // "en", "ko", "ja"
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
}
```

또는 서버에서 `current_user.language`를 직접 참조하는 방법이 더 안정적입니다.

---

## 11. 번역 텍스트 전체 목록

아래는 번역이 필요한 **모든 텍스트**의 목록입니다. en.json을 기준으로 작성되었으며, 각 지원 언어(ko, ja)에 대해 동일한 키로 번역을 제공해야 합니다.

### 11.1 공통 (common)

| 키 | 영어 | 한국어 | 일본어 |
|----|------|-------|-------|
| common.save | Save | 저장 | 保存 |
| common.cancel | Cancel | 취소 | キャンセル |
| common.delete | Delete | 삭제 | 削除 |
| common.confirm | Confirm | 확인 | 確認 |
| common.next | Next | 다음 | 次へ |
| common.back | Back | 뒤로 | 戻る |
| common.loading | Loading... | 로딩 중... | 読み込み中... |
| common.yes | Yes | 예 | はい |
| common.no | No | 아니오 | いいえ |
| common.seeAll | See all | 모두 보기 | すべて見る |
| common.noImage | No Image | 이미지 없음 | 画像なし |

### 11.2 회원가입 (signup)

| 키 | 영어 | 출처 파일 |
|----|------|---------|
| signup.title | One last step, {name} | SignUpProfilePage.tsx:92 |
| signup.subtitle | Help us personalize your travel experience. | SignUpProfilePage.tsx:95 |
| signup.nickname | Nickname | SignUpProfilePage.tsx:123 |
| signup.nicknamePlaceholder | How should we call you? | SignUpProfilePage.tsx:129 |
| signup.gender | Gender | SignUpProfilePage.tsx:143 |
| signup.genderMale | Male | SignUpProfilePage.tsx:145 |
| signup.genderFemale | Female | SignUpProfilePage.tsx:145 |
| signup.genderOther | Other | SignUpProfilePage.tsx:145 |
| signup.country | Country | SignUpProfilePage.tsx:164 |
| signup.countryPlaceholder | Select Country | SignUpProfilePage.tsx:171 |
| signup.language | Language | SignUpProfilePage.tsx:187 |
| signup.fullName | Full Name | SignUpProfilePage.tsx:103 |
| signup.emailAddress | Email Address | SignUpProfilePage.tsx:109 |
| signup.continueToPersona | Continue to Persona Setup | SignUpProfilePage.tsx:227 |
| signup.privacyAgree | I agree to the collection... | SignUpProfilePage.tsx:213 |
| signup.privacyDetail | Your data is secured... | SignUpProfilePage.tsx:214 |
| signup.switchAccount | 다른 구글 계정으로 로그인하기 | SignUpProfilePage.tsx:237 |
| signup.loginRequired | 로그인이 필요합니다. | SignUpProfilePage.tsx:49 |
| signup.profileSaveFailed | 프로필 저장에 실패했습니다. | SignUpProfilePage.tsx:66 |
| signup.continueWithGoogle | Continue with Google | SignUpPage.tsx |
| signup.signupFailed | Sign up failed. Please try again. | SignUpPage.tsx |

### 11.3 유효성 검사 (validation)

| 키 | 영어 | 출처 파일 |
|----|------|---------|
| validation.nicknameSpecialChar | Only Korean, English, and numbers allowed. | validation.ts:16 |
| validation.nicknameLength | Max 10 Korean or 16 English/number characters. | validation.ts:20 |

### 11.4 설문조사 (survey)

| 키 | 영어 | 출처 파일 |
|----|------|---------|
| survey.questionOf | Question {current} of {total} | SurveyPage.tsx:189 |
| survey.previous | Previous | SurveyPage.tsx:205 |
| survey.allSet | You're all set! | SurveyPage.tsx:161 |
| survey.completeMessage | Your signup and preference analysis... | SurveyPage.tsx:164 |
| survey.signUp | Sign Up | SurveyPage.tsx:173 |
| survey.saveFailed | Failed to save preferences. | SurveyPage.tsx:76 |
| survey.sessionExpired | Login required or session expired... | SurveyPage.tsx:53 |
| survey.planPrefer.title | Travel Schedule | constants.ts:2 |
| survey.planPrefer.description | How do you like to plan your trip? | constants.ts:2 |
| survey.vibePrefer.title | Travel Vibe | constants.ts:3 |
| survey.vibePrefer.description | What kind of destination do you prefer? | constants.ts:3 |
| survey.placesPrefer.title | Interests | constants.ts:4 |
| survey.placesPrefer.description | What are you most excited to explore? | constants.ts:4 |

### 11.5 사이드바 (sidebar)

| 키 | 영어 | 출처 |
|----|------|------|
| sidebar.home | Home | Sidebar.tsx (기존 SIDEBAR_I18N) |
| sidebar.moments | Moments | |
| sidebar.bookmark | Bookmark | |
| sidebar.newChat | + New Chat | |
| sidebar.recentChats | Recent Chats | |
| sidebar.profile | Profile | |
| sidebar.signOut | Sign out | |
| sidebar.deleteRoomTitle | 채팅방 삭제 | Sidebar.tsx:593 |
| sidebar.deleteRoomMessage | "{title}"을 삭제할까요?... | Sidebar.tsx:595 |
| sidebar.deleteRoomCancel | 취소 | Sidebar.tsx:606 |
| sidebar.deleting | 삭제 중... | Sidebar.tsx:614 |
| sidebar.deleteFailed | 채팅방 삭제에 실패했습니다. | Sidebar.tsx:318 |

### 11.6 탐색, 북마크, 모먼츠, 마이페이지

(en.json의 해당 섹션 참조 — 위 Phase 3에서 이미 전체 키 목록 제공)

### 11.7 랜딩페이지 & 공통 모달

(en.json의 해당 섹션 참조)

---

## 12. 구현 순서 및 체크리스트

### 12.1 권장 구현 순서

```
Week 1: 인프라
├── Day 1-2: Phase 1 (백엔드 language 필드 + 마이그레이션)
├── Day 3-4: Phase 2 (프론트엔드 i18n 인프라)
└── Day 5:   Phase 3 (번역 JSON 기본 구조 + 공통 키)

Week 2: 핵심 흐름
├── Day 1-2: Phase 4 (회원가입 흐름 연동)
├── Day 3:   Phase 6 (설문조사 다국어 + DB 마이그레이션)
├── Day 4:   Phase 5 - 사이드바 마이그레이션
└── Day 5:   Phase 7 (폰트 + 날짜 포맷)

Week 3: 나머지 페이지
├── Day 1: Explore 페이지
├── Day 2: Bookmark 페이지
├── Day 3: Moments 페이지 + 하위 컴포넌트
├── Day 4: MyPage + 공통 모달 + 랜딩페이지
└── Day 5: Phase 8 (AI 챗봇 응답 언어) + 전체 QA

Week 4: 번역 완성 + QA
├── Day 1-2: 일본어 번역 검수
├── Day 3: 전체 흐름 E2E 테스트 (각 언어로)
├── Day 4: 엣지 케이스 처리 (긴 텍스트 overflow, RTL 등)
└── Day 5: 최종 리뷰 + 배포
```

### 12.2 체크리스트

#### 백엔드
- [ ] `LanguageType` enum 추가 (`enums.py`)
- [ ] `User.language` 컬럼 추가 (`user.py`)
- [ ] `UserBase`, `UserUpdate` 스키마에 `language` 추가 (`schemas/user.py`)
- [ ] Alembic 마이그레이션 생성 및 실행
- [ ] 설문조사 선택지 한국어 → 키 기반 변경 (`prefer.py`)
- [ ] 기존 사용자 설문 데이터 마이그레이션 SQL
- [ ] `User.build_preferences()` 영어 키 기반으로 수정
- [ ] AI 에이전트 프롬프트에 언어 주입

#### 프론트엔드 — 인프라
- [ ] `i18n/` 디렉토리 생성
- [ ] `en.json`, `ko.json`, `ja.json` 번역 파일 작성
- [ ] `LanguageContext.tsx` 작성
- [ ] `useTranslation.ts` 작성
- [ ] `index.ts` 유틸리티 작성
- [ ] `layout.tsx`에 `LanguageProvider` 적용
- [ ] `api.ts`의 `UserProfile` 인터페이스에 `language` 추가

#### 프론트엔드 — 페이지 적용
- [ ] `SignUpPage.tsx` — t() 적용
- [ ] `SignUpProfilePage.tsx` — 언어 드롭다운 연결 + t() 적용
- [ ] `validation.ts` — 에러 키 반환 방식으로 변경
- [ ] `SurveyPage.tsx` — t() 적용
- [ ] `constants.ts` — 질문 메타데이터 + IMAGE_MAP 키 변경
- [ ] `Sidebar.tsx` — SIDEBAR_I18N 제거, useTranslation으로 전환
- [ ] `ExplorePage.tsx` — t() 적용
- [ ] `BookmarkPage.tsx` — t() 적용
- [ ] `MomentsPage.tsx` + 하위 컴포넌트 — t() 적용
- [ ] `MyPagePage.tsx` — t() 적용
- [ ] `IncompleteSignupModal.tsx` — t() 적용
- [ ] 랜딩페이지 컴포넌트 (Hero, Features, CTA, Header 등) — t() 적용

#### 폰트 & 포맷
- [ ] Noto Sans KR, Noto Sans JP 폰트 추가
- [ ] CSS 폰트 스택 설정
- [ ] `document.documentElement.lang` 동적 업데이트
- [ ] 날짜 포맷 유틸리티 `formatDate()` 추가

#### QA
- [ ] 각 언어로 전체 회원가입 플로우 테스트
- [ ] 언어 전환 시 즉시 UI 반영 확인
- [ ] 브라우저 언어 자동 감지 확인
- [ ] 로그인 후 서버 저장된 언어 복원 확인
- [ ] AI 챗봇이 설정 언어로 응답하는지 확인
- [ ] 긴 번역 텍스트의 UI 오버플로우 확인
- [ ] 번역 키 누락 시 개발 콘솔 경고 확인
