import { fireEvent, render, screen } from "@testing-library/react";
import { PlaceCard, type PlaceCardItem } from "../src/components/common/PlaceCard";

// framer-motion 모션 컴포넌트를 div로 대체
jest.mock("framer-motion", () => ({
    motion: {
        div: ({ children, onClick, className }: React.HTMLAttributes<HTMLDivElement>) => (
            <div onClick={onClick} className={className}>{children}</div>
        ),
    },
}));

// PLACE_PLACEHOLDER mock
jest.mock("../src/lib/imageUrl", () => ({
    PLACE_PLACEHOLDER: "/placeholder.png",
}));

const sampleItem: PlaceCardItem = {
    contentid: "123",
    title: "경복궁",
    address: "서울 종로구",
    image_url: "https://example.com/photo.jpg",
};

describe("PlaceCard", () => {
    it("제목과 주소가 렌더링된다", () => {
        render(<PlaceCard item={sampleItem} />);
        expect(screen.getByText("경복궁")).toBeInTheDocument();
        expect(screen.getByText("서울 종로구")).toBeInTheDocument();
    });

    it("image_url이 있으면 해당 src로 이미지를 렌더링한다", () => {
        render(<PlaceCard item={sampleItem} />);
        const img = screen.getByRole("img", { name: "경복궁" });
        expect(img).toHaveAttribute("src", "https://example.com/photo.jpg");
    });

    it("image_url이 없으면 placeholder를 사용한다", () => {
        render(<PlaceCard item={{ ...sampleItem, image_url: null }} />);
        const img = screen.getByRole("img");
        expect(img).toHaveAttribute("src", "/placeholder.png");
    });

    it("이미지 로드 실패 시 placeholder로 교체한다", () => {
        render(<PlaceCard item={sampleItem} />);
        const img = screen.getByRole("img");
        fireEvent.error(img);
        expect(img).toHaveAttribute("src", "/placeholder.png");
    });

    it("onClick이 전달되면 클릭 시 호출된다", () => {
        const onClick = jest.fn();
        render(<PlaceCard item={sampleItem} onClick={onClick} />);
        fireEvent.click(screen.getByText("경복궁").closest("div")!);
        expect(onClick).toHaveBeenCalled();
    });

    it("onClick이 없어도 오류 없이 렌더링된다", () => {
        expect(() => render(<PlaceCard item={sampleItem} />)).not.toThrow();
    });
});
