import { useState } from "react";

/**
 * 다중 선택 토글 패턴을 추상화한 훅.
 *
 * BookmarkPage(2곳) / MomentsPage(1곳) 등 4회 이상 반복되는
 * `prev.includes(id) ? prev.filter(...) : [...prev, id]` 패턴을 추출함.
 */
export function useMultiSelect<T extends number | string>(initial: T[] = []) {
    const [selected, setSelected] = useState<T[]>(initial);

    const toggle = (id: T) => {
        setSelected((prev) =>
            prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
        );
    };

    const clear = () => setSelected([]);

    const isSelected = (id: T) => selected.includes(id);

    return { selected, toggle, clear, setSelected, isSelected };
}
