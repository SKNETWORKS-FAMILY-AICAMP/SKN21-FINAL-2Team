import { DependencyList, useEffect, useState } from "react";

type AsyncDataState<T> = {
    data: T | null;
    loading: boolean;
    error: string | null;
};

/**
 * 비동기 데이터 로딩 패턴을 추상화한 훅.
 *
 * useEffect + loading/error + cancelled 플래그 패턴이 5곳 이상 반복되어 추출함.
 *
 * @param fetchFn  데이터를 가져오는 비동기 함수
 * @param onSuccess fetchFn 결과를 받아 상태를 갱신하는 콜백
 * @param errorMessage 에러 발생 시 반환할 메시지
 * @param deps useEffect 의존성 배열
 */
export function useAsyncData<T>(
    fetchFn: () => Promise<T>,
    onSuccess: (data: T) => void,
    errorMessage: string,
    deps: DependencyList = []
): AsyncDataState<T> {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [data, setData] = useState<T | null>(null);

    useEffect(() => {
        let cancelled = false;

        const load = async () => {
            setLoading(true);
            setError(null);
            try {
                const result = await fetchFn();
                if (cancelled) return;
                setData(result);
                onSuccess(result);
            } catch {
                if (!cancelled) setError(errorMessage);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };

        void load();
        return () => {
            cancelled = true;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps);

    return { data, loading, error };
}
