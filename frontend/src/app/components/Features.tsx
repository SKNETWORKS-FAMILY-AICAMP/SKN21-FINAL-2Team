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
        // Header.tsx의 scrollToSection에서 정지 위치를 제어하므로, 여기서는 디자인 여백(pt, pb)만 관리합니다.
        <section id="features" className="pt-12 pb-20 lg:pt-16 lg:pb-24 bg-gradient-to-b from-gray-50 to-white overflow-hidden relative">
            {/* 은은한 배경 장식 요소 추가 (밋밋함 해소) */}
            <div className="absolute top-0 left-1/2 -ml-[20rem] w-[40rem] h-[40rem] bg-indigo-50/40 rounded-full blur-3xl pointer-events-none opacity-50"></div>

            <div className="max-w-7xl xl:max-w-[90%] mx-auto px-6 lg:px-8 flex flex-col items-center relative z-10">

                {/* 1단 (상단): 헤더 영역 */}
                <div className="text-center mb-12">
                    <h2 className="text-4xl md:text-5xl font-black tracking-tight text-gray-900 mb-4 uppercase">{t("features.heading")}</h2>
                    <p className="text-base md:text-lg text-gray-500 max-w-2xl mx-auto leading-relaxed">{t("features.subheading")}</p>
                </div>

                {/* 2단: 이미지(좌) + 네비게이션 & 설명(우) */}
                <div className="w-full max-w-6xl xl:max-w-none flex flex-col lg:flex-row items-center lg:items-start justify-between gap-8 lg:gap-12">

                    {/* 이미지 영역 (좌측) — 이미지 크기를 다시 충분히 시원하게 키우되, 겹치지 않게 모션 폭을 줄임 */}
                    <div className="w-full lg:w-[55%] shrink-0 relative perspective-[1000px] flex justify-center lg:justify-end">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={activeIndex}
                                initial={{ opacity: 0, x: -8, rotateY: 2 }}
                                animate={{ opacity: 1, x: 0, rotateY: 0 }}
                                exit={{ opacity: 0, x: 8, rotateY: -2 }}
                                transition={{ type: "spring", stiffness: 100, damping: 20 }}
                                className="w-full max-w-3xl lg:max-w-[100%] aspect-[16/10] bg-white rounded-[2rem] shadow-[0_30px_60px_-15px_rgba(0,0,0,0.15)] overflow-hidden border border-gray-200/60 hover:shadow-[0_40px_80px_-20px_rgba(0,0,0,0.15)] transition-shadow duration-700 relative"
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

                    {/* 텍스트 및 네비게이션 영역 (우측) - 이미지와의 간격(gap) 확보 */}
                    <div className="w-full lg:w-[40%] flex flex-col items-start pt-4">

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
                                            "flex items-start gap-4 pb-5 border-b-2 transition-all duration-300 w-full text-left group hover:opacity-100 active:scale-[0.99]",
                                            isActive
                                                ? "border-black text-black opacity-100"
                                                : "border-transparent text-gray-400 opacity-60 hover:text-gray-800 hover:border-gray-300"
                                        )}
                                    >
                                        <div className={cn(
                                            "p-2.5 rounded-full transition-colors duration-300 mt-0.5",
                                            isActive
                                                ? "bg-gray-900 text-white"
                                                : "bg-gray-100/50 text-gray-400 group-hover:bg-gray-100 group-hover:text-gray-600"
                                        )}>
                                            <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
                                        </div>
                                        <div className="flex flex-col pt-1">
                                            <span className="font-bold text-lg leading-tight uppercase tracking-wider">
                                                {feature.shortTitle}
                                            </span>
                                            {/* 활성화된 탭의 경우 설명이 함께 펼쳐짐 (아코디언 형태) */}
                                            <AnimatePresence>
                                                {isActive && (
                                                    <motion.div
                                                        initial={{ opacity: 0, height: 0, y: -10, marginTop: 0 }}
                                                        animate={{ opacity: 1, height: "auto", y: 0, marginTop: 12 }}
                                                        exit={{ opacity: 0, height: 0, y: -10, marginTop: 0 }}
                                                        transition={{ type: "spring", stiffness: 200, damping: 25 }}
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
