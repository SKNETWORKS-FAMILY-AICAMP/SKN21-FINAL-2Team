"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { I18nextProvider } from "react-i18next";
import i18n from "./config";
import { LANGUAGE_COOKIE_KEY } from "./constants";

// cookie 설정 헬퍼
function setLangCookie(lang: string) {
  document.cookie = `${LANGUAGE_COOKIE_KEY}=${lang};path=/;max-age=${365 * 24 * 60 * 60};samesite=lax`;
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  // 마운트 시 cookie 동기화 + html lang 설정
  useEffect(() => {
    setLangCookie(i18n.language);
    document.documentElement.lang = i18n.language;

    const handleLanguageChanged = (lng: string) => {
      setLangCookie(lng);
      document.documentElement.lang = lng;
      // Next.js Router Cache 무효화 — 뒤로 가기해도 새 언어로 렌더링
      router.refresh();
    };
    i18n.on("languageChanged", handleLanguageChanged);
    return () => {
      i18n.off("languageChanged", handleLanguageChanged);
    };
  }, [router]);

  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}
