import React from "react";
import { X, AlertTriangle } from "lucide-react";
import { useTranslation } from "@/i18n/useTranslation";
import { SimpleModal } from "@/components/common/SimpleModal";

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
    <SimpleModal
      open={open}
      onClose={onCancel}
      title={t("mypage.deleteReservationConfirm")}
      icon={<AlertTriangle size={20} className="text-white" />}
      maxWidth="sm"
    >
      <div className="flex flex-col">
        <p className="text-[15px] font-bold text-gray-900 mb-8 leading-relaxed">
          {t("mypage.deleteReservationConfirmDesc")}
        </p>

        <div className="flex flex-col gap-3">
          <button
            type="button"
            onClick={onConfirm}
            className="w-full py-4 bg-black text-white rounded-2xl text-sm font-bold shadow-lg hover:bg-gray-800 transition-all flex items-center justify-center gap-2 active:scale-[0.98]"
          >
            {t("common.yes")}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="w-full py-4 text-gray-500 rounded-2xl text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            {t("common.no")}
          </button>
        </div>
      </div>
    </SimpleModal>
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
      onClose={onClose}
      title={t("mypage.preferenceSavedTitle")}
      icon={<X size={20} className="text-white bg-black rounded-lg p-0.5" />}
      maxWidth="sm"
    >
      <div className="flex flex-col">
        <p className="text-[15px] font-bold text-gray-900 mb-8">
          {t("mypage.preferenceSavedMessage")}
        </p>
        <button
          type="button"
          onClick={onClose}
          className="w-full py-4 rounded-2xl bg-black text-white text-sm font-bold shadow-lg hover:bg-gray-800 transition-all flex items-center justify-center active:scale-[0.98]"
        >
          {t("common.confirm")}
        </button>
      </div>
    </SimpleModal>
  );
}
