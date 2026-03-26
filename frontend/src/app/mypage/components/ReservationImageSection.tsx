import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Loader2, ScanText, RefreshCw, Ticket } from "lucide-react";
import { useTranslation } from "@/i18n/useTranslation";

interface ReservationImageSectionProps {
  isEditMode: boolean;
  effectivePhotoUrl: string | null | undefined;
  previewPhotoUrl: string | undefined;
  isOcrLoading: boolean;
  ocrMessage: { type: "success" | "error"; text: string } | null;
  onPhotoUpload: (url: string) => void;
  onPreviewOpen: () => void;
  onOcrProcess: () => Promise<void>;
  onOcrMessageClear: () => void;
}

export function ReservationImageSection({
  isEditMode,
  effectivePhotoUrl,
  previewPhotoUrl,
  isOcrLoading,
  ocrMessage,
  onPhotoUpload,
  onPreviewOpen,
  onOcrProcess,
  onOcrMessageClear,
}: ReservationImageSectionProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const { t } = useTranslation();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const url = typeof reader.result === "string" ? reader.result : "";
      if (!url) return;
      onPhotoUpload(url);
      onOcrMessageClear();
    };
    reader.readAsDataURL(file);
    e.currentTarget.value = "";
  };

  const handleOcrProcess = async () => {
    setIsProcessing(true);
    try {
      await onOcrProcess();
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="w-full md:w-5/12 space-y-4 flex flex-col">
      <div>
        {isEditMode && (
          <div className="mb-2.5 px-4 py-3 rounded-2xl bg-amber-50 border border-amber-200/60 flex items-start gap-3">
            <span className="text-amber-500 mt-0.5 flex-none">
              <AlertTriangle size={14} />
            </span>
            <div className="flex flex-col gap-1">
              <p className="text-[11px] font-medium text-amber-900 leading-relaxed">
                {t("mypage.imagePrivacyWarning")}
              </p>
              <p className="text-[10px] text-amber-800/70 leading-normal">
                {t("mypage.imageUsageDesc")}
              </p>
            </div>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleFileChange}
        />

        <button
          type="button"
          onClick={() => {
            if (previewPhotoUrl) {
              onPreviewOpen();
              return;
            }
            if (isEditMode) fileInputRef.current?.click();
          }}
          className={`relative w-full rounded-[1.25rem] overflow-hidden transition-all duration-300 min-h-[300px] flex items-center justify-center ${isEditMode
              ? "border border-white/60 bg-[#f5f7f9]/60 backdrop-blur-md shadow-[inset_0_2px_4px_rgba(255,255,255,0.7)] hover:bg-white/70 hover:scale-[1.01]"
              : "border border-white bg-white/40 shadow-sm"
            }`}
        >
          {previewPhotoUrl ? (
            <div className="absolute inset-0 bg-white z-10 p-2">
              <img src={previewPhotoUrl} alt={t("mypage.reservationSuffix")} className="w-full h-full object-contain" />
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center text-gray-400 gap-3 p-8">
              <div className="w-16 h-16 rounded-full bg-white/50 flex items-center justify-center shadow-sm">
                <ScanText size={24} className="opacity-40" />
              </div>
              <div className="text-center">
                <p className="text-sm font-bold text-gray-500">{t("mypage.clickToAttachImage")}</p>
                <p className="text-[11px] mt-1 opacity-60">{t("mypage.imageUsageDesc")}</p>
              </div>
            </div>
          )}
        </button>

        {isEditMode && (
          <div className="mt-4 flex items-center gap-2 px-1">
            <button
              type="button"
              onClick={() => {
                onPreviewOpen();
                fileInputRef.current?.click();
              }}
              className="h-9 px-3 rounded-lg border border-gray-200 bg-white text-[10px] font-bold text-gray-500 hover:text-black hover:border-black uppercase transition-all flex items-center gap-1.5 flex-none"
            >
              <RefreshCw size={11} />
              {t("mypage.changeImage")}
            </button>

            {isProcessing ? (
              <button
                type="button"
                disabled
                className="h-9 px-4 bg-gray-50 text-gray-400 rounded-lg flex items-center justify-center gap-2 font-semibold text-[11px] cursor-not-allowed border border-gray-100 ml-auto"
              >
                <Loader2 size={11} className="animate-spin" /> {t("mypage.ocrLoading")}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleOcrProcess}
                className="h-9 px-4 bg-zinc-900 hover:bg-black text-white rounded-lg shadow-sm flex items-center justify-center gap-2 font-bold text-[11px] transition-all active:scale-95 ml-auto"
              >
                <ScanText size={13} /> {t("mypage.ocrRead")}
              </button>
            )}
          </div>
        )}

        <AnimatePresence>
          {ocrMessage && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={`mt-2 px-3 py-2 rounded-lg text-xs font-medium whitespace-pre-line ${ocrMessage.type === "success"
                  ? "bg-green-50 text-green-700 border border-green-200"
                  : "bg-red-50 text-red-600 border border-red-200"
                }`}
            >
              {ocrMessage.text}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
