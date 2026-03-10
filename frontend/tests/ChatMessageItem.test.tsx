import { render, screen } from "@testing-library/react";
import { ChatMessageItem } from "../src/features/chat/components/ChatMessageItem";

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

jest.mock("remark-gfm", () => jest.fn());

describe("ChatMessageItem", () => {
  const baseMessage = {
    id: 101,
    room_id: 1,
    message: "링크를 준비 중입니다",
    role: "ai" as const,
    created_at: new Date().toISOString(),
  };

  it("현재 스트리밍 메시지에서 링크 버퍼링 문구를 표시한다", () => {
    render(
      <ChatMessageItem
        msg={baseMessage}
        isStreaming
        streamingMsgId={101}
        showPipeline={false}
        streamBufferingReason="link"
        selectedMapPlaceId={null}
        toMapId={() => ""}
        handleSelectMapPlace={() => {}}
        handleTogglePlaceBookmark={() => {}}
        placeCardRefs={{ current: {} }}
      />
    );

    expect(screen.getByText("링크 정리 중...")).toBeInTheDocument();
  });

  it("버퍼링 상태가 아니면 문구를 표시하지 않는다", () => {
    render(
      <ChatMessageItem
        msg={baseMessage}
        isStreaming
        streamingMsgId={101}
        showPipeline={false}
        streamBufferingReason={null}
        selectedMapPlaceId={null}
        toMapId={() => ""}
        handleSelectMapPlace={() => {}}
        handleTogglePlaceBookmark={() => {}}
        placeCardRefs={{ current: {} }}
      />
    );

    expect(screen.queryByText("링크 정리 중...")).not.toBeInTheDocument();
  });

  it("스트리밍 파이프라인을 AI 말풍선 안에서 표시한다", () => {
    render(
      <ChatMessageItem
        msg={{ ...baseMessage, id: 202, message: "" }}
        isStreaming
        streamingMsgId={202}
        showPipeline
        pipelineSteps={{
          intent: "done",
          planner: "pending",
          retriever: "running",
          executor: "pending",
          executor_missing: "pending",
          executor_general: "pending",
        }}
        streamBufferingReason={null}
        selectedMapPlaceId={null}
        toMapId={() => ""}
        handleSelectMapPlace={() => {}}
        handleTogglePlaceBookmark={() => {}}
        placeCardRefs={{ current: {} }}
      />
    );

    expect(screen.getByText("의도 분석 완료")).toBeInTheDocument();
    expect(screen.getByText("장소 검색 중...")).toBeInTheDocument();
    expect(screen.getByTestId("ai-bubble-202")).toHaveTextContent("의도 분석 완료");
    expect(screen.getByTestId("ai-bubble-202")).toHaveTextContent("장소 검색 중...");
  });

  it("토큰과 파이프라인 이벤트가 오기 전에도 첫 AI 말풍선을 표시한다", () => {
    render(
      <ChatMessageItem
        msg={{ ...baseMessage, id: 303, message: "" }}
        isStreaming
        streamingMsgId={303}
        showPipeline={false}
        streamBufferingReason={null}
        selectedMapPlaceId={null}
        toMapId={() => ""}
        handleSelectMapPlace={() => {}}
        handleTogglePlaceBookmark={() => {}}
        placeCardRefs={{ current: {} }}
      />
    );

    expect(screen.getByText("응답 준비 중...")).toBeInTheDocument();
  });

  it("전역 isStreaming이 꺼져도 현재 streamingMsgId 말풍선은 유지한다", () => {
    render(
      <ChatMessageItem
        msg={{ ...baseMessage, id: 304, message: "" }}
        isStreaming={false}
        streamingMsgId={304}
        showPipeline
        pipelineSteps={{
          intent: "done",
          planner: "pending",
          retriever: "pending",
          executor: "pending",
          executor_missing: "pending",
          executor_general: "pending",
        }}
        streamBufferingReason={null}
        selectedMapPlaceId={null}
        toMapId={() => ""}
        handleSelectMapPlace={() => {}}
        handleTogglePlaceBookmark={() => {}}
        placeCardRefs={{ current: {} }}
      />
    );

    expect(screen.getByTestId("ai-bubble-304")).toHaveTextContent("의도 분석 완료");
  });

  it("showPipeline이 true여도 표시할 단계가 없으면 waiting bubble을 유지한다", () => {
    render(
      <ChatMessageItem
        msg={{ ...baseMessage, id: 404, message: "" }}
        isStreaming
        streamingMsgId={404}
        showPipeline
        pipelineSteps={{
          intent: "pending",
          planner: "pending",
          retriever: "pending",
          executor: "pending",
          executor_missing: "pending",
          executor_general: "pending",
        }}
        streamBufferingReason={null}
        selectedMapPlaceId={null}
        toMapId={() => ""}
        handleSelectMapPlace={() => {}}
        handleTogglePlaceBookmark={() => {}}
        placeCardRefs={{ current: {} }}
      />
    );

    expect(screen.getByText("응답 준비 중...")).toBeInTheDocument();
  });

  it("파이프라인과 본문을 하나의 AI 말풍선 안에서 함께 표시한다", () => {
    render(
      <ChatMessageItem
        msg={{ ...baseMessage, id: 505, message: "최종 답변입니다." }}
        isStreaming
        streamingMsgId={505}
        showPipeline
        pipelineSteps={{
          intent: "done",
          planner: "pending",
          retriever: "done",
          executor: "running",
          executor_missing: "pending",
          executor_general: "pending",
        }}
        streamBufferingReason={null}
        selectedMapPlaceId={null}
        toMapId={() => ""}
        handleSelectMapPlace={() => {}}
        handleTogglePlaceBookmark={() => {}}
        placeCardRefs={{ current: {} }}
      />
    );

    const bubble = screen.getByTestId("ai-bubble-505");
    expect(bubble).toHaveTextContent("의도 분석 완료");
    expect(bubble).toHaveTextContent("장소 검색 완료");
    expect(bubble).toHaveTextContent("답변 생성 중...");
    expect(bubble).toHaveTextContent("최종 답변입니다.");
  });
});
