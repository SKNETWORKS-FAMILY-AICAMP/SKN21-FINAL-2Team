"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Users, ArrowRight, CalendarDays, Loader2 } from "lucide-react";

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
}

const today = (() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
})();

export function TripContextModal({ isOpen, onConfirm, onClose, loading = false }: TripContextModalProps) {
    const [startDate, setStartDate] = useState<string>("");
    const [endDate, setEndDate] = useState<string>("");
    const [adultCount, setAdultCount] = useState<number>(1);
    const [childCount, setChildCount] = useState<number>(0);

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
    const endMin = startDate || today;

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div
                        key="backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
                        onClick={handleClose}
                    />

                    <motion.div
                        key="modal"
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        transition={{ duration: 0.25, ease: "easeOut" }}
                        className="fixed inset-0 flex items-center justify-center z-50 p-4"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="bg-white rounded-3xl shadow-2xl w-full max-w-sm p-7 relative">
                            {loading && (
                                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm rounded-3xl gap-3">
                                    <Loader2 className="w-7 h-7 animate-spin text-black" />
                                    <p className="text-xs font-medium text-gray-500">채팅방을 만드는 중...</p>
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
                                    Trip Context
                                </span>
                            </div>
                            <h2 className="text-xl font-medium text-gray-900 mb-1">
                                여행 날짜와 인원을 선택해주세요
                            </h2>
                            <div className="grid grid-cols-2 gap-3 mt-4">
                                <div>
                                    <label className="block text-[10px] font-medium text-gray-400 uppercase tracking-widest mb-1">
                                        출발
                                    </label>
                                    <input
                                        type="date"
                                        value={startDate}
                                        min={today}
                                        onChange={(e) => {
                                            const nextStart = e.target.value;
                                            setStartDate(nextStart);
                                            if (endDate && nextStart && endDate < nextStart) {
                                                setEndDate(nextStart);
                                            }
                                        }}
                                        className="w-full h-10 rounded-xl border border-gray-200 bg-gray-50 px-3 text-sm font-medium text-gray-800 focus:outline-none focus:ring-2 focus:ring-black/10"
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-medium text-gray-400 uppercase tracking-widest mb-1">
                                        귀국
                                    </label>
                                    <input
                                        type="date"
                                        value={endDate}
                                        min={endMin}
                                        onChange={(e) => setEndDate(e.target.value)}
                                        className="w-full h-10 rounded-xl border border-gray-200 bg-gray-50 px-3 text-sm font-medium text-gray-800 focus:outline-none focus:ring-2 focus:ring-black/10"
                                    />
                                </div>
                            </div>

                            <div className="mt-5 space-y-3">
                                <div className="flex items-center gap-2 mb-1">
                                    <div className="w-8 h-8 bg-gray-100 rounded-xl flex items-center justify-center">
                                        <Users size={14} className="text-gray-600" />
                                    </div>
                                    <span className="text-[10px] font-medium text-gray-400 uppercase tracking-widest">
                                        Travelers
                                    </span>
                                </div>

                                <div className="flex items-center justify-between p-4 rounded-2xl border border-gray-100 bg-gray-50">
                                    <div>
                                        <p className="text-sm font-medium text-gray-900">성인</p>
                                        <p className="text-[11px] font-medium text-gray-400">만 13세 이상</p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={() => setAdultCount((v) => Math.max(1, v - 1))}
                                            className="w-8 h-8 rounded-full border border-gray-200 text-gray-600 hover:bg-gray-100 font-medium"
                                        >
                                            -
                                        </button>
                                        <span className="w-6 text-center text-sm font-medium">{adultCount}</span>
                                        <button
                                            onClick={() => setAdultCount((v) => Math.min(99, v + 1))}
                                            className="w-8 h-8 rounded-full border border-gray-200 text-gray-600 hover:bg-gray-100 font-medium"
                                        >
                                            +
                                        </button>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between p-4 rounded-2xl border border-gray-100 bg-gray-50">
                                    <div>
                                        <p className="text-sm font-medium text-gray-900">어린이</p>
                                        <p className="text-[11px] font-medium text-gray-400">만 12세 이하</p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={() => setChildCount((v) => Math.max(0, v - 1))}
                                            className="w-8 h-8 rounded-full border border-gray-200 text-gray-600 hover:bg-gray-100 font-medium"
                                        >
                                            -
                                        </button>
                                        <span className="w-6 text-center text-sm font-medium">{childCount}</span>
                                        <button
                                            onClick={() => setChildCount((v) => Math.min(99, v + 1))}
                                            className="w-8 h-8 rounded-full border border-gray-200 text-gray-600 hover:bg-gray-100 font-medium"
                                        >
                                            +
                                        </button>
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
                                채팅 시작하기
                                <ArrowRight size={15} />
                            </button>

                            <button
                                onClick={() => {
                                    onConfirm({ travelDuration: "", adultCount: 0, childCount: 0 });
                                    resetState();
                                }}
                                className="mt-5 w-full flex items-center justify-center gap-1 text-xs font-medium text-gray-300 hover:text-gray-500 transition-colors"
                            >
                                건너뛰고 바로 시작하기
                                <ArrowRight size={12} />
                            </button>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
