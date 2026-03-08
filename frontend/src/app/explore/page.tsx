"use client";

import { motion } from "framer-motion";
import { Sparkles, MapPin, ArrowRight, Star, Calendar, Clock } from "lucide-react";

// --- MOCK DATA ---

// 1. Hot Places (Neighborhoods) - Randomly shown, general appeal
// ※ 아래 하드코딩 데이터는 API 연동으로 대체됨 (주석으로 보존)
/*
const HOT_PLACES = [
    { id: 1, name: "Hongdae", image: "https://images.unsplash.com/photo-1748696009693-a04d400d08de?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzZW91bCUyMGhvbmdkYWUlMjBzdHJlZXQlMjB0cmVuZHl8ZW58MXx8fHwxNzcxOTAwMzg0fDA&ixlib=rb-4.1.0&q=80&w=1080", tags: ["#Youth", "#Busking"] },
    { id: 2, name: "Euljiro", image: "https://images.unsplash.com/photo-1711923236198-4ae03a28e436?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzZW91bCUyMGV1bGppcm8lMjB2aW50YWdlJTIwYWxsZXl8ZW58MXx8fHwxNzcxOTAwMzg0fDA&ixlib=rb-4.1.0&q=80&w=1080", tags: ["#Hipjiro", "#Vintage"] },
    { id: 3, name: "Seongsu", image: "https://images.unsplash.com/photo-1712651070043-0b8dbb843144?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzZW91bCUyMHBvcHVwJTIwc3RvcmUlMjB0cmVuZHl8ZW58MXx8fHwxNzcxOTAwMzg0fDA&ixlib=rb-4.1.0&q=80&w=1080", tags: ["#Cafe", "#Popup"] },
    { id: 4, name: "Itaewon", image: "https://images.unsplash.com/photo-1676741556435-709eaa1f872f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzZW91bCUyMGl0YWV3b24lMjBuaWdodGxpZmV8ZW58MXx8fHwxNzcxOTAwMzg0fDA&ixlib=rb-4.1.0&q=80&w=1080", tags: ["#Nightlife", "#Global"] },
];
*/

// 2. Your Choices (Personalized) - 3 Categories, 3 Items each
const YOUR_CHOICES = {
    restaurants: [
        { id: 1, name: "Mingles", category: "Fine Dining", rating: 4.8, image: "https://images.unsplash.com/photo-1573470571028-a0ca7a723959?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjBmb29kJTIwbWluaW1hbHxlbnwxfHx8fDE3NzE4OTk4NTJ8MA&ixlib=rb-4.1.0&q=80&w=1080" },
        { id: 2, name: "Gwangjang Market", category: "Street Food", rating: 4.6, image: "https://images.unsplash.com/photo-1694271809210-a1d5df5e747f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzZW91bCUyMGxhbmRzY2FwZSUyMG1pbmltYWx8ZW58MXx8fHwxNzcxODk5ODY4fDA&ixlib=rb-4.1.0&q=80&w=1080" },
        { id: 3, name: "Onion Anguk", category: "Bakery Cafe", rating: 4.5, image: "https://images.unsplash.com/photo-1694079794506-8d4551c3c472?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjB0cmFkaXRpb25hbCUyMGFyY2hpdGVjdHVyZXxlbnwxfHx8fDE3NzE4OTk4Njh8MA&ixlib=rb-4.1.0&q=80&w=1080" },
    ],
    tourist: [
        { id: 1, name: "Gyeongbokgung", category: "History", rating: 4.9, image: "https://images.unsplash.com/photo-1666670750287-176e3218ce12?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzZW91bCUyMGd5ZW9uZ2Jva2d1bmclMjBwYWxhY2UlMjBhdXR1bW58ZW58MXx8fHwxNzcxOTAwMzg0fDA&ixlib=rb-4.1.0&q=80&w=1080" },
        { id: 2, name: "Lotte Tower", category: "Landmark", rating: 4.7, image: "https://images.unsplash.com/photo-1662075241003-9b937a892123?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxsb3R0ZSUyMHdvcmxkJTIwdG93ZXIlMjBzZW91bHxlbnwxfHx8fDE3NzE5MDAzOTN8MA&ixlib=rb-4.1.0&q=80&w=1080" },
        { id: 3, name: "DDP", category: "Culture", rating: 4.6, image: "https://images.unsplash.com/photo-1736951418886-06f726958a2b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxkb25nZGFlbXVuJTIwZGVzaWduJTIwcGxhemElMjBuaWdodHxlbnwxfHx8fDE3NzE5MDAzOTN8MA&ixlib=rb-4.1.0&q=80&w=1080" },
    ],
    activities: [
        { id: 1, name: "Pottery Class", category: "Workshop", rating: 4.8, image: "https://images.unsplash.com/photo-1621269050686-13387e760500?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzZW91bCUyMHBvdHRlcnklMjBjbGFzcyUyMHdvcmtzaG9wfGVufDF8fHx8MTc3MTkwMDM4NHww&ixlib=rb-4.1.0&q=80&w=1080" },
        { id: 2, name: "Han River Kayak", category: "Leisure", rating: 4.7, image: "https://images.unsplash.com/photo-1612794794535-210c45928c5f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzZW91bCUyMGhhbiUyMHJpdmVyJTIwa2F5YWtpbmd8ZW58MXx8fHwxNzcxOTAwMzg0fDA&ixlib=rb-4.1.0&q=80&w=1080" },
        { id: 3, name: "Perfume Making", category: "Workshop", rating: 4.5, image: "https://images.unsplash.com/photo-1524190952534-79b1f7d6ad5c?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjBpbnRlcmlvciUyMHNlb3VsfGVufDF8fHx8MTc3MTg5OTg2OHww&ixlib=rb-4.1.0&q=80&w=1080" },
    ],
};

// Contents 섹션은 API에서 팝업스토어 데이터를 가져옴

import { Sidebar } from "@/components/Sidebar";
import { fetchCategoryPlaces, fetchRandomExplorePlaces, fetchCurrentUser, type CategoryPlaceItem, type HotPlace, type UserProfile } from "@/services/api";
import { isAuthFailureError } from "@/services/authError";
import { clearAuth } from "@/services/errorHandler";
import { useEffect, useState } from "react";

type YourChoicesState = {
    restaurants: CategoryPlaceItem[];
    tourist: CategoryPlaceItem[];
    activities: CategoryPlaceItem[];
};

type ExploreInitPayload = {
    user: UserProfile;
    choices: YourChoicesState;
    hotPlaces: HotPlace[];
    popupStores: CategoryPlaceItem[];
};

let exploreInitInFlight: Promise<ExploreInitPayload> | null = null;
let latestExplorePayload: ExploreInitPayload | null = null;
let latestExplorePayloadAt = 0;
const EXPLORE_DEDUPE_TTL_MS = 2000;

const loadExploreData = async (): Promise<ExploreInitPayload> => {
    const user = await fetchCurrentUser();

    // 1번의 API 호출로 4가지 카테고리를 한번에 모두 가져옵니다 (통합)
    const randomData = await fetchRandomExplorePlaces("hot_places,tourist_spots,restaurants,팝업스토어", 3);

    return {
        user,
        hotPlaces: (randomData["hot_places"] || []).map((p: CategoryPlaceItem & { tag1?: string; tag2?: string }) => ({
            id: Number(p.contentid),
            name: p.title,
            adress: p.address,
            image_path: p.image_url,
            feature: p.description,
            tag1: p.tag1,
            tag2: p.tag2
        })) as unknown as HotPlace[],
        popupStores: randomData["팝업스토어"] || [],
        choices: {
            restaurants: randomData["restaurants"] || [],
            tourist: randomData["tourist_spots"] || [],
            // '축제공연행사' 대신 임시로 관광지 사용 (기존 동작 유지보수 위함)
            activities: randomData["tourist_spots"] || [],
        },
    };
};


const getExploreDataOnce = async (): Promise<ExploreInitPayload> => {
    const now = Date.now();
    if (latestExplorePayload && now - latestExplorePayloadAt < EXPLORE_DEDUPE_TTL_MS) {
        return latestExplorePayload;
    }

    if (!exploreInitInFlight) {
        exploreInitInFlight = loadExploreData()
            .then((payload) => {
                latestExplorePayload = payload;
                latestExplorePayloadAt = Date.now();
                return payload;
            })
            .finally(() => {
                exploreInitInFlight = null;
            });
    }

    return exploreInitInFlight;
};

export default function ExplorePage() {
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const [yourChoices, setYourChoices] = useState<YourChoicesState>({
        restaurants: [],
        tourist: [],
        activities: [],
    });
    const [hotPlaces, setHotPlaces] = useState<HotPlace[]>([]);
    const [popupStores, setPopupStores] = useState<CategoryPlaceItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const initExplore = async () => {
            setIsLoading(true);
            try {
                const payload = await getExploreDataOnce();

                // 주의: 가입(is_join)이나 설문(is_prefer)을 완료하지 않고 /explore 등 정상 서비스 페이지로 이탈한 경우 다시 돌려보냅니다.
                if (!payload.user.is_join) {
                    window.location.href = "/signup/profile";
                    return;
                }
                if (!payload.user.is_prefer) {
                    window.location.href = "/survey";
                    return;
                }

                setUserProfile(payload.user);
                setYourChoices(payload.choices);
                setHotPlaces(payload.hotPlaces);
                setPopupStores(payload.popupStores);
            } catch (error) {
                if (isAuthFailureError(error)) {
                    clearAuth();
                    window.location.href = "/signup";
                    return;
                }
                console.error("Failed to fetch explore data:", error);
            } finally {
                setIsLoading(false);
            }
        };

        initExplore();
    }, []);

    return (
        <div className="flex w-full h-screen bg-gray-100 p-4 gap-4 overflow-hidden">
            {/* Sidebar */}
            <div className="flex-none h-full">
                <Sidebar />
            </div>

            {/* Main Content Area */}
            <main className="flex-1 h-full py-2 px-2 md:px-6 overflow-hidden rounded-lg bg-white border-r border-gray-200">
                <div className="flex flex-col xl:flex-row h-full w-full gap-6">

                    {/* LEFT COLUMN: Your Choices (Largest) */}
                    <div className="flex-1 xl:flex-[2] flex flex-col gap-6 min-h-0">
                        <div className="border border-gray-200 rounded-[32px] p-6 md:p-8 flex flex-col h-full shadow-sm bg-white relative overflow-hidden">

                            {/* Fixed Header */}
                            <div className="flex justify-between items-center mb-4 z-10 flex-none">
                                <div>
                                    <h3 className="page-title text-gray-900 flex items-center gap-2">
                                        Your Choices <Sparkles size={16} className="text-yellow-500" />
                                    </h3>
                                    <p className="section-subtitle mt-1">
                                        {userProfile?.name ? `${userProfile.name}님을 위한 맞춤 여행지` : "Curated recommendations based on your preferences"}
                                    </p>
                                </div>
                                <div className="flex items-center gap-2 text-xs font-medium text-gray-400 border border-gray-100 rounded-full px-3 py-1">
                                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                                    Personalized
                                </div>
                            </div>

                            {/* Scrollable Content */}
                            <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 -mr-2 space-y-6 z-10">
                                {isLoading ? (
                                    <div className="h-full flex items-center justify-center">
                                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-black"></div>
                                    </div>
                                ) : (
                                    <>
                                        {/* Section 1: Restaurants */}
                                        <div>
                                            <div className="flex justify-between items-center mb-3">
                                                <h4 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
                                                    🍽️ Local Eats
                                                </h4>
                                                <button className="text-[10px] text-gray-400 hover:text-black transition-colors">See all</button>
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                {yourChoices.restaurants.map((item) => (
                                                    <motion.div key={item.contentid} whileHover={{ y: -3 }} className="group cursor-pointer">
                                                        <div className="aspect-[4/3] rounded-2xl overflow-hidden bg-gray-100 relative mb-2">
                                                            <img src={item.image_url} alt={item.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                                        </div>
                                                        <h5 className="text-sm font-medium text-gray-900 leading-tight truncate">{item.title}</h5>
                                                        <p className="text-[11px] text-gray-400 truncate">{item.address}</p>
                                                    </motion.div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Section 2: Tourist Spots */}
                                        <div>
                                            <div className="flex justify-between items-center mb-3">
                                                <h4 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
                                                    📸 Must-Visit Spots
                                                </h4>
                                                <button className="text-[10px] text-gray-400 hover:text-black transition-colors">See all</button>
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                {yourChoices.tourist.map((item) => (
                                                    <motion.div key={item.contentid} whileHover={{ y: -3 }} className="group cursor-pointer">
                                                        <div className="aspect-[4/3] rounded-2xl overflow-hidden bg-gray-100 relative mb-2">
                                                            <img src={item.image_url} alt={item.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                                        </div>
                                                        <h5 className="text-sm font-medium text-gray-900 leading-tight truncate">{item.title}</h5>
                                                        <p className="text-[11px] text-gray-400 truncate">{item.address}</p>
                                                    </motion.div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Section 3: Activities */}
                                        <div>
                                            <div className="flex justify-between items-center mb-3">
                                                <h4 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
                                                    🎨 Unique Experiences
                                                </h4>
                                                <button className="text-[10px] text-gray-400 hover:text-black transition-colors">See all</button>
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                {yourChoices.activities.map((item) => (
                                                    <motion.div key={item.contentid} whileHover={{ y: -3 }} className="group cursor-pointer">
                                                        <div className="aspect-[4/3] rounded-2xl overflow-hidden bg-gray-100 relative mb-2">
                                                            <img src={item.image_url} alt={item.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                                        </div>
                                                        <h5 className="text-sm font-medium text-gray-900 leading-tight truncate">{item.title}</h5>
                                                        <p className="text-[11px] text-gray-400 truncate">{item.address}</p>
                                                    </motion.div>
                                                ))}
                                            </div>
                                        </div>
                                    </>
                                )}
                            </div>

                            {/* Decorative Background */}
                            <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-gradient-to-bl from-gray-50 to-transparent rounded-bl-[100px] -z-0 pointer-events-none opacity-50" />
                        </div>
                    </div>

                    {/* RIGHT COLUMN: Hot Places + Contents */}
                    <div className="flex-1 xl:flex-[1.2] flex flex-col gap-6 min-h-0">

                        {/* Hot Places Section */}
                        <div className="flex-1 border border-gray-200 rounded-[32px] p-6 flex flex-col shadow-sm bg-white overflow-hidden min-h-[300px]">
                            {/* Fixed Header */}
                            <div className="flex justify-between items-start mb-4 flex-none">
                                <div>
                                    <h3 className="page-title text-gray-900">Hot Places</h3>
                                    <p className="section-subtitle mt-1">Trending neighborhoods</p>
                                </div>
                                <div className="p-2 bg-gray-50 rounded-full">
                                    <MapPin size={16} className="text-gray-400" />
                                </div>
                            </div>

                            {/* Scrollable Grid */}
                            <div className="flex-1 overflow-y-auto custom-scrollbar pr-1">
                                <div className="grid grid-cols-3 gap-3 pb-2 h-full">
                                    {hotPlaces.map((place) => (
                                        <motion.div
                                            key={place.id}
                                            whileHover={{ scale: 1.02 }}
                                            className="relative group cursor-pointer overflow-hidden rounded-2xl bg-gray-100 h-full"
                                        >
                                            <img
                                                // 핫플레이스는 상대경로일 수도 있고 절대경로(http)일 수도 있으므로 분기처리
                                                src={place.image_path?.startsWith("http") ? place.image_path : `/api/static/${place.image_path}`}
                                                alt={place.name}
                                                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110 grayscale-[30%] group-hover:grayscale-0"
                                            />
                                            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-90" />
                                            <div className="absolute bottom-3 left-3 text-white">
                                                <h4 className="font-bold text-sm tracking-wide">{place.name}</h4>
                                                <div className="flex gap-1 mt-1 flex-wrap">
                                                    {[place.tag1, place.tag2].filter(Boolean).map(tag => (
                                                        <span key={tag} className="text-[8px] bg-white/20 backdrop-blur-sm px-1.5 py-0.5 rounded-sm">#{tag}</span>
                                                    ))}
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Contents Section */}
                        <div className="flex-1 border border-gray-200 rounded-[32px] p-6 flex flex-col shadow-sm bg-white overflow-hidden min-h-[300px]">
                            <div className="flex justify-between items-start mb-4 flex-none">
                                <div>
                                    <h3 className="page-title text-gray-900">Contents</h3>
                                    <p className="section-subtitle mt-1">Events & Exhibitions</p>
                                </div>
                                <div className="p-2 bg-gray-50 rounded-full">
                                    <Calendar size={16} className="text-gray-400" />
                                </div>
                            </div>

                            <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar">
                                <div className="flex flex-col gap-3 pb-2">
                                    {isLoading ? (
                                        <div className="h-full flex items-center justify-center py-8">
                                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-black" />
                                        </div>
                                    ) : popupStores.length === 0 ? (
                                        <p className="text-xs text-gray-400 text-center py-6">팝업스토어 정보가 없습니다</p>
                                    ) : (
                                        popupStores.map((item) => (
                                            <motion.div
                                                key={item.contentid}
                                                whileHover={{ x: 5 }}
                                                className="flex gap-3 p-3 rounded-2xl hover:bg-gray-50 transition-colors cursor-pointer group border border-transparent hover:border-gray-100"
                                            >
                                                <div className="w-16 h-16 rounded-xl overflow-hidden flex-shrink-0 bg-gray-100">
                                                    {item.image_url ? (
                                                        <img src={item.image_url} alt={item.title} className="w-full h-full object-cover" />
                                                    ) : (
                                                        <div className="w-full h-full flex items-center justify-center text-gray-300 text-xs">No img</div>
                                                    )}
                                                </div>
                                                <div className="flex flex-col justify-center flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-[10px] font-bold text-black uppercase tracking-wider border border-gray-200 px-1.5 rounded-sm bg-white">
                                                            POPUP STORE
                                                        </span>
                                                    </div>
                                                    <h4 className="text-sm font-semibold text-gray-900 truncate group-hover:text-black transition-colors">{item.title}</h4>
                                                    <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1">
                                                        <Clock size={10} />
                                                        {item.end_date ? `~ ${item.end_date}` : "진행 중"}
                                                    </p>
                                                </div>
                                                <div className="flex items-center justify-center text-gray-300 group-hover:text-black transition-colors">
                                                    <ArrowRight size={16} />
                                                </div>
                                            </motion.div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
