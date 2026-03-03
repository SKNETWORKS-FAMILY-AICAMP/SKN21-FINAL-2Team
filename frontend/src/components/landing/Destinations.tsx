"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Star, MapPin, Search, CalendarPlus, X } from "lucide-react";
import { useState, useEffect } from "react";
import { cn } from "../../../utils";
import { useRouter } from "next/navigation";

const categories = [
    { id: "hot-places", label: "Hot Places" },
    { id: "historical", label: "Historical" },
    { id: "nature", label: "Nature" },
    { id: "activity", label: "Activity" },
];

// ✅ API 응답과 동일한 필드명을 사용하는 더미 데이터 (hot-places 제외 - 실제 API 연결)
// 주의: hot-places는 아래 useEffect에서 /api/hot-places 로 실시간 호출합니다.
const staticDestinations: Record<string, Destination[]> = {
    historical: [
        { id: 4, name: "Gwanghwamun Gate", image_path: "https://images.unsplash.com/photo-1591203265333-2248cd9470c6?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxHd2FuZ2h3YW11biUyMGdhdGUlMjBTZW91bCUyMGhpc3RvcmljYWx8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080", adress: "Sajik-ro, Jongno-gu" },
        { id: 5, name: "Bukchon Hanok Village", image_path: "https://images.unsplash.com/photo-1707925679578-2a2d1a1b3fcd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxIYW5vayUyMHZpbGxhZ2UlMjByb29mdG9wcyUyMHRyYWRpdGlvbmFsfGVufDF8fHx8MTc3MTQ4MTkxOXww&ixlib=rb-4.1.0&q=80&w=1080", adress: "Gahoe-dong, Jongno-gu" },
        { id: 6, name: "Changdeokgung Secret Garden", image_path: "https://images.unsplash.com/photo-1665688523044-32afbd7a9d28?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxDaGFuZ2Rlb2tndW5nJTIwUGFsYWNlJTIwU2VjcmV0JTIwR2FyZGVufGVufDF8fHx8MTc3MTQ4MTkwOHww&ixlib=rb-4.1.0&q=80&w=1080", adress: "Yulgok-ro, Jongno-gu" },
    ],
    nature: [
        { id: 7, name: "Hangang Park Picnic", image_path: "https://images.unsplash.com/photo-1720250050813-78406c8d1350?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxIYW5nYW5nJTIwcml2ZXIlMjBwaWNuaWMlMjBzdW5zZXR8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080", adress: "Yeouido-dong, Yeongdeungpo-gu" },
        { id: 8, name: "Namsan Seoul Tower", image_path: "https://images.unsplash.com/photo-1760788935785-2f50c6092980?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxOYW1zYW4lMjBTZW91bCUyMFRvd2VyJTIwc2NlbmljJTIwdmlld3xlbnwxfHx8fDE3NzE0ODE5MDh8MA&ixlib=rb-4.1.0&q=80&w=1080", adress: "Namsan-gongwon-gil, Yongsan-gu" },
        { id: 9, name: "Seoul Forest", image_path: "https://images.unsplash.com/photo-1707298409328-55d0c5fa9370?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxTZW91bCUyMEZvcmVzdCUyMFBhcmslMjBkZWVyJTIwdHJlZXN8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080", adress: "Seongsu-dong, Seongdong-gu" },
    ],
    activity: [
        { id: 10, name: "Lotte World Adventure", image_path: "https://images.unsplash.com/photo-1674606067725-b6ab1e340753?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxMb3R0ZSUyMFdvcmxkJTIwVG93ZXIlMjBTZW91bCUyMHRoZW1lJTIwcGFya3xlbnwxfHx8fDE3NzE0ODE5MDh8MA&ixlib=rb-4.1.0&q=80&w=1080", adress: "Jamsil-dong, Songpa-gu" },
        { id: 11, name: "COEX Aquarium", image_path: "https://images.unsplash.com/photo-1677607219759-5ee7279f2774?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxBcXVhcml1bSUyMHR1bm5lbCUyMGZpc2glMjBibHVlfGVufDF8fHx8MTc3MTQ4MTkxOXww&ixlib=rb-4.1.0&q=80&w=1080", adress: "Samseong-dong, Gangnam-gu" },
        { id: 12, name: "Hongdae Nightlife", image_path: "https://images.unsplash.com/photo-1676741556435-709eaa1f872f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxOZW9uJTIwc2lnbiUyMG5pZ2h0JTIwc3RyZWV0JTIwU2VvdWwlMjBsaXZlbHl8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080", adress: "Hongdae, Mapo-gu" },
    ],
};

// ✅ 백엔드 API 응답 구조와 동일한 타입 설계도
// hot_place.py의 응답: { id, name, adress, image_path, feature, tag1, tag2 }
export interface Destination {
    id: number;
    name: string;
    image_path: string;
    adress: string;
    feature?: string;  // 선택 속성 (화면에 표시하지 않아도 됨)
    tag1?: string;
    tag2?: string;
}

export function Destinations() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState("hot-places");
    const [displayItems, setDisplayItems] = useState<Destination[]>([]);
    const [selectedPlace, setSelectedPlace] = useState<Destination | null>(null);

    // // 주의: 실제 로그인 상태는 Context API나 전역 상태 관리(Zustand 등) 혹은 쿠키에서 가져와야 하지만, 
    // 임시로 localStorage를 확인하는 방식을 사용합니다. (구글 로그인 구현 방식에 맞게 나중에 수정 필요)
    const [isLoggedIn, setIsLoggedIn] = useState(false);

    useEffect(() => {
        // 컴포넌트 마운트 시 로그인(토큰) 여부를 확인합니다.
        const token = localStorage.getItem("access_token"); // 또는 구글 OAuth 관련 저장값
        setIsLoggedIn(!!token);
    }, []);

    // Plan Trip 버튼 클릭 핸들러
    const handlePlanTripClick = (place: Destination, e?: React.MouseEvent) => {
        if (e) e.stopPropagation();

        if (!isLoggedIn) {
            // 로그인이 안 되어 있다면 바로 로그인 페이지로 이동합니다.
            router.push("/login");
        } else {
            // 선택한 장소 정보를 localStorage에 저장 후 챗봇 페이지로 이동합니다.
            localStorage.setItem("selectedForChat", JSON.stringify(place));
            router.push("/chatbot");
            setSelectedPlace(null);
        }
    };

    // 배열을 랜덤하게 섞어주는 함수 (Fisher-Yates Shuffle)
    const shuffleArray = (array: any[]) => {
        const newArr = [...array];
        for (let i = newArr.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [newArr[i], newArr[j]] = [newArr[j], newArr[i]];
        }
        return newArr;
    };

    // ✅ 탭이 바뀔 때마다 실행: hot-places는 실제 API, 나머지는 더미 데이터 사용
    useEffect(() => {
        if (activeTab === "hot-places") {
            // 🌐 백엔드 /api/hot-places 에 GET 요청 (인증 불필요)
            const fetchHotPlaces = async () => {
                try {
                    const response = await fetch("/api/hot-places?limit=3");

                    if (!response.ok) {
                        throw new Error("Hot Places 데이터를 불러오는데 실패했습니다.");
                    }

                    // 백엔드에서 받은 JSON 데이터를 Destination[] 타입으로 바로 사용합니다.
                    const data: Destination[] = await response.json();
                    setDisplayItems(data);
                } catch (error) {
                    console.error("API 호출 에러:", error);
                    // 주의: 에러 발생 시(예: 서버 다운) 빈 배열로 유지됩니다.
                    setDisplayItems([]);
                }
            };
            fetchHotPlaces();
        } else {
            // hot-places 이외 탭은 더미 데이터를 랜덤 섞어 표시합니다.
            const items = staticDestinations[activeTab as keyof typeof staticDestinations];
            if (items) {
                setDisplayItems(shuffleArray(items));
            }
        }
    }, [activeTab]);

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
                            {displayItems.map((place) => (
                                <div key={place.id} className="group bg-white rounded-xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col">
                                    <div
                                        className="relative aspect-[4/3] overflow-hidden"
                                    >
                                        {/* image_path가 http로 시작하면 외부 URL, 아니면 /api/static/ 경로로 처리 */}
                                        <img
                                            src={place.image_path.startsWith("http") ? place.image_path : `/api/static/${place.image_path}`}
                                            alt={place.name}
                                            className="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-700 ease-in-out"
                                        />
                                    </div>
                                    <div className="p-6 flex flex-col flex-grow">
                                        <h3 className="text-xl font-bold text-gray-900 mb-2">{place.name}</h3>
                                        <div className="flex items-center gap-4 text-gray-500 text-sm mb-6 font-mono">
                                            <div className="flex items-center gap-1"><MapPin size={14} className="text-gray-400" /><span className="truncate max-w-[120px]">{place.adress}</span></div>
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
    );
}
