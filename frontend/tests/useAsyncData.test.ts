import { act, renderHook, waitFor } from "@testing-library/react";
import { useAsyncData } from "../src/hooks/useAsyncData";

describe("useAsyncData", () => {
    it("초기 상태: loading=true, data=null, error=null", () => {
        const fetchFn = () => new Promise<string[]>(() => {}); // never resolves
        const { result } = renderHook(() =>
            useAsyncData(fetchFn, () => {}, "에러", [])
        );
        expect(result.current.loading).toBe(true);
        expect(result.current.data).toBeNull();
        expect(result.current.error).toBeNull();
    });

    it("성공 시: loading=false, data 반환, onSuccess 호출", async () => {
        const items = ["경복궁", "북촌"];
        const fetchFn = jest.fn().mockResolvedValue(items);
        const onSuccess = jest.fn();

        const { result } = renderHook(() =>
            useAsyncData(fetchFn, onSuccess, "에러", [])
        );

        await waitFor(() => expect(result.current.loading).toBe(false));

        expect(result.current.data).toEqual(items);
        expect(result.current.error).toBeNull();
        expect(onSuccess).toHaveBeenCalledWith(items);
    });

    it("실패 시: loading=false, error에 메시지 설정", async () => {
        const fetchFn = jest.fn().mockRejectedValue(new Error("네트워크 오류"));

        const { result } = renderHook(() =>
            useAsyncData(fetchFn, () => {}, "로딩 실패", [])
        );

        await waitFor(() => expect(result.current.loading).toBe(false));

        expect(result.current.error).toBe("로딩 실패");
        expect(result.current.data).toBeNull();
    });

    it("언마운트 후 onSuccess가 호출되지 않는다 (cancelled)", async () => {
        let resolveRef!: (val: string[]) => void;
        const fetchFn = jest.fn(
            () => new Promise<string[]>((resolve) => { resolveRef = resolve; })
        );
        const onSuccess = jest.fn();

        const { unmount } = renderHook(() =>
            useAsyncData(fetchFn, onSuccess, "에러", [])
        );

        unmount(); // cancelled = true
        act(() => resolveRef([])); // resolve after unmount

        // 짧은 지연 후 onSuccess가 호출되지 않아야 한다
        await new Promise((r) => setTimeout(r, 10));
        expect(onSuccess).not.toHaveBeenCalled();
    });

    it("deps 변경 시 재조회한다", async () => {
        const fetchFn = jest.fn().mockResolvedValue([]);

        const { rerender } = renderHook(
            ({ id }: { id: number }) =>
                useAsyncData(fetchFn, () => {}, "에러", [id]),
            { initialProps: { id: 1 } }
        );

        await waitFor(() => expect(fetchFn).toHaveBeenCalledTimes(1));

        rerender({ id: 2 });
        await waitFor(() => expect(fetchFn).toHaveBeenCalledTimes(2));
    });
});
