// [Feature] 삭제 모드 지원 - 다중 선택 후 일괄 삭제
import { Check, MapPin } from "lucide-react";

import { DiaryListItem } from "@/services/api";
import { useTranslation } from "@/i18n/useTranslation";

const DEFAULT_PLACEHOLDER = "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200&q=80";

type DiaryGalleryProps = {
  diaries: DiaryListItem[];
  selectedDiaryId: number | null;
  onSelect: (diaryId: number) => void;
  isDeleteMode?: boolean;
  selectedToDelete?: Set<number>;
  onToggleDeleteSelect?: (diaryId: number) => void;
};

export function DiaryGallery({
  diaries,
  selectedDiaryId,
  onSelect,
  isDeleteMode = false,
  selectedToDelete = new Set(),
  onToggleDeleteSelect,
}: DiaryGalleryProps) {
  const { t } = useTranslation();
  return (
    <div className="columns-1 gap-4 space-y-4 md:columns-2 xl:columns-3 2xl:columns-4">
      {diaries.map((diary) => {
        const isChecked = selectedToDelete.has(diary.id);
        return (
          <button
            key={diary.id}
            onClick={() => {
              if (isDeleteMode) {
                onToggleDeleteSelect?.(diary.id);
              } else {
                onSelect(diary.id);
              }
            }}
            className={`group relative mb-4 block w-full break-inside-avoid overflow-hidden rounded-2xl text-left shadow-sm transition-all hover:shadow-lg ${
              isDeleteMode
                ? isChecked
                  ? "ring-2 ring-black scale-[0.98]"
                  : "opacity-70 hover:opacity-100"
                : ""
            }`}
          >
            <img
              src={diary.cover_image_path || DEFAULT_PLACEHOLDER}
              alt={diary.title}
              className="h-auto w-full object-cover transition-transform duration-700 group-hover:scale-105"
            />
            <div className={`absolute inset-0 transition-colors duration-300 ${
              isDeleteMode && isChecked
                ? "bg-black/20"
                : "bg-black/0 group-hover:bg-black/20"
            }`} />

            {/* 선택된 카드 테두리 (일반 모드) */}
            {!isDeleteMode && diary.id === selectedDiaryId && (
              <div className="pointer-events-none absolute inset-0 rounded-2xl border-[3px] border-black z-10" />
            )}

            {/* 삭제 모드 체크박스 */}
            {isDeleteMode && (
              <div className={`absolute top-3 right-3 z-10 flex h-6 w-6 items-center justify-center rounded-full border-2 transition-all duration-200 shadow-sm ${
                isChecked
                  ? "border-black bg-black text-white"
                  : "border-white/80 bg-black/30 text-transparent"
              }`}>
                <Check size={13} strokeWidth={3} />
              </div>
            )}

            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/35 to-transparent p-4 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
              <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-white/75">
                {diary.entry_date}
              </p>
              <p className="line-clamp-1 text-lg font-medium text-white">{diary.title}</p>
              <p className="mt-1 flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-white">
                <MapPin size={10} /> {t("moments.places")} {diary.linked_places_count}
              </p>
            </div>
          </button>
        );
      })}
    </div>
  );
}