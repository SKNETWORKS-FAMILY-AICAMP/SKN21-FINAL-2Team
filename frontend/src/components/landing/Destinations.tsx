"use client";

import { motion, AnimatePresence } from "framer-motion";
import { MapPin, Search, CalendarPlus } from "lucide-react";
import { useState, useEffect } from "react";
import { cn } from "../../../utils";
import { useRouter } from "next/navigation";
import { TripContextModal, type TripContext } from "@/components/chat/TripContextModal";
import { createRoom } from "@/services/api";

const categories = [
    { id: "hot-places", label: "Hot Places" },
    { id: "tourist-spot", label: "Tourist Spot" },
    { id: "foods", label: "Foods" },
];

// ✅ tourist-spot, foods 탭의 임시 더미 데이터 (통합 필드명 사용)
// 주의: 나중에 각 탭에 API가 연결되면 이 데이터는 삭제합니다.
const staticDestinations: Record<string, Destination[]> = {
    "tourist-spot": [
        { id: 101, name: "Gyeongbokgung Palace", image: "https://images.unsplash.com/photo-1604640213-0251ead81922?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", address: "Sajik-ro, Jongno-gu" },
        { id: 102, name: "N Seoul Tower", image: "https://images.unsplash.com/photo-1614935151651-0bea6508db6b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", address: "Namsan-gongwon-gil, Yongsan-gu" },
        { id: 103, name: "Bukchon Hanok Village", image: "https://images.unsplash.com/photo-1707925679578-2a2d1a1b3fcd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", address: "Gahoe-dong, Jongno-gu" },
    ],
    foods: [
        { id: 201, name: "Gwangjang Market", image: "https://images.unsplash.com/photo-1583394293214-cce78e594a77?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", address: "Jongno-gu, Seoul" },
        { id: 202, name: "Myeongdong Street Food", image: "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", address: "Myeongdong, Jung-gu" },
        { id: 203, name: "Tongin Market", image: "https://images.unsplash.com/photo-1504674900247-0877df9cc836?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080", address: "Jahamun-ro, Jongno-gu" },
    ],
};

// ✅ 세 API의 다른 필드명을 하나로 통합한 타입 설계도
// fetch 시점에 각 API 응답을 이 타입으로 '변환(매핑)'하여 JSX는 이 타입만 바라봅니다.
export interface Destination {
    id: number | string;   // hot_place: id(number) | attractions·restaurants: contentid(string)
    name: string;          // 세 API 모두 동일
    image: string;         // hot_place: /api/static/ + image_path | 나머지: image URL 그대로
    address: string;       // hot_place: adress(오타) | 나머지: address 로 통일
}

export function Destinations() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState("hot-places");
    const [displayItems, setDisplayItems] = useState<Destination[]>([]);
    // // 주의: 실제 로그인 상태는 Context API나 전역 상태 관리(Zustand 등) 혹은 쿠키에서 가져와야 하지만, 
    // 임시로 localStorage를 확인하는 방식을 사용합니다. (구글 로그인 구현 방식에 맞게 나중에 수정 필요)
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    // 트립 컨텍스트 모달 상태
    const [showTripModal, setShowTripModal] = useState(false);
    const [pendingPlace, setPendingPlace] = useState<Destination | null>(null); // 모달 확인 후 이동할 장소
    const [isTripLoading, setIsTripLoading] = useState(false);

    useEffect(() => {
        // 컴포넌트 마운트 시 로그인(토큰) 여부를 확인합니다.
        const token = localStorage.getItem("access_token"); // 또는 구글 OAuth 관련 저장값
        setIsLoggedIn(!!token);
    }, []);

    // Plan Trip 버튼 클릭 핸들러
    const handlePlanTripClick = (place: Destination, e?: React.MouseEvent) => {
        if (e) e.stopPropagation();

        if (!isLoggedIn) {
            // 주의: 로그인 후 챗봇 연결을 위해 선택한 장소를 localStorage에 임시 저장
            // 로그인 완료 후 login/page.tsx에서 이 값을 읽어 TripContextModal을 띄웁니다
            localStorage.setItem("pendingDestination", JSON.stringify(place));
            router.push("/signup");
        } else {
            // 주의: 장소를 pendingPlace에 저장하고 모달을 먼저 표시
            setPendingPlace(place);
            setShowTripModal(true);
        }
    };

    // 모달 확인 후 실행: 방 생성 + 컨텍스트 저장 + 이동
    const handleModalConfirm = async (context: TripContext) => {
        // 주의: 모달을 즉시 닫지 않고 로딩 스피너 표시
        setIsTripLoading(true);
        try {
            const newRoom = await createRoom("새로운 여행 계획");
            // 주의: autostart는 triver:selected-places:${roomId} 키를 읽습니다 (bookmark와 동일한 방식)
            // selectedForChat(범용 키)이 아닌 방별 키로 저장해야 챗봇에서 장소 정보가 출력됩니다
            if (pendingPlace) {
                localStorage.setItem(
                    `triver:selected-places:${newRoom.id}`,
                    JSON.stringify([{
                        name: pendingPlace.name,
                        adress: pendingPlace.address || (pendingPlace as any).adress, // API 응답에 따라 필드명이 다를 수 있음
                        place_id: typeof pendingPlace.id === "number" ? pendingPlace.id : 0,
                    }])
                );
            }
            if ((context.travelDuration || "").trim()) {
                localStorage.setItem(
                    `triver:trip-context:${newRoom.id}`,
                    JSON.stringify(context)
                );
            }
            router.push(`/chatbot?roomId=${newRoom.id}`);
        } catch (e) {
            console.error("Failed to create room from Destinations", e);
            setIsTripLoading(false);
            setShowTripModal(false);
            // 에러 시 방 ID 없이 이동 → 장소 데이터는 포기하고 기본 챗봇 화면으로
            // (방 생성 자체가 실패했으므로 roomId 기반 키 저장 불가)
            router.push("/chatbot");
        }
    };

    // 배열을 랜덤하게 섞어주는 함수 (Fisher-Yates Shuffle)
    const shuffleArray = <T,>(array: T[]): T[] => {
        const newArr = [...array];
        for (let i = newArr.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [newArr[i], newArr[j]] = [newArr[j], newArr[i]];
        }
        return newArr;
    };

    // ✅ 탭이 바뀔 때마다 실행: 각 탭의 API 호출 후 통합 Destination 타입으로 매핑
    useEffect(() => {
        if (activeTab === "hot-places") {
            // 🌐 /api/hot-places → { id, name, adress, image_path } 반환
            const fetch_ = async () => {
                try {
                    const res = await fetch("/api/hot-places?limit=3");
                    if (!res.ok) throw new Error("Hot Places fetch 실패");
                    type HotPlaceApiItem = {
                        id: number;
                        name: string;
                        adress?: string | null;
                        image_path?: string | null;
                    };
                    const raw: HotPlaceApiItem[] = await res.json();
                    // 주의: hot_place API는 adress(오타), image_path(상대경로)를 사용하므로 변환
                    const mapped: Destination[] = raw.map((p) => ({
                        id: p.id,
                        name: p.name,
                        address: p.adress || "",
                        image: p.image_path ? `/api/static/${p.image_path}` : "",
                    }));
                    setDisplayItems(mapped);
                } catch (error) {
                    console.error("[hot-places] API 호출 에러:", error);
                    setDisplayItems([]);
                }
            };
            fetch_();

        } else if (activeTab === "tourist-spot") {
            // 🌐 /api/attractions → { contentid, name, address, image } 반환
            const fetch_ = async () => {
                try {
                    const res = await fetch("/api/attractions?limit=3");
                    if (!res.ok) throw new Error("Attractions fetch 실패");
                    type CategoryApiItem = {
                        contentid: string;
                        name: string;
                        address?: string | null;
                        image?: string | null;
                    };
                    const raw: CategoryApiItem[] = await res.json();
                    // 주의: attractions API는 contentid(string), address, image(외부URL) 사용
                    const mapped: Destination[] = raw.map((p) => ({
                        id: p.contentid,
                        name: p.name,
                        address: p.address || "",
                        image: p.image || "",
                    }));
                    setDisplayItems(mapped);
                } catch (error) {
                    console.error("[tourist-spot] API 호출 에러:", error);
                    // 주의: API 에러 시 더미 데이터로 폴백
                    setDisplayItems(shuffleArray(staticDestinations["tourist-spot"]));
                }
            };
            fetch_();

        } else if (activeTab === "foods") {
            // 🌐 /api/restaurants → { contentid, name, address, image } 반환
            const fetch_ = async () => {
                try {
                    const res = await fetch("/api/restaurants?limit=3");
                    if (!res.ok) throw new Error("Restaurants fetch 실패");
                    type CategoryApiItem = {
                        contentid: string;
                        name: string;
                        address?: string | null;
                        image?: string | null;
                    };
                    const raw: CategoryApiItem[] = await res.json();
                    // restaurants API도 attractions과 동일한 필드 구조
                    const mapped: Destination[] = raw.map((p) => ({
                        id: p.contentid,
                        name: p.name,
                        address: p.address || "",
                        image: p.image || "",
                    }));
                    setDisplayItems(mapped);
                } catch (error) {
                    console.error("[foods] API 호출 에러:", error);
                    // 주의: API 에러 시 더미 데이터로 폴백
                    setDisplayItems(shuffleArray(staticDestinations["foods"]));
                }
            };
            fetch_();
        }
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

                    <div className="min-h-[400px]">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={activeTab}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                transition={{ duration: 0.4 }}
                                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
                            >
                                {displayItems.map((place) => (
                                    <div key={place.id} className="group bg-white rounded-xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col">
                                        <div className="relative aspect-[16/9] overflow-hidden bg-gray-100">
                                            {/* 주의: image가 빈 문자열("")이면 브라우저 에러 발생 → 있을 때만 img 렌더링 */}
                                            {place.image ? (
                                                <img
                                                    src={place.image}
                                                    alt={place.name}
                                                    className="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-700 ease-in-out"
                                                />
                                            ) : (
                                                // 이미지 없을 때: 탭별 픽토그램 placeholder
                                                <div className="w-full h-full flex flex-col items-center justify-center gap-3 bg-gray-50">
                                                    {activeTab === "tourist-spot" ? (
                                                        // 🗼 남산타워 픽토그램
                                                        <svg width="80" height="100" viewBox="0 0 80 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                            {/* 안테나 */}
                                                            <rect x="38" y="0" width="4" height="18" rx="2" fill="#CBD5E1" />
                                                            {/* 전망대 디스크 */}
                                                            <ellipse cx="40" cy="26" rx="18" ry="7" fill="#94A3B8" />
                                                            <rect x="36" y="18" width="8" height="10" fill="#94A3B8" />
                                                            {/* 타워 몸통 (위) */}
                                                            <polygon points="36,28 44,28 48,60 32,60" fill="#CBD5E1" />
                                                            {/* 타워 받침 */}
                                                            <rect x="28" y="60" width="24" height="8" rx="2" fill="#94A3B8" />
                                                            {/* 다리 왼쪽 */}
                                                            <polygon points="28,68 34,68 30,92 24,92" fill="#CBD5E1" />
                                                            {/* 다리 오른쪽 */}
                                                            <polygon points="46,68 52,68 56,92 50,92" fill="#CBD5E1" />
                                                            {/* 받침대 */}
                                                            <rect x="20" y="92" width="40" height="5" rx="2.5" fill="#94A3B8" />
                                                        </svg>
                                                    ) : activeTab === "foods" ? (
                                                        // 🍲 비빔밥 픽토그램
                                                        <svg width="100" height="90" viewBox="0 0 100 90" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                            {/* 그릇 테두리 */}
                                                            <ellipse cx="50" cy="38" rx="42" ry="12" fill="#94A3B8" />
                                                            {/* 그릇 몸통 */}
                                                            <path d="M8 38 Q8 78 50 78 Q92 78 92 38 Z" fill="#CBD5E1" />
                                                            {/* 밥 (흰색) */}
                                                            <ellipse cx="50" cy="36" rx="36" ry="9" fill="#F8FAFC" />
                                                            {/* 나물 - 초록 */}
                                                            <ellipse cx="34" cy="32" rx="10" ry="5" fill="#86EFAC" transform="rotate(-20 34 32)" />
                                                            {/* 당근 - 주황 */}
                                                            <ellipse cx="62" cy="31" rx="10" ry="5" fill="#FCA5A5" transform="rotate(15 62 31)" />
                                                            {/* 고추장 - 빨강 */}
                                                            <ellipse cx="50" cy="30" rx="8" ry="5" fill="#F87171" />
                                                            {/* 계란 노른자 */}
                                                            <circle cx="50" cy="29" r="5" fill="#FDE68A" />
                                                            {/* 그릇 하단 굽 */}
                                                            <ellipse cx="50" cy="78" rx="20" ry="5" fill="#94A3B8" />
                                                            <rect x="30" y="78" width="40" height="6" rx="3" fill="#94A3B8" />
                                                        </svg>
                                                    ) : (
                                                        // 기본 (혹시 다른 탭 추가 시)
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

            {/* TripContextModal: Plan Trip 시 여행 일정 + 인원 수집, fixed 포지션으로 전체 화면 덮음 */}
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
        </>
    );
}
