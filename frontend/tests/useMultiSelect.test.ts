import { act, renderHook } from "@testing-library/react";
import { useMultiSelect } from "../src/hooks/useMultiSelect";

describe("useMultiSelect", () => {
    it("초기 상태는 빈 배열이다", () => {
        const { result } = renderHook(() => useMultiSelect<number>());
        expect(result.current.selected).toEqual([]);
    });

    it("초기값을 지정할 수 있다", () => {
        const { result } = renderHook(() => useMultiSelect<number>([1, 2]));
        expect(result.current.selected).toEqual([1, 2]);
    });

    it("toggle: 없는 id를 추가한다", () => {
        const { result } = renderHook(() => useMultiSelect<number>());
        act(() => result.current.toggle(5));
        expect(result.current.selected).toContain(5);
    });

    it("toggle: 이미 있는 id를 제거한다", () => {
        const { result } = renderHook(() => useMultiSelect<number>([5]));
        act(() => result.current.toggle(5));
        expect(result.current.selected).not.toContain(5);
    });

    it("toggle을 두 번 하면 원래 상태로 돌아온다", () => {
        const { result } = renderHook(() => useMultiSelect<number>());
        act(() => result.current.toggle(3));
        act(() => result.current.toggle(3));
        expect(result.current.selected).toEqual([]);
    });

    it("clear: 전체 선택 해제", () => {
        const { result } = renderHook(() => useMultiSelect<number>([1, 2, 3]));
        act(() => result.current.clear());
        expect(result.current.selected).toEqual([]);
    });

    it("isSelected: 선택된 id는 true를 반환한다", () => {
        const { result } = renderHook(() => useMultiSelect<number>([7]));
        expect(result.current.isSelected(7)).toBe(true);
    });

    it("isSelected: 선택되지 않은 id는 false를 반환한다", () => {
        const { result } = renderHook(() => useMultiSelect<number>());
        expect(result.current.isSelected(99)).toBe(false);
    });

    it("string 타입도 지원한다", () => {
        const { result } = renderHook(() => useMultiSelect<string>());
        act(() => result.current.toggle("abc"));
        expect(result.current.selected).toContain("abc");
    });
});
