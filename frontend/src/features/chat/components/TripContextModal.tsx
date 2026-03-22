"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Users, ArrowRight, CalendarDays, Loader2, Check } from "lucide-react";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { useTranslation } from "@/i18n/useTranslation";

export interface TripContext {
    travelDuration: string; // "2026-03-03 ~ 2026-03-07"
    adultCount: number;
    childCount: number;
}

interface TripContextModalProps {
    isOpen: boolean;
    onConfirm: (context: TripContext) => void;
    onClose: () => void;
    /** true이면 방 생성 API 대기 중 — 모달을 닫지 않고 스피너 표시 */
    loading?: boolean;
    /** 수정 모드일 때 기존 값을 전달 */
    initialContext?: TripContext;
    /** true이면 수정 모드 — "채팅 시작" 대신 "수정 완료" 버튼, skip 숨김 */
    isEdit?: boolean;
}

const today = new Date();
today.setHours(0, 0, 0, 0);

const parseDate = (str: string): Date | null => {
    if (!str) return null;
    const [y, m, d] = str.split("-").map(Number);
    if (!y || !m || !d) return null;
    return new Date(y, m - 1, d);
};

const formatDate = (date: Date): string =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;

export function TripContextModal({ isOpen, onConfirm, onClose, loading = false, initialContext, isEdit = false }: TripContextModalProps) {
    const { t } = useTranslation();
    const [startDate, setStartDate] = useState<string>("");
    const [endDate, setEndDate] = useState<string>("");
    const [adultCount, setAdultCount] = useState<number>(1);
    const [childCount, setChildCount] = useState<number>(0);
    const endPickerRef = useRef<DatePicker>(null);

    // 수정 모드: 모달이 열릴 때 기존 값으로 초기화
    useEffect(() => {
        if (isOpen && initialContext) {
            const parts = initialContext.travelDuration?.split(" ~ ") ?? [];
            setStartDate(parts[0] ?? "");
            setEndDate(parts[1] ?? "");
            setAdultCount(initialContext.adultCount ?? 1);
            setChildCount(initialContext.childCount ?? 0);
        } else if (isOpen && !initialContext) {
            resetState();
        }
    // isOpen이 true로 바뀔 때만 실행
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen]);

    const resetState = () => {
        setStartDate("");
        setEndDate("");
        setAdultCount(1);
        setChildCount(0);
    };

    const handleClose = () => {
        resetState();
        onClose();
    };

    const handleTravelerConfirm = () => {
        onConfirm({
            travelDuration: startDate && endDate ? `${startDate} ~ ${endDate}` : startDate,
            adultCount: Math.max(1, adultCount),
            childCount: Math.max(0, childCount),
        });
        resetState();
    };

    const canProceed = !!startDate;
    const startDateObj = parseDate(startDate);
    const endDateObj = parseDate(endDate);
    const endMinDate = startDateObj ?? today;

    const inputClass = "w-full h-10 rounded-xl border border-gray-200 bg-gray-50 px-3 text-sm font-medium text-gray-800 focus:outline-none focus:ring-2 focus:ring-black/10 cursor-pointer";

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* 배경 딤 — 항상 표시 */}
                    <motion.div
                        key="backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[9998]"
                        onClick={handleClose}
                    />

                    {/*
                     * 단일 모달 — 화면 크기 무관하게 항상 중앙 팝업
                     * 화면이 좁아지면 p-4 여백 유지하며 팝업 크기가 줄어듦
                     * 내용이 길면 max-h-[90vh] + overflow-y-auto 로 스크롤 처리
                     */}
                    <motion.div
                        key="modal"
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        transition={{ duration: 0.25, ease: "easeOut" }}
                        className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
                        onClick={handleClose}
                    >
                        <div
                            className="relative bg-white rounded-3xl shadow-2xl w-full max-w-sm max-h-[90vh] overflow-y-auto p-7"
                            onClick={(e) => e.stopPropagation()}
                        >
                            {loading && (
                                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm rounded-3xl gap-3">
                                    <Loader2 className="w-7 h-7 animate-spin text-black" />
                                    <p className="text-xs font-medium text-gray-500">{t("chat.creatingRoom")}</p>
                                </div>
                            )}

                            <button
                                onClick={handleClose}
                                className="absolute top-5 right-5 p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
                            >
                                <X size={16} />
                            </button>

                            <div className="flex items-center gap-2 mb-1">
                                <div className="w-8 h-8 bg-gray-100 rounded-xl flex items-center justify-center">
                                    <CalendarDays size={14} className="text-gray-600" />
                                </div>
                                <span className="text-[10px] font-medium text-gray-400 uppercase tracking-widest">
                                    {t("tripContext.label")}
                                </span>
                            </div>
                            <h2 className="text-xl font-medium text-gray-900 mb-1">
                                {t("tripContext.heading")}
                            </h2>

                            <div className="grid grid-cols-2 gap-3 mt-4">
                                <div>
                                    <label className="block text-[10px] font-medium text-gray-400 uppercase tracking-widest mb-1">
                                        {t("tripContext.departure")}
                                    </label>
                                    <DatePicker
                                        selected={startDateObj}
                                        onChange={(date: Date | null) => {
                                            if (!date) return;
                                            const next = formatDate(date);
                                            setStartDate(next);
                                            if (endDate && next > endDate) setEndDate(next);
                                            setTimeout(() => endPickerRef.current?.setOpen(true), 50);
                                        }}
                                        minDate={today}
                                        dateFormat="yyyy-MM-dd"
                                        className={inputClass}
                                        placeholderText="YYYY-MM-DD"
                                        popperPlacement="bottom-start"
                                        showMonthDropdown
                                        showYearDropdown
                                        dropdownMode="select"
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-medium text-gray-400 uppercase tracking-widest mb-1">
                                        {t("tripContext.return")}
                                    </label>
                                    <DatePicker
                                        ref={endPickerRef}
                                        selected={endDateObj}
                                        onChange={(date: Date | null) => {
                                            if (!date) return;
                                            setEndDate(formatDate(date));
                                        }}
                                        minDate={endMinDate}
                                        dateFormat="yyyy-MM-dd"
                                        className={inputClass}
                                        placeholderText="YYYY-MM-DD"
                                        popperPlacement="bottom-end"
                                        showMonthDropdown
                                        showYearDropdown
                                        dropdownMode="select"
                                    />
                                </div>
                            </div>

                            <div className="mt-5 space-y-3">
                                <div className="flex items-center gap-2 mb-1">
                                    <div className="w-8 h-8 bg-gray-100 rounded-xl flex items-center justify-center">
                                        <Users size={14} className="text-gray-600" />
                                    </div>
                                    <span className="text-[10px] font-medium text-gray-400 uppercase tracking-widest">
                                        {t("tripContext.travelers")}
                                    </span>
                                </div>

                                <div className="flex items-center justify-between p-4 rounded-2xl border border-gray-100 bg-gray-50">
                                    <div>
                                        <p className="text-sm font-medium text-gray-900">{t("tripContext.adults")}</p>
                                        <p className="text-[11px] font-medium text-gray-400">{t("tripContext.adultsAge")}</p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button onClick={() => setAdultCount((v) => Math.max(1, v - 1))} className="w-8 h-8 rounded-full border border-gray-200 text-gray-600 hover:bg-gray-100 font-medium">-</button>
                                        <span className="w-6 text-center text-sm font-medium">{adultCount}</span>
                                        <button onClick={() => setAdultCount((v) => Math.min(99, v + 1))} className="w-8 h-8 rounded-full border border-gray-200 text-gray-600 hover:bg-gray-100 font-medium">+</button>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between p-4 rounded-2xl border border-gray-100 bg-gray-50">
                                    <div>
                                        <p className="text-sm font-medium text-gray-900">{t("tripContext.children")}</p>
                                        <p className="text-[11px] font-medium text-gray-400">{t("tripContext.childrenAge")}</p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button onClick={() => setChildCount((v) => Math.max(0, v - 1))} className="w-8 h-8 rounded-full border border-gray-200 text-gray-600 hover:bg-gray-100 font-medium">-</button>
                                        <span className="w-6 text-center text-sm font-medium">{childCount}</span>
                                        <button onClick={() => setChildCount((v) => Math.min(99, v + 1))} className="w-8 h-8 rounded-full border border-gray-200 text-gray-600 hover:bg-gray-100 font-medium">+</button>
                                    </div>
                                </div>
                            </div>

                            <button
                                onClick={handleTravelerConfirm}
                                disabled={!canProceed}
                                className={`mt-5 w-full py-3 rounded-2xl text-sm font-medium flex items-center justify-center gap-2 transition-all duration-200 ${canProceed
                                    ? "bg-black text-white hover:bg-gray-800 active:scale-[0.98]"
                                    : "bg-gray-100 text-gray-300 cursor-not-allowed"
                                    }`}
                            >
                                {isEdit ? t("tripContext.saveEdit") : t("tripContext.startChat")}
                                {isEdit ? <Check size={15} /> : <ArrowRight size={15} />}
                            </button>

                            {!isEdit && (
                                <button
                                    onClick={() => {
                                        onConfirm({ travelDuration: "", adultCount: 0, childCount: 0 });
                                        resetState();
                                    }}
                                    className="mt-5 w-full flex items-center justify-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-500 transition-colors"
                                >
                                    {t("tripContext.skipAndStart")}
                                    <ArrowRight size={12} />
                                </button>
                            )}
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
