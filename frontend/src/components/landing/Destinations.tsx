"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Star, MapPin, Search, CalendarPlus } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

const categories = [
    { id: "hot-places", label: "Hot Places" },
    { id: "historical", label: "Historical" },
    { id: "nature", label: "Nature" },
    { id: "activity", label: "Activity" },
];

const destinations = {
    "hot-places": [
        { id: 1, name: "Seongsu-dong Cafe Street", image: "https://images.unsplash.com/photo-1735491428084-853fb91c09e7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxTZW91bCUyMGNhZmUlMjBhZXN0aGV0aWMlMjBtaW5pbWFsaXN0fGVufDF8fHx8MTc3MTQ4MTgyNnww&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.8, address: "Seongsu-dong, Seongdong-gu", distance: "2.5 km" },
        { id: 2, name: "Yeonnam-dong Park", image: "https://images.unsplash.com/photo-1692103675608-6e635afa077b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxLb3JlYW4lMjBzdHJlZXQlMjBmb29kJTIwdHRlb2tib2traSUyMGFlc3RoZXRpY3xlbnwxfHx8fDE3NzE0ODE4MjZ8MA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.7, address: "Yeonnam-dong, Mapo-gu", distance: "4.2 km" },
        { id: 3, name: "Starfield Library", image: "https://images.unsplash.com/photo-1659243013574-3b0ffb781fe4?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxTdGFyZmllbGQlMjBMaWJyYXJ5JTIwQ29leCUyME1hbGwlMjBTZW91bHxlbnwxfHx8fDE3NzE0ODE5MDh8MA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.9, address: "Samseong-dong, Gangnam-gu", distance: "8.1 km" },
    ],
    historical: [
        { id: 4, name: "Gwanghwamun Gate", image: "https://images.unsplash.com/photo-1591203265333-2248cd9470c6?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxHd2FuZ2h3YW11biUyMGdhdGUlMjBTZW91bCUyMGhpc3RvcmljYWx8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.9, address: "Sajik-ro, Jongno-gu", distance: "1.2 km" },
        { id: 5, name: "Bukchon Hanok Village", image: "https://images.unsplash.com/photo-1707925679578-2a2d1a1b3fcd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxIYW5vayUyMHZpbGxhZ2UlMjByb29mdG9wcyUyMHRyYWRpdGlvbmFsfGVufDF8fHx8MTc3MTQ4MTkxOXww&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.6, address: "Gahoe-dong, Jongno-gu", distance: "1.5 km" },
        { id: 6, name: "Changdeokgung Secret Garden", image: "https://images.unsplash.com/photo-1665688523044-32afbd7a9d28?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxDaGFuZ2Rlb2tndW5nJTIwUGFsYWNlJTIwU2VjcmV0JTIwR2FyZGVufGVufDF8fHx8MTc3MTQ4MTkwOHww&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.8, address: "Yulgok-ro, Jongno-gu", distance: "2.0 km" },
    ],
    nature: [
        { id: 7, name: "Hangang Park Picnic", image: "https://images.unsplash.com/photo-1720250050813-78406c8d1350?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxIYW5nYW5nJTIwcml2ZXIlMjBwaWNuaWMlMjBzdW5zZXR8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.8, address: "Yeouido-dong, Yeongdeungpo-gu", distance: "5.5 km" },
        { id: 8, name: "Namsan Seoul Tower", image: "https://images.unsplash.com/photo-1760788935785-2f50c6092980?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxOYW1zYW4lMjBTZW91bCUyMFRvd2VyJTIwc2NlbmljJTIwdmlld3xlbnwxfHx8fDE3NzE0ODE5MDh8MA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.7, address: "Namsan-gongwon-gil, Yongsan-gu", distance: "3.0 km" },
        { id: 9, name: "Seoul Forest", image: "https://images.unsplash.com/photo-1707298409328-55d0c5fa9370?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxTZW91bCUyMEZvcmVzdCUyMFBhcmslMjBkZWVyJTIwdHJlZXN8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.9, address: "Seongsu-dong, Seongdong-gu", distance: "4.0 km" },
    ],
    activity: [
        { id: 10, name: "Lotte World Adventure", image: "https://images.unsplash.com/photo-1674606067725-b6ab1e340753?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxMb3R0ZSUyMFdvcmxkJTIwVG93ZXIlMjBTZW91bCUyMHRoZW1lJTIwcGFya3xlbnwxfHx8fDE3NzE0ODE5MDh8MA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.6, address: "Jamsil-dong, Songpa-gu", distance: "9.5 km" },
        { id: 11, name: "COEX Aquarium", image: "https://images.unsplash.com/photo-1677607219759-5ee7279f2774?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxBcXVhcml1bSUyMHR1bm5lbCUyMGZpc2glMjBibHVlfGVufDF8fHx8MTc3MTQ4MTkxOXww&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.5, address: "Samseong-dong, Gangnam-gu", distance: "8.2 km" },
        { id: 12, name: "Hongdae Nightlife", image: "https://images.unsplash.com/photo-1676741556435-709eaa1f872f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxOZW9uJTIwc2lnbiUyMG5pZ2h0JTIwc3RyZWV0JTIwU2VvdWwlMjBsaXZlbHl8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.7, address: "Hongdae, Mapo-gu", distance: "4.5 km" },
    ],
};

export function Destinations() {
    const [activeTab, setActiveTab] = useState("hot-places");

    return (
        <section id="destinations" className="py-24 bg-gray-50/30">
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
                <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-6">
                    <div>
                        <h2 className="text-4xl md:text-5xl font-black tracking-tight text-gray-900 mb-4 uppercase">Explore Seoul</h2>
                        <p className="text-gray-500 text-lg max-w-xl font-light">From historic palaces to neon-lit streets, find your perfect spot.</p>
                    </div>
                    <div className="flex flex-wrap gap-2 p-1.5 bg-gray-100/50 rounded-lg overflow-hidden backdrop-blur-sm border border-gray-200">
                        {categories.map((category) => (
                            <button
                                key={category.id}
                                onClick={() => setActiveTab(category.id)}
                                className={cn("px-5 py-2.5 rounded-md text-sm font-medium transition-all duration-300", activeTab === category.id ? "bg-black text-white shadow-sm" : "text-gray-500 hover:text-black hover:bg-gray-200/50")}
                            >
                                {category.label}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="min-h-[500px]">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={activeTab}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            transition={{ duration: 0.4 }}
                            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
                        >
                            {destinations[activeTab as keyof typeof destinations].map((place) => (
                                <div key={place.id} className="group bg-white rounded-xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col">
                                    <div className="relative aspect-[4/3] overflow-hidden">
                                        <img src={place.image} alt={place.name} className="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-700 ease-in-out" />
                                        <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-md px-3 py-1 rounded-full flex items-center gap-1 shadow-sm">
                                            <Star size={14} className="fill-black text-black" />
                                            <span className="text-xs font-bold text-gray-900">{place.rating}</span>
                                        </div>
                                    </div>
                                    <div className="p-6 flex flex-col flex-grow">
                                        <h3 className="text-xl font-bold text-gray-900 mb-2">{place.name}</h3>
                                        <div className="flex items-center gap-4 text-gray-500 text-sm mb-6 font-mono">
                                            <div className="flex items-center gap-1"><MapPin size={14} className="text-gray-400" /><span className="truncate max-w-[120px]">{place.address}</span></div>
                                            <div className="w-1 h-1 bg-gray-300 rounded-full" />
                                            <span>{place.distance}</span>
                                        </div>
                                        <div className="mt-auto flex items-center justify-between gap-3 pt-4 border-t border-gray-50">
                                            <button className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-black transition-colors px-2 py-1.5 rounded-md hover:bg-gray-100">
                                                <Search size={14} /><span>Reviews</span>
                                            </button>
                                            <button className="flex items-center gap-2 bg-black text-white px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors shadow-lg">
                                                <CalendarPlus size={16} />Plan Trip
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </motion.div>
                    </AnimatePresence>
                </div>
            </div>
        </section>
    );
}
