"use client";

import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";

// 파이프라인 단계 정의
const PIPELINE_STEPS = [
    { key: "image_analysis", label: "이미지 분석" },
    { key: "intent", label: "의도 분석" },
    { key: "planner", label: "여행 계획 수립" },
    { key: "geocoder", label: "위치 좌표 확인" },
    { key: "retriever", label: "장소 검색" },
    { key: "retriever_retry", label: "반경 확대 후 장소 검색" },
    { key: "web_search", label: "웹 검색" },
    { key: "executor", label: "답변 생성" },
    { key: "executor_missing", label: "추가 정보 확인" },
    { key: "executor_general", label: "일반 답변 생성" },
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

    const visibleSteps = PIPELINE_STEPS.filter((step) => {
        const status = steps[step.key];
        return status === "running" || status === "done";
    });

    if (visibleSteps.length === 0) return null;

    const isRunning = visibleSteps.some((step) => steps[step.key] === "running");

    return (
        <div className="flex items-start gap-2.5 py-1">
            <Loader2
                size={16}
                className={`mt-[2px] flex-shrink-0 ${isRunning ? "animate-spin text-blue-500" : "text-gray-300"}`}
            />
            <div className="flex min-w-0 flex-col gap-0.5">
                {visibleSteps.map((step) => {
                    const status = steps[step.key];
                    const isStepRunning = status === "running";
                    const text = isStepRunning ? `${step.label} 중...` : `${step.label} 완료`;

                    return (
                        <motion.span
                            key={`${step.key}-${status}`}
                            initial={{ opacity: 0, y: 3 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.12, ease: "easeOut" }}
                            className={`text-[13px] font-medium ${
                                isStepRunning ? "text-gray-700" : "text-gray-400"
                            }`}
                        >
                            {text}
                        </motion.span>
                    );
                })}
            </div>
        </div>
    );
}

/**
 * 초기 상태 — intent를 running으로 설정하여 즉시 표시
 */
export function createInitialPipelineSteps(): PipelineSteps {
    return {
        image_analysis: "pending",
        intent: "running",
        planner: "pending",
        geocoder: "pending",
        retriever: "pending",
        retriever_retry: "pending",
        web_search: "pending",
        executor: "pending",
        executor_missing: "pending",
        executor_general: "pending",
    };
}
