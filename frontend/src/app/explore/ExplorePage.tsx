"use client";

import { motion } from "framer-motion";
import { Sparkles, MapPin, ArrowRight, Star, Calendar, Clock } from "lucide-react";

// Contents 섹션은 API에서 데이터를 가져옵니다.

import { Sidebar } from "@/components/navigation/Sidebar";
import { PLACE_PLACEHOLDER } from "@/lib/imageUrl";
import { fetchRandomExplorePlaces, fetchCategoryPlaces, fetchCurrentUser, createRoom, type CategoryPlaceItem, type HotPlace, type UserProfile } from "@/services/api";

/** 백엔드 카테고리 값(한국어) → 번역 키 매핑 */
const CONTENT_CATEGORY_KEY_MAP: Record<string, string> = {
    "공연": "explore.categoryPerformance",
    "전시": "explore.categoryExhibition",
    "축제": "explore.categoryFestival",
    "팝업스토어": "explore.categoryPopup",
};
import { isAuthFailureError } from "@/services/authError";
import { clearAuth } from "@/services/errorHandler";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
// [Feature] 장소 카드 클릭 → 여행 컨텍스트 설정 팝업 → 챗봇 이동
import { TripContextModal, type TripContext } from "@/features/chat/components/TripContextModal";
import { setPendingAutoStartMeta } from "@/services/autoStart";
import { useTranslation } from "@/i18n/useTranslation";

type YourChoicesState = {
    restaurants: CategoryPlaceItem[];
    tourist: CategoryPlaceItem[];
    tours: CategoryPlaceItem[];
};

type ExploreInitPayload = {
    user: UserProfile;
    choices: YourChoicesState;
    hotPlaces: HotPlace[];
    contents: CategoryPlaceItem[];
};

let exploreInitInFlight: Promise<ExploreInitPayload> | null = null;
let latestExplorePayload: ExploreInitPayload | null = null;
let latestExplorePayloadAt = 0;
const EXPLORE_DEDUPE_TTL_MS = 2000;

const loadExploreData = async (): Promise<ExploreInitPayload> => {
    const user = await fetchCurrentUser();

    // 설문 결과를 user_prefs 텍스트로 조합 (개인화 벡터 검색용)
    const userPrefsText = [
        user.plan_prefer,
        user.vibe_prefer,
        user.places_prefer,
        user.extra_prefer1,
        user.extra_prefer2,
        user.extra_prefer3,
    ].filter(Boolean).join(", ") || "서울 여행 맛집 관광지";

    // hot_places·콘텐츠(랜덤) + Your Choices(개인화 벡터 검색) 병렬 호출
    const [randomData, categoryData] = await Promise.all([
        fetchRandomExplorePlaces("hot_places,콘텐츠", 3),
        fetchCategoryPlaces(userPrefsText),
    ]);

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
        contents: randomData["콘텐츠"] || [],
        choices: {
            restaurants: categoryData["음식점"] || [],
            tourist: categoryData["관광지"] || [],
            tours: categoryData["투어"] || [],
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
    const { t } = useTranslation();
    const router = useRouter();
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const [yourChoices, setYourChoices] = useState<YourChoicesState>({
        restaurants: [],
        tourist: [],
        tours: [],
    });
    const [hotPlaces, setHotPlaces] = useState<HotPlace[]>([]);
    const [contents, setContents] = useState<CategoryPlaceItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    // [Feature] 장소 카드 클릭 → TripContextModal → 챗봇 이동 상태
    const [showTripModal, setShowTripModal] = useState(false);
    const [pendingPlace, setPendingPlace] = useState<{ name: string; address: string; id: number | string; description?: string; image_url?: string; category?: string } | null>(null);
    const [isTripLoading, setIsTripLoading] = useState(false);

    // [Feature] Your Choices 카드 클릭 시 TripContextModal 표시
    const handleChoiceCardClick = (item: CategoryPlaceItem) => {
        // start_date/end_date가 있으면 description에 기간 정보 append
        const datePart = item.start_date
            ? `기간: ${item.start_date}${item.end_date ? ` ~ ${item.end_date}` : ""}`
            : "";
        const description = [item.description, datePart].filter(Boolean).join(" / ");
        setPendingPlace({
            name: item.title,
            address: item.address,
            id: item.contentid,
            description: description || undefined,
            image_url: item.image_url || undefined,
            category: item.category || undefined,
        });
        setShowTripModal(true);
    };

    // [Feature] Hot Places 카드 클릭 시 TripContextModal 표시
    const handleHotPlaceCardClick = (place: HotPlace) => {
        setPendingPlace({
            name: place.name,
            address: place.adress || "",
            id: place.id,
            description: place.feature || undefined,
            image_url: place.image_path || undefined,
        });
        setShowTripModal(true);
    };

    // [Feature] TripContextModal 확인 → 방 생성 + 메타 저장 + 챗봇 이동
    const handleTripModalConfirm = async (context: TripContext) => {
        setIsTripLoading(true);
        try {
            const newRoom = await createRoom(t("explore.newTripPlan"));
            const selectedPlaces = pendingPlace ? [{
                name: pendingPlace.name,
                adress: pendingPlace.address,
                contenttypeid: typeof pendingPlace.id === "number" ? pendingPlace.id : 0,
                description: pendingPlace.description,
                image_path: pendingPlace.image_url || undefined,
                category: pendingPlace.category || undefined,
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
                    router.push("/signup/profile");
                    return;
                }
                if (!payload.user.is_prefer) {
                    window.location.href = "/survey";
                    return;
                }

                setUserProfile(payload.user);
                setYourChoices(payload.choices);
                setHotPlaces(payload.hotPlaces);
                setContents(payload.contents);
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
                                        {t("explore.yourChoices")} <Sparkles size={16} className="text-yellow-500" />
                                    </h3>
                                    <p className="section-subtitle mt-1">
                                        {userProfile?.name ? t("explore.choicesSubtitle", { name: userProfile.name }) : t("explore.choicesSubtitleDefault")}
                                    </p>
                                </div>
                                <div className="flex items-center gap-2 text-xs font-medium text-gray-400 border border-gray-100 rounded-full px-3 py-1">
                                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                                    {t("explore.personalized")}
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
                                                    {t("explore.localEats")}
                                                </h4>
                                            </div>
                                            {/* [Fix] 이미지를 aspect-ratio 기반으로 변경하여 화면 크기에 맞게 유동 확장 */}
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                {yourChoices.restaurants.map((item) => (
                                                    <motion.div key={item.contentid} whileHover={{ y: -3 }} className="group cursor-pointer" onClick={() => handleChoiceCardClick(item)}>
                                                        <div className="aspect-[16/10] w-full rounded-2xl overflow-hidden bg-gray-100 mb-2">
                                                            <img src={item.image_url || PLACE_PLACEHOLDER} alt={item.title} onError={(e) => { e.currentTarget.src = PLACE_PLACEHOLDER; }} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
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
                                                    {t("explore.mustVisitSpots")}
                                                </h4>
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                {yourChoices.tourist.map((item) => (
                                                    <motion.div key={item.contentid} whileHover={{ y: -3 }} className="group cursor-pointer" onClick={() => handleChoiceCardClick(item)}>
                                                        <div className="aspect-[16/10] w-full rounded-2xl overflow-hidden bg-gray-100 mb-2">
                                                            <img src={item.image_url || PLACE_PLACEHOLDER} alt={item.title} onError={(e) => { e.currentTarget.src = PLACE_PLACEHOLDER; }} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                                        </div>
                                                        <h5 className="text-sm font-medium text-gray-900 leading-tight truncate">{item.title}</h5>
                                                        <p className="text-[11px] text-gray-400 truncate">{item.address}</p>
                                                    </motion.div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Section 3: Tours */}
                                        <div>
                                            <div className="flex justify-between items-center mb-3">
                                                <h4 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
                                                    {t("explore.tourCourses")}
                                                </h4>
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                {yourChoices.tours.map((item) => (
                                                    <motion.div key={item.contentid} whileHover={{ y: -3 }} className="group cursor-pointer" onClick={() => handleChoiceCardClick(item)}>
                                                        <div className="aspect-[16/10] w-full rounded-2xl overflow-hidden bg-gray-100 mb-2">
                                                            <img src={item.image_url || PLACE_PLACEHOLDER} alt={item.title} onError={(e) => { e.currentTarget.src = PLACE_PLACEHOLDER; }} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
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
                                    <h3 className="page-title text-gray-900">{t("explore.hotPlacesTitle")}</h3>
                                    <p className="section-subtitle mt-1">{t("explore.trendingNeighborhoods")}</p>
                                </div>
                                <div className="p-2 bg-gray-50 rounded-full">
                                    <MapPin size={16} className="text-gray-400" />
                                </div>
                            </div>

                            {/* Scrollable Grid */}
                            <div className="flex-1 overflow-y-auto custom-scrollbar pr-1">
                                {isLoading ? (
                                    <div className="h-full flex items-center justify-center py-8">
                                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-black" />
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 pb-2 h-full">
                                        {hotPlaces.map((place) => (
                                            <motion.div
                                                key={place.id}
                                                whileHover={{ scale: 1.02 }}
                                                className="relative group cursor-pointer overflow-hidden rounded-2xl bg-gray-100 min-h-[120px]"
                                                onClick={() => handleHotPlaceCardClick(place)}
                                            >
                                                <img
                                                    src={place.image_path ? (place.image_path.startsWith("http") ? place.image_path : `/api/static/${place.image_path}`) : PLACE_PLACEHOLDER}
                                                    alt={place.name}
                                                    onError={(e) => { e.currentTarget.src = PLACE_PLACEHOLDER; }}
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
                                )}
                            </div>
                        </div>

                        {/* Contents Section — 높이 = (전체 - gap) / 2 로 고정 */}
                        <div className="border border-gray-200 rounded-[32px] p-6 flex flex-col shadow-sm bg-white overflow-hidden h-[calc((100vh-80px-24px)/2)]">
                            <div className="flex justify-between items-start mb-4 flex-none">
                                <div>
                                    <h3 className="page-title text-gray-900">{t("explore.contentsTitle")}</h3>
                                    <p className="section-subtitle mt-1">{t("explore.eventsExhibitions")}</p>
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
                                    ) : contents.length === 0 ? (
                                        <p className="text-xs text-gray-400 text-center py-6">{t("explore.noContents")}</p>
                                    ) : (
                                        contents.map((item) => (
                                            <motion.div
                                                key={item.contentid}
                                                whileHover={{ x: 5 }}
                                                className="flex gap-3 p-3 rounded-2xl hover:bg-gray-50 transition-colors cursor-pointer group border border-transparent hover:border-gray-100"
                                                onClick={() => handleChoiceCardClick(item)}
                                            >
                                                <div className="w-16 h-16 rounded-xl overflow-hidden flex-shrink-0 bg-gray-100">
                                                    <img src={item.image_url || PLACE_PLACEHOLDER} alt={item.title} onError={(e) => { e.currentTarget.src = PLACE_PLACEHOLDER; }} className="w-full h-full object-cover" />
                                                </div>
                                                <div className="flex flex-col justify-center flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-[10px] font-bold text-black uppercase tracking-wider border border-gray-200 px-1.5 rounded-sm bg-white">
                                                            {CONTENT_CATEGORY_KEY_MAP[item.category || ""] ? t(CONTENT_CATEGORY_KEY_MAP[item.category || ""]) : t("explore.contentFallback")}
                                                        </span>
                                                    </div>
                                                    <h4 className="text-sm font-semibold text-gray-900 truncate group-hover:text-black transition-colors">{item.title}</h4>
                                                    {item.start_date && (
                                                        <p className="text-[11px] text-gray-500 mt-0.5">
                                                            {item.start_date}{item.end_date ? ` ~ ${item.end_date}` : ""}
                                                        </p>
                                                    )}
                                                    <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1 truncate">
                                                        <MapPin size={10} />
                                                        {item.address || t("explore.noAddress")}
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
