"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ChevronLeft, ChevronRight, Users, ArrowRight, CalendarDays, Loader2 } from "lucide-react";

// ──────────────────────────────────────────────
// 타입
// ──────────────────────────────────────────────

export interface TripContext {
    travelDuration: string; // "2026-03-03 ~ 2026-03-07"
    groupSize: string;      // "2명 (커플/친구)"
}

interface TripContextModalProps {
    isOpen: boolean;
    onConfirm: (context: TripContext) => void;
    onClose: () => void;
    /** true이면 방 생성 API 대기 중 — 모달을 닫지 않고 스피너 표시 */
    loading?: boolean;
}

// ──────────────────────────────────────────────
// 인원 선택지
// ──────────────────────────────────────────────

const GROUP_OPTIONS = [
    { label: "혼자", value: "혼자 (1명)", emoji: "🧍" },
    { label: "2명", value: "2명 (커플/친구)", emoji: "👫" },
    { label: "3~5명", value: "3~5명 (소그룹)", emoji: "👥" },
    { label: "6명+", value: "6명 이상 (단체)", emoji: "🎉" },
];

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

// ──────────────────────────────────────────────
// 날짜 유틸
// ──────────────────────────────────────────────

const toStr = (y: number, m: number, d: number) =>
    `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;

const today = (() => {
    const now = new Date();
    return toStr(now.getFullYear(), now.getMonth() + 1, now.getDate());
})();

// ──────────────────────────────────────────────
// 소형 캘린더 컴포넌트
// ──────────────────────────────────────────────

interface MiniCalendarProps {
    year: number;
    month: number; // 1-12
    startDate: string | null;
    endDate: string | null;
    hoverDate: string | null;
    onDateClick: (dateStr: string) => void;
    onHover: (dateStr: string | null) => void;
    onPrev: () => void;
    onNext: () => void;
}

function MiniCalendar({
    year, month, startDate, endDate, hoverDate,
    onDateClick, onHover, onPrev, onNext,
}: MiniCalendarProps) {
    // 해당 월의 1일이 무슨 요일인지
    const firstDay = new Date(year, month - 1, 1).getDay();
    const totalDays = new Date(year, month, 0).getDate();

    // 캘린더에 표시할 셀 배열 (빈 칸 + 날짜)
    const cells: (number | null)[] = [
        ...Array(firstDay).fill(null),
        ...Array.from({ length: totalDays }, (_, i) => i + 1),
    ];

    // 비교용 기준일: 두 번째 클릭 대기 중이면 hover 범위 미리보기
    const rangeEnd = endDate ?? hoverDate;

    const isStart = (ds: string) => ds === startDate;
    const isEnd = (ds: string) => ds === endDate;
    const isInRange = (ds: string) =>
        startDate && rangeEnd && ds > startDate && ds < rangeEnd;
    const isPast = (ds: string) => ds < today;

    return (
        <div className="select-none">
            {/* 월 헤더 */}
            <div className="flex items-center justify-between mb-4">
                <button
                    onClick={onPrev}
                    className="p-1.5 rounded-full hover:bg-gray-100 text-gray-400 hover:text-black transition-colors"
                >
                    <ChevronLeft size={16} />
                </button>
                <span className="text-sm font-semibold text-gray-800">
                    {year}년 {month}월
                </span>
                <button
                    onClick={onNext}
                    className="p-1.5 rounded-full hover:bg-gray-100 text-gray-400 hover:text-black transition-colors"
                >
                    <ChevronRight size={16} />
                </button>
            </div>

            {/* 요일 헤더 */}
            <div className="grid grid-cols-7 mb-1">
                {WEEKDAYS.map((w, i) => (
                    <div
                        key={w}
                        className={`text-center text-[10px] font-semibold py-1 ${i === 0 ? "text-red-400" : i === 6 ? "text-blue-400" : "text-gray-400"
                            }`}
                    >
                        {w}
                    </div>
                ))}
            </div>

            {/* 날짜 셀 */}
            <div className="grid grid-cols-7 gap-y-0.5">
                {cells.map((day, idx) => {
                    if (day === null) return <div key={`empty-${idx}`} />;

                    const ds = toStr(year, month, day);
                    const past = isPast(ds);
                    const start = isStart(ds);
                    const end_ = isEnd(ds);
                    const inRange = isInRange(ds);
                    const isToday = ds === today;

                    // 셀 배경: 시작·끝은 검정, 범위 내는 연회색
                    const bgClass = start || end_
                        ? "bg-black text-white"
                        : inRange
                            ? "bg-gray-100 text-gray-800"
                            : past
                                ? "text-gray-200 cursor-not-allowed"
                                : "text-gray-700 hover:bg-gray-100 cursor-pointer";

                    // 좌우 모서리 라운드 처리 (범위의 시작/끝)
                    const roundClass = start
                        ? "rounded-full"
                        : end_
                            ? "rounded-full"
                            : "";

                    return (
                        <div key={ds} className="flex justify-center">
                            <div
                                onClick={() => !past && onDateClick(ds)}
                                onMouseEnter={() => !past && onHover(ds)}
                                onMouseLeave={() => onHover(null)}
                                className={`w-8 h-8 flex items-center justify-center text-xs font-medium transition-all duration-100 ${bgClass} ${roundClass} ${isToday && !start && !end_ ? "ring-1 ring-black/30 rounded-full" : ""
                                    }`}
                            >
                                {day}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ──────────────────────────────────────────────
// 메인 모달
// ──────────────────────────────────────────────

export function TripContextModal({ isOpen, onConfirm, onClose, loading = false }: TripContextModalProps) {
    const now = new Date();

    const [step, setStep] = useState<0 | 1>(0);

    // 캘린더 표시 월
    const [calYear, setCalYear] = useState(now.getFullYear());
    const [calMonth, setCalMonth] = useState(now.getMonth() + 1);

    // 선택된 날짜 범위
    const [startDate, setStartDate] = useState<string | null>(null);
    const [endDate, setEndDate] = useState<string | null>(null);
    const [hoverDate, setHoverDate] = useState<string | null>(null);

    // 주의: startDate만 있고 endDate 없는 상태가 "두 번째 클릭 대기" 상태
    const handleDateClick = (ds: string) => {
        if (!startDate || (startDate && endDate)) {
            // 처음 클릭 or 재선택 시작
            setStartDate(ds);
            setEndDate(null);
        } else {
            // 두 번째 클릭
            if (ds < startDate) {
                // 시작보다 앞 날짜 클릭 → 새로운 시작으로 교체
                setStartDate(ds);
                setEndDate(null);
            } else {
                setEndDate(ds);
            }
        }
    };

    const prevMonth = () => {
        if (calMonth === 1) { setCalYear(y => y - 1); setCalMonth(12); }
        else setCalMonth(m => m - 1);
    };
    const nextMonth = () => {
        if (calMonth === 12) { setCalYear(y => y + 1); setCalMonth(1); }
        else setCalMonth(m => m + 1);
    };

    const handleClose = () => {
        resetState();
        onClose();
    };

    const resetState = () => {
        setStep(0);
        setStartDate(null);
        setEndDate(null);
        setHoverDate(null);
        setCalYear(now.getFullYear());
        setCalMonth(now.getMonth() + 1);
    };

    const handleDateConfirm = () => {
        setStep(1);
    };

    const handleGroupSelect = (value: string) => {
        onConfirm({
            travelDuration: startDate && endDate ? `${startDate} ~ ${endDate}` : startDate ?? "",
            groupSize: value,
        });
        resetState();
    };

    // 날짜 표시 문자열
    const formatDisplay = (ds: string | null) => {
        if (!ds) return "선택 안 함";
        const [y, m, d] = ds.split("-");
        return `${y}. ${parseInt(m)}. ${parseInt(d)}.`;
    };

    const canProceed = !!startDate; // 출발일 최소 선택 필요

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* 오버레이 */}
                    <motion.div
                        key="backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
                        onClick={handleClose}
                    />

                    {/* 모달 */}
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
                            {/* 로딩 오버레이 — API 응답 대기 중 모달을 닫지 않고 스피너 표시 */}
                            {loading && (
                                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm rounded-3xl gap-3">
                                    <Loader2 className="w-7 h-7 animate-spin text-black" />
                                    <p className="text-xs font-medium text-gray-500">채팅방을 만드는 중...</p>
                                </div>
                            )}
                            {/* 닫기 */}
                            <button
                                onClick={handleClose}
                                className="absolute top-5 right-5 p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
                            >
                                <X size={16} />
                            </button>

                            {/* 스텝 바 */}
                            <div className="flex gap-2 mb-6">
                                <div className="h-1 flex-1 rounded-full bg-black" />
                                <div className={`h-1 flex-1 rounded-full transition-colors duration-300 ${step >= 1 ? "bg-black" : "bg-gray-100"}`} />
                            </div>

                            <AnimatePresence mode="wait">
                                {/* ── STEP 0: 캘린더 날짜 선택 ── */}
                                {step === 0 && (
                                    <motion.div
                                        key="step-calendar"
                                        initial={{ opacity: 0, x: 30 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: -30 }}
                                        transition={{ duration: 0.2 }}
                                    >
                                        <div className="flex items-center gap-2 mb-1">
                                            <div className="w-8 h-8 bg-gray-100 rounded-xl flex items-center justify-center">
                                                <CalendarDays size={14} className="text-gray-600" />
                                            </div>
                                            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                                                Step 1 of 2
                                            </span>
                                        </div>
                                        <h2 className="text-xl font-serif font-medium text-gray-900 mb-1">
                                            여행 날짜를 선택해주세요
                                        </h2>
                                        <p className="text-xs text-gray-400 mb-5">
                                            출발일 → 귀국일 순서로 클릭하세요
                                        </p>

                                        {/* 캘린더 */}
                                        <MiniCalendar
                                            year={calYear}
                                            month={calMonth}
                                            startDate={startDate}
                                            endDate={endDate}
                                            hoverDate={hoverDate}
                                            onDateClick={handleDateClick}
                                            onHover={setHoverDate}
                                            onPrev={prevMonth}
                                            onNext={nextMonth}
                                        />

                                        {/* 선택된 날짜 요약 */}
                                        <div className="mt-5 flex items-center gap-2 px-1">
                                            <div className="flex-1 text-center">
                                                <p className="text-[9px] font-bold text-gray-400 uppercase tracking-widest mb-0.5">출발</p>
                                                <p className={`text-sm font-semibold ${startDate ? "text-black" : "text-gray-300"}`}>
                                                    {formatDisplay(startDate)}
                                                </p>
                                            </div>
                                            <ChevronRight size={14} className="text-gray-300 flex-shrink-0" />
                                            <div className="flex-1 text-center">
                                                <p className="text-[9px] font-bold text-gray-400 uppercase tracking-widest mb-0.5">귀국</p>
                                                <p className={`text-sm font-semibold ${endDate ? "text-black" : "text-gray-300"}`}>
                                                    {formatDisplay(endDate)}
                                                </p>
                                            </div>
                                        </div>

                                        {/* 다음 버튼 */}
                                        <button
                                            onClick={handleDateConfirm}
                                            disabled={!canProceed}
                                            className={`mt-5 w-full py-3 rounded-2xl text-sm font-semibold flex items-center justify-center gap-2 transition-all duration-200 ${canProceed
                                                ? "bg-black text-white hover:bg-gray-800 active:scale-[0.98]"
                                                : "bg-gray-100 text-gray-300 cursor-not-allowed"
                                                }`}
                                        >
                                            다음으로
                                            <ArrowRight size={15} />
                                        </button>
                                    </motion.div>
                                )}

                                {/* ── STEP 1: 인원 선택 ── */}
                                {step === 1 && (
                                    <motion.div
                                        key="step-group"
                                        initial={{ opacity: 0, x: 30 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: -30 }}
                                        transition={{ duration: 0.2 }}
                                    >
                                        <div className="flex items-center gap-2 mb-1">
                                            <div className="w-8 h-8 bg-gray-100 rounded-xl flex items-center justify-center">
                                                <Users size={14} className="text-gray-600" />
                                            </div>
                                            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                                                Step 2 of 2
                                            </span>
                                        </div>
                                        <h2 className="text-xl font-serif font-medium text-gray-900 mb-1">
                                            몇 명이서 여행하시나요?
                                        </h2>
                                        <p className="text-xs text-gray-400 mb-6">
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

                                        <button
                                            onClick={() => setStep(0)}
                                            className="mt-5 w-full text-xs text-gray-400 hover:text-gray-700 transition-colors py-2"
                                        >
                                            ← 날짜 다시 선택
                                        </button>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* 건너뛰기 */}
                            <button
                                onClick={() => { onConfirm({ travelDuration: "", groupSize: "" }); resetState(); }}
                                className="mt-5 w-full flex items-center justify-center gap-1 text-xs text-gray-300 hover:text-gray-500 transition-colors"
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
