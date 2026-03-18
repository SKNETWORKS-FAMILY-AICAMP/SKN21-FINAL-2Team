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

interface LanguageProviderProps {
  children: React.ReactNode;
  initialLang?: string;
}

export function LanguageProvider({ children, initialLang = "en" }: LanguageProviderProps) {
  const router = useRouter();

  // 서버에서 전달받은 언어로 i18n 동기화 — SSR과 클라이언트 렌더링 일치시킴
  if (i18n.language !== initialLang) {
    i18n.changeLanguage(initialLang);
  }

  useEffect(() => {
    setLangCookie(i18n.language);
    document.documentElement.lang = i18n.language;

    const handleLanguageChanged = (lng: string) => {
      setLangCookie(lng);
      document.documentElement.lang = lng;
      router.refresh();
    };
    i18n.on("languageChanged", handleLanguageChanged);
    return () => {
      i18n.off("languageChanged", handleLanguageChanged);
    };
  }, [router]);

  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}
