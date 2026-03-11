"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Star, Quote, ChevronLeft, ChevronRight } from "lucide-react";

const reviews = [
    {
        id: 1, name: "Jimin Park", role: "Digital Nomad", location: "Busan, South Korea",
        image: "https://images.unsplash.com/photo-1624091844772-554661d10173?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjB3b21hbiUyMHBvcnRyYWl0JTIwcHJvZmVzc2lvbmFsJTIwbWluaW1hbHxlbnwxfHx8fDE3NzE0ODI4ODd8MA&ixlib=rb-4.1.0&q=80&w=1080",
        rating: 5, text: "Triver completely changed how I explore my own country. It found hidden gems in Seongsu-dong that even locals don't know about.",
    },
    {
        id: 2, name: "Alex Kim", role: "Photography Enthusiast", location: "Seoul, South Korea",
        image: "https://images.unsplash.com/photo-1661854236305-b02cef4aa0af?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjBtYW4lMjBwb3J0cmFpdCUyMHN0eWxpc2glMjBtaW5pbWFsfGVufDF8fHx8MTc3MTQ4Mjg4N3ww&ixlib=rb-4.1.0&q=80&w=1080",
        rating: 5, text: "As a photographer, I'm always chasing the perfect light and aesthetic. Triver's 'Moments' feature is a game-changer.",
    },
    {
        id: 3, name: "Sarah Jenkins", role: "Food Blogger", location: "New York, USA",
        image: "https://images.unsplash.com/photo-1628544220588-4d364916a3c1?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx3b21hbiUyMHRyYXZlbGVyJTIwcG9ydHJhaXQlMjBtaW5pbWFsfGVufDF8fHx8MTc3MTQ4Mjg4N3ww&ixlib=rb-4.1.0&q=80&w=1080",
        rating: 5, text: "Planning a foodie trip to Seoul was overwhelming until I found Triver. It built a logical route connecting the best street food stalls.",
    },
    {
        id: 4, name: "Lucas Müller", role: "Solo Backpacker", location: "Berlin, Germany",
        image: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtYW4lMjBwb3J0cmFpdCUyMG1pbmltYWwlMjBuYXR1cmFsfGVufDF8fHx8MTc3MTQ4Mjg4N3ww&ixlib=rb-4.1.0&q=80&w=1080",
        rating: 5, text: "I backpacked through Korea for three weeks using Triver as my guide. The AI suggested routes I would have never thought of on my own.",
    },
    {
        id: 5, name: "Yuna Choi", role: "Travel Influencer", location: "Jeju, South Korea",
        image: "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx3b21hbiUyMHBvcnRyYWl0JTIwYXNpYW4lMjBuYXR1cmFsfGVufDF8fHx8MTc3MTQ4Mjg4N3ww&ixlib=rb-4.1.0&q=80&w=1080",
<<<<<<< HEAD
        rating: 5, text: "Triver's bookmark and moments features help me organize content ideas effortlessly. My followers love the unique spots I discover!",
=======
        rating: 5, text: "Triver's bookmark and Moments features help me organize content ideas effortlessly. My followers love the unique spots I discover!",
>>>>>>> codex/refact/front
    },
    {
        id: 6, name: "Daniel Park", role: "Business Traveler", location: "Toronto, Canada",
        image: "https://images.unsplash.com/photo-1560250097-0b93528c311a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtYW4lMjBwb3J0cmFpdCUyMHByb2Zlc3Npb25hbCUyMHN1aXR8ZW58MXx8fHwxNzcxNDgyODg3fDA&ixlib=rb-4.1.0&q=80&w=1080",
        rating: 5, text: "Even on tight business trips, Triver finds me the best local experiences. It maximizes every free hour I have between meetings.",
    },
];

export function ReviewSection() {
    const [currentIndex, setCurrentIndex] = useState(0);
    // 슬라이드 방향을 추적해 애니메이션 방향을 결정 (1: 앞으로, -1: 뒤로)
    const [direction, setDirection] = useState(1);

    // 2개씩 보여주므로 step=2, 전체 페이지 수 = ceil(reviews.length / 2)
    const totalPages = Math.ceil(reviews.length / 2);

    const goPrev = () => {
        // 항상 -1(왼쪽)로 고정 → 첫→마지막 wrap 때도 왼쪽으로 슬라이드
        setDirection(-1);
        setCurrentIndex((prev) => (prev - 1 + totalPages) % totalPages);
    };

    const goNext = () => {
        // 항상 1(오른쪽)로 고정 → 마지막→첫 wrap 때도 오른쪽으로 슬라이드
        setDirection(1);
        setCurrentIndex((prev) => (prev + 1) % totalPages);
    };

    // 15초마다 자동으로 다음 페이지로 넘김. currentIndex가 바뀔 때마다 타이머가 초기화되어
    // 수동 클릭 후에도 15초 뒤부터 다시 자동 전환이 시작됨
    useEffect(() => {
        const timer = setInterval(() => {
            setDirection(1);
            setCurrentIndex((prev) => (prev + 1) % totalPages);
        }, 15000);
        return () => clearInterval(timer); // 언마운트 또는 인덱스 변경 시 타이머 정리
    }, [currentIndex, totalPages]);

    // 현재 페이지에 해당하는 리뷰 2개를 슬라이스
    const visibleReviews = reviews.slice(currentIndex * 2, currentIndex * 2 + 2);

    // AnimatePresence의 mode="wait": 이전 카드가 사라진 뒤 새 카드가 등장 → 겹침 방지
    const variants = {
        enter: (dir: number) => ({ opacity: 0, x: dir > 0 ? 80 : -80 }),
        center: { opacity: 1, x: 0 },
        exit: (dir: number) => ({ opacity: 0, x: dir > 0 ? -80 : 80 }),
    };

    // [Fix] scroll-mt-24: 네비게이션 앵커 클릭 시 fixed Header(64px) 높이 보정
    return (
        // [Fix] min-h-[calc(100vh-64px)] + flex justify-center: Header(64px) 제외 뷰포트 채움 + 세로 중앙
        <section id="reviews" className="py-24 bg-gray-50 overflow-hidden min-h-[calc(100vh-64px)] flex flex-col justify-center">
            {/* [Fix] max-w-7xl → xl:max-w-[90%]: 큰 화면에서 콘텐츠가 화면 너비에 맞게 유동 확장 */}
            <div className="max-w-7xl xl:max-w-[90%] mx-auto px-6 lg:px-8">
                <div className="text-center mb-16">
                    <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}>
                        <h2 className="text-4xl md:text-6xl font-black tracking-tight text-black mb-6 uppercase">Community Voices</h2>
                        <p className="text-gray-500 font-light max-w-xl mx-auto">Hear from the explorers who have redefined their travel experiences with Triver.</p>
                    </motion.div>
                </div>

                {/* 캐러셀 영역 */}
                <div className="relative flex items-center justify-center gap-4">
                    {/* 왼쪽 화살표 - 배경 없이 꺽쇄만 */}
                    <button
                        onClick={goPrev}
                        className="flex-shrink-0 p-2 text-gray-300 hover:text-gray-500 transition-colors duration-200"
                        aria-label="Previous review"
                    >
                        <ChevronLeft size={28} strokeWidth={1.5} />
                    </button>

                    {/* 카드 슬라이드 - 2개 나란히 */}
                    {/* [Fix] max-w-4xl → xl:max-w-[75%]: 캐러셀도 넓은 화면에서 유동 확장 */}
                    <div className="relative w-full max-w-4xl xl:max-w-[75%] overflow-hidden">
                        <AnimatePresence mode="wait" custom={direction}>
                            <motion.div
                                key={currentIndex}
                                custom={direction}
                                variants={variants}
                                initial="enter"
                                animate="center"
                                exit="exit"
                                transition={{ duration: 0.35, ease: "easeInOut" }}
                                className="grid grid-cols-1 md:grid-cols-2 gap-6"
                            >
                                {visibleReviews.map((rev) => (
                                    <div
                                        key={rev.id}
                                        className="bg-white p-8 rounded-[32px] shadow-sm relative group border border-gray-100/50"
                                    >
                                        <div className="absolute top-8 right-8 text-gray-100 group-hover:text-black/5 transition-colors duration-300">
                                            <Quote size={36} fill="currentColor" strokeWidth={0} />
                                        </div>
                                        <div className="flex gap-1 mb-5 text-black">
                                            {[...Array(rev.rating)].map((_, i) => (
                                                <Star key={i} size={13} fill="currentColor" strokeWidth={0} />
                                            ))}
                                        </div>
                                        <p className="text-gray-600 text-sm leading-relaxed mb-8 font-light italic">&quot;{rev.text}&quot;</p>
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 rounded-full overflow-hidden ring-2 ring-gray-50 flex-shrink-0">
                                                <img src={rev.image} alt={rev.name} className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500" />
                                            </div>
                                            <div>
                                                <h4 className="font-bold text-sm text-black">{rev.name}</h4>
                                                <div className="flex flex-col text-[10px] text-gray-400 font-medium uppercase tracking-wide">
                                                    <span>{rev.role}</span>
                                                    <span className="text-gray-300">{rev.location}</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </motion.div>
                        </AnimatePresence>
                    </div>

                    {/* 오른쪽 화살표 - 배경 없이 꺽쇄만 */}
                    <button
                        onClick={goNext}
                        className="flex-shrink-0 p-2 text-gray-300 hover:text-gray-500 transition-colors duration-200"
                        aria-label="Next review"
                    >
                        <ChevronRight size={28} strokeWidth={1.5} />
                    </button>
                </div>

            </div>
        </section>
    );
}
