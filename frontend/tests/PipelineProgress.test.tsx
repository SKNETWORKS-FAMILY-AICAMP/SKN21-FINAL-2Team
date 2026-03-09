import { render, screen } from "@testing-library/react";

import { PipelineProgress } from "../src/components/chat/PipelineProgress";

describe("PipelineProgress", () => {
  it("실제로 시작된 단계만 표시한다", () => {
    render(
      <PipelineProgress
        visible={true}
        steps={{
          intent: "done",
          planner: "running",
          retriever: "pending",
          executor: "pending",
          executor_missing: "pending",
          executor_general: "pending",
        }}
      />
    );

    expect(screen.getByText("의도 분석 완료")).toBeInTheDocument();
    expect(screen.getByText("여행 계획 수립 중...")).toBeInTheDocument();
    expect(screen.queryByText("장소 검색 완료")).not.toBeInTheDocument();
    expect(screen.queryByText("장소 검색 중...")).not.toBeInTheDocument();
  });

  it("일반 대화 분기의 executor_general 단계를 표시한다", () => {
    render(
      <PipelineProgress
        visible={true}
        steps={{
          intent: "done",
          planner: "pending",
          retriever: "pending",
          executor: "pending",
          executor_missing: "pending",
          executor_general: "running",
        }}
      />
    );

    expect(screen.getByText("의도 분석 완료")).toBeInTheDocument();
    expect(screen.getByText("일반 답변 생성 중...")).toBeInTheDocument();
  });
});
