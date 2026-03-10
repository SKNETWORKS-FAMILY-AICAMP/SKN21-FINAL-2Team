import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { MomentsPage } from "../src/app/moments/MomentsPage";

jest.mock("@/components/navigation/Sidebar", () => ({
  Sidebar: () => <div data-testid="sidebar" />,
}));

const mockFetchDiaries = jest.fn();
const mockFetchDiary = jest.fn();
const mockCreateDiary = jest.fn();
const mockUpdateDiary = jest.fn();
const mockUploadImageDataUrl = jest.fn();
const mockSearchDiaryPlaces = jest.fn();
const mockReverseGeocodeDiaryPlace = jest.fn();

jest.mock("@/services/api", () => ({
  fetchDiaries: (...args: unknown[]) => mockFetchDiaries(...args),
  fetchDiary: (...args: unknown[]) => mockFetchDiary(...args),
  createDiary: (...args: unknown[]) => mockCreateDiary(...args),
  updateDiary: (...args: unknown[]) => mockUpdateDiary(...args),
  uploadImageDataUrl: (...args: unknown[]) => mockUploadImageDataUrl(...args),
  searchDiaryPlaces: (...args: unknown[]) => mockSearchDiaryPlaces(...args),
  reverseGeocodeDiaryPlace: (...args: unknown[]) => mockReverseGeocodeDiaryPlace(...args),
}));

describe("MomentsPage", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockFetchDiaries.mockReset();
    mockFetchDiary.mockReset();
    mockCreateDiary.mockReset();
    mockUpdateDiary.mockReset();
    mockUploadImageDataUrl.mockReset();
    mockSearchDiaryPlaces.mockReset();
    mockReverseGeocodeDiaryPlace.mockReset();
    mockUploadImageDataUrl.mockImplementation(async (value: string) => value);
  });

  afterEach(() => {
    act(() => {
      jest.runOnlyPendingTimers();
    });
    jest.useRealTimers();
  });

  it("빈 상태를 렌더링한다", async () => {
    mockFetchDiaries.mockResolvedValue([]);

    render(<MomentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Start Your First Memory")).toBeInTheDocument();
    });
  });

  it("목록과 검색을 반영한다", async () => {
    mockFetchDiaries
      .mockResolvedValueOnce([
        { id: 1, title: "성수 카페", content: "커피 향이 좋았다.", entry_date: "2026-03-09", linked_places_count: 1 },
      ])
      .mockResolvedValue([
        { id: 2, title: "한강 산책", content: "노을을 봤다.", entry_date: "2026-03-08", linked_places_count: 0 },
      ]);

    render(<MomentsPage />);

    await waitFor(() => expect(screen.getByText("성수 카페")).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText("Search diary"), {
      target: { value: "한강" },
    });

    await act(async () => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(mockFetchDiaries).toHaveBeenLastCalledWith({ query: "한강" });
      expect(screen.getByText("한강 산책")).toBeInTheDocument();
    });
  });

  it("새 일기 생성 후 목록을 다시 불러온다", async () => {
    mockFetchDiaries
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        { id: 11, title: "새 일기", content: "본문입니다.", entry_date: "2026-03-09", linked_places_count: 1 },
      ]);
    mockCreateDiary.mockResolvedValue({
      id: 11,
      user_id: 1,
      title: "새 일기",
      content: "본문입니다.",
      entry_date: "2026-03-09",
      linked_places_count: 1,
      linked_chat_room: null,
      linked_places: [{ id: 101, chat_place_id: 20, name: "북촌", adress: "서울 종로구" }],
    });

    render(<MomentsPage />);

    await waitFor(() => expect(screen.getByText("Start Your First Memory")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Create"));

    fireEvent.change(screen.getByPlaceholderText("Title your diary"), {
      target: { value: "새 일기" },
    });
    fireEvent.change(screen.getByPlaceholderText("오늘의 동선, 감정, 기억하고 싶은 장면을 적어보세요."), {
      target: { value: "본문입니다." },
    });
    fireEvent.click(screen.getByText("Save"));

    await waitFor(() => {
      expect(mockCreateDiary).toHaveBeenCalledWith({
        title: "새 일기",
        content: "본문입니다.",
        entry_date: expect.any(String),
        cover_image_path: null,
        linked_places: [],
      });
      expect(mockFetchDiaries).toHaveBeenCalledTimes(2);
    });
  });

  it("상세 조회 후 수정한다", async () => {
    mockFetchDiaries
      .mockResolvedValueOnce([
        { id: 1, title: "기존 일기", content: "예전 기록", entry_date: "2026-03-09", linked_places_count: 0 },
      ])
      .mockResolvedValue([
        { id: 1, title: "수정된 일기", content: "예전 기록", entry_date: "2026-03-09", linked_places_count: 0 },
      ]);
    mockFetchDiary.mockResolvedValue({
      id: 1,
      user_id: 1,
      title: "기존 일기",
      content: "예전 기록",
      entry_date: "2026-03-09",
      linked_places_count: 0,
      linked_chat_room: null,
      linked_places: [],
    });
    mockUpdateDiary.mockResolvedValue({
      id: 1,
      user_id: 1,
      title: "수정된 일기",
      content: "예전 기록",
      entry_date: "2026-03-09",
      linked_places_count: 0,
      linked_chat_room: null,
      linked_places: [],
    });
    render(<MomentsPage />);

    await waitFor(() => expect(screen.getByText("기존 일기")).toBeInTheDocument());
    fireEvent.click(screen.getByText("기존 일기"));

    await waitFor(() => expect(mockFetchDiary).toHaveBeenCalledWith(1));
    await waitFor(() => expect(screen.getByPlaceholderText("Title your diary")).toHaveValue("기존 일기"));

    fireEvent.change(screen.getByPlaceholderText("Title your diary"), {
      target: { value: "수정된 일기" },
    });
    fireEvent.click(screen.getByText("Save"));

    await waitFor(() => expect(mockUpdateDiary).toHaveBeenCalledWith(1, expect.objectContaining({ title: "수정된 일기" })));
  });
});
