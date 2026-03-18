"use client";

import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Calendar, MapPin, Sparkles, X, CheckCircle, Clock } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/i18n/useTranslation";

export function Features() {
    const { t } = useTranslation();

    const features = [
        {
            title: t("features.hyperPersonalized.title"),
            shortTitle: t("features.hyperPersonalized.shortTitle"),
            description: t("features.hyperPersonalized.description"),
            icon: Sparkles,
            mockupImage: "https://plus.unsplash.com/premium_photo-1663013548362-cb77800e7439?q=80&w=1170&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
        },
        {
            title: t("features.smartItinerary.title"),
            shortTitle: t("features.smartItinerary.shortTitle"),
            description: t("features.smartItinerary.description"),
            icon: Calendar,
            mockupImage: "https://images.unsplash.com/photo-1542121123-4418d14b0ec7?q=80&w=765&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
        },
        {
            title: t("features.integratedBooking.title"),
            shortTitle: t("features.integratedBooking.shortTitle"),
            description: t("features.integratedBooking.description"),
            icon: MapPin,
            mockupImage: "https://images.unsplash.com/photo-1506784365847-bbad939e9335?q=80&w=1000&auto=format&fit=crop",
        },
    ];

    // 선택된 탭(카드)의 인덱스를 관리하는 상태 (기본값: 0번째 항목)
    const [activeIndex, setActiveIndex] = useState(0);
    const activeFeature = features[activeIndex];

    return (
        // justify-center 제거 → 콘텐츠 높이 변해도 위치 재배치 안 됨
        <section id="features" className="py-16 bg-gray-50 overflow-hidden relative">
            <div className="max-w-7xl xl:max-w-[90%] mx-auto px-6 lg:px-8 flex flex-col items-center">

                {/* 1단 (상단): 헤더 영역 */}
                <div className="text-center mb-12">
                    <h2 className="text-4xl md:text-5xl font-black tracking-tight text-gray-900 mb-4 uppercase">{t("features.heading")}</h2>
                    <p className="text-base md:text-lg text-gray-500 max-w-2xl mx-auto leading-relaxed">{t("features.subheading")}</p>
                </div>

                {/* 2단: 이미지(좌) + 네비게이션 & 설명(우) */}
                <div className="w-full max-w-6xl xl:max-w-none flex flex-col lg:flex-row items-start justify-between gap-8 lg:gap-10">

                    {/* 이미지 영역 (좌측) — aspect-ratio로 비율 고정, 너비 기반이라 절대 안 변함 */}
                    <div className="w-full lg:w-3/5 shrink-0 relative perspective-[1000px]">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={activeIndex}
                                initial={{ opacity: 0, x: -30, rotateY: 5 }}
                                animate={{ opacity: 1, x: 0, rotateY: 0 }}
                                exit={{ opacity: 0, x: 30, rotateY: -5 }}
                                transition={{ duration: 0.5, ease: "easeOut" }}
                                className="w-full aspect-[16/10] bg-white rounded-3xl shadow-2xl shadow-black/70 overflow-hidden border-[1px] border-gray-300 relative"
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
                    <div className="w-full lg:w-2/5 flex flex-col items-start">

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
                                                        <p className="text-gray-600 leading-relaxed font-light text-base pr-4 whitespace-pre-line">
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
