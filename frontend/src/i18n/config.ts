"use client";

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import en from "./locales/en.json";
import ko from "./locales/ko.json";
import ja from "./locales/ja.json";
import zh from "./locales/zh.json";

// re-export for client components (원본은 constants.ts)
export { LANGUAGE_STORAGE_KEY, LANGUAGE_COOKIE_KEY, SUPPORTED_LANGUAGES } from "./constants";
export type { SupportedLanguage } from "./constants";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      ko: { translation: ko },
      ja: { translation: ja },
      zh: { translation: zh },
    },
    fallbackLng: "en",

    detection: {
      order: ["cookie", "localStorage", "navigator"],
      lookupCookie: "triver_lang",
      lookupLocalStorage: "triver:language:v1",
      caches: ["cookie", "localStorage"],
      cookieOptions: { path: "/", sameSite: "lax", maxAge: 365 * 24 * 60 * 60 },
    },

    interpolation: {
      escapeValue: false,
      prefix: "{",
      suffix: "}",
    },
  });

export default i18n;
