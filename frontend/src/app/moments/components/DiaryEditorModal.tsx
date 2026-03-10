import { ChangeEvent, RefObject } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Camera, Loader2, MapPin, Save, X } from "lucide-react";

import { DiaryListItem } from "@/services/api";

import { EditorState } from "../types";
import { todayString } from "../utils";

type DiaryEditorModalProps = {
  isOpen: boolean;
  detailLoading: boolean;
  saving: boolean;
  error: string | null;
  editor: EditorState;
  selectedDiarySummary: DiaryListItem | null;
  modalImageInputRef: RefObject<HTMLInputElement | null>;
  onClose: () => void;
  onImageChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onEditorChange: (updater: (prev: EditorState) => EditorState) => void;
  onOpenLocationPicker: () => void;
  onClearLinkedPlace: () => void;
  onSave: () => void;
};

export function DiaryEditorModal({
  isOpen,
  detailLoading,
  saving,
  error,
  editor,
  selectedDiarySummary,
  modalImageInputRef,
  onClose,
  onImageChange,
  onEditorChange,
  onOpenLocationPicker,
  onClearLinkedPlace,
  onSave,
}: DiaryEditorModalProps) {
  const linkedPlace = editor.linked_places[0] ?? null;

  return (
    <AnimatePresence>
      {isOpen && (
          <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-white/10 p-4 backdrop-blur-md md:p-8"
          onClick={onClose}
        >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(event) => event.stopPropagation()}
          className="flex h-[78vh] w-full max-w-5xl flex-col overflow-hidden rounded-3xl border border-zinc-800 bg-black shadow-2xl md:flex-row"
          >
            {(() => {
              const coverImagePath =
                editor.cover_image_path || selectedDiarySummary?.cover_image_path || "";

              return (
            <div className="group relative flex-1 overflow-hidden bg-black">
              <button
                onClick={onClose}
                aria-label="Close diary modal"
                className="absolute right-4 top-4 z-20 flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-black/50 text-white transition-colors hover:bg-black/70"
              >
                <X size={18} />
              </button>

              <div
                className="h-full w-full cursor-pointer"
                onClick={() => modalImageInputRef.current?.click()}
              >
                {coverImagePath ? (
                  <img
                    src={coverImagePath}
                    alt={editor.title || "Diary cover"}
                    className="h-full w-full object-cover opacity-90 transition-opacity group-hover:opacity-100"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center bg-zinc-950 text-zinc-600">
                    <div className="text-center">
                      <Camera size={28} className="mx-auto mb-3" />
                      <p className="text-sm">Add a cover photo</p>
                    </div>
                  </div>
                )}
                <input
                  ref={modalImageInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={onImageChange}
                />
                {coverImagePath && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
                    <span className="flex items-center gap-2 rounded-full border border-white/10 bg-black/60 px-4 py-2 text-sm font-medium text-white backdrop-blur-sm">
                      <Camera size={14} /> Change Photo
                    </span>
                  </div>
                )}
              </div>

              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/95 to-transparent p-6">
                <input
                  value={editor.title}
                  onChange={(event) =>
                    onEditorChange((prev) => ({ ...prev, title: event.target.value }))
                  }
                  placeholder="Title your diary"
                  className="w-full border-b border-white/25 bg-transparent pb-2 text-2xl font-bold text-white outline-none placeholder:text-white/50"
                />
                <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-white/70">
                  <span>{editor.entry_date || todayString()}</span>
                  {linkedPlace ? (
                    <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-white/15 bg-black/35 px-3 py-1.5 text-xs text-white/85">
                      <MapPin size={13} className="shrink-0" />
                      <span className="truncate">{linkedPlace.adress}</span>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          onClearLinkedPlace();
                        }}
                        className="rounded-full px-1 text-white/60 transition hover:text-white"
                        aria-label="Clear linked place"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        onOpenLocationPicker();
                      }}
                      className="inline-flex items-center gap-2 rounded-full border border-dashed border-white/20 bg-black/25 px-3 py-1.5 text-xs text-white/75 transition hover:bg-black/40"
                    >
                      <MapPin size={13} />
                      Add location
                    </button>
                  )}
                  {linkedPlace && (
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        onOpenLocationPicker();
                      }}
                      className="text-xs text-white/70 underline underline-offset-4 transition hover:text-white"
                    >
                      Change location
                    </button>
                  )}
                </div>
              </div>
            </div>
              );
            })()}

            <div className="flex w-full flex-col bg-zinc-950 p-5 md:w-[360px]">
              <div className="mb-6 flex items-center justify-between">
                <div className="text-sm font-semibold text-zinc-200">Diary</div>
                <input
                  type="date"
                  value={editor.entry_date}
                  onChange={(event) =>
                    onEditorChange((prev) => ({ ...prev, entry_date: event.target.value }))
                  }
                  className="cursor-pointer bg-transparent text-sm text-zinc-400 outline-none"
                />
              </div>

              {detailLoading ? (
                <div className="flex flex-1 items-center justify-center text-zinc-400">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : (
                <>
                  <textarea
                    value={editor.content}
                    onChange={(event) =>
                      onEditorChange((prev) => ({ ...prev, content: event.target.value }))
                    }
                    placeholder="오늘의 동선, 감정, 기억하고 싶은 장면을 적어보세요."
                    className="min-h-[220px] flex-1 resize-none bg-transparent text-base leading-relaxed text-zinc-300 outline-none placeholder:text-zinc-700"
                  />

                  <div className="mt-6 space-y-4">
                    {linkedPlace && (
                      <div className="rounded-2xl border border-zinc-900 bg-black/30 p-3">
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-full bg-white text-black">
                            <MapPin size={14} />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-zinc-300">Linked place</p>
                            <p className="mt-1 text-xs leading-5 text-zinc-500">{linkedPlace.adress}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {error && <p className="text-sm text-rose-400">{error}</p>}
                  </div>

                  <div className="mt-6 flex justify-end gap-3 border-t border-zinc-900 pt-6">
                    <button
                      onClick={onSave}
                      disabled={saving}
                      className="flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-zinc-200 disabled:opacity-60"
                    >
                      {saving ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Save size={14} />
                      )}
                      Save
                    </button>
                  </div>
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
