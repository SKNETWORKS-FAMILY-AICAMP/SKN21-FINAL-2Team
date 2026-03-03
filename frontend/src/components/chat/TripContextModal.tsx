"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Calendar, Users, ArrowRight } from "lucide-react";

// ──────────────────────────────────────────────
// 타입 정의
// ──────────────────────────────────────────────

export interface TripContext {
    travelDuration: string; // 예: "당일치기", "1박 2일" 등
    groupSize: string;      // 예: "혼자", "2명" 등
}

interface TripContextModalProps {
    isOpen: boolean;
    onConfirm: (context: TripContext) => void;
    onClose: () => void;
}

// ──────────────────────────────────────────────
// 선택지 데이터
// ──────────────────────────────────────────────

const DURATION_OPTIONS = [
    { label: "당일치기", value: "당일치기", emoji: "☀️" },
    { label: "1박 2일", value: "1박 2일", emoji: "🌙" },
    { label: "2박 3일", value: "2박 3일", emoji: "🌙🌙" },
    { label: "3박 4일+", value: "3박 4일 이상", emoji: "✈️" },
];

const GROUP_OPTIONS = [
    { label: "혼자", value: "혼자 (1명)", emoji: "🧍" },
    { label: "2명", value: "2명 (커플/친구)", emoji: "👫" },
    { label: "3~5명", value: "3~5명 (소그룹)", emoji: "👥" },
    { label: "6명+", value: "6명 이상 (단체)", emoji: "🎉" },
];

// ──────────────────────────────────────────────
// 컴포넌트
// ──────────────────────────────────────────────

export function TripContextModal({ isOpen, onConfirm, onClose }: TripContextModalProps) {
    // 주의: step은 0(일정 선택) → 1(인원 선택) 순서로 진행됩니다
    const [step, setStep] = useState<0 | 1>(0);
    const [travelDuration, setTravelDuration] = useState<string>("");
    const [groupSize, setGroupSize] = useState<string>("");

    // 모달이 닫힐 때 상태 초기화
    const handleClose = () => {
        setStep(0);
        setTravelDuration("");
        setGroupSize("");
        onClose();
    };

    // 일정 선택 후 다음 스텝으로
    const handleDurationSelect = (value: string) => {
        setTravelDuration(value);
        setStep(1);
    };

    // 인원 선택 후 완료 → 부모로 context 전달
    const handleGroupSelect = (value: string) => {
        setGroupSize(value);
        onConfirm({ travelDuration, groupSize: value });
        // 주의: onConfirm 호출 후 상태 초기화해서 다음 사용에 대비
        setStep(0);
        setTravelDuration("");
        setGroupSize("");
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* 배경 오버레이 */}
                    <motion.div
                        key="backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
                        onClick={handleClose}
                    />

                    {/* 모달 본체 */}
                    <motion.div
                        key="modal"
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        transition={{ duration: 0.25, ease: "easeOut" }}
                        className="fixed inset-0 flex items-center justify-center z-50 p-4"
                        // 주의: 이 div는 클릭 이벤트가 backdrop까지 전파되지 않도록 막아야 합니다
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md p-8 relative">
                            {/* 닫기 버튼 */}
                            <button
                                onClick={handleClose}
                                className="absolute top-5 right-5 p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
                            >
                                <X size={16} />
                            </button>

                            {/* 스텝 인디케이터 */}
                            <div className="flex gap-2 mb-8">
                                <div className={`h-1 flex-1 rounded-full transition-colors duration-300 ${step >= 0 ? "bg-black" : "bg-gray-100"}`} />
                                <div className={`h-1 flex-1 rounded-full transition-colors duration-300 ${step >= 1 ? "bg-black" : "bg-gray-100"}`} />
                            </div>

                            <AnimatePresence mode="wait">
                                {/* ── STEP 0: 여행 일정 선택 ── */}
                                {step === 0 && (
                                    <motion.div
                                        key="step-duration"
                                        initial={{ opacity: 0, x: 30 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: -30 }}
                                        transition={{ duration: 0.2 }}
                                    >
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="w-9 h-9 bg-gray-100 rounded-2xl flex items-center justify-center">
                                                <Calendar size={16} className="text-gray-600" />
                                            </div>
                                            <span className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
                                                Step 1 of 2
                                            </span>
                                        </div>
                                        <h2 className="text-2xl font-serif font-medium text-gray-900 mb-1">
                                            여행 기간이 어떻게 되나요?
                                        </h2>
                                        <p className="text-sm text-gray-400 mb-8">
                                            Triver가 더 알맞은 일정을 추천해드릴게요
                                        </p>

                                        <div className="grid grid-cols-2 gap-3">
                                            {DURATION_OPTIONS.map((opt) => (
                                                <button
                                                    key={opt.value}
                                                    onClick={() => handleDurationSelect(opt.value)}
                                                    className="group flex flex-col items-center gap-2 p-5 rounded-2xl border border-gray-100 bg-gray-50 hover:border-black hover:bg-black hover:text-white transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-2"
                                                >
                                                    <span className="text-2xl">{opt.emoji}</span>
                                                    <span className="text-sm font-semibold">{opt.label}</span>
                                                </button>
                                            ))}
                                        </div>
                                    </motion.div>
                                )}

                                {/* ── STEP 1: 여행 인원 선택 ── */}
                                {step === 1 && (
                                    <motion.div
                                        key="step-group"
                                        initial={{ opacity: 0, x: 30 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: -30 }}
                                        transition={{ duration: 0.2 }}
                                    >
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="w-9 h-9 bg-gray-100 rounded-2xl flex items-center justify-center">
                                                <Users size={16} className="text-gray-600" />
                                            </div>
                                            <span className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
                                                Step 2 of 2
                                            </span>
                                        </div>
                                        <h2 className="text-2xl font-serif font-medium text-gray-900 mb-1">
                                            몇 명이서 여행하시나요?
                                        </h2>
                                        <p className="text-sm text-gray-400 mb-8">
                                            선택하시면 바로 채팅이 시작됩니다
                                        </p>

                                        <div className="grid grid-cols-2 gap-3">
                                            {GROUP_OPTIONS.map((opt) => (
                                                <button
                                                    key={opt.value}
                                                    onClick={() => handleGroupSelect(opt.value)}
                                                    className="group flex flex-col items-center gap-2 p-5 rounded-2xl border border-gray-100 bg-gray-50 hover:border-black hover:bg-black hover:text-white transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-2"
                                                >
                                                    <span className="text-2xl">{opt.emoji}</span>
                                                    <span className="text-sm font-semibold">{opt.label}</span>
                                                </button>
                                            ))}
                                        </div>

                                        {/* 이전 단계로 돌아가기 */}
                                        <button
                                            onClick={() => setStep(0)}
                                            className="mt-5 w-full text-xs text-gray-400 hover:text-gray-700 transition-colors py-2"
                                        >
                                            ← 이전으로
                                        </button>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* 선택 없이 건너뛰기 */}
                            <button
                                onClick={() => onConfirm({ travelDuration: "", groupSize: "" })}
                                className="mt-6 w-full flex items-center justify-center gap-1 text-xs text-gray-300 hover:text-gray-500 transition-colors"
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
