"use client";

import { AnimatePresence, motion } from "framer-motion";
import { X, Ticket, CheckCircle2 } from "lucide-react";
import type { ReservationItem } from "../types";

// 새롭게 분리한 커스텀 훅 및 프레젠터 컴포넌트 임포트
import { useReservationForm } from "./useReservationForm";
import { SimpleModal } from "./SimpleModal";
import { ReservationImageSection } from "./ReservationImageSection";
import { ReservationFormSection } from "./ReservationFormSection";
import { useTranslation } from "@/i18n/useTranslation";

export function ReservationDetailModal({
    open,
    reservation,
    photoUrl,
    onSavePhoto,
    onSaveTitle,
    onSaveCategory,
    onSaveDetails,
    onClose,
}: {
    open: boolean;
    reservation: ReservationItem | null;
    photoUrl?: string;
    onSavePhoto: (nextUrl: string | null) => Promise<void> | void;
    onSaveTitle?: (newTitle: string) => Promise<void> | void;
    onSaveCategory?: (newCategory: string) => Promise<void> | void;
    onSaveDetails?: (newDetails: Record<string, string>) => Promise<void> | void;
    onClose: (wasSaved: boolean, isNewDraft: boolean, shouldDeleteDraft?: boolean) => void;
}) {
    // 1. 상태 및 비즈니스 로직은 커스텀 훅이 전담
    const { state, actions } = useReservationForm({
        open, reservation, photoUrl, onSavePhoto, onSaveTitle, onSaveCategory, onSaveDetails, onClose
    });

    const {
        draftDetails, editingTitle, draftTitle, isOcrLoading, ocrMessage,
        showCloseWarning, showSuccessMessage, isEditMode, promptOpen, promptValue,
        effectivePhotoUrl, previewPhotoUrl, draftCategory, previewOpen
    } = state;

    const {
        setDraftDetails, setEditingTitle, setDraftTitle, setPreviewOpen, setOcrMessage,
        setShowCloseWarning, setPromptOpen, setPromptValue, setDraftCategory,
        handleClose, handleSave, handleOcr, setDraftPhotoUrl
    } = actions;
    const { t } = useTranslation();

    const handleAddPromptConfirm = () => {
        if (promptValue.trim()) {
            setDraftDetails((prev) => ({ ...prev, [promptValue.trim()]: "" }));
            setPromptOpen(false);
            setPromptValue("");
        }
    };

    // 2. 렌더링 뷰 (컨테이너 역할)
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
                    {/* 뒷배경 덮개 */}
                    <motion.button
                        type="button"
                        className="absolute inset-0 bg-black/30 backdrop-blur-md"
                        onClick={handleClose}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                    />

                    {/* 메인 모달 */}
                    <motion.div
                        className="relative z-10 w-full max-w-[96vw] sm:max-w-[700px] md:max-w-[850px] rounded-[2rem] bg-white/95 backdrop-blur-3xl border border-white shadow-[0_16px_40px_-8px_rgba(0,0,0,0.15)] overflow-hidden flex flex-col"
                        initial={{ opacity: 0, scale: 0.9, y: 30 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        transition={{ type: "spring", damping: 25, stiffness: 300 }}
                    >
                        {/* 헤더 */}
                        <div className="relative p-7 pb-4">
                            <button
                                type="button"
                                onClick={handleClose}
                                className="absolute top-6 right-6 p-2.5 text-gray-400 hover:text-gray-800 hover:bg-gray-100/70 rounded-full transition-all bg-transparent z-20"
                            >
                                <X size={16} />
                            </button>

                            <div className="flex items-center gap-3 mb-4">
                                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#f1f3f5] text-gray-700">
                                    <Ticket size={14} className="text-gray-600" />
                                </div>
                                <h2 className="text-[11px] font-extrabold text-[#8b98a5] uppercase tracking-widest mt-0.5">
                                    RESERVATION DETAIL
                                </h2>
                            </div>
                        </div>

                        {/* 본문 콘텐츠 (2단 분리된 컴포넌트 렌더링) */}
                        <div className="px-6 pb-4 max-h-[75vh] overflow-y-auto flex flex-col md:flex-row gap-8">
                            <ReservationImageSection
                                isEditMode={isEditMode}
                                effectivePhotoUrl={effectivePhotoUrl}
                                previewPhotoUrl={previewPhotoUrl}
                                isOcrLoading={isOcrLoading}
                                ocrMessage={ocrMessage}
                                onPhotoUpload={setDraftPhotoUrl}
                                onPreviewOpen={() => setPreviewOpen(true)}
                                onOcrProcess={handleOcr}
                                onOcrMessageClear={() => setOcrMessage(null)}
                            />

                            <ReservationFormSection
                                isEditMode={isEditMode}
                                draftTitle={draftTitle}
                                setDraftTitle={setDraftTitle}
                                editingTitle={editingTitle}
                                setEditingTitle={setEditingTitle}
                                draftCategory={draftCategory}
                                setDraftCategory={setDraftCategory}
                                draftDetails={draftDetails}
                                setDraftDetails={setDraftDetails}
                                setPromptOpen={setPromptOpen}
                                setPromptValue={setPromptValue}
                            />
                        </div>

                        {/* 하단 저장 버튼 */}
                        <div className="px-6 pb-6 pt-2">
                            {isEditMode ? (
                                <div className="flex gap-2">
                                    <button
                                        type="button"
                                        onClick={handleClose}
                                        className="flex-1 h-10 sm:h-12 px-6 sm:px-8 rounded-full border border-gray-200 bg-white text-xs font-bold hover:bg-gray-50 transition-all active:translate-y-0"
                                    >
                                        <span className="text-gray-400 group-hover:text-black transition-colors">{t("common.cancel")}</span>
                                    </button>
                                    <button
                                        type="button"
                                        onClick={handleSave}
                                        disabled={!isEditMode}
                                        className="flex-1 h-10 sm:h-12 px-6 sm:px-8 rounded-full border border-gray-900 bg-black text-white text-xs font-bold hover:shadow-lg hover:shadow-black/20 hover:-translate-y-0.5 transition-all active:translate-y-0 disabled:opacity-50 disabled:hover:shadow-none disabled:hover:translate-y-0"
                                    >
                                        {t("common.save")}
                                    </button>
                                </div>
                            ) : (
                                <div className="h-[48px]" />
                            )}
                        </div>
                    </motion.div>
                </motion.div>
            )}

            {/* 성공 알림 오버레이 */}
            {showSuccessMessage && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm"
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="bg-white/90 backdrop-blur-md px-8 py-6 rounded-[2rem] flex flex-col items-center shadow-2xl"
                    >
                        <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: "spring", stiffness: 300, damping: 20 }}
                            className="w-16 h-16 bg-black rounded-full flex items-center justify-center mb-6"
                        >
                            <CheckCircle2 className="text-white" size={32} />
                        </motion.div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">{t("mypage.preferenceSavedTitle")}</h3>
                        <p className="text-sm font-medium text-gray-500">{t("mypage.preferenceSavedMessage")}</p>
                    </motion.div>
                </motion.div>
            )}

            {/* 이미지 원본 프리뷰 서브 모달 */}
            {previewOpen && previewPhotoUrl && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[70] flex items-center justify-center bg-black/90 backdrop-blur-sm p-4"
                >
                    <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col">
                        <button
                            type="button"
                            onClick={() => setPreviewOpen(false)}
                            className="absolute -top-12 right-0 p-2 text-white/70 hover:text-white transition-colors"
                        >
                            <X size={24} />
                        </button>
                        <img
                            src={effectivePhotoUrl || undefined}
                            alt={t("mypage.reservationSuffix")}
                            className="w-full h-auto object-contain"
                        />
                    </div>
                </motion.div>
            )}

            {/* 새로운 항목 추가 프롬프트 */}
            {promptOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[80] flex items-center justify-center p-4"
                >
                    <button type="button" className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setPromptOpen(false)} />
                    <motion.div
                        initial={{ scale: 0.95, y: 10 }}
                        animate={{ scale: 1, y: 0 }}
                        exit={{ scale: 0.95, opacity: 0 }}
                        className="relative w-full max-w-[360px] bg-white/95 backdrop-blur-2xl rounded-3xl p-6 shadow-2xl border border-white"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-2">{t("mypage.itemName")}</h3>
                            <p className="text-xs font-medium text-gray-500 mb-5">
                                {t("mypage.addItemDesc")}
                            </p>
                            <input
                                type="text"
                                value={promptValue}
                                onChange={(e) => setPromptValue(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && promptValue.trim()) {
                                        handleAddPromptConfirm();
                                    }
                                }}
                                autoFocus
                                placeholder={t("mypage.itemName")}
                                className="w-full h-12 px-4 rounded-xl bg-gray-100/50 border-none font-medium focus:outline-none focus:ring-[1px] focus:ring-black/[0.08]"
                            />
                        </div>
                        <div className="flex gap-2 mt-5">
                            <button
                                type="button"
                                onClick={() => {
                                    setPromptOpen(false);
                                    setPromptValue("");
                                }}
                                className="flex-1 h-11 rounded-xl bg-gray-100 text-gray-600 font-bold text-sm hover:bg-gray-200 transition-colors tracking-wide"
                            >
                                {t("common.cancel")}
                            </button>
                            <button
                                type="button"
                                onClick={handleAddPromptConfirm}
                                disabled={!promptValue.trim()}
                                className="flex-1 h-11 rounded-xl bg-black text-white font-bold text-sm hover:bg-gray-800 transition-colors tracking-wide disabled:opacity-30 disabled:hover:bg-black"
                            >
                                {t("mypage.add")}
                            </button>
                        </div>
                    </motion.div>
                </motion.div>
            )}

            {/* 변경사항 취소 경고창 */}
            {showCloseWarning && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[80] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
                >
                    <motion.div
                        initial={{ scale: 0.95, y: 10 }}
                        animate={{ scale: 1, y: 0 }}
                        className="relative w-full max-w-[340px] bg-white rounded-3xl shadow-xl overflow-hidden"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="p-6 pt-8 pb-7 text-center">
                            <div className="mb-4 inline-flex items-center justify-center w-14 h-14 bg-red-50 text-red-500 rounded-full">
                                <X size={28} />
                            </div>
                            <h3 className="text-2xl font-bold text-gray-900 mb-3 whitespace-pre-line">
                                {t("mypage.closeWarningTitle")}
                            </h3>
                            <p className="text-[13px] text-gray-500 leading-relaxed whitespace-pre-line">
                                {t("mypage.closeWarningDesc")}
                            </p>
                        </div>

                        <div className="p-2 flex flex-col gap-2 bg-gray-50/50">
                            <button
                                onClick={() => setShowCloseWarning(false)}
                                className="w-full h-12 bg-black text-white rounded-2xl font-bold text-sm hover:opacity-90 transition-opacity flex items-center justify-center"
                            >
                                {t("mypage.continueEditing")}
                            </button>
                            <button
                                onClick={() => {
                                    setShowCloseWarning(false);
                                    onClose(false, reservation?.title === t("mypage.newReservation") || reservation?.title === "Reservation" || reservation?.title === "새 예약", true);
                                }}
                                className="w-full h-12 bg-white text-gray-500 border border-gray-200 rounded-2xl font-bold text-sm hover:bg-gray-100 hover:text-gray-900 transition-colors flex items-center justify-center"
                            >
                                {t("mypage.yesClose")}
                            </button>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
