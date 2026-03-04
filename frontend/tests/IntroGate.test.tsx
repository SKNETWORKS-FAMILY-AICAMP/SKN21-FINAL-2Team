import { render, screen, fireEvent } from "@testing-library/react";
import IntroGate from "../src/components/IntroGate";

jest.mock("../src/components/IntroOverlay", () => ({
  __esModule: true,
  default: ({ onDone }: { onDone: () => void }) => (
    <button onClick={onDone}>Intro Overlay Mock</button>
  ),
}));

describe("IntroGate", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("세션 첫 진입에서는 인트로 오버레이를 표시한다", () => {
    render(
      <IntroGate>
        <div>Home Content</div>
      </IntroGate>
    );

    expect(screen.getByText("Home Content")).toBeInTheDocument();
    expect(screen.getByText("Intro Overlay Mock")).toBeInTheDocument();
  });

  it("인트로 완료 후 같은 세션 재진입 시 오버레이를 숨긴다", () => {
    const { unmount } = render(
      <IntroGate>
        <div>Home Content</div>
      </IntroGate>
    );

    fireEvent.click(screen.getByText("Intro Overlay Mock"));
    unmount();

    render(
      <IntroGate>
        <div>Home Content</div>
      </IntroGate>
    );

    expect(screen.queryByText("Intro Overlay Mock")).not.toBeInTheDocument();
  });
});
