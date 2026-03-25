import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Loader2, ScanText, RefreshCw, StickyNote } from "lucide-react";
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
        <div className="flex items-center gap-2">
          <StickyNote className="text-gray-400" size={18} />
          <h3 className="text-[14px] font-bold text-gray-900 uppercase tracking-wide">
            {t("mypage.relatedImage")}
          </h3>
        </div>

        {isEditMode && (
          <div className="mb-2.5 px-4 py-3 rounded-2xl bg-amber-50 border border-amber-200/60 flex items-start gap-2">
            <span className="text-amber-500 mt-0.5">
              <AlertTriangle size={14} />
            </span>
            <p className="text-[11px] leading-relaxed">
              {t("mypage.imagePrivacyWarning")}
            </p>
            <p className="text-[11px] mt-0.5 opacity-80">
              {t("mypage.imageUsageDesc")}
            </p>
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
          className={`w-full rounded-[1.25rem] overflow-hidden transition-all duration-300 ${isEditMode
              ? "border border-white/60 bg-[#f5f7f9]/60 backdrop-blur-md shadow-[inset_0_2px_4px_rgba(255,255,255,0.7)] hover:bg-white/70 hover:scale-[1.01]"
              : "border border-white bg-white/40 shadow-sm"
            }`}
        >
          {previewPhotoUrl ? (
            <div className="absolute inset-0 bg-white z-10 p-2">
              <img src={previewPhotoUrl} alt={t("mypage.reservationSuffix")} className="w-full h-full object-contain" />
              {/* 이미지 변경 버튼 (우측 상단 플로팅) */}
            </div>
          ) : (
            <div className="h-[300px] flex flex-col items-center justify-center text-gray-400">
              {/* NO IMAGE and (Click to Upload) removed */}
            </div>
          )}
        </button>

        {isEditMode && (
          <div className="mt-2.5 flex items-center justify-between gap-3 px-1">
            <button
              type="button"
              onClick={() => {
                onPreviewOpen();
                fileInputRef.current?.click();
              }}
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
              className="text-[10px] font-bold text-gray-400 hover:text-black uppercase tracking-widest transition-colors flex items-center gap-1"
            >
              <RefreshCw size={12} />
              {t("mypage.changeImage")}
            </button>

            {isProcessing ? (
              <button
                type="button"
                disabled
                className="w-full h-11 sm:h-12 bg-gray-100 text-gray-400 rounded-xl flex items-center justify-center gap-2 font-semibold text-sm cursor-not-allowed"
              >
                <Loader2 size={12} className="animate-spin" /> {t("mypage.ocrLoading")}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleOcrProcess}
                className="w-full h-11 sm:h-12 bg-black hover:bg-gray-800 text-white rounded-xl shadow-[0_4px_12px_rgba(0,0,0,0.15)] flex items-center justify-center gap-2 font-bold text-sm transition-all transform hover:scale-[1.02] active:scale-95"
              >
                <ScanText size={12} /> {t("mypage.ocrRead")}
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
