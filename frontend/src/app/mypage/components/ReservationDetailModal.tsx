"use client";
import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Ticket, AlertTriangle, RefreshCw, Trash2, Check, ExternalLink, AlertCircle } from "lucide-react";
import { useTranslation } from "@/i18n/useTranslation";
import { SimpleModal, MODAL_STYLES } from "@/components/common/SimpleModal";
import { useReservationForm, isNewDraftTitle } from "./useReservationForm";
import { ReservationImageSection } from "./ReservationImageSection";
import { ReservationFormSection } from "./ReservationFormSection";
import type { ReservationItem } from "../types";

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
                    key="main-modal"
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
                        className={`${MODAL_STYLES.container} w-full max-w-[96vw] sm:max-w-[800px] lg:max-w-[1000px] flex flex-col max-h-[90vh]`}
                        initial={{ opacity: 0, scale: 0.96, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.96, y: 10 }}
                        transition={{ duration: 0.2 }}
                    >
                        {/* 헤더 */}
                        <div className="relative pt-8 pb-5 px-8 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className={MODAL_STYLES.headerIconBox}>
                                    <Ticket size={18} />
                                </div>
                                <div className="flex flex-col">
                                    <h2 className={MODAL_STYLES.headerLabel}>
                                      {t("mypage.reservationDetailLabel")}
                                    </h2>
                                </div>
                            </div>

                            <button
                                type="button"
                                onClick={handleClose}
                                className={MODAL_STYLES.closeButton}
                            >
                                <X size={20} />
                            </button>
                        </div>

                        {/* 본문 콘텐츠 (2단 분리된 컴포넌트 렌더링) */}
                        <div className="px-8 pt-4 pb-7 overflow-y-auto flex flex-col md:flex-row gap-8 min-h-0">
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
                        <div className="px-8 pb-8 pt-3">
                            {isEditMode ? (
                                <button
                                    type="button"
                                    onClick={handleSave}
                                    disabled={!isEditMode}
                                    className="w-full h-12 rounded-2xl bg-black text-white text-sm font-bold shadow-xl shadow-black/10 hover:bg-zinc-800 hover:-translate-y-0.5 transition-all active:translate-y-0 disabled:opacity-20 flex items-center justify-center gap-2 group"
                                >
                                    <Check size={16} className="group-hover:scale-110 transition-transform" />
                                    {t("common.save")}
                                </button>
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
                    key="success-overlay"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm"
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="bg-white px-10 py-10 rounded-[2rem] flex flex-col items-center shadow-2xl border border-black/[0.05]"
                    >
                        <motion.div
                            initial={{ scale: 0, rotate: -45 }}
                            animate={{ scale: 1, rotate: 0 }}
                            transition={{ type: "spring", stiffness: 300, damping: 20 }}
                            className="w-14 h-14 bg-gray-50 border border-gray-100 rounded-2xl flex items-center justify-center mb-6 shadow-sm"
                        >
                            <AlertCircle className="text-gray-900" size={24} strokeWidth={2.5} />
                        </motion.div>
                        <h3 className="text-base font-semibold text-gray-900 mb-2">{t("mypage.reservationSavedTitle")}</h3>
                        <p className="text-[13px] font-normal text-gray-500 opacity-80">{t("mypage.reservationSavedMessage")}</p>
                    </motion.div>
                </motion.div>
            )}

            {/* 이미지 원본 프리뷰 서브 모달 */}
            {previewOpen && previewPhotoUrl && (
                <motion.div
                    key="preview-modal"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[70] flex items-center justify-center bg-black/90 backdrop-blur-sm p-4"
                >
                    <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col">
                        <button
                            type="button"
                            onClick={() => setPreviewOpen(false)}
                            className="absolute -top-14 right-2 p-3 text-white/50 hover:text-white transition-all bg-white/10 hover:bg-white/20 rounded-full"
                        >
                            <X size={24} />
                        </button>
                        <div className="overflow-hidden rounded-3xl border border-white/10 shadow-2xl">
                          <img
                              src={effectivePhotoUrl || undefined}
                              alt={t("mypage.reservationSuffix")}
                              className="w-full h-auto object-contain"
                          />
                        </div>
                    </div>
                </motion.div>
            )}

            {/* 새로운 항목 추가 프롬프트 */}
            {promptOpen && (
                <motion.div
                    key="prompt-modal"
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
                        className="relative w-full max-w-[380px] bg-white/95 backdrop-blur-3xl rounded-[2.5rem] p-8 shadow-2xl border border-white"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="mb-6">
                            <h3 className="text-xl font-bold text-gray-900 mb-2">{t("mypage.itemName")}</h3>
                            <p className="text-[13px] font-medium text-gray-400">
                                {t("mypage.addItemDesc")}
                            </p>
                        </div>
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
                            className="w-full h-13 px-5 rounded-2xl bg-gray-100/60 border-none font-medium text-gray-900 focus:outline-none focus:ring-1 focus:ring-black/5"
                        />
                        <div className="flex gap-3 mt-6">
                            <button
                                type="button"
                                onClick={() => {
                                    setPromptOpen(false);
                                    setPromptValue("");
                                }}
                                className="flex-1 h-12 rounded-2xl bg-gray-100 text-gray-600 font-bold text-sm hover:bg-gray-200 transition-colors"
                            >
                                {t("common.cancel")}
                            </button>
                            <button
                                type="button"
                                onClick={handleAddPromptConfirm}
                                disabled={!promptValue.trim()}
                                className="flex-1 h-12 rounded-2xl bg-black text-white font-bold text-sm hover:bg-gray-800 transition-colors disabled:opacity-20"
                            >
                                {t("mypage.add")}
                            </button>
                        </div>
                    </motion.div>
                </motion.div>
            )}

            {/* 변경사항 취소 경고창 (Close Warning Modal) - 디자인 개선 버전 */}
            {showCloseWarning && (
                <motion.div
                    key="close-warning"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-md"
                >
                    <motion.div
                        initial={{ scale: 0.9, y: 20 }}
                        animate={{ scale: 1, y: 0 }}
                        exit={{ scale: 0.9, opacity: 0 }}
                        className="relative w-full max-w-[360px] bg-white rounded-[2rem] p-8 shadow-[0_32px_80px_rgba(0,0,0,0.2)] border border-black/[0.05]"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="text-center mb-8">
                            <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-gray-50 border border-gray-100 text-gray-900 shadow-sm">
                                <Check size={28} strokeWidth={3} />
                            </div>
                            <h3 className="text-base font-semibold text-gray-900 mb-2 leading-tight">
                                {t("mypage.closeWarningTitle").split('\n').map((line, i) => (
                                  <React.Fragment key={i}>
                                    {line}<br/>
                                  </React.Fragment>
                                ))}
                            </h3>
                            <p className="text-[13px] font-medium text-gray-500 leading-relaxed px-4">
                                {t("mypage.closeWarningDesc")}
                            </p>
                        </div>

                        <div className="flex flex-col gap-2.5">
                            <button
                                onClick={() => setShowCloseWarning(false)}
                                className="w-full h-12 bg-black text-white rounded-2xl font-bold text-sm hover:bg-zinc-800 transition-all flex items-center justify-center"
                            >
                                {t("mypage.continueEditing")}
                            </button>
                             <button
                                onClick={() => {
                                    setShowCloseWarning(false);
                                    onClose(false, isNewDraftTitle(reservation?.title, t), true);
                                }}
                                className="w-full h-12 bg-gray-50 text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded-2xl font-bold text-sm transition-all flex items-center justify-center"
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
