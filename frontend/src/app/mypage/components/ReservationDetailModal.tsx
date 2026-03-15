"use client";

import { useRef, useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, ScanText, Loader2 } from "lucide-react";
import type { ReservationItem } from "../types";
import { ocrReservationImage } from "@/services/api";

// 카테고리 목록 (사용자가 선택 가능)
const CATEGORY_OPTIONS = [
    { value: "transportation", label: "✈️ 교통" },
    { value: "hotel", label: "🏨 호텔" },
    { value: "activity", label: "🎭 공연/활동" },
    { value: "restaurant", label: "🍽️ 식당" },
    { value: "etc", label: "📋 기타" },
] as const;

export function ReservationDetailModal({
    open,
    reservation,
    photoUrl,
    onSavePhoto,
    onSaveTitle,
    onSaveDate,    // [추가] 날짜+시간 저장 콜백
    onSaveCategory, // [추가] 카테고리 저장 콜백
    onClose,
}: {
    open: boolean;
    reservation: ReservationItem | null;
    photoUrl?: string;
    onSavePhoto: (nextUrl: string | null) => Promise<void> | void;
    onSaveTitle?: (newTitle: string) => Promise<void> | void;
    onSaveDate?: (newDate: string | null) => Promise<void> | void; // [추가] "YYYY-MM-DD" 형태
    onSaveCategory?: (newCategory: string) => Promise<void> | void;
    onClose: () => void;
}) {
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    // undefined: unchanged, string: new image, null: removed
    const [draftPhotoUrl, setDraftPhotoUrl] = useState<string | null | undefined>(undefined);

    // [추가] 날짜 편집 상태 (날짜만, DB는 Date 타입)
    const [draftDate, setDraftDate] = useState<string>(""); // "YYYY-MM-DD"

    // [추가] 카테고리 상태
    const [draftCategory, setDraftCategory] = useState<string>(reservation?.category || "etc");

    // 제목 편집 상태
    const [editingTitle, setEditingTitle] = useState(false);
    const [draftTitle, setDraftTitle] = useState(reservation?.title || "");

    const [previewOpen, setPreviewOpen] = useState(false);

    // [추가] OCR 로딩 상태 및 결과 메시지
    const [isOcrLoading, setIsOcrLoading] = useState(false);
    const [ocrMessage, setOcrMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

    // 닫기 경고 및 저장 완료 메시지 상태
    const [showCloseWarning, setShowCloseWarning] = useState(false);
    const [showSuccessMessage, setShowSuccessMessage] = useState(false);

    // reservation이 변경될 때 상태 업데이트
    useEffect(() => {
        if (reservation?.title) setDraftTitle(reservation.title);
        if (reservation?.category) setDraftCategory(reservation.category);

        // 기존 date를 YYYY-MM-DD / HH:MM으로 파싱
        // 주의: reservation.details에 Date 정보가 없으면 dateLabel을 파싱
        setDraftDate("");
    }, [reservation?.title, reservation?.category]);

    const initialPhotoUrl = (typeof photoUrl === "string" && photoUrl.trim().length
        ? photoUrl
        : (typeof reservation?.reservationImageUrl === "string" && reservation.reservationImageUrl.trim().length
            ? reservation.reservationImageUrl
            : null));

    const effectivePhotoUrl = draftPhotoUrl === undefined ? initialPhotoUrl : draftPhotoUrl;
    const previewPhotoUrl = effectivePhotoUrl || undefined;

    // 수정사항 확인 함수
    const hasChanges = () => {
        const photoChanged = draftPhotoUrl !== undefined;
        const titleChanged = draftTitle !== (reservation?.title || "");
        const dateChanged = draftDate !== "";
        const categoryChanged = draftCategory !== (reservation?.category || "etc");
        return photoChanged || titleChanged || dateChanged || categoryChanged;
    };

    // 모달 닫기 핸들러 (수정사항 체크)
    const handleClose = () => {
        if (hasChanges()) {
            setShowCloseWarning(true);
        } else {
            onClose();
        }
    };

    // 저장 후 닫기 핸들러
    const handleSave = async () => {
        await onSavePhoto(effectivePhotoUrl ?? null);

        if (onSaveTitle && draftTitle !== reservation?.title) {
            await onSaveTitle(draftTitle);
        }

        // [추가] 날짜 저장 (Date 타입 — 날짜만)
        if (onSaveDate && draftDate) {
            await onSaveDate(draftDate);
        }

        // [추가] 카테고리 저장
        if (onSaveCategory && draftCategory !== (reservation?.category || "etc")) {
            await onSaveCategory(draftCategory);
        }

        setShowSuccessMessage(true);
        setTimeout(() => {
            setShowSuccessMessage(false);
            onClose();
        }, 1500);
    };

    // [추가] 현재 업로드된 이미지로 OCR 실행
    const handleOcr = async () => {
        if (!effectivePhotoUrl) return;
        setIsOcrLoading(true);
        setOcrMessage(null);

        try {
            // base64 Data URL → File 객체로 변환 (백엔드가 File을 기대함)
            let file: File;
            if (effectivePhotoUrl.startsWith("data:image/")) {
                const res = await fetch(effectivePhotoUrl);
                const blob = await res.blob();
                file = new File([blob], "ticket.jpg", { type: blob.type || "image/jpeg" });
            } else {
                // 이미 서버에 올라간 URL인 경우 → 다시 fetch해서 blob으로 변환
                const res = await fetch(effectivePhotoUrl);
                const blob = await res.blob();
                file = new File([blob], "ticket.jpg", { type: blob.type || "image/jpeg" });
            }

            const result = await ocrReservationImage(file);

            if (result.date) {
                setDraftDate(result.date);
                setOcrMessage({
                    type: "success",
                    text: result.time
                        ? `날짜: ${result.date} (시간 ${result.time}도 인식됐지만 날짜만 저장됩니다)`
                        : `날짜: ${result.date} 를 인식했어요!`,
                });
            } else {
                setOcrMessage({
                    type: "error",
                    text: result.error || "날짜를 찾지 못했어요. 이미지를 확인해 주세요.",
                });
            }
        } catch (e) {
            setOcrMessage({ type: "error", text: "OCR 요청 중 오류가 발생했어요." });
            console.error(e);
        } finally {
            setIsOcrLoading(false);
        }
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
                        aria-label="닫기"
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
                        {/* 헤더 */}
                        <div className="relative p-6 pb-4">
                            <button
                                type="button"
                                aria-label="닫기"
                                onClick={handleClose}
                                className="absolute right-4 top-4 w-9 h-9 rounded-lg border border-gray-200 bg-white text-gray-700 flex items-center justify-center hover:bg-gray-50 transition-colors"
                            >
                                <X size={16} />
                            </button>
                            <h2 className="text-3xl font-bold text-gray-900 text-center pr-12">예약 상세</h2>
                        </div>

                        <div className="px-6 pb-4 max-h-[70vh] overflow-y-auto space-y-4">
                            {/* 예약 제목 편집 */}
                            <div>
                                <label className="block text-xs font-semibold text-gray-600 mb-2">예약 제목</label>
                                {editingTitle ? (
                                    <input
                                        type="text"
                                        value={draftTitle}
                                        onChange={(e) => setDraftTitle(e.target.value)}
                                        onBlur={() => setEditingTitle(false)}
                                        onKeyDown={(e) => { if (e.key === 'Enter') setEditingTitle(false); }}
                                        autoFocus
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-black text-sm"
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

                            {/* 카테고리 선택 */}
                            <div>
                                <label className="block text-xs font-semibold text-gray-600 mb-2">카테고리</label>
                                <div className="flex flex-wrap gap-2">
                                    {CATEGORY_OPTIONS.map((opt) => (
                                        <button
                                            key={opt.value}
                                            type="button"
                                            onClick={() => setDraftCategory(opt.value)}
                                            className={`px-3 py-1.5 rounded-full text-[11px] font-semibold border transition-colors ${draftCategory === opt.value
                                                ? "bg-black text-white border-black"
                                                : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                                                }`}
                                        >
                                            {opt.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* 이미지 업로드 영역 */}
                            <div>
                                <label className="block text-xs font-semibold text-gray-600 mb-2">예약 이미지</label>

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
                                            // 새 이미지 업로드 시 OCR 메시지 초기화
                                            setOcrMessage(null);
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
                                    className="w-full rounded-xl border border-gray-200 bg-gray-100 text-gray-900 overflow-hidden"
                                    aria-label="예약 이미지 업로드"
                                >
                                    {previewPhotoUrl ? (
                                        <div className="h-[180px] bg-gray-100 flex items-center justify-center">
                                            <img src={previewPhotoUrl} alt="예약 이미지" className="w-full h-full object-contain" />
                                        </div>
                                    ) : (
                                        <div className="h-[140px] flex flex-col items-center justify-center">
                                            <div className="text-lg font-bold">예약 이미지</div>
                                            <div className="text-xs text-gray-500 mt-1">(이미지 없을 시 클릭하여 업로드)</div>
                                        </div>
                                    )}
                                </button>

                                <div className="mt-1.5 flex items-center justify-between gap-3">
                                    <button
                                        type="button"
                                        onClick={() => { setPreviewOpen(false); fileInputRef.current?.click(); }}
                                        className="text-[11px] font-semibold text-gray-600 hover:text-black"
                                    >
                                        이미지 변경
                                    </button>

                                    {/* [추가] OCR 버튼 — 이미지가 있을 때만 활성화 */}
                                    <button
                                        type="button"
                                        onClick={handleOcr}
                                        disabled={!effectivePhotoUrl || isOcrLoading}
                                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold border transition-colors ${effectivePhotoUrl && !isOcrLoading
                                            ? "bg-black text-white border-black hover:bg-gray-800"
                                            : "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed"
                                            }`}
                                    >
                                        {isOcrLoading
                                            ? <><Loader2 size={12} className="animate-spin" /> 분석 중...</>
                                            : <><ScanText size={12} /> OCR로 날짜 읽기</>
                                        }
                                    </button>
                                </div>

                                {/* OCR 결과 메시지 */}
                                <AnimatePresence>
                                    {ocrMessage && (
                                        <motion.div
                                            initial={{ opacity: 0, y: -4 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0 }}
                                            className={`mt-2 px-3 py-2 rounded-lg text-xs font-medium ${ocrMessage.type === "success"
                                                ? "bg-green-50 text-green-700 border border-green-200"
                                                : "bg-red-50 text-red-600 border border-red-200"
                                                }`}
                                        >
                                            {ocrMessage.text}
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>

                            {/* [추가] 날짜 편집 필드 (Date 타입 — 날짜만 저장) */}
                            <div>
                                <label className="block text-xs font-semibold text-gray-600 mb-2">
                                    예약 날짜
                                    <span className="ml-1 text-gray-400 font-normal">(OCR 인식 또는 직접 입력)</span>
                                </label>
                                <input
                                    type="date"
                                    value={draftDate}
                                    onChange={(e) => setDraftDate(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black"
                                />
                            </div>
                        </div>

                        {/* 저장 버튼 */}
                        <div className="px-6 pb-6">
                            <button
                                type="button"
                                onClick={handleSave}
                                disabled={showSuccessMessage}
                                className="w-full bg-black text-white py-3 rounded-lg text-sm font-semibold disabled:opacity-50 transition-opacity"
                            >
                                저장
                            </button>
                        </div>

                        {/* 저장 완료 메시지 */}
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

                    {/* 닫기 경고 팝업 */}
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
                                            onClick={async () => { setShowCloseWarning(false); await handleSave(); }}
                                            className="flex-1 bg-black text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors"
                                        >
                                            네
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => { setShowCloseWarning(false); onClose(); }}
                                            className="flex-1 bg-gray-200 text-gray-900 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-300 transition-colors"
                                        >
                                            아니요
                                        </button>
                                    </div>
                                </motion.div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* 이미지 풀스크린 미리보기 */}
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
                                    aria-label="미리보기 닫기"
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
                                        aria-label="미리보기 닫기"
                                        onClick={() => setPreviewOpen(false)}
                                        className="absolute right-3 top-3 w-8 h-8 rounded-full border border-white/30 text-white bg-black/40 flex items-center justify-center"
                                    >
                                        <X size={14} />
                                    </button>
                                    <div className="w-full h-[80vh] max-h-[80vh] flex items-center justify-center">
                                        <img src={previewPhotoUrl} alt="원본 예약 이미지" className="max-w-full max-h-full object-contain" />
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
