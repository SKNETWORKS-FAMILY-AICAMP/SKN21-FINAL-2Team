"use client";

import React, { useEffect } from "react";
import { I18nextProvider } from "react-i18next";
import i18n from "./config";
import { setTriverLangCookie } from "./languageCookie";

function setLangCookie(lang: string) {
  setTriverLangCookie(lang);
}

interface LanguageProviderProps {
  children: React.ReactNode;
  initialLang?: string;
}

export function LanguageProvider({ children, initialLang = "en" }: LanguageProviderProps) {

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
      window.dispatchEvent(new Event("triver:language"));
      // react-i18next가 클라이언트에서 즉시 언어를 변경하므로 router.refresh() 불필요
      // router.refresh()를 호출하면 서버 재렌더링 중 화면이 깨지는 문제가 있었음
    };
    i18n.on("languageChanged", handleLanguageChanged);
    return () => {
      i18n.off("languageChanged", handleLanguageChanged);
    };
  }, []);

  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}
