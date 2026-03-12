"use client";

import { useState, useEffect } from "react";
import { useTranslation } from "@/i18n/useTranslation";
import {
  detectBrowserLanguage,
  SUPPORTED_LANGUAGES,
  type SupportedLanguage,
} from "@/i18n";
import { X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

const DISMISS_KEY = "triver:lang-banner-dismissed";

function getLanguageName(code: SupportedLanguage): string {
  return SUPPORTED_LANGUAGES.find((l) => l.code === code)?.label ?? code;
}

export function LanguageBanner() {
  const { language, setLanguage, t } = useTranslation();
  const [visible, setVisible] = useState(false);
  const [detectedLang, setDetectedLang] = useState<SupportedLanguage>("en");

  useEffect(() => {
    const dismissed = sessionStorage.getItem(DISMISS_KEY);
    if (dismissed) return;

    const detected = detectBrowserLanguage();
    setDetectedLang(detected);

    if (detected !== language) {
      setVisible(true);
    }
  }, [language]);

  const handleSwitch = () => {
    setLanguage(detectedLang);
    sessionStorage.setItem(DISMISS_KEY, "true");
    setVisible(false);
  };

  const handleDismiss = () => {
    sessionStorage.setItem(DISMISS_KEY, "true");
    setVisible(false);
  };

  const detectedName = getLanguageName(detectedLang);

  // Build prompt text: use translation key if available, otherwise fallback
  const promptText =
    t("banner.switchPrompt") !== "banner.switchPrompt"
      ? t("banner.switchPrompt").replace("{language}", detectedName)
      : `Switch to ${detectedName}?`;

  const switchLabel =
    t("banner.switch") !== "banner.switch" ? t("banner.switch") : "Switch";

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-2rem)] max-w-md"
        >
          <div className="flex items-center justify-between gap-3 rounded-xl bg-gray-900 px-4 py-3 text-white shadow-lg">
            <p className="text-sm">{promptText}</p>

            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={handleSwitch}
                className="rounded-lg bg-white px-3 py-1.5 text-sm font-medium text-gray-900 hover:bg-gray-100 transition-colors"
              >
                {switchLabel}
              </button>

              <button
                type="button"
                onClick={handleDismiss}
                className="rounded-lg p-1.5 text-gray-400 hover:text-white transition-colors"
                aria-label="Dismiss"
              >
                <X size={16} />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
