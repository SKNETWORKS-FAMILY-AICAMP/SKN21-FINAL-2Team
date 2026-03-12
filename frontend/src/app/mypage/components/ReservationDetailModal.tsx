"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useTranslation } from "@/i18n/useTranslation";
import type { ReservationItem } from "../types";

export function ReservationDetailModal({
    open,
    reservation,
    photoUrl,
    onSavePhoto,
    onClose,
}: {
    open: boolean;
    reservation: ReservationItem | null;
    photoUrl?: string;
    onSavePhoto: (nextUrl: string | null) => Promise<void> | void;
    onClose: () => void;
}) {
    const { t } = useTranslation();
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    // undefined: unchanged, string: new image, null: removed
    const [draftPhotoUrl, setDraftPhotoUrl] = useState<string | null | undefined>(undefined);
    const [previewOpen, setPreviewOpen] = useState(false);
    const initialPhotoUrl = (typeof photoUrl === "string" && photoUrl.trim().length
        ? photoUrl
        : (typeof reservation?.reservationImageUrl === "string" && reservation.reservationImageUrl.trim().length
            ? reservation.reservationImageUrl
            : null));

    const effectivePhotoUrl = draftPhotoUrl === undefined ? initialPhotoUrl : draftPhotoUrl;
    const previewPhotoUrl = effectivePhotoUrl || undefined;

    return (
        <AnimatePresence>
            {open && reservation && (
                <motion.div
                    className="fixed inset-0 z-50 flex items-center justify-center p-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                >
                    <motion.button
                        type="button"
                        aria-label="Close"
                        className="absolute inset-0 bg-black/40"
                        onClick={onClose}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                    />

                    <motion.div
                        className="relative z-10 w-full max-w-sm rounded-xl bg-white border border-gray-200 shadow-lg overflow-hidden flex flex-col"
                        initial={{ opacity: 0, y: 10, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.98 }}
                        transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    >
                        <div className="relative p-6 pb-4">
                            <button
                                type="button"
                                aria-label="Close"
                                onClick={onClose}
                                className="absolute right-4 top-4 w-9 h-9 rounded-lg border border-gray-200 bg-white text-gray-700 flex items-center justify-center hover:bg-gray-50 transition-colors"
                            >
                                <X size={16} />
                            </button>
                            <h2 className="text-3xl font-bold text-gray-900 text-center">{t("mypage.reservationDetails")}</h2>
                        </div>

                        <div className="px-6 pb-4 max-h-[60vh] overflow-y-auto">
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                className="hidden"
                                onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (!file) return;
                                    const reader = new FileReader();
                                    reader.onload = () => {
                                        const url = typeof reader.result === "string" ? reader.result : "";
                                        if (!url) return;
                                        setDraftPhotoUrl(url);
                                    };
                                    reader.readAsDataURL(file);
                                    e.currentTarget.value = "";
                                }}
                            />

                            <button
                                type="button"
                                onClick={() => {
                                    if (previewPhotoUrl) {
                                        setPreviewOpen(true);
                                        return;
                                    }
                                    fileInputRef.current?.click();
                                }}
                                className="w-full rounded-xl border border-gray-200 bg-gray-200 text-gray-900 overflow-hidden"
                                aria-label="Upload reservation image"
                            >
                                {previewPhotoUrl ? (
                                    <div className="h-[220px] bg-gray-100 flex items-center justify-center">
                                        <img src={previewPhotoUrl} alt="Reservation" className="w-full h-full object-contain" />
                                    </div>
                                ) : (
                                    <div className="h-[180px] flex flex-col items-center justify-center">
                                        <div className="text-lg font-bold">{t("mypage.reservationImage")}</div>
                                        <div className="text-xs text-gray-700 mt-1">{t("mypage.uploadImageHint")}</div>
                                    </div>
                                )}
                            </button>

                            <div className="mt-2 flex items-center justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setPreviewOpen(false);
                                        fileInputRef.current?.click();
                                    }}
                                    className="text-[11px] font-semibold text-gray-600 hover:text-black"
                                >
                                    {t("mypage.changeImage")}
                                </button>
                                {!!previewPhotoUrl && (
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setPreviewOpen(false);
                                            setDraftPhotoUrl(null);
                                        }}
                                        className="text-[11px] font-semibold text-gray-600 hover:text-black"
                                    >
                                        {t("mypage.removePhoto")}
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="px-6 pb-6">
                            <button
                                type="button"
                                onClick={async () => {
                                    await onSavePhoto(effectivePhotoUrl ?? null);
                                    onClose();
                                }}
                                className="w-full bg-black text-white py-3 rounded-lg text-sm font-semibold"
                            >
                                {t("common.save")}
                            </button>
                        </div>
                    </motion.div>

                    <AnimatePresence>
                        {previewOpen && !!effectivePhotoUrl && (
                            <motion.div
                                className="fixed inset-0 z-[60] flex items-center justify-center p-4"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                            >
                                <button
                                    type="button"
                                    aria-label="Close preview"
                                    className="absolute inset-0 bg-black/75"
                                    onClick={() => setPreviewOpen(false)}
                                />
                                <motion.div
                                    className="relative z-10 w-full max-w-4xl max-h-[90vh] rounded-2xl bg-black/95 p-4 border border-white/20"
                                    initial={{ opacity: 0, y: 8, scale: 0.98 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: 8, scale: 0.98 }}
                                >
                                    <button
                                        type="button"
                                        aria-label="Close preview"
                                        onClick={() => setPreviewOpen(false)}
                                        className="absolute right-3 top-3 w-8 h-8 rounded-full border border-white/30 text-white bg-black/40 flex items-center justify-center"
                                    >
                                        <X size={14} />
                                    </button>
                                    <div className="w-full h-[80vh] max-h-[80vh] flex items-center justify-center">
                                        <img src={previewPhotoUrl} alt="Original reservation" className="max-w-full max-h-full object-contain" />
                                    </div>
                                </motion.div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
