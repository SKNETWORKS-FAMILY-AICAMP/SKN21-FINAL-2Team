"use client";

import { useEffect, useMemo, useState } from "react";
import { useMultiSelect } from "@/hooks/useMultiSelect";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, MapPin, ArrowRight, Check, Bookmark as BookmarkIcon, Loader2, Trash2, X } from "lucide-react";
import { Sidebar } from "@/components/navigation/Sidebar";
import { useRouter } from "next/navigation";
import {
    BookmarkedPlaceItem,
    BookmarkedRoomItem,
    createRoom,
    fetchBookmarkedPlaces,
    fetchBookmarkedRooms,
    updatePlaceBookmark,
    updateRoomBookmark,
} from "@/services/api";
import { setPendingAutoStartMeta } from "@/services/autoStart";
import { useTranslation } from "@/i18n/useTranslation";
import { SimpleModal } from "@/components/common/SimpleModal";
import { AlertTriangle } from "lucide-react";
import { PLACE_PLACEHOLDER } from "@/lib/imageUrl";

export function BookmarkPage() {
    const router = useRouter();
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState<"sessions" | "places">("sessions");
    const [selectedPlacesForPlan, setSelectedPlacesForPlan] = useState<number[]>([]);
    const [isDeletingSessions, setIsDeletingSessions] = useState<boolean>(false);
    const [isDeletingPlaces, setIsDeletingPlaces] = useState<boolean>(false);
    const {
        selected: selectedSessionIdsForDelete,
        toggle: toggleSessionSelectionForDelete,
        clear: clearSelectedSessions,
        setSelected: setSelectedSessionIdsForDelete,
    } = useMultiSelect<number>();
    const {
        selected: selectedPlaceIdsForDelete,
        toggle: togglePlaceSelectionForDelete,
        clear: clearSelectedPlaces,
        setSelected: setSelectedPlaceIdsForDelete,
    } = useMultiSelect<number>();
    const [confirmOpen, setConfirmOpen] = useState<boolean>(false);
    const [confirmKind, setConfirmKind] = useState<"sessions" | "places">("sessions");
    const [sessions, setSessions] = useState<BookmarkedRoomItem[]>([]);
    const [places, setPlaces] = useState<BookmarkedPlaceItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isCreatingRoom, setIsCreatingRoom] = useState(false);
    const [isDeletingSubmitting, setIsDeletingSubmitting] = useState<boolean>(false);

    useEffect(() => {
        let cancelled = false;
        const loadBookmarks = async () => {
            setLoading(true);
            setError(null);
            try {
                const [bookmarkedRooms, bookmarkedPlaces] = await Promise.all([
                    fetchBookmarkedRooms(),
                    fetchBookmarkedPlaces(),
                ]);
                if (cancelled) return;
                setSessions(bookmarkedRooms);
                setPlaces(bookmarkedPlaces);
            } catch {
                if (cancelled) return;
                setError(t("bookmark.loadFailed"));
            } finally {
                if (!cancelled) setLoading(false);
            }
        };

        void loadBookmarks();
        return () => {
            cancelled = true;
        };
    }, []);

    const selectedPlaceItems = useMemo(
        () => places.filter((place) => selectedPlacesForPlan.includes(place.id)),
        [places, selectedPlacesForPlan]
    );

    const togglePlaceSelectionForPlan = (id: number) => {
        if (selectedPlacesForPlan.includes(id)) {
            setSelectedPlacesForPlan((prev) => prev.filter((placeId) => placeId !== id));
        } else if (selectedPlacesForPlan.length < 5) {
            setSelectedPlacesForPlan((prev) => [...prev, id]);
        }
    };

    const handleEnterDeleteSessions = () => {
        setIsDeletingSessions(true);
        clearSelectedSessions();
        setError(null);
    };

    const handleCancelDeleteSessions = () => {
        setIsDeletingSessions(false);
        clearSelectedSessions();
        setConfirmOpen(false);
        setError(null);
    };

    const handleEnterDeletePlaces = () => {
        setIsDeletingPlaces(true);
        clearSelectedPlaces();
        setSelectedPlacesForPlan([]);
        setError(null);
    };

    const handleCancelDeletePlaces = () => {
        setIsDeletingPlaces(false);
        clearSelectedPlaces();
        setConfirmOpen(false);
        setError(null);
    };

    const openConfirmForSessions = () => {
        if (selectedSessionIdsForDelete.length === 0) return;
        setConfirmKind("sessions");
        setConfirmOpen(true);
    };

    const openConfirmForPlaces = () => {
        if (selectedPlaceIdsForDelete.length === 0) return;
        setConfirmKind("places");
        setConfirmOpen(true);
    };

    const closeConfirm = () => {
        if (isDeletingSubmitting) return;
        setConfirmOpen(false);
    };

    const confirmDeleteSelected = async () => {
        if (isDeletingSubmitting) return;
        setIsDeletingSubmitting(true);
        setError(null);

        try {
            if (confirmKind === "sessions") {
                const ids = [...selectedSessionIdsForDelete];
                await Promise.all(ids.map((roomId) => updateRoomBookmark(roomId, false)));
                setSessions((prev) => prev.filter((s) => !ids.includes(s.id)));
                clearSelectedSessions();
                setIsDeletingSessions(false);
            } else {
                const ids = [...selectedPlaceIdsForDelete];
                await Promise.all(ids.map((placeId) => updatePlaceBookmark(placeId, false)));
                setPlaces((prev) => prev.filter((p) => !ids.includes(p.id)));
                clearSelectedPlaces();
                setIsDeletingPlaces(false);
            }
            setConfirmOpen(false);
        } catch {
            setError(t("bookmark.deleteFailed"));
            setConfirmOpen(false);
        } finally {
            setIsDeletingSubmitting(false);
        }
    };

    const confirmMessage = useMemo(() => {
        if (confirmKind === "sessions") {
            const count = selectedSessionIdsForDelete.length;
            if (count <= 1) return t("bookmark.confirmDeleteSession");
            return t("bookmark.confirmDeleteSessions");
        }
        const count = selectedPlaceIdsForDelete.length;
        if (count <= 1) return t("bookmark.confirmDeletePlace");
        return t("bookmark.confirmDeletePlaces");
    }, [confirmKind, selectedPlaceIdsForDelete.length, selectedSessionIdsForDelete.length, t]);

    const handlePlanWithSelection = async () => {
        if (selectedPlaceItems.length === 0) return;
        if (isCreatingRoom) return;

        try {
            setIsCreatingRoom(true);
            const topNames = selectedPlaceItems
                .map((place) => place.name)
                .filter((name): name is string => !!name)
                .slice(0, 2);
            const roomTitle = topNames.length > 0
                ? `${topNames.join(", ")} ${t("bookmark.travelPlan")}`
                : t("bookmark.selectedPlacesPlan");

            const newRoom = await createRoom(roomTitle);

            setPendingAutoStartMeta(newRoom.id, {
                mode: "selected_places",
                selectedPlaces: selectedPlaceItems.map((place) => ({
                    id: place.id,
                    contenttypeid: place.contenttypeid,
                    name: place.name,
                    adress: place.adress,
                    image_path: place.image_path,
                    room_id: place.room_id,
                })),
            });

            window.dispatchEvent(new CustomEvent("triver:rooms-updated"));
            router.push(`/chatbot?roomId=${newRoom.id}`);
        } catch {
            setError(t("bookmark.createRoomFailed"));
        } finally {
            setIsCreatingRoom(false);
        }
    };

    return (
        <div className="flex w-full h-screen bg-gray-100 p-4 gap-4 overflow-hidden">
            <div className="flex-none h-full">
                <Sidebar />
            </div>
            <main className="flex-1 h-full relative min-w-0 bg-white rounded-lg flex flex-col overflow-hidden">
                <header className="flex-none p-6 pb-4 border-b border-gray-100 flex items-center justify-between bg-white z-10">
                    <div>
                        <h1 className="page-title text-gray-900 flex items-center gap-2">
                            {t("bookmark.pageTitle")} <BookmarkIcon size={16} className="text-gray-400" />
                        </h1>
                        <p className="page-subtitle mt-1">{t("bookmark.pageSubtitle")}</p>
                    </div>
                    <div className="flex flex-col-reverse md:flex-row md:items-center gap-3">
                        <div className="bg-gray-100 p-1 rounded-full flex gap-1 self-start md:self-auto">
                            <button
                                onClick={() => {
                                    setActiveTab("sessions");
                                    setIsDeletingPlaces(false);
                                    clearSelectedPlaces();
                                    setSelectedPlacesForPlan([]);
                                    setConfirmOpen(false);
                                }}
                                className={`px-5 py-1.5 rounded-full text-[11px] font-bold uppercase transition-all ${activeTab === "sessions" ? "bg-white shadow-sm text-black ring-1 ring-gray-200" : "text-gray-400 hover:text-gray-600"}`}
                            >
                                {t("bookmark.tabSessions")}
                            </button>
                            <button
                                onClick={() => {
                                    setActiveTab("places");
                                    setIsDeletingSessions(false);
                                    clearSelectedSessions();
                                    setConfirmOpen(false);
                                }}
                                className={`px-5 py-1.5 rounded-full text-[11px] font-bold uppercase transition-all ${activeTab === "places" ? "bg-white shadow-sm text-black ring-1 ring-gray-200" : "text-gray-400 hover:text-gray-600"}`}
                            >
                                {t("bookmark.tabPlaces")}
                            </button>
                        </div>

                        <div className="flex items-center gap-3">
                            {activeTab === "sessions" ? (
                                isDeletingSessions ? (
                                    <>
                                        <button
                                            onClick={openConfirmForSessions}
                                            disabled={selectedSessionIdsForDelete.length === 0}
                                            className={`flex items-center gap-1.5 rounded-full px-5 py-2.5 text-sm font-semibold transition-colors ${selectedSessionIdsForDelete.length > 0 ? "bg-black text-white hover:bg-gray-800" : "bg-gray-100 text-gray-300 cursor-not-allowed"}`}
                                        >
                                            <Trash2 size={14} />
                                            {selectedSessionIdsForDelete.length > 0 ? `${selectedSessionIdsForDelete.length} ${t("bookmark.deleteSelected") || "삭제"}` : t("bookmark.deleteSelected")}
                                        </button>
                                        <button
                                            onClick={handleCancelDeleteSessions}
                                            className="flex items-center justify-center rounded-full border border-gray-200 p-2.5 text-gray-500 transition-colors hover:bg-gray-100"
                                            title={t("bookmark.cancel")}
                                        >
                                            <X size={16} />
                                        </button>
                                    </>
                                ) : (
                                    <button
                                        onClick={handleEnterDeleteSessions}
                                        className="flex items-center justify-center rounded-full border border-gray-200 p-2.5 text-gray-400 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-500"
                                        title={t("bookmark.deleteChat")}
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                )
                            ) : activeTab === "places" ? (
                                isDeletingPlaces ? (
                                    <>
                                        <button
                                            onClick={openConfirmForPlaces}
                                            disabled={selectedPlaceIdsForDelete.length === 0}
                                            className={`flex items-center gap-1.5 rounded-full px-5 py-2.5 text-sm font-semibold transition-colors ${selectedPlaceIdsForDelete.length > 0 ? "bg-black text-white hover:bg-gray-800" : "bg-gray-100 text-gray-300 cursor-not-allowed"}`}
                                        >
                                            <Trash2 size={14} />
                                            {selectedPlaceIdsForDelete.length > 0 ? `${selectedPlaceIdsForDelete.length} ${t("bookmark.deleteSelected") || "삭제"}` : t("bookmark.deleteSelected")}
                                        </button>
                                        <button
                                            onClick={handleCancelDeletePlaces}
                                            className="flex items-center justify-center rounded-full border border-gray-200 p-2.5 text-gray-500 transition-colors hover:bg-gray-100"
                                            title={t("bookmark.cancel")}
                                        >
                                            <X size={16} />
                                        </button>
                                    </>
                                ) : (
                                    <button
                                        onClick={handleEnterDeletePlaces}
                                        className="flex items-center justify-center rounded-full border border-gray-200 p-2.5 text-gray-400 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-500"
                                        title={t("bookmark.deletePlace")}
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                )
                            ) : null}
                        </div>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto custom-scrollbar p-6 pb-24">
                    {loading ? (
                        <div className="h-full flex items-center justify-center text-gray-400">
                            <Loader2 className="w-6 h-6 animate-spin" />
                        </div>
                    ) : error ? (
                        <div className="h-full flex items-center justify-center text-sm text-gray-500">{error}</div>
                    ) : (
                        <AnimatePresence mode="wait">
                            {activeTab === "sessions" ? (
                                <motion.div key="sessions" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-3">
                                    {sessions.length === 0 ? (
                                        <div className="h-56 rounded-lg border border-dashed border-gray-300 bg-gray-50 flex items-center justify-center text-sm text-gray-500">
                                            {t("bookmark.noSessions")}
                                        </div>
                                    ) : (
                                        sessions.map((session) => (
                                            <div
                                                key={session.id}
                                                onClick={() => {
                                                    if (isDeletingSessions) {
                                                        toggleSessionSelectionForDelete(session.id);
                                                        return;
                                                    }
                                                    router.push(`/chatbot?roomId=${session.id}`);
                                                }}
                                                className={`group relative rounded-2xl bg-white border border-gray-200 p-5 transition-all duration-200 flex flex-col justify-center min-w-0 cursor-pointer shadow-sm hover:shadow-md hover:border-black ${
                                                    isDeletingSessions
                                                        ? selectedSessionIdsForDelete.includes(session.id)
                                                            ? "ring-2 ring-black scale-[0.98] bg-gray-50"
                                                            : "opacity-70 hover:opacity-100 hover:border-gray-400"
                                                        : ""
                                                }`}
                                            >
                                                {isDeletingSessions && (
                                                    <div className={`absolute top-4 right-4 z-10 flex h-6 w-6 items-center justify-center rounded-full border-2 transition-all duration-200 shadow-sm ${selectedSessionIdsForDelete.includes(session.id) ? "border-black bg-black text-white" : "border-gray-300 bg-white text-transparent"}`}>
                                                        <Check size={13} strokeWidth={3} />
                                                    </div>
                                                )}
                                                <div className="flex items-center gap-4 min-w-0 flex-1">
                                                    <div className="w-12 h-12 flex items-center justify-center rounded-2xl bg-gray-50 text-gray-700 transition-colors flex-none border border-gray-100 group-hover:bg-gray-100">
                                                        <MessageSquare size={20} className="opacity-80" strokeWidth={1.5} />
                                                    </div>
                                                    <div className="min-w-0 flex-1 pr-6">
                                                        <h3 className="font-bold text-gray-900 truncate text-[13px] mb-0.5 group-hover:text-blue-600 transition-colors">{session.title}</h3>
                                                        <p className="text-xs text-gray-500 mb-1.5 truncate">
                                                            {session.latest_message_preview || t("bookmark.noHistory")}
                                                        </p>
                                                        <span className="text-[10px] font-bold text-gray-400 flex items-center gap-1 uppercase">
                                                            {new Date(session.created_at).toLocaleDateString()}
                                                        </span>
                                                    </div>
                                                    {!isDeletingSessions && (
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                router.push(`/chatbot?roomId=${session.id}`);
                                                            }}
                                                            className="opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all duration-200 text-gray-400 hover:text-black p-2 hover:bg-gray-100 rounded-full flex-none shrink-0"
                                                        >
                                                            <ArrowRight size={18} />
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </motion.div>
                            ) : (
                                <motion.div key="places" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {places.length === 0 ? (
                                        <div className="col-span-full h-56 rounded-lg border border-dashed border-gray-300 bg-gray-50 flex items-center justify-center text-sm text-gray-500">
                                            {t("bookmark.noPlaces")}
                                        </div>
                                    ) : (
                                        places.map((place) => {
                                            const isSelected = isDeletingPlaces
                                                ? selectedPlaceIdsForDelete.includes(place.id)
                                                : selectedPlacesForPlan.includes(place.id);
                                            const imageUrl = place.image_path || PLACE_PLACEHOLDER;
                                            return (
                                                <div
                                                    key={place.id}
                                                    onClick={() => (isDeletingPlaces ? togglePlaceSelectionForDelete(place.id) : togglePlaceSelectionForPlan(place.id))}
                                                    className={`group relative h-60 w-full overflow-hidden rounded-2xl cursor-pointer text-left shadow-sm transition-all hover:shadow-lg ${
                                                        isDeletingPlaces
                                                            ? isSelected
                                                                ? "ring-2 ring-black scale-[0.98]"
                                                                : "opacity-70 hover:opacity-100"
                                                            : isSelected
                                                                ? "ring-2 ring-black scale-[0.98]"
                                                                : ""
                                                    }`}
                                                >
                                                    <img src={imageUrl} alt={place.name || t("bookmark.placeAlt")} onError={(e) => { e.currentTarget.src = PLACE_PLACEHOLDER; }} className="absolute inset-0 w-full h-full object-cover object-center transition-transform duration-700 group-hover:scale-105" />
                                                    <div className={`absolute inset-0 transition-colors duration-300 ${isDeletingPlaces && isSelected ? "bg-black/20" : "bg-black/0 group-hover:bg-black/20"}`} />
                                                    
                                                    {!isDeletingPlaces && isSelected && (
                                                        <div className="pointer-events-none absolute inset-0 rounded-2xl border-[3px] border-black z-10" />
                                                    )}
                                                    
                                                    {(isDeletingPlaces || isSelected) && (
                                                        <div className={`absolute top-3 right-3 z-10 flex h-6 w-6 items-center justify-center rounded-full border-2 transition-all duration-200 shadow-sm ${
                                                            isSelected
                                                                ? "border-black bg-black text-white"
                                                                : "border-white/80 bg-black/30 text-transparent"
                                                        }`}>
                                                            <Check size={13} strokeWidth={3} />
                                                        </div>
                                                    )}

                                                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/35 to-transparent p-5">
                                                        <h3 className="text-white font-medium text-xl mb-1 leading-none truncate">
                                                            {place.name || t("bookmark.unnamedPlace")}
                                                        </h3>
                                                        <p className="text-white/60 text-[10px] font-bold uppercase flex items-center gap-1 min-w-0">
                                                            <MapPin size={10} className="flex-none" />
                                                            <span className="truncate">{place.adress || place.room_title}</span>
                                                        </p>
                                                    </div>
                                                </div>
                                            );
                                        })
                                    )}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    )}
                </div>

                <AnimatePresence>
                    {activeTab === "places" && !isDeletingPlaces && selectedPlacesForPlan.length > 0 && (
                        <motion.div
                            initial={{ y: 100, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            exit={{ y: 100, opacity: 0 }}
                            className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30 w-full max-w-md px-6"
                        >
                            <button
                                onClick={handlePlanWithSelection}
                                disabled={isCreatingRoom}
                                className="w-full bg-black text-white px-6 py-4 rounded-2xl shadow-2xl hover:bg-zinc-800 font-bold text-xs uppercase flex items-center justify-between group transition-all"
                            >
                                <div className="flex items-center gap-3">
                                    <span className="bg-white text-black text-[10px] font-extrabold w-5 h-5 flex items-center justify-center rounded-sm">{selectedPlacesForPlan.length}</span>
                                    <span>{isCreatingRoom ? t("bookmark.creatingRoom") : t("bookmark.planWithSelection")}</span>
                                </div>
                                <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>



                <SimpleModal
                    open={confirmOpen}
                    onClose={closeConfirm}
                    title={t("bookmark.confirmTitle")}
                    icon={<AlertTriangle size={20} />}
                    maxWidth="sm"
                >
                    <div className="flex flex-col">
                        <p className="text-[14px] font-medium text-gray-800 mb-6 leading-relaxed">
                            {t("bookmark.deleteConfirmDesc")}
                        </p>
                        <div className="flex flex-col gap-3">
                            <div className="flex gap-3">
                                <button
                                    type="button"
                                    onClick={confirmDeleteSelected}
                                    disabled={isDeletingSubmitting}
                                    className="w-full py-4 rounded-2xl bg-black text-white text-sm font-bold shadow-lg hover:bg-gray-800 transition-all flex items-center justify-center gap-2 active:scale-[0.98] disabled:opacity-50"
                                >
                                    {isDeletingSubmitting ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                                    {isDeletingSubmitting ? t("bookmark.deleting") : t("common.yes")}
                                </button>
                            </div>
                        </div>
                    </div>
                </SimpleModal>
            </main>
        </div>
    );
}
