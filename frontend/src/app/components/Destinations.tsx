"use client";

import { motion, AnimatePresence } from "framer-motion";
import { MapPin, Search, CalendarPlus } from "lucide-react";
import React, { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { TripContextModal, type TripContext } from "@/features/chat/components/TripContextModal";
import { createRoom, fetchRandomExplorePlaces, fetchCurrentUser, type UserProfile } from "@/services/api";
import { IncompleteSignupModal } from "@/app/components/IncompleteSignupModal";
import { setPendingAutoStartMeta } from "@/services/autoStart";

const categories = [
    { id: "hot-places", label: "Hot Places" },
    { id: "tourist-spot", label: "Tourist Spot" },
    { id: "foods", label: "Foods" },
];

// ✅ 세 API의 다른 필드명을 하나로 통합한 타입 설계도
export interface Destination {
    id: number | string;
    name: string;
    image: string;
    address: string;
}

// ✅ tourist-spot, foods 탭의 임시 더미 데이터 (통합 필드명 사용)
const staticDestinations: Record<string, Destination[]> = {
    "tourist-spot": [
        { id: "101", name: "Gyeongbokgung Palace", image: "https://images.unsplash.com/photo-1604640213-0251ead81922?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", address: "Sajik-ro, Jongno-gu" },
        { id: "102", name: "N Seoul Tower", image: "https://images.unsplash.com/photo-1614935151651-0bea6508db6b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", address: "Namsan-gongwon-gil, Yongsan-gu" },
        { id: "103", name: "Bukchon Hanok Village", image: "https://images.unsplash.com/photo-1707925679578-2a2d1a1b3fcd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", address: "Gahoe-dong, Jongno-gu" },
    ],
    foods: [
        { id: "201", name: "Gwangjang Market", image: "https://images.unsplash.com/photo-1583394293214-cce78e594a77?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", address: "Jongno-gu, Seoul" },
        { id: "202", name: "Myeongdong Street Food", image: "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", address: "Myeongdong, Jung-gu" },
        { id: "203", name: "Tongin Market", image: "https://images.unsplash.com/photo-1504674900247-0877df9cc836?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", address: "Jahamun-ro, Jongno-gu" },
    ],
};

// fetch 시점에 각 API 응답을 이 타입으로 '변환(매핑)'하여 JSX는 이 타입만 바라봅니다.
// hot_place: id(number) | attractions·restaurants: contentid(string)
// name: 세 API 모두 동일
// image: API 응답 이미지 URL
// address: hot_place: adress(오타) | 나머지: address 로 통일
export function Destinations() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState("hot-places");
    const [displayItems, setDisplayItems] = useState<Destination[]>([]);
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    // 트립 컨텍스트 모달 상태
    const [showTripModal, setShowTripModal] = useState(false);
    const [pendingPlace, setPendingPlace] = useState<Destination | null>(null);
    const [isTripLoading, setIsTripLoading] = useState(false);
    const [allRandomData, setAllRandomData] = useState<Record<string, Destination[]>>({});

    // 가입/설문 미완료 시 경고 모달 상태
    const [isWarningModalOpen, setIsWarningModalOpen] = useState(false);
    const [warningStep, setWarningStep] = useState<"profile" | "survey" | null>(null);

    useEffect(() => {
        const token = localStorage.getItem("access_token");
        setIsLoggedIn(!!token);
        if (token) {
            fetchCurrentUser()
                .then(user => setUserProfile(user))
                .catch(() => console.warn("Failed to fetch user profile in Destinations"));
        }
    }, []);

    const handlePlanTripClick = (place: Destination, e?: React.MouseEvent) => {
        if (e) e.stopPropagation();
        if (!isLoggedIn) {
            localStorage.setItem("pendingDestination", JSON.stringify(place));
            router.push("/signup");
        } else {
            // 주의: 로그인 후 정보나 설문 기입이 덜 끝났다면 즉시 이동하지 않고 모달 표시
            if (userProfile && !userProfile.is_join) {
                // 사용자가 챗봇 목적지로 향하려 했다는 의도를 남겨두기 위해 세팅
                localStorage.setItem("pendingDestination", JSON.stringify(place));
                setWarningStep("profile");
                setIsWarningModalOpen(true);
                return;
            }
            if (userProfile && !userProfile.is_prefer) {
                localStorage.setItem("pendingDestination", JSON.stringify(place));
                setWarningStep("survey");
                setIsWarningModalOpen(true);
                return;
            }

            // 주의: 장소를 pendingPlace에 저장하고 모달을 먼저 표시
            setPendingPlace(place);
            setShowTripModal(true);
        }
    };

    const confirmWarning = () => {
        setIsWarningModalOpen(false);
        if (warningStep === "profile") {
            router.push("/signup/profile");
        } else if (warningStep === "survey") {
            router.push("/survey");
        }
    };

    // 모달 확인 후 실행: 방 생성 + 컨텍스트 저장 + 이동
    const handleModalConfirm = async (context: TripContext) => {
        setIsTripLoading(true);
        try {
            const newRoom = await createRoom("새로운 여행 계획");
            const selectedPlaces = pendingPlace ? [{
                name: pendingPlace.name,
                adress: pendingPlace.address || (pendingPlace as Destination & { adress?: string }).adress,
                place_id: typeof pendingPlace.id === "number" ? pendingPlace.id : 0,
            }] : [];

            if ((context.travelDuration || "").trim()) {
                setPendingAutoStartMeta(newRoom.id, {
                    mode: selectedPlaces.length > 0 ? "combined" : "trip_context",
                    tripContext: context,
                    selectedPlaces,
                });
            } else if (selectedPlaces.length > 0) {
                setPendingAutoStartMeta(newRoom.id, {
                    mode: "selected_places",
                    selectedPlaces,
                });
            }
            router.push(`/chatbot?roomId=${newRoom.id}`);
        } catch (e) {
            console.error("Failed to create room from Destinations", e);
            setIsTripLoading(false);
            setShowTripModal(false);
            router.push("/chatbot");
        }
    };

    const shuffleArray = <T,>(array: T[]): T[] => {
        const newArr = [...array];
        for (let i = newArr.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [newArr[i], newArr[j]] = [newArr[j], newArr[i]];
        }
        return newArr;
    };
    const [isLoading, setIsLoading] = useState(false);

    // ✅ 탭이 바뀔 때마다 서버에서 새로운 랜덤 데이터를 가져옵니다.
    useEffect(() => {
        const fetchCurrentTabRandom = async () => {
            setIsLoading(true);
            try {
                const raw = await fetchRandomExplorePlaces("hot_places,tourist_spots,restaurants", 3);
                const mappedData: Record<string, Destination[]> = {};

                // 1. 핫플레이스 매핑
                mappedData["hot-places"] = (raw["hot_places"] || []).map(p => ({
                    id: p.contentid,
                    name: p.title,
                    address: p.address,
                    // 주의: image_url이 있을 때만 경로를 생성, 없으면 빈 문자열(placeholder용)
                    image: p.image_url && p.image_url.trim() !== ""
                        ? (p.image_url.startsWith("http") ? p.image_url : `/api/static/${p.image_url}`)
                        : ""
                }));

                // 2. 관광지 매핑
                mappedData["tourist-spot"] = (raw["tourist_spots"] || []).map(p => ({
                    id: p.contentid,
                    name: p.title,
                    address: p.address,
                    image: p.image_url || ""
                }));

                // 3. 음식점 매핑
                mappedData["foods"] = (raw["restaurants"] || []).map(p => ({
                    id: p.contentid,
                    name: p.title,
                    address: p.address,
                    image: p.image_url || ""
                }));

                // 현재 탭에 맞는 데이터로 즉시 업데이트
                if (mappedData[activeTab] && mappedData[activeTab].length > 0) {
                    setDisplayItems(mappedData[activeTab]);
                } else {
                    // 데이터가 없는 경우 더미 데이터 폴백
                    if (activeTab === "tourist-spot") {
                        setDisplayItems(shuffleArray(staticDestinations["tourist-spot"]));
                    } else if (activeTab === "foods") {
                        setDisplayItems(shuffleArray(staticDestinations["foods"]));
                    } else {
                        setDisplayItems([]);
                    }
                }
            } catch (error) {
                console.error("Failed to fetch random places on tab change:", error);
                // 에러 발생 시 더미 데이터 폴백
                if (activeTab === "tourist-spot") {
                    setDisplayItems(shuffleArray(staticDestinations["tourist-spot"]));
                } else if (activeTab === "foods") {
                    setDisplayItems(shuffleArray(staticDestinations["foods"]));
                }
            } finally {
                setIsLoading(false);
            }
        };

        fetchCurrentTabRandom();
    }, [activeTab]);

    return (
        <>
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

                    <div className="min-h-[400px] relative">
                        {isLoading && (
                            <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/50 backdrop-blur-[2px] rounded-xl">
                                <div className="flex flex-col items-center gap-2">
                                    <div className="w-8 h-8 border-4 border-black border-t-transparent rounded-full animate-spin" />
                                    <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">Refreshing...</span>
                                </div>
                            </div>
                        )}
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={activeTab + (isLoading ? "-loading" : "-ready")}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                transition={{ duration: 0.4 }}
                                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
                            >
                                {displayItems.map((place) => (
                                    <div key={place.id} className="group bg-white rounded-xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col h-full">
                                        <div className="relative w-full h-48 sm:h-56 overflow-hidden bg-gray-100 flex-shrink-0">
                                            {/* 주의: image가 존재하고 비어있지 않을 때만 img 렌더링 → object-cover로 크롭 강제 */}
                                            {place.image && place.image.trim() !== "" ? (
                                                <img
                                                    src={place.image}
                                                    alt={place.name}
                                                    className="absolute inset-0 w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-700 ease-in-out"
                                                />
                                            ) : (
                                                <div className="absolute inset-0 w-full h-full flex flex-col items-center justify-center gap-3 bg-gray-50">
                                                    {activeTab === "tourist-spot" ? (
                                                        <svg width="80" height="100" viewBox="0 0 80 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                            <rect x="38" y="0" width="4" height="18" rx="2" fill="#CBD5E1" />
                                                            <ellipse cx="40" cy="26" rx="18" ry="7" fill="#94A3B8" />
                                                            <rect x="36" y="18" width="8" height="10" fill="#94A3B8" />
                                                            <polygon points="36,28 44,28 48,60 32,60" fill="#CBD5E1" />
                                                            <rect x="28" y="60" width="24" height="8" rx="2" fill="#94A3B8" />
                                                            <polygon points="28,68 34,68 30,92 24,92" fill="#CBD5E1" />
                                                            <polygon points="46,68 52,68 56,92 50,92" fill="#CBD5E1" />
                                                            <rect x="20" y="92" width="40" height="5" rx="2.5" fill="#94A3B8" />
                                                        </svg>
                                                    ) : activeTab === "foods" ? (
                                                        <svg width="100" height="90" viewBox="0 0 100 90" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                            <ellipse cx="50" cy="38" rx="42" ry="12" fill="#94A3B8" />
                                                            <path d="M8 38 Q8 78 50 78 Q92 78 92 38 Z" fill="#CBD5E1" />
                                                            <ellipse cx="50" cy="36" rx="36" ry="9" fill="#F8FAFC" />
                                                            <ellipse cx="34" cy="32" rx="10" ry="5" fill="#86EFAC" transform="rotate(-20 34 32)" />
                                                            <ellipse cx="62" cy="31" rx="10" ry="5" fill="#FCA5A5" transform="rotate(15 62 31)" />
                                                            <ellipse cx="50" cy="30" rx="8" ry="5" fill="#F87171" />
                                                            <circle cx="50" cy="29" r="5" fill="#FDE68A" />
                                                            <ellipse cx="50" cy="78" rx="20" ry="5" fill="#94A3B8" />
                                                            <rect x="30" y="78" width="40" height="6" rx="3" fill="#94A3B8" />
                                                        </svg>
                                                    ) : (
                                                        <MapPin size={40} className="text-gray-300" />
                                                    )}
                                                    <span className="text-xs font-medium text-gray-400">No Image</span>
                                                </div>
                                            )}
                                        </div>
                                        <div className="p-4 flex flex-col flex-grow">
                                            <h3 className="text-xl font-bold text-gray-900 mb-2">{place.name}</h3>
                                            <div className="flex items-center gap-4 text-gray-500 text-sm mb-2 font-mono">
                                                <div className="flex items-center gap-1"><MapPin size={14} className="text-gray-400" /><span>{place.address}</span></div>
                                            </div>
                                            <div className="mt-auto flex items-center justify-between gap-3 pt-4 border-t border-gray-50">
                                                <button className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-black transition-colors px-2 py-1.5 rounded-md hover:bg-gray-100">
                                                    <Search size={14} /><span>Reviews</span>
                                                </button>
                                                <button
                                                    onClick={(e) => handlePlanTripClick(place, e)}
                                                    className="flex items-center gap-2 bg-black text-white px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors shadow-lg z-10 relative"
                                                >
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

            <TripContextModal
                isOpen={showTripModal}
                onConfirm={handleModalConfirm}
                loading={isTripLoading}
                onClose={() => {
                    if (!isTripLoading) {
                        setShowTripModal(false);
                        setPendingPlace(null);
                    }
                }}
            />
            {/* 미가입/미설문 경고 모달 */}
            <IncompleteSignupModal
                isOpen={isWarningModalOpen}
                missingStep={warningStep}
                onClose={() => setIsWarningModalOpen(false)}
                onConfirm={confirmWarning}
            />
        </>
    );
}
