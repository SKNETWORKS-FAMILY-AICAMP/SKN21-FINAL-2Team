import { LANGUAGE_COOKIE_KEY } from "./constants";

const MAX_AGE_SEC = 365 * 24 * 60 * 60;

/** triver_lang — layout SSR·i18n과 동일한 속성으로 설정 */
export function setTriverLangCookie(lang: string): void {
  if (typeof document === "undefined") return;
  document.cookie = `${LANGUAGE_COOKIE_KEY}=${lang};path=/;max-age=${MAX_AGE_SEC};samesite=lax`;
}

export const SUPPORTED_UI_LANGUAGE_CODES = ["en", "ko", "ja", "zh"] as const;

export function isSupportedUiLanguage(lang: unknown): lang is (typeof SUPPORTED_UI_LANGUAGE_CODES)[number] {
  return typeof lang === "string" && (SUPPORTED_UI_LANGUAGE_CODES as readonly string[]).includes(lang);
}
