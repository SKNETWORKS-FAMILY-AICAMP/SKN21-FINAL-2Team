"use client";

import React, { createContext, useState, useEffect, useCallback } from "react";
import {
  type SupportedLanguage,
  LANGUAGE_STORAGE_KEY,
  LANGUAGE_EVENT,
  getTranslation,
  detectBrowserLanguage,
} from "./index";

interface LanguageContextValue {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

export const LanguageContext = createContext<LanguageContextValue>({
  language: "en",
  setLanguage: () => {},
  t: (key) => key,
});

function getInitialLanguage(): SupportedLanguage {
  if (typeof window === "undefined") return "en";

  const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored && ["en", "ko", "ja", "zh"].includes(stored)) {
    return stored as SupportedLanguage;
  }

  return detectBrowserLanguage();
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<SupportedLanguage>("en");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setLanguageState(getInitialLanguage());
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted) {
      document.documentElement.lang = language;
    }
  }, [language, mounted]);

  const setLanguage = useCallback((lang: SupportedLanguage) => {
    setLanguageState(lang);
    localStorage.setItem(LANGUAGE_STORAGE_KEY, lang);
    window.dispatchEvent(new CustomEvent(LANGUAGE_EVENT));
  }, []);

  // 다른 컴포넌트에서 CustomEvent로 언어 변경 시 동기화
  useEffect(() => {
    const onLangChange = () => {
      const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
      if (stored && ["en", "ko", "ja", "zh"].includes(stored)) {
        setLanguageState(stored as SupportedLanguage);
      }
    };

    window.addEventListener(LANGUAGE_EVENT, onLangChange);
    return () => window.removeEventListener(LANGUAGE_EVENT, onLangChange);
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => getTranslation(language, key, params),
    [language]
  );

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}
