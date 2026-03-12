// [Feature] Add Memory + Delete Memory(쓰레기통 아이콘) 버튼
import { Search, Grid, Plus, Trash2 } from "lucide-react";

type MomentsHeaderProps = {
  query: string;
  onQueryChange: (value: string) => void;
  onCreate: () => void;
  onDeleteSelect: () => void;
};

export function MomentsHeader({
  query,
  onQueryChange,
  onCreate,
  onDeleteSelect,
}: MomentsHeaderProps) {
  return (
    <header className="mb-6 flex flex-none items-end justify-between border-b border-gray-100 pb-4">
      <div>
        <h1 className="page-title mb-1 flex items-center gap-2 text-gray-900">
          Moments <Grid size={16} className="text-gray-400" />
        </h1>
        <p className="page-subtitle">Captured places & memories</p>
      </div>

      <div className="flex items-center gap-3">
        <label className="hidden items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-4 py-2 text-xs text-gray-500 md:flex">
          <Search size={14} />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Search diary"
            className="w-40 bg-transparent text-sm outline-none placeholder:text-gray-400"
          />
        </label>
        <button
          onClick={onCreate}
          className="flex items-center gap-1.5 rounded-full bg-black px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-gray-800"
        >
          <Plus size={14} /> Add Memory
        </button>
        {/* [Feature] Delete Memory - 쓰레기통 아이콘만 표시 */}
        <button
          onClick={onDeleteSelect}
          className="flex items-center justify-center rounded-full border border-gray-200 p-2.5 text-gray-400 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-500"
          title="Delete Memory"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </header>
  );
}