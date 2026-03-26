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

    const inputClass = "w-full h-12 rounded-2xl border-none bg-black/[0.03] px-4 text-[13px] font-medium text-gray-800 transition-all duration-300 focus:outline-none focus:bg-black/[0.05] focus:ring-[1px] focus:ring-black/[0.08] shadow-[inset_0_2px_4px_rgba(0,0,0,0.02)] cursor-pointer";

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
                        transition={{ duration: 0.3, ease: "easeInOut" }}
                        className="fixed inset-0 bg-black/30 backdrop-blur-md z-[9998]"
                        onClick={handleClose}
                    />

                    {/*
                     * 단일 모달 — 화면 크기 무관하게 항상 중앙 팝업
                     * 화면이 좁아지면 p-4 여백 유지하며 팝업 크기가 줄어듦
                     * 내용이 길면 max-h-[90vh] + overflow-y-auto 로 스크롤 처리
                     */}
                    <motion.div
                        key="modal"
                        initial={{ opacity: 0, scale: 0.9, y: 30 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        transition={{ type: "spring", damping: 25, stiffness: 300 }}
                        className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
                        onClick={handleClose}
                    >
                        <div
                            className="relative w-full max-w-sm max-h-[90vh] overflow-y-auto p-8 rounded-[2rem] bg-white/95 backdrop-blur-3xl border border-white shadow-[0_16px_40px_-8px_rgba(0,0,0,0.15)]"
                            onClick={(e) => e.stopPropagation()}
                        >
                            {loading && (
                                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm rounded-[2rem] gap-3">
                                    <Loader2 className="w-7 h-7 animate-spin text-black" />
                                    <p className="text-xs font-bold text-gray-500">{t("chat.creatingRoom")}</p>
                                </div>
                            )}

                            <button
                                onClick={handleClose}
                                className="absolute top-6 right-6 p-2.5 text-gray-400 hover:text-gray-800 hover:bg-gray-100/70 rounded-full transition-all bg-transparent"
                            >
                                <X size={16} />
                            </button>

                            <div className="flex items-center gap-2 mb-5">
                                <div className="w-8 h-8 bg-black rounded-xl flex items-center justify-center shadow-lg transition-transform hover:scale-110">
                                    <CalendarDays size={14} className="text-white" />
                                </div>
                                <h2 className="text-[14px] font-bold text-[#8b98a5] uppercase mt-0.5">
                                    TRIP CONTEXT
                                </h2>
                            </div>

                            <div className="grid grid-cols-2 gap-4 mt-5">
                                <div>
                                    <label className="block text-[10px] font-bold text-[#8b98a5] uppercase mb-1.5 pl-1">
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
                                    <label className="block text-[10px] font-bold text-[#8b98a5] uppercase mb-1.5 pl-1">
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

                            <div className="mt-6 space-y-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="text-[10px] font-bold text-[#8b98a5] uppercase pl-1">
                                        {t("tripContext.travelers")}
                                    </span>
                                </div>

                                <div className="flex items-center justify-between p-5 rounded-[1.25rem] border border-white/60 bg-[#f5f7f9]/60 backdrop-blur-md shadow-[inset_0_2px_4px_rgba(255,255,255,0.7)]">
                                    <div>
                                        <p className="text-sm font-semibold text-gray-900">{t("tripContext.adults")}</p>
                                        <p className="text-[10px] font-medium uppercase text-[#8b98a5] mt-0.5">{t("tripContext.adultsAge")}</p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button onClick={() => setAdultCount((v) => Math.max(1, v - 1))} className="w-8 h-8 rounded-full bg-white/80 shadow-sm border border-white hover:bg-white hover:scale-105 transition-all font-medium text-gray-700">-</button>
                                        <span className="w-6 text-center text-[13px] font-semibold">{adultCount}</span>
                                        <button onClick={() => setAdultCount((v) => Math.min(99, v + 1))} className="w-8 h-8 rounded-full bg-white/80 shadow-sm border border-white hover:bg-white hover:scale-105 transition-all font-medium text-gray-700">+</button>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between p-5 rounded-[1.25rem] border border-white/60 bg-[#f5f7f9]/60 backdrop-blur-md shadow-[inset_0_2px_4px_rgba(255,255,255,0.7)]">
                                    <div>
                                        <p className="text-sm font-semibold text-gray-900">{t("tripContext.children")}</p>
                                        <p className="text-[10px] font-medium uppercase text-[#8b98a5] mt-0.5">{t("tripContext.childrenAge")}</p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button onClick={() => setChildCount((v) => Math.max(0, v - 1))} className="w-8 h-8 rounded-full bg-white/80 shadow-sm border border-white hover:bg-white hover:scale-105 transition-all font-medium text-gray-700">-</button>
                                        <span className="w-6 text-center text-[13px] font-semibold">{childCount}</span>
                                        <button onClick={() => setChildCount((v) => Math.min(99, v + 1))} className="w-8 h-8 rounded-full bg-white/80 shadow-sm border border-white hover:bg-white hover:scale-105 transition-all font-medium text-gray-700">+</button>
                                    </div>
                                </div>
                            </div>

                            <button
                                onClick={handleTravelerConfirm}
                                disabled={!canProceed}
                                className={`mt-6 w-full h-13 py-3.5 rounded-2xl text-sm font-extrabold flex items-center justify-center gap-2 transition-all duration-300 tracking-wide ${canProceed
                                    ? "bg-gradient-to-r from-gray-900 to-black text-white hover:-translate-y-0.5 shadow-[0_8px_16px_-4px_rgba(0,0,0,0.3)] hover:shadow-[0_12px_24px_-6px_rgba(0,0,0,0.4)] active:scale-[0.98]"
                                    : "bg-black/[0.04] text-gray-300 cursor-not-allowed"
                                    }`}
                            >
                                {isEdit ? t("tripContext.saveEdit") : t("tripContext.startChat")}
                                {isEdit ? <Check size={16} strokeWidth={2.5} /> : <ArrowRight size={16} strokeWidth={2.5} />}
                            </button>

                            {!isEdit && (
                                <button
                                    onClick={() => {
                                        onConfirm({ travelDuration: "", adultCount: 0, childCount: 0 });
                                        resetState();
                                    }}
                                    className="mt-4 w-full h-11 flex items-center justify-center gap-1.5 text-xs font-bold text-gray-400 hover:text-gray-700 hover:bg-gray-50 rounded-xl transition-all"
                                >
                                    {t("tripContext.skipAndStart")}
                                    <ArrowRight size={13} strokeWidth={2.5} />
                                </button>
                            )}
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
