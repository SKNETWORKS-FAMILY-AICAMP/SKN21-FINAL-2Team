import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import GoogleLoginBtn from "../src/components/GoogleLoginBtn";
import "@testing-library/jest-dom";

// Mock useRouter
const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

// Mock useGoogleLogin to run onSuccess when returned function is executed
const mockLogin = jest.fn();
jest.mock("@react-oauth/google", () => {
  return {
    useGoogleLogin: (config: { onSuccess?: (resp: { code: string }) => void }) => {
      return () => {
        mockLogin();
        config.onSuccess?.({ code: "test-code" });
      };
    },
  };
});

describe("GoogleLoginBtn", () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockLogin.mockClear();
    // @ts-ignore
    global.fetch = jest.fn((url: string) => {
      if (url.includes("/api/auth/google/callback")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ access_token: "token", refresh_token: "rt" }),
        } as Response);
      }
      if (url.includes("/api/users/me")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ id: 1, email: "a@test.com", is_join: false, is_prefer: false }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: async () => ({}) } as Response);
    });
  });

  it("renders login button", () => {
    render(<GoogleLoginBtn />);
    expect(screen.getByText("Google로 시작하기")).toBeInTheDocument();
  });

  it("calls login function and routes based on user flags", async () => {
    render(<GoogleLoginBtn />);
    const button = screen.getByRole("button");
    fireEvent.click(button);
    await waitFor(() => expect(mockLogin).toHaveBeenCalled());
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/signup/profile"));
  });
});
