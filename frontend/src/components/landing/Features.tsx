"use client";

import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Calendar, MapPin, Sparkles, X, CheckCircle, Clock } from "lucide-react";
import { useState } from "react";
import { cn } from "../../../utils";

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
        shortTitle: "Personalized",
        description: "Our advanced AI doesn't just list popular spots; it learns your unique travel DNA. By analyzing your preferences—from your favorite cuisine to your preferred pace of travel—it crafts a bespoke journey that feels exclusively yours.",
        icon: Sparkles,
        image: "https://images.unsplash.com/photo-1656975852164-37b8b18546f2?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxJbmR1c3RyaWFsJTIwY2FmZSUyMGludGVyaW9yJTIwY29mZmVlfGVufDF8fHx8MTc3MTQ4MTkxOXww&ixlib=rb-4.1.0&q=80&w=1080",
        mockupImage: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=1000&auto=format&fit=crop", // Dashboard/User page mock
    },
    {
        title: "Smart itinerary",
        shortTitle: "Smart Route",
        description: "Forget the hassle of manual scheduling. Our intelligent system optimizes your routes in real-time, accounting for traffic patterns, opening hours, and geographical proximity.",
        icon: Calendar,
        image: "https://images.unsplash.com/photo-1764344558503-0579b0b0cb73?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxVcmJhbiUyMHBhcmslMjBjaXR5JTIwcGVvcGxlJTIwcmVsYXhpbmd8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080",
        mockupImage: "https://images.unsplash.com/photo-1616469829581-73993eb86b02?q=80&w=1000&auto=format&fit=crop", // Chatbot/Search mock
    },
    {
        title: "Integrated booking",
        shortTitle: "Booking",
        description: "Experience true convenience with our all-in-one booking platform. From reserving a table at a Michelin-starred restaurant to securing tickets for cultural exhibitions, everything is just a tap away.",
        icon: MapPin,
        image: "https://images.unsplash.com/photo-1707925679578-2a2d1a1b3fcd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxIYW5bokl2aWxsYWdlJTIwcm9vZnRvcHMlMjB0cmFkaXRpb25hbHxlbnwxfHx8fDE3NzE0ODE5MTl8MA&ixlib=rb-4.1.0&q=80&w=1080",
        mockupImage: "https://images.unsplash.com/photo-1506784365847-bbad939e9335?q=80&w=1000&auto=format&fit=crop", // Calendar/Schedule mock
    },
];

export function Features() {
    // 선택된 탭(카드)의 인덱스를 관리하는 상태 (기본값: 0번째 항목)
    const [activeIndex, setActiveIndex] = useState(0);
    const activeFeature = features[activeIndex];

    return (
        <section id="features" className="py-24 bg-gray-50 overflow-hidden relative">
            <div className="max-w-7xl mx-auto px-6 lg:px-8 flex flex-col items-center">

                {/* 1단 (상단): 헤더 영역 */}
                <div className="text-center mb-10">
                    <h2 className="text-4xl md:text-5xl font-black tracking-tight text-gray-900 mb-4 uppercase">Travel Redefined</h2>
                    <p className="text-base md:text-lg text-gray-500 max-w-2xl mx-auto leading-relaxed">Cutting-edge technology meets the art of exploration.</p>
                </div>

                {/* 2단: 이미지(좌) + 네비게이션 & 설명(우) 통합 영역 */}
                <div className="w-full max-w-6xl flex flex-col lg:flex-row items-center justify-between gap-12 lg:gap-16">

                    {/* 이미지 영역 (좌측) */}
                    <div className="w-full lg:w-3/5 relative perspective-[1000px]">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={activeIndex}
                                initial={{ opacity: 0, x: -30, rotateY: 5 }}
                                animate={{ opacity: 1, x: 0, rotateY: 0 }}
                                exit={{ opacity: 0, x: 30, rotateY: -5 }}
                                transition={{ duration: 0.5, ease: "easeOut" }}
                                className="w-full aspect-[4/3] sm:aspect-[16/9] lg:aspect-[4/3] bg-white rounded-3xl shadow-2xl overflow-hidden border-8 border-gray-900 relative"
                            >
                                <img
                                    src={activeFeature.mockupImage}
                                    alt={`${activeFeature.title} App interface`}
                                    className="w-full h-full object-cover"
                                />
                                <div className="absolute inset-0 shadow-[inset_0_0_50px_rgba(0,0,0,0.1)] pointer-events-none"></div>
                            </motion.div>
                        </AnimatePresence>
                    </div>

                    {/* 텍스트 및 네비게이션 영역 (우측) */}
                    <div className="w-full lg:w-2/5 flex flex-col items-start min-h-[400px]">

                        {/* 네비게이션 탭 (아이콘 + 텍스트) */}
                        <div className="flex flex-col gap-6 w-full pr-4">
                            {features.map((feature, index) => {
                                const Icon = feature.icon;
                                const isActive = index === activeIndex;
                                return (
                                    <button
                                        key={feature.title}
                                        onClick={() => setActiveIndex(index)}
                                        className={cn(
                                            "flex items-center gap-4 pb-4 border-b-2 transition-all duration-300 w-full text-left group",
                                            isActive
                                                ? "border-black text-black"
                                                : "border-gray-200 text-gray-400 hover:text-black hover:border-gray-400"
                                        )}
                                    >
                                        <div className={cn(
                                            "p-3 rounded-full transition-colors",
                                            isActive ? "bg-black text-white" : "bg-gray-100 group-hover:bg-gray-200"
                                        )}>
                                            <Icon size={24} />
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="font-bold text-lg leading-tight uppercase tracking-wider">
                                                {feature.shortTitle}
                                            </span>
                                            {/* 활성화된 탭의 경우 설명이 함께 펼쳐짐 (아코디언 형태) */}
                                            <AnimatePresence>
                                                {isActive && (
                                                    <motion.div
                                                        initial={{ opacity: 0, height: 0, marginTop: 0 }}
                                                        animate={{ opacity: 1, height: "auto", marginTop: 12 }}
                                                        exit={{ opacity: 0, height: 0, marginTop: 0 }}
                                                        transition={{ duration: 0.3 }}
                                                        className="overflow-hidden"
                                                    >
                                                        <p className="text-gray-600 leading-relaxed font-light text-base pr-4">
                                                            {feature.description}
                                                        </p>
                                                    </motion.div>
                                                )}
                                            </AnimatePresence>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>

            </div>
        </section>
    );
}
