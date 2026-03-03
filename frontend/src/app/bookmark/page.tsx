"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, MapPin, ArrowRight, Check, Bookmark as BookmarkIcon, Loader2 } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { useRouter } from "next/navigation";
import { BookmarkedPlaceItem, BookmarkedRoomItem, createRoom, fetchBookmarkedPlaces, fetchBookmarkedRooms } from "@/services/api";

const DEFAULT_PLACEHOLDER = "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200&q=80";

export default function BookmarkPage() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<"sessions" | "places">("sessions");
    const [selectedPlaces, setSelectedPlaces] = useState<number[]>([]);
    const [sessions, setSessions] = useState<BookmarkedRoomItem[]>([]);
    const [places, setPlaces] = useState<BookmarkedPlaceItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isCreatingRoom, setIsCreatingRoom] = useState(false);

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
                setError("북마크를 불러오지 못했습니다.");
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
        () => places.filter((place) => selectedPlaces.includes(place.id)),
        [places, selectedPlaces]
    );

    const togglePlaceSelection = (id: number) => {
        if (selectedPlaces.includes(id)) {
            setSelectedPlaces((prev) => prev.filter((placeId) => placeId !== id));
        } else if (selectedPlaces.length < 5) {
            setSelectedPlaces((prev) => [...prev, id]);
        }
    };

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
                ? `${topNames.join(", ")} 여행 계획`
                : "선택 장소 여행 계획";

            const newRoom = await createRoom(roomTitle);

            localStorage.setItem(
                `triver:selected-places:${newRoom.id}`,
                JSON.stringify(
                    selectedPlaceItems.map((place) => ({
                        id: place.id,
                        place_id: place.place_id,
                        name: place.name,
                        adress: place.adress,
                        image_path: place.image_path,
                        room_id: place.room_id,
                    }))
                )
            );

            window.dispatchEvent(new CustomEvent("triver:rooms-updated"));
            router.push(`/chatbot?roomId=${newRoom.id}`);
        } catch {
            setError("새 채팅방 생성에 실패했습니다.");
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
                        <h1 className="text-xl font-serif font-bold text-gray-900 flex items-center gap-2">
                            Bookmarks <BookmarkIcon size={16} className="text-gray-400" />
                        </h1>
                        <p className="text-xs text-gray-500 mt-1 font-medium tracking-wide uppercase">Saved Chats & Spots</p>
                    </div>
                    <div className="bg-gray-100 p-1 rounded-lg flex gap-0.5">
                        <button
                            onClick={() => setActiveTab("sessions")}
                            className={`px-4 py-1.5 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all ${activeTab === "sessions" ? "bg-white shadow-sm text-black ring-1 ring-gray-200" : "text-gray-400 hover:text-gray-600"}`}
                        >
                            Sessions
                        </button>
                        <button
                            onClick={() => setActiveTab("places")}
                            className={`px-4 py-1.5 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all ${activeTab === "places" ? "bg-white shadow-sm text-black ring-1 ring-gray-200" : "text-gray-400 hover:text-gray-600"}`}
                        >
                            Places
                        </button>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto p-6 pb-24">
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
                                            북마크된 채팅방이 없습니다.
                                        </div>
                                    ) : (
                                        sessions.map((session) => (
                                            <div key={session.id} className="group rounded-md bg-gray-50 border border-gray-200 rounded-lg p-5 hover:border-black transition-all duration-200 flex items-center justify-between shadow-sm hover:shadow-md group-hover:bg-black group-hover:text-white cursor-pointer">
                                                <div className="flex items-start gap-4">
                                                    <div className="w-10 h-10 flex items-center justify-center text-gray-900 transition-colors">
                                                        <MessageSquare size={16} strokeWidth={1.5} />
                                                    </div>
                                                    <div>
                                                        <h3 className="font-bold text-sm text-gray-900 mb-0.5">{session.title}</h3>
                                                        <p className="text-xs text-gray-500 mb-2 line-clamp-1">
                                                            {session.latest_message_preview || "대화 내역이 없습니다."}
                                                        </p>
                                                        <span className="text-[10px] font-medium text-gray-400 uppercase tracking-widest">
                                                            {new Date(session.created_at).toLocaleDateString()}
                                                        </span>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => router.push(`/chatbot?roomId=${session.id}`)}
                                                    className="opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all duration-200 text-black p-2 hover:bg-gray-100 rounded-md"
                                                >
                                                    <ArrowRight size={16} />
                                                </button>
                                            </div>
                                        ))
                                    )}
                                </motion.div>
                            ) : (
                                <motion.div key="places" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {places.length === 0 ? (
                                        <div className="col-span-full h-56 rounded-lg border border-dashed border-gray-300 bg-gray-50 flex items-center justify-center text-sm text-gray-500">
                                            북마크된 장소가 없습니다.
                                        </div>
                                    ) : (
                                        places.map((place) => {
                                            const isSelected = selectedPlaces.includes(place.id);
                                            const imageUrl = place.image_path || DEFAULT_PLACEHOLDER;
                                            return (
                                                <div
                                                    key={place.id}
                                                    onClick={() => togglePlaceSelection(place.id)}
                                                    className={`group relative h-60 rounded-lg overflow-hidden cursor-pointer border-2 transition-all duration-200 ${isSelected ? "border-black shadow-lg" : "border-transparent"}`}
                                                >
                                                    <img src={imageUrl} alt={place.name || "Bookmarked place"} className="absolute inset-0 w-full h-full object-cover object-center transition-transform duration-700 group-hover:scale-105" />
                                                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/10 to-transparent opacity-90" />
                                                    <div className="absolute top-3 right-3 w-6 h-6 flex items-center justify-center">
                                                        {isSelected ? (
                                                            <div className="w-full h-full bg-black border border-white flex items-center justify-center rounded-sm text-white shadow-lg">
                                                                <Check size={12} strokeWidth={3} />
                                                            </div>
                                                        ) : (
                                                            <div className="w-full h-full border-2 border-white/50 rounded-sm hover:border-white transition-colors" />
                                                        )}
                                                    </div>
                                                    <div className="absolute bottom-0 left-0 w-full p-5">
                                                        <h3 className="text-white font-medium text-xl mb-1 leading-none line-clamp-1">
                                                            {place.name || "Unnamed place"}
                                                        </h3>
                                                        <p className="text-white/60 text-[10px] font-bold uppercase tracking-widest flex items-center gap-1 line-clamp-1">
                                                            <MapPin size={10} /> {place.adress || place.room_title}
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
                    {activeTab === "places" && selectedPlaces.length > 0 && (
                        <motion.div
                            initial={{ y: 100, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            exit={{ y: 100, opacity: 0 }}
                            className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30 w-full max-w-md px-6"
                        >
                            <button
                                onClick={handlePlanWithSelection}
                                disabled={isCreatingRoom}
                                className="w-full bg-black text-white px-6 py-4 rounded-lg shadow-2xl hover:bg-gray-900 font-bold text-xs uppercase tracking-widest flex items-center justify-between group transition-all"
                            >
                                <div className="flex items-center gap-3">
                                    <span className="bg-white text-black text-[10px] font-extrabold w-5 h-5 flex items-center justify-center rounded-sm">{selectedPlaces.length}</span>
                                    <span>{isCreatingRoom ? "Creating Room..." : "Plan Trip with Selection"}</span>
                                </div>
                                <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>
        </div>
    );
}
