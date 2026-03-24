// [Feature] Add Memory + Delete Memory(다중 선택 삭제) 버튼
import { Search, Grid, Plus, Trash2, X } from "lucide-react";
import { useTranslation } from "@/i18n/useTranslation";

type MomentsHeaderProps = {
  query: string;
  onQueryChange: (value: string) => void;
  onCreate: () => void;
  onDeleteSelect: () => void;
  isDeleteMode?: boolean;
  deleteCount?: number;
  onConfirmDelete?: () => void;
};

export function MomentsHeader({
  query,
  onQueryChange,
  onCreate,
  onDeleteSelect,
  isDeleteMode = false,
  deleteCount = 0,
  onConfirmDelete,
}: MomentsHeaderProps) {
  const { t } = useTranslation();
  return (
    <header className="mb-6 flex flex-none items-end justify-between border-b border-gray-100 pb-4">
      <div>
        <h1 className="page-title mb-1 flex items-center gap-2 text-gray-900">
          {t("moments.pageTitle")} <Grid size={16} className="text-gray-400" />
        </h1>
        <p className="page-subtitle">{t("moments.pageSubtitle")}</p>
      </div>

      <div className="flex items-center gap-3">
        {!isDeleteMode && (
          <label className="hidden items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-4 py-2 text-xs text-gray-500 md:flex">
            <Search size={14} />
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder={t("moments.searchPlaceholder")}
              className="w-40 bg-transparent text-sm outline-none placeholder:text-gray-400"
            />
          </label>
        )}

        {isDeleteMode ? (
          <>
            {/* 선택된 개수 표시 + 삭제 실행 버튼 */}
            <button
              onClick={onConfirmDelete}
              disabled={deleteCount === 0}
              className={`flex items-center gap-1.5 rounded-full px-5 py-2.5 text-sm font-semibold transition-colors ${
                deleteCount > 0
                  ? "bg-red-600 text-white hover:bg-red-700"
                  : "bg-gray-100 text-gray-300 cursor-not-allowed"
              }`}
            >
              <Trash2 size={14} />
              {deleteCount > 0 ? `${deleteCount}개 삭제` : "삭제"}
            </button>
            {/* 취소 버튼 */}
            <button
              onClick={onDeleteSelect}
              className="flex items-center justify-center rounded-full border border-gray-200 p-2.5 text-gray-500 transition-colors hover:bg-gray-100"
              title="취소"
            >
              <X size={16} />
            </button>
          </>
        ) : (
          <>
            <button
              onClick={onCreate}
              className="flex items-center gap-1.5 rounded-full bg-black px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-gray-800"
            >
              <Plus size={14} /> {t("moments.addMemory")}
            </button>
            {/* 삭제 모드 진입 버튼 */}
            <button
              onClick={onDeleteSelect}
              className="flex items-center justify-center rounded-full border border-gray-200 p-2.5 text-gray-400 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-500"
              title={t("moments.deleteMemory")}
            >
              <Trash2 size={16} />
            </button>
          </>
        )}
      </div>
    </header>
  );
}