// 서버/클라이언트 양쪽에서 사용하는 i18n 상수
// "use client" 지시문이 없어서 서버 컴포넌트(layout.tsx)에서도 import 가능

export const LANGUAGE_STORAGE_KEY = "triver:language:v1";
export const LANGUAGE_COOKIE_KEY = "triver_lang";

export type SupportedLanguage = "en" | "ko" | "ja" | "zh";

export const SUPPORTED_LANGUAGES: { code: SupportedLanguage; label: string }[] = [
  { code: "en", label: "English" },
  { code: "ko", label: "한국어" },
  { code: "ja", label: "日本語" },
  { code: "zh", label: "中文" },
];
