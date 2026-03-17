import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";

import { ChatMessageItem } from "../src/features/chat/components/ChatMessageItem";
import type { ChatPlaceItem } from "../src/services/api";

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

jest.mock("remark-gfm", () => ({
  __esModule: true,
  default: () => null,
}));

describe("ChatMessageItem", () => {
  const baseAiMessage = {
    id: 100,
    room_id: 1,
    message: "추천 중간 텍스트",
    role: "ai" as const,
    created_at: "2026-03-17T12:00:00.000Z",
    places: [] as ChatPlaceItem[],
  };

  it("스트리밍 중 첫 토큰이 와도 파이프라인을 계속 표시한다", () => {
    render(
      <ChatMessageItem
        msg={baseAiMessage}
        isStreaming={true}
        streamingMsgId={100}
        showPipeline={true}
        pipelineSteps={{
          intent: "done",
          geocoder: "running",
          planner: "pending",
          retriever: "pending",
          retriever_retry: "pending",
          web_search: "pending",
          executor: "pending",
          executor_missing: "pending",
          executor_general: "pending",
          image_analysis: "pending",
        }}
        streamBufferingReason={null}
        selectedMapPlaceId={null}
        toMapId={(place) => String(place.id)}
        handleSelectMapPlace={() => {}}
        handleTogglePlaceBookmark={() => {}}
        placeCardRefs={{ current: {} }}
      />
    );

    expect(screen.getByText("위치 좌표 확인 중...")).toBeInTheDocument();
    expect(screen.getByText("추천 중간 텍스트")).toBeInTheDocument();
  });
});
