// src/i18n/index.ts — 번역 유틸리티

import en from "./locales/en.json";
import ko from "./locales/ko.json";
import ja from "./locales/ja.json";
import zh from "./locales/zh.json";

export type SupportedLanguage = "en" | "ko" | "ja" | "zh";

export const LANGUAGE_STORAGE_KEY = "triver:language:v1";
export const LANGUAGE_EVENT = "triver:language";

export const SUPPORTED_LANGUAGES: { code: SupportedLanguage; label: string }[] = [
  { code: "en", label: "English" },
  { code: "ko", label: "한국어" },
  { code: "ja", label: "日本語" },
  { code: "zh", label: "中文" },
];

const dictionaries: Record<SupportedLanguage, Record<string, string>> = {
  en,
  ko,
  ja,
  zh,
};

/**
 * 번역 키로 현재 언어의 텍스트를 가져옵니다.
 * 해당 언어에 없으면 영어 → 키 자체 순서로 fallback합니다.
 */
export function getTranslation(
  lang: SupportedLanguage,
  key: string,
  params?: Record<string, string | number>,
): string {
  let text = dictionaries[lang]?.[key] ?? dictionaries.en[key] ?? key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      text = text.replaceAll(`{${k}}`, String(v));
    }
  }
  return text;
}

/**
 * 브라우저 설정 언어를 감지해서 지원 언어 중 하나를 반환합니다.
 */
export function detectBrowserLanguage(): SupportedLanguage {
  if (typeof navigator === "undefined") return "en";

  const browserLang = navigator.language?.slice(0, 2).toLowerCase();
  const supported = SUPPORTED_LANGUAGES.map((l) => l.code);

  if (supported.includes(browserLang as SupportedLanguage)) {
    return browserLang as SupportedLanguage;
  }

  return "en";
}
