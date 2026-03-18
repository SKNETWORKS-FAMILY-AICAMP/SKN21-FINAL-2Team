"use client";

import React, { useEffect } from "react";
import { I18nextProvider } from "react-i18next";
import i18n from "./config";
import { LANGUAGE_COOKIE_KEY } from "./constants";

// cookie 설정 헬퍼
function setLangCookie(lang: string) {
  document.cookie = `${LANGUAGE_COOKIE_KEY}=${lang};path=/;max-age=${365 * 24 * 60 * 60};samesite=lax`;
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  // 마운트 시 cookie 동기화 + html lang 설정
  useEffect(() => {
    // 기존 localStorage 사용자를 위해 cookie가 없으면 현재 언어로 cookie 설정
    setLangCookie(i18n.language);
    document.documentElement.lang = i18n.language;

    const handleLanguageChanged = (lng: string) => {
      setLangCookie(lng);
      document.documentElement.lang = lng;
    };
    i18n.on("languageChanged", handleLanguageChanged);
    return () => {
      i18n.off("languageChanged", handleLanguageChanged);
    };
  }, []);

  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}
