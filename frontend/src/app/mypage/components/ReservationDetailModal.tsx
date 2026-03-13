"use client";

import { useRef, useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import type { ReservationItem } from "../types";

export function ReservationDetailModal({
    open,
    reservation,
    photoUrl,
    onSavePhoto,
    onSaveTitle, // [추가] 예약 제목 저장 함수
    onClose,
}: {
    open: boolean;
    reservation: ReservationItem | null;
    photoUrl?: string;
    onSavePhoto: (nextUrl: string | null) => Promise<void> | void;
    onSaveTitle?: (newTitle: string) => Promise<void> | void; // [추가] 제목 저장 prop
    onClose: () => void;
}) {
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    // undefined: unchanged, string: new image, null: removed
    const [draftPhotoUrl, setDraftPhotoUrl] = useState<string | null | undefined>(undefined);
    
    // [추가] 제목 편집 상태 관리
    const [editingTitle, setEditingTitle] = useState(false);
    const [draftTitle, setDraftTitle] = useState(reservation?.title || "");
    
    const [previewOpen, setPreviewOpen] = useState(false);
    
    // [추가] 닫기 경고 및 저장 완료 메시지 상태
    const [showCloseWarning, setShowCloseWarning] = useState(false);
    const [showSuccessMessage, setShowSuccessMessage] = useState(false);
    
    // [추가] reservation이 변경될 때 제목 업데이트
    useEffect(() => {
        if (reservation?.title) {
            setDraftTitle(reservation.title);
        }
    }, [reservation?.title]);
    
    const initialPhotoUrl = (typeof photoUrl === "string" && photoUrl.trim().length
        ? photoUrl
        : (typeof reservation?.reservationImageUrl === "string" && reservation.reservationImageUrl.trim().length
            ? reservation.reservationImageUrl
            : null));

    const effectivePhotoUrl = draftPhotoUrl === undefined ? initialPhotoUrl : draftPhotoUrl;
    const previewPhotoUrl = effectivePhotoUrl || undefined;
    
    // [추가] 수정사항 확인 함수
    const hasChanges = () => {
        const photoChanged = draftPhotoUrl !== undefined;
        const titleChanged = draftTitle !== (reservation?.title || "");
        return photoChanged || titleChanged;
    };
    
    // [추가] 모달 닫기 핸들러 (수정사항 체크)
    const handleClose = () => {
        if (hasChanges()) {
            setShowCloseWarning(true);
        } else {
            onClose();
        }
    };
    
    // [추가] 저장 후 닫기 핸들러
    const handleSave = async () => {
        await onSavePhoto(effectivePhotoUrl ?? null);
        if (onSaveTitle && draftTitle !== reservation?.title) {
            await onSaveTitle(draftTitle);
        }
        setShowSuccessMessage(true);
        setTimeout(() => {
            setShowSuccessMessage(false);
            onClose();
        }, 1500);
    };

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
                        onClick={handleClose}
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
                                onClick={handleClose}
                                className="absolute right-4 top-4 w-9 h-9 rounded-lg border border-gray-200 bg-white text-gray-700 flex items-center justify-center hover:bg-gray-50 transition-colors"
                            >
                                <X size={16} />
                            </button>
                            <h2 className="text-3xl font-bold text-gray-900 text-center">Reservation Details</h2>
                        </div>

                        <div className="px-6 pb-4 max-h-[60vh] overflow-y-auto">
                            {/* [추가] 예약 제목 편집 섹션 */}
                            <div className="mb-4">
                                <label className="block text-xs font-semibold text-gray-600 mb-2">Reservation Title</label>
                                {editingTitle ? (
                                    <input
                                        type="text"
                                        value={draftTitle}
                                        onChange={(e) => setDraftTitle(e.target.value)}
                                        onBlur={() => setEditingTitle(false)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                                setEditingTitle(false);
                                            }
                                        }}
                                        autoFocus
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-black"
                                        placeholder="예약 제목을 입력하세요"
                                    />
                                ) : (
                                    <div
                                        onClick={() => setEditingTitle(true)}
                                        className="w-full px-3 py-2 border border-gray-200 rounded-lg cursor-pointer hover:border-gray-300 transition-colors"
                                    >
                                        <p className="text-sm font-medium text-gray-900">{draftTitle || "클릭하여 제목 입력"}</p>
                                    </div>
                                )}
                            </div>
                            
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
                                        <div className="text-lg font-bold">Reservation Image</div>
                                        <div className="text-xs text-gray-700 mt-1">(Click here to upload if no image is available)</div>
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
                                    Change Image
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
                                        Remove photo
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="px-6 pb-6">
                            <button
                                type="button"
                                onClick={handleSave}
                                disabled={showSuccessMessage}
                                className="w-full bg-black text-white py-3 rounded-lg text-sm font-semibold disabled:opacity-50 transition-opacity"
                            >
                                Save
                            </button>
                        </div>
                        
                        {/* [추가] 저장 완료 메시지 */}
                        <AnimatePresence>
                            {showSuccessMessage && (
                                <motion.div
                                    className="absolute inset-0 z-20 flex items-center justify-center bg-white/95 rounded-xl"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                >
                                    <div className="text-center">
                                        <div className="mb-2 text-4xl">✅</div>
                                        <p className="text-lg font-semibold text-gray-900">변경하신 내역이 저장되었습니다!</p>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </motion.div>
                    
                    {/* [추가] 닫기 경고 팝업 */}
                    <AnimatePresence>
                        {showCloseWarning && (
                            <motion.div
                                className="fixed inset-0 z-[70] flex items-center justify-center p-4"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                            >
                                <div className="absolute inset-0 bg-black/60" onClick={() => setShowCloseWarning(false)} />
                                <motion.div
                                    className="relative z-10 w-full max-w-xs rounded-xl bg-white p-6 shadow-2xl"
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.95 }}
                                >
                                    <h3 className="text-lg font-bold text-gray-900 mb-3 text-center">저장 확인</h3>
                                    <p className="text-sm text-gray-600 mb-6 text-center">
                                        저장하지 않은 변경사항이 있습니다.<br />저장하시겠습니까?
                                    </p>
                                    <div className="flex gap-3">
                                        <button
                                            type="button"
                                            onClick={async () => {
                                                setShowCloseWarning(false);
                                                await handleSave();
                                            }}
                                            className="flex-1 bg-black text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors"
                                        >
                                            네
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setShowCloseWarning(false);
                                                onClose();
                                            }}
                                            className="flex-1 bg-gray-200 text-gray-900 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-300 transition-colors"
                                        >
                                            아니요
                                        </button>
                                    </div>
                                </motion.div>
                            </motion.div>
                        )}
                    </AnimatePresence>

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
