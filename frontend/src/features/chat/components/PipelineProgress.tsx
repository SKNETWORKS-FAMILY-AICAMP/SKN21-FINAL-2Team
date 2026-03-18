"use client";

import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { useTranslation } from "@/i18n/useTranslation";

// 파이프라인 단계 정의 — label은 번역 키
const PIPELINE_STEPS = [
    { key: "image_analysis", labelKey: "pipeline.imageAnalysis" },
    { key: "intent", labelKey: "pipeline.intent" },
    { key: "planner", labelKey: "pipeline.planner" },
    { key: "geocoder", labelKey: "pipeline.geocoder" },
    { key: "retriever", labelKey: "pipeline.retriever" },
    { key: "retriever_retry", labelKey: "pipeline.retrieverRetry" },
    { key: "web_search", labelKey: "pipeline.webSearch" },
    { key: "executor", labelKey: "pipeline.executor" },
    { key: "executor_missing", labelKey: "pipeline.executorMissing" },
    { key: "executor_general", labelKey: "pipeline.executorGeneral" },
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
    const { t } = useTranslation();

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
                    const label = t(step.labelKey);
                    const text = isStepRunning ? t("pipeline.running", { label }) : t("pipeline.done", { label });

                    return (
                        <motion.span
                            key={step.key}
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
