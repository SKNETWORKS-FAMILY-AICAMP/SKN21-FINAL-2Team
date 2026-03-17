/**
 * Pipeline 단계 업데이트 및 표시 로직 테스트
 *
 * 검증 대상:
 * 1. updatePipelineStep 로직 — 새 단계 start 시 이전 running이 done으로 전환되는가
 * 2. PipelineProgress displayStep 선택 로직 — 올바른 단계 텍스트가 선택되는가
 */

import { createInitialPipelineSteps } from "@/features/chat/components/PipelineProgress";
import type { PipelineSteps, StepStatus } from "@/features/chat/components/PipelineProgress";

// useChatMessages의 updatePipelineStep 로직을 순수 함수로 추출하여 테스트
function applyStep(prev: PipelineSteps, step: string, status: string): PipelineSteps {
    const mappedStatus: StepStatus = status === "start" ? "running" : status as StepStatus;
    if (mappedStatus === "running") {
        const next = { ...prev };
        for (const key of Object.keys(next)) {
            if (next[key] === "running" && key !== step) {
                next[key] = "done";
            }
        }
        next[step] = "running";
        return next;
    }
    return { ...prev, [step]: mappedStatus };
}

// PipelineProgress의 displayStep 선택 로직을 순수 함수로 추출
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

function getDisplayLabel(steps: PipelineSteps): string | null {
    const runningStep = PIPELINE_STEPS.find((s) => steps[s.key] === "running");
    const lastDoneStep = [...PIPELINE_STEPS].reverse().find((s) => steps[s.key] === "done");
    const displayStep = runningStep ?? lastDoneStep;
    return displayStep ? displayStep.label : null;
}

// ──────────────────────────────────────────────
// 1. 초기 상태
// ──────────────────────────────────────────────
describe("createInitialPipelineSteps", () => {
    it("intent가 running으로 초기화된다", () => {
        const steps = createInitialPipelineSteps();
        expect(steps.intent).toBe("running");
    });

    it("나머지 단계는 pending으로 초기화된다", () => {
        const steps = createInitialPipelineSteps();
        for (const [key, val] of Object.entries(steps)) {
            if (key !== "intent") {
                expect(val).toBe("pending");
            }
        }
    });
});

// ──────────────────────────────────────────────
// 2. applyStep — running 전환 시 이전 단계 done 처리
// ──────────────────────────────────────────────
describe("applyStep — running 전환 시 이전 단계 처리", () => {
    it("geocoder start → intent가 done으로 바뀐다", () => {
        let steps = createInitialPipelineSteps(); // intent: running
        steps = applyStep(steps, "geocoder", "start");

        expect(steps.intent).toBe("done");
        expect(steps.geocoder).toBe("running");
    });

    it("retriever start → geocoder가 done으로 바뀐다", () => {
        let steps = createInitialPipelineSteps();
        steps = applyStep(steps, "geocoder", "start");
        steps = applyStep(steps, "retriever", "start");

        expect(steps.geocoder).toBe("done");
        expect(steps.retriever).toBe("running");
    });

    it("executor start → retriever가 done으로 바뀐다", () => {
        let steps = createInitialPipelineSteps();
        steps = applyStep(steps, "geocoder", "start");
        steps = applyStep(steps, "retriever", "start");
        steps = applyStep(steps, "executor", "start");

        expect(steps.retriever).toBe("done");
        expect(steps.executor).toBe("running");
    });

    it("done 이벤트는 해당 단계만 done으로 바꾼다", () => {
        let steps = createInitialPipelineSteps();
        steps = applyStep(steps, "intent", "done");

        expect(steps.intent).toBe("done");
        expect(steps.geocoder).toBe("pending");
    });
});

// ──────────────────────────────────────────────
// 3. getDisplayLabel — 올바른 텍스트 표시
// ──────────────────────────────────────────────
describe("getDisplayLabel — 파이프라인 텍스트 표시", () => {
    it("초기 상태: '의도 분석' 표시", () => {
        const steps = createInitialPipelineSteps();
        expect(getDisplayLabel(steps)).toBe("의도 분석");
    });

    it("geocoder start 후: '위치 좌표 확인' 표시", () => {
        let steps = createInitialPipelineSteps();
        steps = applyStep(steps, "geocoder", "start");
        expect(getDisplayLabel(steps)).toBe("위치 좌표 확인");
    });

    it("retriever start 후: '장소 검색' 표시", () => {
        let steps = createInitialPipelineSteps();
        steps = applyStep(steps, "geocoder", "start");
        steps = applyStep(steps, "retriever", "start");
        expect(getDisplayLabel(steps)).toBe("장소 검색");
    });

    it("retriever_retry start 후: '반경 확대 후 장소 검색' 표시", () => {
        let steps = createInitialPipelineSteps();
        steps = applyStep(steps, "geocoder", "start");
        steps = applyStep(steps, "retriever", "start");
        steps = applyStep(steps, "retriever_retry", "start");
        expect(getDisplayLabel(steps)).toBe("반경 확대 후 장소 검색");
    });

    it("executor start 후: '답변 생성' 표시", () => {
        let steps = createInitialPipelineSteps();
        steps = applyStep(steps, "geocoder", "start");
        steps = applyStep(steps, "retriever", "start");
        steps = applyStep(steps, "executor", "start");
        expect(getDisplayLabel(steps)).toBe("답변 생성");
    });

    it("모든 단계 완료 후 running 없음: 마지막 done 단계(executor) 표시", () => {
        let steps = createInitialPipelineSteps();
        steps = applyStep(steps, "geocoder", "start");
        steps = applyStep(steps, "retriever", "start");
        steps = applyStep(steps, "executor", "start");
        steps = applyStep(steps, "executor", "done");
        expect(getDisplayLabel(steps)).toBe("답변 생성");
    });

    it("GENERAL 경로 — executor_general start 후: '일반 답변 생성' 표시", () => {
        let steps = createInitialPipelineSteps();
        steps = applyStep(steps, "executor_general", "start");
        expect(getDisplayLabel(steps)).toBe("일반 답변 생성");
    });

    it("TRIP_PLANNING 경로 — planner start 후: '여행 계획 수립' 표시", () => {
        let steps = createInitialPipelineSteps();
        steps = applyStep(steps, "planner", "start");
        expect(getDisplayLabel(steps)).toBe("여행 계획 수립");
    });
});

// ──────────────────────────────────────────────
// 4. 실제 SSE 이벤트 시퀀스 시뮬레이션
// ──────────────────────────────────────────────
describe("SSE 이벤트 시퀀스 시뮬레이션", () => {
    it("일반 장소 검색 흐름: intent→geocoder→retriever→executor 순으로 텍스트 변경", () => {
        const labels: string[] = [];
        let steps = createInitialPipelineSteps();
        labels.push(getDisplayLabel(steps)!);

        // on_chain_start: intent (초기값이 이미 intent running이므로 중복이지만 문제없음)
        steps = applyStep(steps, "intent", "start");
        labels.push(getDisplayLabel(steps)!);

        // on_chain_end: intent
        steps = applyStep(steps, "intent", "done");

        // on_chain_start: geocoder
        steps = applyStep(steps, "geocoder", "start");
        labels.push(getDisplayLabel(steps)!);

        // on_chain_end: geocoder
        steps = applyStep(steps, "geocoder", "done");

        // on_chain_start: retriever
        steps = applyStep(steps, "retriever", "start");
        labels.push(getDisplayLabel(steps)!);

        // on_chain_end: retriever
        steps = applyStep(steps, "retriever", "done");

        // on_chain_start: executor
        steps = applyStep(steps, "executor", "start");
        labels.push(getDisplayLabel(steps)!);

        expect(labels).toEqual([
            "의도 분석",
            "의도 분석",
            "위치 좌표 확인",
            "장소 검색",
            "답변 생성",
        ]);
    });
});
