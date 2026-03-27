"use client";

import { motion, AnimatePresence } from "framer-motion";
import { MapPin, CalendarPlus } from "lucide-react";
import React, { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { TripContextModal, type TripContext } from "@/features/chat/components/TripContextModal";
import { createRoom, fetchRandomExplorePlaces, fetchCurrentUser, type UserProfile, type CategoryPlaceItem } from "@/services/api";
import { IncompleteSignupModal } from "@/app/components/IncompleteSignupModal";
import { setPendingAutoStartMeta } from "@/services/autoStart";
import { useTranslation } from "@/i18n/useTranslation";

// ✅ 세 API의 다른 필드명을 하나로 통합한 타입 설계도
export interface Destination {
    id: number | string;
    name: string;
    image: string;
    address: string;
    description?: string;
}

// fetch 시점에 각 API 응답을 이 타입으로 '변환(매핑)'하여 JSX는 이 타입만 바라봅니다.
// hot_place: id(number) | attractions·restaurants: contentid(string)
// name: 세 API 모두 동일
// image: API 응답 이미지 URL
// address: hot_place: adress(오타) | 나머지: address 로 통일
export function Destinations() {
    const { t } = useTranslation();
    const router = useRouter();

    const categories = [
        { id: "hot-places", label: t("destinations.hotPlaces") },
        { id: "tourist-spot", label: t("destinations.touristSpot") },
        { id: "foods", label: t("destinations.foods") },
    ];
    const [activeTab, setActiveTab] = useState("hot-places");
    const [displayItems, setDisplayItems] = useState<Destination[]>([]);
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    // 트립 컨텍스트 모달 상태
    const [showTripModal, setShowTripModal] = useState(false);
    const [pendingPlace, setPendingPlace] = useState<Destination | null>(null);
    const [isTripLoading, setIsTripLoading] = useState(false);

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
            // [Feature] Plan Trip 버튼을 통한 로그인/가입 플로우임을 표시
            localStorage.setItem("planTripFlow", "true");
            localStorage.setItem("pendingDestination", JSON.stringify(place));
            router.push("/signup");
        } else {
            // 주의: 로그인 후 정보나 설문 기입이 덜 끝났다면 즉시 이동하지 않고 모달 표시
            if (userProfile && !userProfile.is_join) {
                // 사용자가 챗봇 목적지로 향하려 했다는 의도를 남겨두기 위해 세팅
                // planTripFlow=true: 프로필/설문 완료 후 챗봇으로 직행하도록 표시
                localStorage.setItem("planTripFlow", "true");
                localStorage.setItem("pendingDestination", JSON.stringify(place));
                setWarningStep("profile");
                setIsWarningModalOpen(true);
                return;
            }
            if (userProfile && !userProfile.is_prefer) {
                // planTripFlow=true: 설문 완료 후 챗봇으로 직행하도록 표시
                localStorage.setItem("planTripFlow", "true");
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
            const newRoom = await createRoom(t("explore.newTripPlan"));
            const selectedPlaces = pendingPlace ? [{
                name: pendingPlace.name,
                adress: pendingPlace.address || (pendingPlace as Destination & { adress?: string }).adress,
                contenttypeid: typeof pendingPlace.id === "number" ? pendingPlace.id : 0,
                description: pendingPlace.description,
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

    const [isLoading, setIsLoading] = useState(false);

    // ✅ 탭이 바뀔 때마다 서버에서 새로운 랜덤 데이터를 가져옵니다.
    useEffect(() => {
        const fetchCurrentTabRandom = async () => {
            setIsLoading(true);
            try {
                const raw = await fetchRandomExplorePlaces("hot_places,tourist_spots,restaurants", 3);
                const mappedData: Record<string, Destination[]> = {};

                // 1. 핫플레이스 매핑
                mappedData["hot-places"] = (raw["hot_places"] || []).map((p: CategoryPlaceItem) => ({
                    id: p.contentid,
                    name: p.title,
                    address: p.address,
                    description: p.description,
                    // 주의: image_url이 있을 때만 경로를 생성, 없으면 빈 문자열(placeholder용)
                    image: p.image_url && p.image_url.trim() !== ""
                        ? (p.image_url.startsWith("http") ? p.image_url : `/api/static/${p.image_url}`)
                        : ""
                }));

                // 2. 관광지 매핑
                mappedData["tourist-spot"] = (raw["tourist_spots"] || []).map((p: CategoryPlaceItem) => ({
                    id: p.contentid,
                    name: p.title,
                    address: p.address,
                    description: p.description,
                    image: p.image_url || ""
                }));

                // 3. 음식점 매핑
                mappedData["foods"] = (raw["restaurants"] || []).map((p: CategoryPlaceItem) => ({
                    id: p.contentid,
                    name: p.title,
                    address: p.address,
                    description: p.description,
                    image: p.image_url || ""
                }));

                // 현재 탭에 맞는 데이터로 즉시 업데이트
                setDisplayItems(mappedData[activeTab] ?? []);
            } catch (error) {
                console.warn("Failed to fetch random places on tab change:", error);
                setDisplayItems([]);
            } finally {
                setIsLoading(false);
            }
        };

        fetchCurrentTabRandom();
    }, [activeTab]);

    return (
        <>
            {/* [Fix] scroll-mt-24: 네비게이션 앵커 클릭 시 fixed Header(64px) 높이 보정 */}
            {/* [Fix] min-h-[calc(100vh-64px)] + flex justify-center: Header(64px) 제외 뷰포트 채움 + 세로 중앙 */}
            <section id="destinations" className="pt-10 pb-24 bg-gray-50/30 min-h-[calc(100vh-64px)] flex flex-col justify-center">
                <div className="max-w-7xl mx-auto px-10 md:px-16 lg:px-8 w-full">
                    <div className="flex flex-col lg:flex-row lg:items-end justify-between mb-10 md:mb-16 gap-8">
                        <div className="text-center lg:text-left">
                            <h2 className="text-4xl md:text-5xl font-black tracking-tight text-gray-900 mb-4 uppercase">{t("destinations.heading")}</h2>
                            <p className="text-gray-500 text-lg max-w-xl lg:mx-0 mx-auto font-light">{t("destinations.subheading")}</p>
                        </div>
                        <div className="flex justify-center">
                            <div className="flex flex-wrap justify-center gap-1.5 p-1.5 bg-gray-100/50 rounded-xl overflow-hidden backdrop-blur-sm border border-gray-200 w-fit">
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
                    </div>

                    {/* 주의: relative + 고정 min-h로 로딩 overlay와 카드 그리드 높이를 동일하게 유지 */}
                    <div className="relative min-h-[300px] sm:min-h-[400px]">
                    <div className="relative min-h-[300px] sm:min-h-[400px]">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
                                {displayItems.map((place) => (
                                    <div 
                                        key={place.id}
                                        className="group bg-white rounded-2xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-xl transition-shadow duration-300 flex flex-col w-full h-full"
                                    >
                                        <div className="relative w-full aspect-[16/10] md:aspect-[4/3] lg:aspect-[16/10] overflow-hidden bg-gray-100 flex-shrink-0">
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
                                                    <span className="text-xs font-medium text-gray-400">{t("destinations.noImage")}</span>
                                                </div>
                                            )}
                                        </div>
                                        <div className="p-5 md:p-6 flex flex-col flex-1">
                                            <h3 className="text-lg md:text-xl font-bold text-gray-900 mb-2 line-clamp-1">{place.name}</h3>
                                            <div className="flex items-start gap-2 text-gray-500 text-xs mb-4">
                                                <MapPin size={14} className="text-gray-400 mt-0.5 flex-shrink-0" />
                                                <span className="line-clamp-2 leading-relaxed">{place.address}</span>
                                            </div>
                                            <div className="mt-auto pt-4 border-t border-gray-50 flex justify-end">
                                                <button
                                                    onClick={(e) => handlePlanTripClick(place, e)}
                                                    className="inline-flex items-center justify-center gap-2 bg-black text-white px-5 py-2.5 rounded-xl text-xs font-bold hover:bg-gray-800 transition-all active:scale-95 shadow-lg z-10 relative whitespace-nowrap"
                                                >
                                                    <CalendarPlus size={14} />
                                                    {t("destinations.planTrip")}
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
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
