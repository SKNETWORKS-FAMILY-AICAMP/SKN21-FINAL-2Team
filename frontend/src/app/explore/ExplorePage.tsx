"use client";

import { motion } from "framer-motion";
import { Sparkles, MapPin, ArrowRight, Star, Calendar, Clock } from "lucide-react";

// Contents 섹션은 API에서 데이터를 가져옵니다.

import { Sidebar } from "@/components/navigation/Sidebar";
import { fetchRandomExplorePlaces, fetchCurrentUser, createRoom, type CategoryPlaceItem, type HotPlace, type UserProfile } from "@/services/api";
import { isAuthFailureError } from "@/services/authError";
import { clearAuth } from "@/services/errorHandler";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
// [Feature] 장소 카드 클릭 → 여행 컨텍스트 설정 팝업 → 챗봇 이동
import { TripContextModal, type TripContext } from "@/features/chat/components/TripContextModal";
import { setPendingAutoStartMeta } from "@/services/autoStart";

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

    // 1번의 API 호출로 5가지 카테고리를 한번에 모두 가져옵니다 (통합)
    const randomData = await fetchRandomExplorePlaces("hot_places,tourist_spots,restaurants,팝업스토어,activities", 3);

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
            activities: randomData["activities"] || [],
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

export function ExplorePage() {
    const router = useRouter();
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const [yourChoices, setYourChoices] = useState<YourChoicesState>({
        restaurants: [],
        tourist: [],
        activities: [],
    });
    const [hotPlaces, setHotPlaces] = useState<HotPlace[]>([]);
    const [popupStores, setPopupStores] = useState<CategoryPlaceItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    // [Feature] 장소 카드 클릭 → TripContextModal → 챗봇 이동 상태
    const [showTripModal, setShowTripModal] = useState(false);
    const [pendingPlace, setPendingPlace] = useState<{ name: string; address: string; id: number | string } | null>(null);
    const [isTripLoading, setIsTripLoading] = useState(false);

    // [Feature] Your Choices 카드 클릭 시 TripContextModal 표시
    const handleChoiceCardClick = (item: CategoryPlaceItem) => {
        setPendingPlace({
            name: item.title,
            address: item.address,
            id: item.contentid,
        });
        setShowTripModal(true);
    };

    // [Feature] Hot Places 카드 클릭 시 TripContextModal 표시
    const handleHotPlaceCardClick = (place: HotPlace) => {
        setPendingPlace({
            name: place.name,
            address: place.adress || "",
            id: place.id,
        });
        setShowTripModal(true);
    };

    // [Feature] TripContextModal 확인 → 방 생성 + 메타 저장 + 챗봇 이동
    const handleTripModalConfirm = async (context: TripContext) => {
        setIsTripLoading(true);
        try {
            const newRoom = await createRoom("새로운 여행 계획");
            const selectedPlaces = pendingPlace ? [{
                name: pendingPlace.name,
                adress: pendingPlace.address,
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
            console.error("Failed to create room from ExplorePage", e);
            setIsTripLoading(false);
            setShowTripModal(false);
            router.push("/chatbot");
        }
    };

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
                console.warn("Failed to fetch explore data:", error);
            } finally {
                setIsLoading(false);
            }
        };

        initExplore();
    }, []);

    return (
        <div className="flex w-full min-h-screen flex-col bg-gray-100 p-3 sm:p-4 gap-4 lg:h-screen lg:flex-row lg:overflow-hidden">
            {/* Sidebar */}
            <div className="flex-none lg:h-full">
                <Sidebar />
            </div>

            {/* Main Content Area — [Feature] lg 이상에서도 스크롤 가능하도록 overflow-y-auto 적용 (100% 줌에서 Contents까지 스크롤 가능) */}
            <main className="flex-1 min-w-0 rounded-lg bg-white border-r border-gray-200 p-2 md:p-6 lg:h-full lg:overflow-y-auto custom-scrollbar">
                {/* [Fix] 두 컬럼 너비/높이를 고정하여 새로고침 시 레이아웃 변동 완전 방지 */}
                <div className="flex flex-col gap-6 w-full xl:flex-row">

                    {/* LEFT COLUMN: Your Choices — 너비 62% 고정, 높이 calc(100vh - 80px) 고정 */}
                    <div className="w-full xl:w-[62%] flex-shrink-0 flex flex-col gap-6">
                        <div className="border border-gray-200 rounded-[32px] p-6 md:p-8 flex flex-col h-[calc(100vh-80px)] shadow-sm bg-white relative overflow-hidden">

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
                                            </div>
                                            {/* [Fix] 이미지를 aspect-ratio 기반으로 변경하여 화면 크기에 맞게 유동 확장 */}
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                {yourChoices.restaurants.map((item) => (
                                                    <motion.div key={item.contentid} whileHover={{ y: -3 }} className="group cursor-pointer" onClick={() => handleChoiceCardClick(item)}>
                                                        <div className="aspect-[16/10] w-full rounded-2xl overflow-hidden bg-gray-100 mb-2">
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
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                {yourChoices.tourist.map((item) => (
                                                    <motion.div key={item.contentid} whileHover={{ y: -3 }} className="group cursor-pointer" onClick={() => handleChoiceCardClick(item)}>
                                                        <div className="aspect-[16/10] w-full rounded-2xl overflow-hidden bg-gray-100 mb-2">
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
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                {yourChoices.activities.map((item) => (
                                                    <motion.div key={item.contentid} whileHover={{ y: -3 }} className="group cursor-pointer" onClick={() => handleChoiceCardClick(item)}>
                                                        <div className="aspect-[16/10] w-full rounded-2xl overflow-hidden bg-gray-100 mb-2">
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

                    {/* RIGHT COLUMN: Hot Places + Contents — 너비 36% 고정 */}
                    <div className="w-full xl:w-[36%] flex-shrink-0 flex flex-col gap-6">

                        {/* Hot Places Section — 높이 = (전체 - gap) / 2 로 고정 */}
                        <div className="border border-gray-200 rounded-[32px] p-6 flex flex-col shadow-sm bg-white overflow-hidden h-[calc((100vh-80px-24px)/2)]">
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
                                {/* [Fix] 카드가 남은 공간을 꽉 채우도록 flex + flex-1 적용 */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 pb-2 h-full">
                                    {hotPlaces.map((place) => (
                                        <motion.div
                                            key={place.id}
                                            whileHover={{ scale: 1.02 }}
                                            className="relative group cursor-pointer overflow-hidden rounded-2xl bg-gray-100 min-h-[120px]"
                                            onClick={() => handleHotPlaceCardClick(place)}
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

                        {/* Contents Section — 높이 = (전체 - gap) / 2 로 고정 */}
                        <div className="border border-gray-200 rounded-[32px] p-6 flex flex-col shadow-sm bg-white overflow-hidden h-[calc((100vh-80px-24px)/2)]">
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

            {/* [Feature] 장소 카드 클릭 후 여행 컨텍스트 설정 팝업 — 확인 시 챗봇으로 이동 */}
            <TripContextModal
                isOpen={showTripModal}
                onConfirm={handleTripModalConfirm}
                loading={isTripLoading}
                onClose={() => {
                    if (!isTripLoading) {
                        setShowTripModal(false);
                        setPendingPlace(null);
                    }
                }}
            />
        </div>
    );
}
