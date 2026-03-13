"use client";

import { useState, useEffect } from "react";
import { useTranslation } from "@/i18n/useTranslation";
import { detectBrowserLanguage } from "@/i18n";
import { X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

const DISMISS_KEY = "triver:lang-banner-dismissed";

export function LanguageBanner() {
  const { language, t } = useTranslation();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const dismissed = sessionStorage.getItem(DISMISS_KEY);
    if (dismissed) return;

    const detected = detectBrowserLanguage();

    if (detected !== language) {
      setVisible(true);
    }
  }, [language]);

  const handleSwitch = () => {
    // 배너 닫고 LanguageSwitcher 드롭다운 열기
    sessionStorage.setItem(DISMISS_KEY, "true");
    setVisible(false);
    window.dispatchEvent(new CustomEvent("triver:open-language-switcher"));
  };

  const handleDismiss = () => {
    sessionStorage.setItem(DISMISS_KEY, "true");
    setVisible(false);
  };

  const promptText = t("banner.switchPrompt");
  const switchLabel = t("banner.switch");

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -50, opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="fixed top-20 left-1/2 -translate-x-1/2 z-50"
        >
          <div className="flex items-center justify-between gap-3 rounded-xl bg-gray-900 px-4 py-3 text-white shadow-lg whitespace-nowrap">
            <p className="text-sm shrink-0">{promptText}</p>

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
