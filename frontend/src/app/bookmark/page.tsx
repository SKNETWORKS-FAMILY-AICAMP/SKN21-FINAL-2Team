"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, MapPin, ArrowRight, Check, Bookmark as BookmarkIcon } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { useRouter } from "next/navigation";

const MOCK_SESSIONS = [
    { id: 1, title: "Romantic Getaway to Jeju", date: "2023-10-15", preview: "Focusing on coastal cafes and sunset spots." },
    { id: 2, title: "Seoul Historic Tour", date: "2023-11-02", preview: "Palaces, museums, and traditional markets." },
    { id: 3, title: "Busan Foodie Adventure", date: "2023-12-20", preview: "Seafood markets and street food exploration." },
];

const MOCK_PLACES = [
    { id: 1, name: "N Seoul Tower", location: "Seoul, Yongsan-gu", image: "https://images.unsplash.com/photo-1687777504692-e825e3cb0e01?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzZW91bCUyMG4lMjB0b3dlciUyMG5pZ2h0JTIwdmlld3xlbnwxfHx8fDE3NzE0Nzk1OTB8MA&ixlib=rb-4.1.0&q=80&w=1080" },
    { id: 2, name: "Gyeongbokgung Palace", location: "Seoul, Jongno-gu", image: "https://images.unsplash.com/photo-1734828813144-7ac7ad69120f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxneWVvbmdib2tndW5nJTIwcGFsYWNlJTIwd2ludGVyJTIwc25vd3xlbnwxfHx8fDE3NzE0Nzk1OTB8MA&ixlib=rb-4.1.0&q=80&w=1080" },
    { id: 3, name: "Haeundae Beach", location: "Busan, Haeundae-gu", image: "https://images.unsplash.com/photo-1552873547-b88e7b2760e2?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxyZWxheGluZyUyMGJlYWNoJTIwcmVzb3J0JTIwbHV4dXJ5fGVufDF8fHx8MTc3MTQ3ODg2NHww&ixlib=rb-4.1.0&q=80&w=1080" },
    { id: 4, name: "Bukchon Hanok Village", location: "Seoul, Jongno-gu", image: "https://images.unsplash.com/photo-1670823927806-5cc785754a4b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx0cmFkaXRpb25hbCUyMGhhbm9rJTIwdmlsbGFnZSUyMGtvcmVhJTIwYXV0dW1ufGVufDF8fHx8MTc3MTQ3OTU4OXww&ixlib=rb-4.1.0&q=80&w=1080" },
    { id: 5, name: "Seongsan Ilchulbong", location: "Jeju, Seogwipo", image: "https://images.unsplash.com/photo-1766244953579-e829796849cc?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxqZWp1JTIwaXNsYW5kJTIwY29hc3QlMjBjbGlmZiUyMG9jZWFufGVufDF8fHx8MTc3MTQ3OTU4OXww&ixlib=rb-4.1.0&q=80&w=1080" },
    { id: 6, name: "Dongdaemun Design Plaza", location: "Seoul, Jung-gu", image: "https://images.unsplash.com/photo-1767168157604-dc1ccfbe3602?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjBtdXNldW0lMjBpbnRlcmlvciUyMGxpZ2h0JTIwY29uY3JldGV8ZW58MXx8fHwxNzcxNDc5NTg5fDA&ixlib=rb-4.1.0&q=80&w=1080" },
];

export default function BookmarkPage() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<"sessions" | "places">("sessions");
    const [selectedPlaces, setSelectedPlaces] = useState<number[]>([]);

    const togglePlaceSelection = (id: number) => {
        if (selectedPlaces.includes(id)) {
            setSelectedPlaces((prev) => prev.filter((placeId) => placeId !== id));
        } else {
            if (selectedPlaces.length < 5) {
                setSelectedPlaces((prev) => [...prev, id]);
            }
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
                    <AnimatePresence mode="wait">
                        {activeTab === "sessions" ? (
                            <motion.div key="sessions" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-3">
                                {MOCK_SESSIONS.map((session) => (
                                    <div key={session.id} className="group bg-white border border-gray-200 rounded-lg p-5 hover:border-black transition-all duration-200 flex items-center justify-between shadow-sm hover:shadow-md cursor-pointer">
                                        <div className="flex items-start gap-4">
                                            <div className="w-10 h-10 rounded-md bg-gray-50 border border-gray-100 flex items-center justify-center text-gray-900 group-hover:bg-black group-hover:text-white transition-colors">
                                                <MessageSquare size={16} strokeWidth={1.5} />
                                            </div>
                                            <div>
                                                <h3 className="font-bold text-sm text-gray-900 mb-0.5">{session.title}</h3>
                                                <p className="text-xs text-gray-500 mb-2 font-light">{session.preview}</p>
                                                <span className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">{session.date}</span>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => router.push("/chatbot")}
                                            className="opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all duration-200 text-black p-2 hover:bg-gray-100 rounded-md"
                                        >
                                            <ArrowRight size={16} />
                                        </button>
                                    </div>
                                ))}
                            </motion.div>
                        ) : (
                            <motion.div key="places" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {MOCK_PLACES.map((place) => {
                                    const isSelected = selectedPlaces.includes(place.id);
                                    return (
                                        <div
                                            key={place.id}
                                            onClick={() => togglePlaceSelection(place.id)}
                                            className={`group relative h-60 rounded-lg overflow-hidden cursor-pointer border-2 transition-all duration-200 ${isSelected ? "border-black shadow-lg" : "border-transparent"}`}
                                        >
                                            <img src={place.image} alt={place.name} className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" />
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
                                                <h3 className="text-white font-serif font-light text-xl mb-1 leading-none italic">{place.name}</h3>
                                                <p className="text-white/60 text-[10px] font-bold uppercase tracking-widest flex items-center gap-1">
                                                    <MapPin size={10} /> {place.location}
                                                </p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </motion.div>
                        )}
                    </AnimatePresence>
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
                                onClick={() => router.push("/chatbot")}
                                className="w-full bg-black text-white px-6 py-4 rounded-lg shadow-2xl hover:bg-gray-900 font-bold text-xs uppercase tracking-widest flex items-center justify-between group transition-all"
                            >
                                <div className="flex items-center gap-3">
                                    <span className="bg-white text-black text-[10px] font-extrabold w-5 h-5 flex items-center justify-center rounded-sm">{selectedPlaces.length}</span>
                                    <span>Plan Trip with Selection</span>
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
