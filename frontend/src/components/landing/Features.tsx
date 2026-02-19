"use client";

import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Calendar, MapPin, Sparkles, X, CheckCircle, Clock } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

const demoContent = {
    "Hyper personalized": {
        user: "I need a quiet place in Seoul to focus, maybe with jazz?",
        ai: "I've found a hidden gem in Seongsu-dong called 'Blue Note Shelter'. It has excellent wifi, a strict quiet policy, and plays soft jazz vinyls.",
        details: { name: "Blue Note Shelter", type: "Jazz Cafe", rating: "4.9" },
    },
    "Smart itinerary": {
        user: "I have 4 hours in Itaewon. Optimize my route.",
        ai: "Route optimized. Starting at Namsan Park (1h) → Walk down Antique Street (30m) → Late lunch at Plant (1h) → Coffee at Anthracite (30m). You save 45 minutes of walking time.",
        details: { totalTime: "3h 45m", stops: 4, saved: "45 min" },
    },
    "Integrated booking": {
        user: "Book a table for 2 at Mingles for this Friday, 7 PM.",
        ai: "Checking availability... Confirmed. I've reserved a window table for two at Mingles, Friday at 19:00.",
        details: { status: "Confirmed", time: "19:00", date: "Fri, Oct 24" },
    },
};

const features = [
    {
        title: "Hyper personalized",
        description: "Our advanced AI doesn't just list popular spots; it learns your unique travel DNA. By analyzing your preferences—from your favorite cuisine to your preferred pace of travel—it crafts a bespoke journey that feels exclusively yours.",
        icon: Sparkles,
        image: "https://images.unsplash.com/photo-1656975852164-37b8b18546f2?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxJbmR1c3RyaWFsJTIwY2FmZSUyMGludGVyaW9yJTIwY29mZmVlfGVufDF8fHx8MTc3MTQ4MTkxOXww&ixlib=rb-4.1.0&q=80&w=1080",
    },
    {
        title: "Smart itinerary",
        description: "Forget the hassle of manual scheduling. Our intelligent system optimizes your routes in real-time, accounting for traffic patterns, opening hours, and geographical proximity.",
        icon: Calendar,
        image: "https://images.unsplash.com/photo-1764344558503-0579b0b0cb73?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxVcmJhbiUyMHBhcmslMjBjaXR5JTIwcGVvcGxlJTIwcmVsYXhpbmd8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080",
    },
    {
        title: "Integrated booking",
        description: "Experience true convenience with our all-in-one booking platform. From reserving a table at a Michelin-starred restaurant to securing tickets for cultural exhibitions, everything is just a tap away.",
        icon: MapPin,
        image: "https://images.unsplash.com/photo-1707925679578-2a2d1a1b3fcd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxIYW5vayUyMHZpbGxhZ2UlMjByb29mdG9wcyUyMHRyYWRpdGlvbmFsfGVufDF8fHx8MTc3MTQ4MTkxOXww&ixlib=rb-4.1.0&q=80&w=1080",
    },
];

export function Features() {
    const [selectedFeature, setSelectedFeature] = useState<string | null>(null);

    return (
        <section id="features" className="py-24 bg-white overflow-hidden relative">
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
                <div className="text-center mb-24">
                    <h2 className="text-4xl md:text-6xl font-black tracking-tight text-black mb-6 uppercase">Travel Redefined</h2>
                    <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed">Cutting-edge technology meets the art of exploration.</p>
                </div>

                <div className="flex flex-col gap-16 lg:gap-20">
                    {features.map((feature, index) => (
                        <motion.div
                            key={feature.title}
                            initial={{ opacity: 0, y: 40 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, margin: "-100px" }}
                            transition={{ duration: 0.7, ease: "easeOut" }}
                            className={cn("flex flex-col lg:flex-row items-start gap-8 lg:gap-12", index % 2 === 1 && "lg:flex-row-reverse")}
                        >
                            <div className="w-full lg:w-1/2 relative group cursor-pointer" onClick={() => setSelectedFeature(feature.title)}>
                                <div className="relative overflow-hidden aspect-[16/9] lg:aspect-[3/2] bg-gray-100 shadow-md rounded-xl">
                                    <img src={feature.image} alt={feature.title} className="object-cover w-full h-full transition-all duration-700 ease-out opacity-90 hover:opacity-100 hover:scale-105" />
                                    <div className="absolute top-6 left-6 z-10">
                                        <h3 className="text-2xl font-bold text-white leading-none drop-shadow-md">{feature.title}</h3>
                                    </div>
                                    <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                                        <div className="bg-white/90 backdrop-blur-sm text-black px-6 py-2 rounded-full font-medium text-sm transform translate-y-4 group-hover:translate-y-0 transition-all duration-300">View Demo</div>
                                    </div>
                                </div>
                            </div>
                            <div className="w-full lg:w-1/2 flex flex-col justify-center h-full pt-4 lg:pt-0">
                                <div className="h-[1px] w-full bg-gray-200 mb-6" />
                                <p className="text-base md:text-lg text-gray-600 leading-relaxed font-light text-justify">{feature.description}</p>
                                <div className="mt-8 flex items-center justify-between">
                                    <span className="text-xs font-mono text-gray-400">0{index + 1} / 03</span>
                                    <button onClick={() => setSelectedFeature(feature.title)} className="group/btn flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-black hover:text-gray-500 transition-colors">
                                        Learn more <ArrowRight size={14} className="group-hover/btn:translate-x-1 transition-transform" />
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>

            <AnimatePresence>
                {selectedFeature && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setSelectedFeature(null)} className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
                        <motion.div initial={{ scale: 0.9, opacity: 0, y: 20 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.9, opacity: 0, y: 20 }} className="relative w-full max-w-sm md:max-w-md bg-white rounded-[40px] shadow-2xl overflow-hidden border-8 border-gray-900">
                            <div className="bg-gray-50 p-6 border-b border-gray-100 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 bg-black rounded-full flex items-center justify-center text-white font-serif italic">T</div>
                                    <div>
                                        <h4 className="font-bold text-sm text-gray-900 leading-tight">Triver AI</h4>
                                        <span className="text-[10px] text-green-500 font-medium flex items-center gap-1">
                                            <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />Online
                                        </span>
                                    </div>
                                </div>
                                <button onClick={() => setSelectedFeature(null)} className="p-2 hover:bg-gray-200 rounded-full transition-colors">
                                    <X size={18} className="text-gray-500" />
                                </button>
                            </div>
                            <div className="h-[400px] bg-white p-6 flex flex-col gap-6 overflow-y-auto">
                                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="self-end max-w-[85%]">
                                    <div className="bg-gray-900 text-white p-4 rounded-[20px] rounded-br-sm text-sm leading-relaxed shadow-md">
                                        {demoContent[selectedFeature as keyof typeof demoContent].user}
                                    </div>
                                </motion.div>
                                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8, duration: 0.5 }} className="self-start flex items-center gap-2 pl-2">
                                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></span>
                                </motion.div>
                                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.5 }} className="self-start max-w-[90%]">
                                    <div className="bg-gray-50 border border-gray-100 text-gray-800 p-4 rounded-[20px] rounded-bl-sm text-sm leading-relaxed shadow-sm">
                                        {demoContent[selectedFeature as keyof typeof demoContent].ai}
                                        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} transition={{ delay: 2.5 }} className="mt-4 bg-white rounded-xl p-3 border border-gray-200 shadow-sm">
                                            {selectedFeature === "Hyper personalized" && (
                                                <div className="flex gap-3 items-center">
                                                    <div className="font-bold text-xs">{demoContent["Hyper personalized"].details.name}</div>
                                                    <div className="text-[10px] text-gray-500">{demoContent["Hyper personalized"].details.type} • ⭐ {demoContent["Hyper personalized"].details.rating}</div>
                                                </div>
                                            )}
                                            {selectedFeature === "Smart itinerary" && (
                                                <div className="flex justify-between items-center text-xs">
                                                    <div className="flex flex-col gap-1">
                                                        <span className="font-bold text-gray-900">Optimal Route</span>
                                                        <span className="text-gray-500 flex items-center gap-1"><Clock size={10} /> {demoContent["Smart itinerary"].details.totalTime}</span>
                                                    </div>
                                                    <div className="bg-green-100 text-green-700 px-2 py-1 rounded-md font-bold">Saved {demoContent["Smart itinerary"].details.saved}</div>
                                                </div>
                                            )}
                                            {selectedFeature === "Integrated booking" && (
                                                <div className="text-center">
                                                    <div className="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center mx-auto mb-2"><CheckCircle size={16} /></div>
                                                    <div className="font-bold text-sm text-gray-900">Confirmed</div>
                                                    <div className="text-[10px] text-gray-500 mt-1">{demoContent["Integrated booking"].details.date} • {demoContent["Integrated booking"].details.time}</div>
                                                </div>
                                            )}
                                        </motion.div>
                                    </div>
                                </motion.div>
                            </div>
                            <div className="p-4 bg-white border-t border-gray-100">
                                <div className="w-full h-10 bg-gray-50 rounded-full px-4 flex items-center text-gray-400 text-xs">Type a message...</div>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </section>
    );
}
