"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Loader2, CheckCircle2 } from "lucide-react";

// 파이프라인 단계 정의
const PIPELINE_STEPS = [
    { key: "intent", label: "의도 분석" },
    { key: "planner", label: "여행 계획 수립" },
    { key: "retriever", label: "장소 검색" },
    { key: "executor", label: "답변 생성" },
    { key: "executor_missing", label: "추가 정보 확인" },
] as const;

export type StepStatus = "pending" | "running" | "done";

export interface PipelineSteps {
    [key: string]: StepStatus;
}

interface PipelineProgressProps {
    steps: PipelineSteps;
    visible: boolean;
}

export function PipelineProgress({ steps, visible }: PipelineProgressProps) {
    if (!visible) return null;

    // 활성화된(시작됐거나 완료된) 단계만 표시
    const visibleSteps = PIPELINE_STEPS.filter((step) => {
        const status = steps[step.key];
        return status === "running" || status === "done";
    });

    if (visibleSteps.length === 0) return null;

    return (
        <div className="flex flex-col gap-2 py-1">
            <AnimatePresence mode="popLayout">
                {visibleSteps.map((step) => {
                    const status = steps[step.key] || "pending";

                    return (
                        <motion.div
                            key={step.key}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -8 }}
                            transition={{ duration: 0.2, ease: "easeOut" }}
                            className="flex items-center gap-2.5"
                        >
                            {/* 아이콘: 로딩 스피너 or 완료 체크 */}
                            {status === "running" ? (
                                <Loader2 size={16} className="animate-spin text-blue-500" />
                            ) : (
                                <motion.div
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    transition={{ type: "spring", stiffness: 400, damping: 12 }}
                                >
                                    <CheckCircle2 size={16} className="text-emerald-500" />
                                </motion.div>
                            )}

                            {/* 상태 텍스트 */}
                            <span
                                className={`text-[13px] font-medium ${status === "running"
                                        ? "text-gray-700"
                                        : "text-gray-400"
                                    }`}
                            >
                                {step.label}
                                {status === "running" ? " 중..." : " 완료"}
                            </span>
                        </motion.div>
                    );
                })}
            </AnimatePresence>
        </div>
    );
}

/**
 * 초기 상태 — intent를 running으로 설정하여 즉시 표시
 */
export function createInitialPipelineSteps(): PipelineSteps {
    return {
        intent: "running",
        planner: "pending",
        retriever: "pending",
        executor: "pending",
    };
}
