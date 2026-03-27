import { ChangeEvent, RefObject } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Camera, Loader2, MapPin, Pencil, Save, X } from "lucide-react";

import { MomentListItem } from "@/services/api";
import { useTranslation } from "@/i18n/useTranslation";

import { EditorState } from "../types";
import { todayString } from "../utils";

type MomentEditorModalProps = {
  isOpen: boolean;
  isEditMode: boolean;
  detailLoading: boolean;
  saving: boolean;
  error: string | null;
  editor: EditorState;
  selectedMomentSummary: MomentListItem | null;
  modalImageInputRef: RefObject<HTMLInputElement | null>;
  onClose: () => void;
  onEnterEditMode: () => void;
  onImageChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onEditorChange: (updater: (prev: EditorState) => EditorState) => void;
  onOpenLocationPicker: () => void;
  onClearLocation: () => void;
  onSave: () => void;
};

export function MomentEditorModal({
  isOpen,
  isEditMode,
  detailLoading,
  saving,
  error,
  editor,
  selectedMomentSummary,
  modalImageInputRef,
  onClose,
  onEnterEditMode,
  onImageChange,
  onEditorChange,
  onOpenLocationPicker,
  onClearLocation,
  onSave,
}: MomentEditorModalProps) {
  const { t } = useTranslation();
  const hasLocation = Boolean(editor.adress);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9998] bg-black/30 backdrop-blur-md"
            onClick={onClose}
          />

          {/* Modal Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="fixed inset-0 z-[9999] flex items-center justify-center p-4 md:p-8 pointer-events-none"
          >
            <div
              className="relative flex h-[85vh] w-full max-w-5xl flex-col md:flex-row overflow-hidden rounded-[2.5rem] bg-white border border-gray-100 shadow-[0_32px_80px_-16px_rgba(0,0,0,0.08)] pointer-events-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Left Side: Image Section */}
              {(() => {
                const imagePath =
                  editor.image_path || selectedMomentSummary?.image_path || "";

                return (
                  <div className="relative flex-1 overflow-hidden bg-gray-50 border-r border-gray-100">
                    <div
                      className="h-full w-full cursor-pointer relative group"
                      onClick={() => isEditMode && modalImageInputRef.current?.click()}
                    >
                      {imagePath ? (
                        <img
                          src={imagePath}
                          alt={editor.title || t("diary.coverAlt")}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full w-full flex-col items-center justify-center text-gray-400 gap-3">
                          <div className="w-12 h-12 bg-white rounded-xl shadow-lg flex items-center justify-center mb-3">
                            <Camera size={20} className="text-gray-400 group-hover:text-gray-900 transition-colors" />
                          </div>
                          <p className="text-sm font-medium">{isEditMode ? t("diary.addCoverPhoto") : t("diary.noCoverPhoto")}</p>
                        </div>
                      )}

                      {isEditMode && (
                        <>
                          <input
                            ref={modalImageInputRef}
                            type="file"
                            accept="image/*"
                            className="hidden"
                            onChange={onImageChange}
                          />
                          {imagePath && (
                            <div className="absolute inset-0 bg-black/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                              <span className="bg-black text-white px-5 py-2.5 rounded-full text-xs font-bold shadow-lg flex items-center gap-2">
                                <Camera size={14} /> {t("diary.changePhoto")}
                              </span>
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    {/* Left overlay content (Title, Date) */}
                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-10 pt-20">
                      {isEditMode ? (
                        <input
                          value={editor.title}
                          onChange={(event) =>
                            onEditorChange((prev) => ({ ...prev, title: event.target.value }))
                          }
                          placeholder={t("diary.titlePlaceholder")}
                          className="w-full border-b border-white/40 bg-transparent pb-2 text-3xl font-bold text-white outline-none placeholder:text-white/60"
                        />
                      ) : (
                        <h1 className="text-3xl font-bold text-white">
                          {editor.title || t("diary.noTitle")}
                        </h1>
                      )}
                      
                      <div className="mt-4 flex flex-wrap items-center gap-3">
                         <span className="text-sm font-medium text-white/90">{editor.entry_date || todayString()}</span>
                         
                         {isEditMode && (
                           hasLocation ? (
                             <div className="flex items-center gap-2 bg-white/20 backdrop-blur-md px-4 py-1.5 rounded-full border border-white/20 text-xs font-bold text-white">
                                <MapPin size={12} className="shrink-0" />
                                <span className="truncate">{editor.adress}</span>
                                <button type="button" onClick={onClearLocation} className="hover:text-red-300 ml-1 shrink-0"><X size={12}/></button>
                             </div>
                           ) : (
                             <button type="button" onClick={onOpenLocationPicker} className="bg-white/20 backdrop-blur-md px-4 py-1.5 rounded-full border border-white/20 text-xs font-bold text-white hover:bg-white/30 truncate">
                                + {t("diary.addLocation")}
                             </button>
                           )
                         )}
                         {!isEditMode && hasLocation && (
                            <div className="flex items-center gap-2 bg-white/20 backdrop-blur-md px-4 py-1.5 rounded-full border border-white/20 text-xs font-bold text-white">
                                <MapPin size={12} className="shrink-0" />
                                <span className="truncate">{editor.adress}</span>
                            </div>
                         )}
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Right Side: Content Section */}
              <div className="flex w-full flex-col bg-white p-8 md:p-10 md:w-[420px]">
                <div className="mb-6 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="text-[14px] font-bold text-[#8b98a5] uppercase">{t("diary.label")}</div>
                    {isEditMode ? (
                      <input
                        type="date"
                        value={editor.entry_date}
                        onChange={(event) =>
                          onEditorChange((prev) => ({ ...prev, entry_date: event.target.value }))
                        }
                        className="bg-gray-50 px-3 py-1.5 rounded-lg text-sm text-gray-600 font-bold border border-gray-100 outline-none"
                      />
                    ) : (
                      <span className="text-sm font-bold text-gray-400">{editor.entry_date}</span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={onClose}
                    className="p-2 -mr-2 text-gray-400 hover:text-gray-800 hover:bg-gray-50 rounded-full transition-all"
                  >
                    <X size={20} />
                  </button>
                </div>

                {detailLoading ? (
                  <div className="flex flex-1 items-center justify-center">
                    <Loader2 className="h-6 w-6 animate-spin text-black" />
                  </div>
                ) : (
                  <>
                    <div className="flex flex-1 flex-col overflow-y-auto pr-2 custom-scrollbar">
                      {isEditMode ? (
                        <textarea
                          value={editor.content}
                          onChange={(event) =>
                            onEditorChange((prev) => ({ ...prev, content: event.target.value }))
                          }
                          placeholder={t("diary.contentPlaceholder")}
                          className="flex-1 resize-none bg-gray-50 border border-gray-100 rounded-2xl p-5 text-[14px] leading-relaxed text-gray-700 outline-none placeholder:text-gray-400 focus:bg-white focus:border-gray-200 transition-colors shadow-sm"
                        />
                      ) : (
                        <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-gray-600">
                          {editor.content || t("diary.noContent")}
                        </p>
                      )}
                      {error && <p className="mt-4 text-sm text-red-500 font-medium">{error}</p>}
                    </div>

                    <div className="mt-8 pt-8 border-t border-gray-100 flex flex-col gap-4">
                      {isEditMode ? (
                        <button
                          type="button"
                          onClick={onSave}
                          disabled={saving}
                          className="w-full py-4 rounded-2xl bg-black text-white text-sm font-bold shadow-lg hover:bg-gray-800 transition-all flex items-center justify-center gap-2 active:scale-[0.98] disabled:opacity-50"
                        >
                          {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                          {t("common.save")}
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={onEnterEditMode}
                          className="w-full py-4 rounded-2xl bg-black text-white text-sm font-bold shadow-lg hover:bg-gray-800 transition-all flex items-center justify-center gap-2 active:scale-[0.98]"
                        >
                          <Pencil size={16} />
                          {t("common.edit")}
                        </button>
                      )}
                      
                      {!isEditMode && (
                        <button type="button" onClick={onClose} className="w-full py-4 rounded-2xl bg-gray-50 text-gray-500 text-sm font-medium hover:bg-gray-100 transition-colors">
                           {t("common.close")}
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
