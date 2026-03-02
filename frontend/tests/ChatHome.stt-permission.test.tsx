import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { ChatHome } from "../src/components/chat/ChatHome";

const mockReplace = jest.fn();
const mockRecognitionStart = jest.fn();
const mockRecognitionStop = jest.fn();
const mockRouter = { replace: mockReplace };

jest.mock("next/navigation", () => ({
  useSearchParams: () => ({ get: () => null }),
  useRouter: () => mockRouter,
}));

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }: { children: any }) => <>{children}</>,
}));

jest.mock("remark-gfm", () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock("../src/components/chat/PipelineProgress", () => ({
  PipelineProgress: () => null,
  createInitialPipelineSteps: () => ({
    intent: "idle",
    planner: "idle",
    retriever: "idle",
    executor: "idle",
    executor_missing: "idle",
  }),
}));

jest.mock("../src/services/api", () => ({
  createRoom: jest.fn(async () => ({
    id: 1,
    user_id: 1,
    title: "새로운 여행 계획",
    created_at: new Date().toISOString(),
    messages: [],
  })),
  fetchRoom: jest.fn(async () => ({
    id: 1,
    user_id: 1,
    title: "새로운 여행 계획",
    created_at: new Date().toISOString(),
    messages: [],
  })),
  fetchRooms: jest.fn(async () => []),
  sendChatMessageStream: jest.fn(async () => undefined),
  fetchCurrentUser: jest.fn(async () => ({
    id: 1,
    email: "test@example.com",
    name: "Test User",
  })),
  verifyAndRefreshToken: jest.fn(async () => ({ valid: true })),
}));

class MockSpeechRecognition {
  lang = "ko-KR";
  continuous = false;
  interimResults = false;
  maxAlternatives = 1;
  onresult: ((event: any) => void) | null = null;
  onerror: ((event: any) => void) | null = null;
  onend: (() => void) | null = null;
  onstart: (() => void) | null = null;

  start() {
    mockRecognitionStart();
    this.onstart?.();
  }
  stop() {
    mockRecognitionStop();
    this.onend?.();
  }
  abort() {}
}

describe("ChatHome STT permission behavior", () => {
  const waitUntilChatReady = async () => {
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Ask Triver regarding your next destination...")).toBeInTheDocument();
    });
  };

  beforeEach(() => {
    mockReplace.mockClear();
    mockRecognitionStart.mockClear();
    mockRecognitionStop.mockClear();

    Object.defineProperty(window, "SpeechRecognition", {
      configurable: true,
      writable: true,
      value: undefined,
    });
    Object.defineProperty(window, "webkitSpeechRecognition", {
      configurable: true,
      writable: true,
      value: MockSpeechRecognition,
    });
    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      writable: true,
      value: jest.fn(),
    });
  });

  it("applies denied design when microphone permission is denied", async () => {
    const permissionStatus: any = { state: "denied", onchange: null };
    Object.defineProperty(navigator, "permissions", {
      configurable: true,
      value: { query: jest.fn(async () => permissionStatus) },
    });

    render(<ChatHome />);
    await waitUntilChatReady();

    await waitFor(() => {
      expect(screen.getByTitle("마이크 권한 거부됨 - 다시 시도")).toBeInTheDocument();
    });
  });

  it("applies default design when microphone permission is granted", async () => {
    const permissionStatus: any = { state: "granted", onchange: null };
    Object.defineProperty(navigator, "permissions", {
      configurable: true,
      value: { query: jest.fn(async () => permissionStatus) },
    });

    render(<ChatHome />);
    await waitUntilChatReady();

    await waitFor(() => {
      expect(screen.getByTitle("음성으로 입력")).toBeInTheDocument();
    });
  });

  it("updates button state when permission change event occurs", async () => {
    const permissionStatus: any = { state: "granted", onchange: null };
    Object.defineProperty(navigator, "permissions", {
      configurable: true,
      value: { query: jest.fn(async () => permissionStatus) },
    });

    render(<ChatHome />);
    await waitUntilChatReady();

    await waitFor(() => {
      expect(screen.getByTitle("음성으로 입력")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(typeof permissionStatus.onchange).toBe("function");
    });

    permissionStatus.state = "denied";
    permissionStatus.onchange?.();

    await waitFor(() => {
      expect(screen.getByTitle("마이크 권한 거부됨 - 다시 시도")).toBeInTheDocument();
    });
  });

  it("retries recognition start when denied button is clicked", async () => {
    const permissionStatus: any = { state: "denied", onchange: null };
    Object.defineProperty(navigator, "permissions", {
      configurable: true,
      value: { query: jest.fn(async () => permissionStatus) },
    });

    render(<ChatHome />);
    await waitUntilChatReady();

    const deniedButton = await screen.findByTitle("마이크 권한 거부됨 - 다시 시도");
    fireEvent.click(deniedButton);

    await waitFor(() => {
      expect(mockRecognitionStart).toHaveBeenCalled();
    });
  });
});
