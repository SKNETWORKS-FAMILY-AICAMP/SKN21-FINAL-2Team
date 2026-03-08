import { render, screen } from "@testing-library/react";
import ChatbotPage from "../src/app/chatbot/page";
import "@testing-library/jest-dom";

jest.mock("../src/components/navigation/Sidebar", () => ({
  Sidebar: () => <aside>Sidebar Mock</aside>,
}));

jest.mock("../src/features/chat/components/ChatHome", () => ({
  ChatHome: () => <section>ChatHome Mock</section>,
}));

describe("ChatbotPage", () => {
  it("renders page layout with sidebar and chat home", () => {
    render(<ChatbotPage />);

    expect(screen.getByText("Sidebar Mock")).toBeInTheDocument();
    expect(screen.getByText("ChatHome Mock")).toBeInTheDocument();
  });
});
