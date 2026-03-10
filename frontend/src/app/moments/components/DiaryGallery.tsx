import { MapPin } from "lucide-react";

import { DiaryListItem } from "@/services/api";

const DEFAULT_PLACEHOLDER = "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200&q=80";

type DiaryGalleryProps = {
  diaries: DiaryListItem[];
  selectedDiaryId: number | null;
  onSelect: (diaryId: number) => void;
};

export function DiaryGallery({
  diaries,
  selectedDiaryId,
  onSelect,
}: DiaryGalleryProps) {
  return (
    <div className="columns-1 gap-4 space-y-4 md:columns-2 xl:columns-3 2xl:columns-4">
      {diaries.map((diary) => (
        <button
          key={diary.id}
          onClick={() => onSelect(diary.id)}
          className={`group relative mb-4 block w-full break-inside-avoid overflow-hidden rounded-2xl text-left shadow-sm transition-shadow hover:shadow-lg ${
            diary.id === selectedDiaryId ? "ring-2 ring-black" : ""
          }`}
        >
          <img
            src={diary.cover_image_path || DEFAULT_PLACEHOLDER}
            alt={diary.title}
            className="h-auto w-full object-cover transition-transform duration-700 group-hover:scale-105"
          />
          <div className="absolute inset-0 bg-black/0 transition-colors duration-300 group-hover:bg-black/20" />
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/35 to-transparent p-4 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-white/75">
              {diary.entry_date}
            </p>
            <p className="line-clamp-1 text-lg font-medium text-white">{diary.title}</p>
            <p className="mt-1 flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-white">
              <MapPin size={10} /> Places {diary.linked_places_count}
            </p>
          </div>
        </button>
      ))}
    </div>
  );
}
