"use client";

import { useRef, useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, ScanText, Loader2 } from "lucide-react";
import type { ReservationItem } from "../types";
import { ocrReservationImage } from "@/services/api";
import { resolveImageUrl } from "@/lib/imageUrl";

// 카테고리 목록 (사용자가 선택 가능)
const CATEGORY_OPTIONS = [
    { value: "transportation", label: "✈️ 교통" },
    { value: "hotel", label: "🏨 호텔" },
    { value: "activity", label: "🎭 공연/활동" },
    { value: "restaurant", label: "🍽️ 식당" },
    { value: "etc", label: "📋 기타" },
] as const;

const CATEGORY_MAP: Record<string, string> = {
    transportation: "교통",
    hotel: "호텔",
    restaurant: "식당",
    activity: "공연/활동",
    etc: "기타",
};

const TEMPLATE_MAP: Record<string, string[]> = {
    transportation: ['날짜', '출발지', '출발시간', '도착지', '도착시간', '승차홈', '차량 번호', '좌석 번호'],
    hotel: ['숙소 이름', '체크인 날짜', '체크인 시간', '체크아웃 날짜', '체크아웃 시간', '방 호실'],
    activity: ['날짜', '이름', '시간', '장소', '좌석 번호'],
    restaurant: ['날짜', '식당이름', '예약시간', '예약자명', '예약 인원'],
    etc: ['예약내역', '시간', '예약자명']
};

export function ReservationDetailModal({
    open,
    reservation,
    photoUrl,
    onSavePhoto,
    onSaveTitle,
    onSaveCategory, // [추가] 카테고리 저장 콜백
    onSaveDetails,   // [추가] JSON 상세 저장 콜백
    onClose,
}: {
    open: boolean;
    reservation: ReservationItem | null;
    photoUrl?: string;
    onSavePhoto: (nextUrl: string | null) => Promise<void> | void;
    onSaveTitle?: (newTitle: string) => Promise<void> | void;
    onSaveCategory?: (newCategory: string) => Promise<void> | void;
    onSaveDetails?: (newDetails: Record<string, string>) => Promise<void> | void; // [추가] JSON 상세 저장
    onClose: (wasSaved: boolean, isNewDraft: boolean, shouldDeleteDraft?: boolean) => void;
}) {
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    // undefined: unchanged, string: new image, null: removed
    const [draftPhotoUrl, setDraftPhotoUrl] = useState<string | null | undefined>(undefined);

    // [추가] 날짜 편집 상태 (날짜만, DB는 Date 타입)
    const [draftDate, setDraftDate] = useState<string>(""); // "YYYY-MM-DD"

    const [draftCategory, setDraftCategory] = useState<string>(reservation?.category || "etc");
    const [draftDetails, setDraftDetails] = useState<Record<string, string>>({}); // [추가] 세부 정보 보관

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

    // [추가] 편집 모드 상태
    const [isEditMode, setIsEditMode] = useState(false);

    // open 되거나 reservation이 변경될 때 상태 초기화
    useEffect(() => {
        if (open) {
            setDraftTitle(reservation?.title || "");
            setDraftCategory(reservation?.category || "etc");
            setDraftPhotoUrl(undefined); // 새 이미지 초기화
            setDraftDate("");
            setEditingTitle(false);
            setOcrMessage(null);
            setShowSuccessMessage(false);

            const existingDetails = reservation?.details;
            let pDetails: Record<string, string> = {};
            if (Array.isArray(existingDetails)) {
                existingDetails.forEach(d => {
                    pDetails[d.label] = d.value;
                });
            }

            const cat = reservation?.category || "etc";

            if (Object.keys(pDetails).length === 0 && (!reservation?.title || reservation?.title === "Reservation" || reservation?.title === "새 예약")) {
                const newKeys = TEMPLATE_MAP[cat] || TEMPLATE_MAP["etc"];
                newKeys.forEach(k => { pDetails[k] = ""; });
                setIsEditMode(true);
            } else {
                setIsEditMode(false);
            }

            setDraftDetails(pDetails);
        }
    }, [open, reservation]);

    const initialPhotoUrl = (typeof photoUrl === "string" && photoUrl.trim().length
        ? photoUrl
        : (typeof reservation?.reservationImageUrl === "string" && reservation.reservationImageUrl.trim().length
            ? reservation.reservationImageUrl
            : null));

    const effectivePhotoUrl = draftPhotoUrl === undefined ? initialPhotoUrl : draftPhotoUrl;
    const previewPhotoUrl = effectivePhotoUrl ? resolveImageUrl(effectivePhotoUrl) : undefined;

    // 수정사항 확인 함수
    const hasChanges = () => {
        if (!isEditMode) return false;

        const photoChanged = draftPhotoUrl !== undefined;
        const initialTitle = reservation?.title || "";
        const titleChanged = Boolean(reservation) && draftTitle !== initialTitle;
        const initialCategory = reservation?.category || "etc";
        const categoryChanged = draftCategory !== initialCategory;

        // 원본 상세 정보 복구
        let originalDetails: Record<string, string> = {};
        if (Array.isArray(reservation?.details)) {
            reservation.details.forEach(d => {
                originalDetails[d.label] = d.value;
            });
        }

        // 새로 생성된 예약(빈 데이터)의 경우 초기 템플릿과 비교
        if (Object.keys(originalDetails).length === 0 && (!reservation?.title || reservation?.title === "Reservation" || reservation?.title === "새 예약")) {
            const newKeys = TEMPLATE_MAP[initialCategory] || TEMPLATE_MAP["etc"];
            newKeys.forEach(k => { originalDetails[k] = ""; });
        }

        let detailsChanged = false;
        const draftKeys = Object.keys(draftDetails);
        const originalKeys = Object.keys(originalDetails);

        if (draftKeys.length !== originalKeys.length) {
            detailsChanged = true;
        } else {
            for (const key of draftKeys) {
                if (draftDetails[key] !== originalDetails[key]) {
                    detailsChanged = true;
                    break;
                }
            }
        }

        return photoChanged || titleChanged || categoryChanged || detailsChanged;
    };

    // 모달 닫기 핸들러 (수정사항 체크)
    const handleClose = () => {
        const isNewDraft = reservation?.title === "새 예약" || reservation?.title === "Reservation";
        
        if (!isEditMode) {
            onClose(false, isNewDraft);
            return;
        }

        if (hasChanges()) {
            setShowCloseWarning(true);
        } else {
            onClose(false, isNewDraft);
        }
    };

    // 저장 후 닫기 핸들러
    const handleSave = async () => {
        await onSavePhoto(effectivePhotoUrl ?? null);

        if (onSaveTitle && draftTitle !== reservation?.title) {
            await onSaveTitle(draftTitle);
        }

        // [추가] 카테고리 저장
        if (onSaveCategory && draftCategory !== (reservation?.category || "etc")) {
            await onSaveCategory(draftCategory);
        }

        if (onSaveDetails && Object.keys(draftDetails).length > 0) {
            await onSaveDetails(draftDetails);
        }

        setShowSuccessMessage(true);
        setTimeout(() => {
            setShowSuccessMessage(false);
            const isNewDraft = reservation?.title === "새 예약" || reservation?.title === "Reservation";
            onClose(true, isNewDraft);
        }, 1500);
    };

    // [추가] 현재 업로드된 이미지로 OCR 실행
    const handleOcr = async () => {
        if (!effectivePhotoUrl) return;
        setIsOcrLoading(true);
        setOcrMessage(null);

        try {
            let result;

            if (effectivePhotoUrl.startsWith("data:image/")) {
                // 새로 업로드한 이미지: data: URL → File 변환 후 multipart 전송
                const res = await fetch(effectivePhotoUrl);
                const blob = await res.blob();
                const mimeType = blob.type || "image/jpeg";
                let extension = mimeType.split('/')[1] || "jpg";
                if (extension === "jpeg") extension = "jpg";
                const file = new File([blob], `ticket.${extension}`, { type: mimeType });
                result = await ocrReservationImage({ file, category: draftCategory });
            } else {
                // 저장된 이미지: S3면 https:// URL로 변환해 전달, 로컬이면 상대경로 그대로 전달
                const resolvedForOcr = resolveImageUrl(effectivePhotoUrl);
                const ocrImagePath = resolvedForOcr.startsWith("http")
                    ? resolvedForOcr   // S3: 백엔드가 httpx로 다운로드
                    : effectivePhotoUrl; // 로컬: 백엔드가 파일시스템에서 직접 읽음
                result = await ocrReservationImage({ imagePath: ocrImagePath, category: draftCategory });
            }

            if (result.date) {
                // [추가] 날짜를 찾았다면 제목을 "카테고리명 YYYY-MM-DD" 형태로 자동 덮어쓰기
                const autoTitle = `${CATEGORY_MAP[draftCategory] || "예약"} ${result.date}`;
                setDraftTitle(autoTitle);

                if (result.details) {
                    setDraftDetails(result.details);
                }
                setOcrMessage({
                    type: "success",
                    text: "이미지를 인식했습니다. \n정보가 맞는지 확인해 주세요.",
                });
            } else {
                setOcrMessage({
                    type: "error",
                    text: "이미지를 인식하지 못 했습니다.",
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
                        className="relative z-10 w-full max-w-[96vw] sm:max-w-[480px] rounded-xl bg-white border border-gray-200 shadow-lg overflow-hidden flex flex-col"
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
                            <h2 className="text-3xl font-bold text-gray-900 text-center">예약 상세</h2>
                        </div>

                        <div className="px-6 pb-4 max-h-[70vh] overflow-y-auto space-y-4">
                            {/* 예약 제목 편집 */}
                            <div>
                                <label className="block text-xs font-semibold text-gray-600 mb-2">예약 제목</label>
                                {isEditMode ? (
                                    editingTitle ? (
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
                                            className="w-full px-3 py-2 border border-blue-200 bg-blue-50/50 rounded-lg cursor-pointer hover:border-blue-300 transition-colors"
                                        >
                                            <p className="text-sm font-medium text-gray-900">{draftTitle || "클릭하여 제목 입력"}</p>
                                        </div>
                                    )
                                ) : (
                                    <div className="w-full px-3 py-2 border border-transparent rounded-lg bg-gray-50">
                                        <p className="text-sm font-bold text-gray-900">{draftTitle}</p>
                                    </div>
                                )}
                            </div>

                            {/* 카테고리 선택 / 표시 */}
                            <div>
                                <label className="block text-xs font-semibold text-gray-600 mb-2">카테고리</label>
                                {isEditMode ? (
                                    <div className="flex flex-nowrap gap-2 overflow-x-auto pb-1">
                                        {CATEGORY_OPTIONS.map((opt) => (
                                            <button
                                                key={opt.value}
                                                type="button"
                                                onClick={() => {
                                                    setDraftCategory(opt.value);
                                                    // 새 카테고리의 템플릿 필드 가져오기
                                                    const newKeys = TEMPLATE_MAP[opt.value] || TEMPLATE_MAP["etc"];
                                                    const nextDetails: Record<string, string> = {};
                                                    
                                                    // 새 템플릿 키만 초기화 (같은 필드명이면 기존 값 유지, 없으면 빈 값)
                                                    newKeys.forEach(k => { 
                                                        nextDetails[k] = draftDetails[k] || ""; 
                                                    });
                                                    
                                                    // 다른 필드는 추가하지 않음 (필드 증가 방지)
                                                    setDraftDetails(nextDetails);
                                                }}
                                                className={`whitespace-nowrap px-3 py-1.5 rounded-full text-[11px] font-semibold border transition-colors ${draftCategory === opt.value
                                                    ? "bg-black text-white border-black"
                                                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                                                    }`}
                                            >
                                                {opt.label}
                                            </button>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="w-full px-3 py-2 bg-gray-50 border border-transparent rounded-lg">
                                        <p className="text-sm font-medium text-gray-700">{CATEGORY_MAP[draftCategory]}</p>
                                    </div>
                                )}
                            </div>

                            {/* 이미지 업로드 영역 */}
                            <div>
                                <label className="block text-xs font-semibold text-gray-600 mb-2">관련 이미지 / 티켓</label>

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
                                        if (isEditMode) fileInputRef.current?.click();
                                    }}
                                    className={`w-full rounded-xl overflow-hidden ${isEditMode ? "border border-blue-200 bg-blue-50/30" : "border border-gray-200 bg-gray-50"}`}
                                    aria-label="예약 이미지"
                                >
                                    {previewPhotoUrl ? (
                                        <div className="h-[180px] flex items-center justify-center">
                                            <img src={previewPhotoUrl} alt="예약 이미지" className="w-full h-full object-contain" />
                                        </div>
                                    ) : (
                                        <div className="h-[140px] flex flex-col items-center justify-center text-gray-400">
                                            <div className="text-lg font-bold text-gray-300">NO IMAGE</div>
                                            {isEditMode && <div className="text-xs mt-1">(클릭하여 업로드)</div>}
                                        </div>
                                    )}
                                </button>

                                {isEditMode && (
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
                                                : <><ScanText size={12} /> OCR로 데이터 읽기</>
                                            }
                                        </button>
                                    </div>
                                )}

                                {/* OCR 결과 메시지 */}
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

                            {/* [추가] 다이나믹 JSON 상세 정보 폼 */}
                            {Object.keys(draftDetails).length > 0 && (
                                <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-100">
                                    <h4 className="text-xs font-bold text-gray-800 mb-3 uppercase tracking-wider">상세 정보</h4>
                                    <div className="space-y-3">
                                        {Object.entries(draftDetails).map(([key, value]) => (
                                            <div key={key}>
                                                <label className="block text-[11px] font-semibold text-gray-500 mb-1">{key}</label>
                                                {isEditMode ? (
                                                    <div className="flex gap-2">
                                                        <input
                                                            type="text"
                                                            value={value || ""}
                                                            onChange={(e) => setDraftDetails(prev => ({ ...prev, [key]: e.target.value }))}
                                                            className="w-full px-3 py-2 bg-white border border-blue-200 rounded-lg text-sm focus:outline-none focus:border-blue-400 transition-colors"
                                                            placeholder="내용을 입력하세요"
                                                        />
                                                        <button
                                                            type="button"
                                                            onClick={() => {
                                                                const newDetails = { ...draftDetails };
                                                                delete newDetails[key];
                                                                setDraftDetails(newDetails);
                                                            }}
                                                            className="flex-shrink-0 px-2 py-2 text-gray-400 hover:text-red-500 rounded-lg border border-transparent hover:border-red-200 transition-colors"
                                                            aria-label={`${key} 삭제`}
                                                        >
                                                            <X size={16} />
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <div className="w-full px-3 py-2 bg-white border border-transparent rounded-lg text-sm font-medium text-gray-800">
                                                        {value || <span className="text-gray-300 font-normal">입력된 내용 없음</span>}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                        {isEditMode && (
                                            <div className="pt-2">
                                                <button
                                                    type="button"
                                                    onClick={() => {
                                                        const newKey = window.prompt("추가할 항목의 이름을 입력하세요 (예: 시간, 메모 등)");
                                                        if (newKey && newKey.trim() !== "") {
                                                            setDraftDetails(prev => ({ ...prev, [newKey.trim()]: "" }));
                                                        }
                                                    }}
                                                    className="w-full py-2 border border-dashed border-blue-300 rounded-lg text-xs font-semibold text-blue-600 hover:bg-blue-50 transition-colors"
                                                >
                                                    + 새로운 항목 추가
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* 저장 버튼 */}
                        <div className="px-6 pb-6">
                            {isEditMode ? (
                                <button
                                    type="button"
                                    onClick={handleSave}
                                    disabled={showSuccessMessage}
                                    className="w-full bg-black text-white py-3 rounded-lg text-sm font-semibold disabled:opacity-50 transition-opacity"
                                >
                                    저장
                                </button>
                            ) : (
                                <button
                                    type="button"
                                    onClick={() => setIsEditMode(true)}
                                    className="w-full py-3 bg-white border border-gray-300 text-gray-800 hover:bg-gray-50 rounded-lg text-sm font-semibold transition-colors shadow-sm"
                                >
                                    ✏️ 수정하기
                                </button>
                            )}
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
                                            onClick={() => { setShowCloseWarning(false); onClose(false, reservation?.title === "새 예약" || reservation?.title === "Reservation"); }}
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
