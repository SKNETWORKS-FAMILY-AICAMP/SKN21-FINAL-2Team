"use client";

import { useCallback } from "react";
import { useTranslation as useI18nextTranslation } from "react-i18next";
import type { SupportedLanguage } from "./config";

export function useTranslation() {
  const { t, i18n } = useI18nextTranslation();

  // 기존 컴포넌트와의 호환성을 맞추기 위해 t 함수를 재정의합니다
  // 기존 코드: t("key", { param: "value" })
  const customT = useCallback(
    (key: string, params?: Record<string, string | number>): string => {
      return t(key, params as any) as string;
    },
    [t],
  );

  const setLanguage = useCallback(
    (lang: SupportedLanguage) => {
      i18n.changeLanguage(lang);
    },
    [i18n],
  );

  return {
    t: customT,
    language: i18n.language as SupportedLanguage,
    setLanguage,
  };
}
