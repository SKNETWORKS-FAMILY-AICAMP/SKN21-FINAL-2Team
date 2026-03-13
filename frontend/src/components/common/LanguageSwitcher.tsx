"use client";

import { useState, useRef, useEffect } from "react";
import { useTranslation } from "@/i18n/useTranslation";
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from "@/i18n";
import { Globe } from "lucide-react";
import { updateCurrentUser } from "@/services/api";

interface LanguageSwitcherProps {
  variant?: "dropdown" | "select";
  onLanguageChange?: (lang: SupportedLanguage) => void;
  className?: string;
}

export function LanguageSwitcher({
  variant = "dropdown",
  onLanguageChange,
  className = "",
}: LanguageSwitcherProps) {
  const { language, setLanguage } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (variant !== "dropdown") return;

    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [variant]);

  // LanguageBanner에서 "전환" 클릭 시 드롭다운 자동 열기
  useEffect(() => {
    if (variant !== "dropdown") return;

    function handleOpenSwitcher() {
      setOpen(true);
    }

    window.addEventListener("triver:open-language-switcher", handleOpenSwitcher);
    return () => window.removeEventListener("triver:open-language-switcher", handleOpenSwitcher);
  }, [variant]);

  const handleChange = (lang: SupportedLanguage) => {
    setLanguage(lang);
    updateCurrentUser({ language: lang }).catch(() => {});
    onLanguageChange?.(lang);
    setOpen(false);
  };

  if (variant === "select") {
    return (
      <select
        value={language}
        onChange={(e) => handleChange(e.target.value as SupportedLanguage)}
        className={`rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-gray-400 ${className}`}
      >
        {SUPPORTED_LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>
            {l.label}
          </option>
        ))}
      </select>
    );
  }

  // dropdown variant
  return (
    <div ref={ref} className={`relative inline-block ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 transition-colors"
        aria-label="Change language"
      >
        <Globe size={16} />
        <span>{language.toUpperCase()}</span>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-44 rounded-xl bg-white shadow-lg ring-1 ring-black/5 z-50 overflow-hidden">
          {SUPPORTED_LANGUAGES.map((l) => (
            <button
              key={l.code}
              type="button"
              onClick={() => handleChange(l.code)}
              className="flex w-full items-center justify-between px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <span>{l.label}</span>
              {language === l.code && (
                <span className="text-blue-500">&#10003;</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
