import React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useTranslation } from "@/i18n/useTranslation";
import { SimpleModal } from "./SimpleModal";

interface DeleteReservationConfirmModalProps {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function DeleteReservationConfirmModal({
  open,
  onConfirm,
  onCancel,
}: DeleteReservationConfirmModalProps) {
  const { t } = useTranslation();

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[70] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          <motion.button
            type="button"
            className="absolute inset-0 bg-black/40"
            onClick={onCancel}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          />

          <motion.div
            className="relative z-10 w-full max-w-[420px] rounded-xl bg-white shadow-lg overflow-hidden"
            initial={{ opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 420, damping: 32 }}
          >
            <div className="p-6">
              <div className="text-lg font-semibold text-gray-900">
                {t("mypage.deleteReservationConfirm")}
              </div>
              <div className="mt-5 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onCancel}
                  className="bg-gray-200 text-gray-900 px-6 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-300 transition-colors"
                >
                  {t("common.no")}
                </button>
                <button
                  type="button"
                  onClick={onConfirm}
                  className="bg-black text-white px-6 py-2.5 rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
                >
                  {t("common.yes")}
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

interface PreferenceSavedPopupProps {
  open: boolean;
  onClose: () => void;
}

export function PreferenceSavedPopup({ open, onClose }: PreferenceSavedPopupProps) {
  const { t } = useTranslation();

  return (
    <SimpleModal
      open={open}
      title={t("mypage.preferenceSavedTitle")}
      onClose={onClose}
      zIndex={60}
    >
      <div className="space-y-4">
        <p className="text-sm text-gray-700">{t("mypage.preferenceSavedMessage")}</p>
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="h-10 px-6 rounded-full border border-gray-900 bg-black text-white text-xs font-bold hover:opacity-90 transition-all"
          >
            {t("common.confirm")}
          </button>
        </div>
      </div>
    </SimpleModal>
  );
}
