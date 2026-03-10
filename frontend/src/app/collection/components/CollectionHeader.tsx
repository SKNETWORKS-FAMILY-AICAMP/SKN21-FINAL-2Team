import { RefObject } from "react";
import { Grid, Plus, Search } from "lucide-react";

type CollectionHeaderProps = {
  query: string;
  onQueryChange: (value: string) => void;
  uploadInputRef: RefObject<HTMLInputElement | null>;
};

export function CollectionHeader({
  query,
  onQueryChange,
  uploadInputRef,
}: CollectionHeaderProps) {
  return (
    <header className="mb-6 flex flex-none items-end justify-between border-b border-gray-100 pb-4">
      <div>
        <h1 className="page-title mb-1 flex items-center gap-2 text-gray-900">
          Collection <Grid size={16} className="text-gray-400" />
        </h1>
        <p className="page-subtitle">Inspirations & Moments</p>
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
          onClick={() => uploadInputRef.current?.click()}
          className="flex items-center gap-1.5 rounded-full bg-black px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-gray-800"
        >
          <Plus size={14} /> Add Memory
        </button>
      </div>
    </header>
  );
}
