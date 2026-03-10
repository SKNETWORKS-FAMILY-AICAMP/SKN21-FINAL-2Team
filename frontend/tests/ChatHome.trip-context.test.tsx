import { act, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { ReactNode } from "react";
import { ChatHome } from "../src/features/chat/components/ChatHome";
import { setPendingAutoStartMeta } from "../src/services/autoStart";

const deferred = <T,>() => {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

const mockReplace = jest.fn();
let mockRoomIdParam: string | null = "1";
const mockChatMessageItem = jest.fn(({ msg, showPipeline }: { msg: { id: number; room_id: number; message: string }, showPipeline?: boolean }) => (
  <div data-testid={`msg-${msg.id}`}>
    {msg.room_id}:{msg.message || "EMPTY"}:{showPipeline ? "pipeline" : "no-pipeline"}
  </div>
));
const mockCreateRoom = jest.fn();
const mockFetchRoom = jest.fn();
const mockFetchRooms = jest.fn();
const mockSendChatMessageStream = jest.fn();
const mockSendAutoStartChatRoomStream = jest.fn();
const mockFetchCurrentUser = jest.fn();
const mockVerifyAndRefreshToken = jest.fn();
const mockUpdatePlaceBookmark = jest.fn();
const mockUpdateRoomBookmark = jest.fn();

jest.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: (key: string) => {
      if (key === "roomId") return mockRoomIdParam;
      return null;
    },
  }),
  useRouter: () => ({ replace: mockReplace }),
}));

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

jest.mock("remark-gfm", () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock("../src/features/chat/components/PipelineProgress", () => ({
  PipelineProgress: () => null,
  createInitialPipelineSteps: () => ({
    intent: "idle",
    planner: "idle",
    retriever: "idle",
    executor: "idle",
    executor_missing: "idle",
  }),
}));

jest.mock("../src/hooks/common/useSpeechRecognition", () => ({
  useSpeechRecognition: () => ({
    isListening: false,
    sttPermission: "granted",
    handleToggleListening: jest.fn(),
  }),
}));

jest.mock("../src/features/chat/components/PlaceMapPanel", () => ({
  PlaceMapPanel: () => null,
}));

jest.mock("../src/features/chat/components/PlaceMapSheet", () => ({
  PlaceMapSheet: () => null,
}));

jest.mock("../src/features/chat/components/ChatMessageItem", () => ({
  ChatMessageItem: (props: unknown) => mockChatMessageItem(props),
}));

jest.mock("../src/services/api", () => ({
  createRoom: (...args: unknown[]) => mockCreateRoom(...args),
  fetchRoom: (...args: unknown[]) => mockFetchRoom(...args),
  fetchRooms: (...args: unknown[]) => mockFetchRooms(...args),
  sendChatMessageStream: (...args: unknown[]) => mockSendChatMessageStream(...args),
  sendAutoStartChatRoomStream: (...args: unknown[]) => mockSendAutoStartChatRoomStream(...args),
  fetchCurrentUser: (...args: unknown[]) => mockFetchCurrentUser(...args),
  verifyAndRefreshToken: (...args: unknown[]) => mockVerifyAndRefreshToken(...args),
  updatePlaceBookmark: (...args: unknown[]) => mockUpdatePlaceBookmark(...args),
  updateRoomBookmark: (...args: unknown[]) => mockUpdateRoomBookmark(...args),
}));

describe("ChatHome trip context header", () => {
  const bannerText = "2026-03-10 ~ 2026-03-12 · 성인 2명 / 어린이 0명";

  beforeEach(() => {
    mockRoomIdParam = "1";
    mockReplace.mockClear();
    mockChatMessageItem.mockClear();
    mockCreateRoom.mockReset();
    mockFetchRoom.mockReset();
    mockFetchRooms.mockReset();
    mockSendChatMessageStream.mockReset();
    mockSendAutoStartChatRoomStream.mockReset();
    mockFetchCurrentUser.mockReset();
    mockVerifyAndRefreshToken.mockReset();
    mockUpdatePlaceBookmark.mockReset();
    mockUpdateRoomBookmark.mockReset();
    localStorage.clear();
    localStorage.setItem(
      "triver:trip-context:1",
      JSON.stringify({
        travelDuration: "2026-03-10 ~ 2026-03-12",
        adultCount: 2,
        childCount: 0,
      })
    );
    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      writable: true,
        value: jest.fn(),
    });

    mockFetchRoom.mockImplementation(async (roomId: number) => ({
      id: roomId,
      user_id: 1,
      title: `room-${roomId}`,
      created_at: new Date().toISOString(),
      messages: [],
    }));
    mockFetchRooms.mockResolvedValue([
      { id: 2, user_id: 1, title: "room-2", created_at: new Date().toISOString(), messages: [] },
      { id: 1, user_id: 1, title: "room-1", created_at: new Date().toISOString(), messages: [] },
    ]);
    mockSendChatMessageStream.mockResolvedValue(undefined);
    mockSendAutoStartChatRoomStream.mockResolvedValue(undefined);
    mockFetchCurrentUser.mockResolvedValue({
      id: 1,
      email: "test@example.com",
      name: "Tester",
      is_join: true,
      is_prefer: true,
    });
    mockVerifyAndRefreshToken.mockResolvedValue({ valid: true, refreshed: false });
  });

  it("hides the previous room date banner immediately when roomId changes", async () => {
    const { rerender } = render(<ChatHome />);

    await waitFor(() => {
      expect(screen.getByText(bannerText)).toBeInTheDocument();
    });

    mockRoomIdParam = "2";
    rerender(<ChatHome />);

    expect(screen.queryByText(bannerText)).not.toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText(bannerText)).not.toBeInTheDocument();
    });
  });

  it("keeps the auto-start placeholder message visible before tokens arrive", async () => {
    setPendingAutoStartMeta(1, { mode: "greeting" });

    const streamDeferred = deferred<void>();
    mockSendAutoStartChatRoomStream.mockImplementation(
      async (_roomId: number, _payload: unknown, callbacks: { onStep: (step: string, status: string) => void }) => {
        callbacks.onStep("intent", "start");
        return streamDeferred.promise;
      }
    );

    render(<ChatHome />);

    await waitFor(() => {
      expect(mockSendAutoStartChatRoomStream).toHaveBeenCalled();
    });

    await waitFor(() => {
      const latestCall = mockChatMessageItem.mock.calls.at(-1)?.[0];
      expect(latestCall?.msg.room_id).toBe(1);
      expect(latestCall?.msg.message).toBe("");
      expect(latestCall?.showPipeline).toBe(true);
    });

    await act(async () => {
      streamDeferred.resolve();
    });
  });

  it("filters rendered messages to the current room only", async () => {
    mockFetchRoom.mockImplementation(async (roomId: number) => ({
      id: roomId,
      user_id: 1,
      title: `room-${roomId}`,
      created_at: new Date().toISOString(),
      messages: [
        {
          id: roomId * 10,
          room_id: roomId,
          message: `room-${roomId}-message`,
          role: "ai",
          created_at: new Date().toISOString(),
        },
        {
          id: roomId * 100,
          room_id: roomId + 100,
          message: "foreign-message",
          role: "ai",
          created_at: new Date().toISOString(),
        },
      ],
    }));

    render(<ChatHome />);

    await waitFor(() => {
      expect(screen.getByTestId("msg-10")).toHaveTextContent("1:room-1-message");
    });

    expect(screen.queryByText(/foreign-message/)).not.toBeInTheDocument();
  });

  it("ignores stale room hydration responses from the previous room", async () => {
    const room1Deferred = deferred<{
      id: number;
      user_id: number;
      title: string;
      created_at: string;
      messages: Array<{ id: number; room_id: number; message: string; role: "ai"; created_at: string }>;
    }>();

    mockFetchRoom.mockImplementation((roomId: number) => {
      if (roomId === 1) {
        return room1Deferred.promise;
      }

      return Promise.resolve({
        id: roomId,
        user_id: 1,
        title: `room-${roomId}`,
        created_at: new Date().toISOString(),
        messages: [
          {
            id: 20,
            room_id: 2,
            message: "room-2-message",
            role: "ai" as const,
            created_at: new Date().toISOString(),
          },
        ],
      });
    });

    const { rerender } = render(<ChatHome />);

    mockRoomIdParam = "2";
    rerender(<ChatHome />);

    await waitFor(() => {
      expect(screen.getByTestId("msg-20")).toHaveTextContent("2:room-2-message");
    });

    await act(async () => {
      room1Deferred.resolve({
        id: 1,
        user_id: 1,
        title: "room-1",
        created_at: new Date().toISOString(),
        messages: [
          {
            id: 10,
            room_id: 1,
            message: "room-1-message",
            role: "ai",
            created_at: new Date().toISOString(),
          },
        ],
      });
    });

    expect(screen.queryByText(/room-1-message/)).not.toBeInTheDocument();
    expect(screen.getByTestId("msg-20")).toHaveTextContent("2:room-2-message");
  });
});
