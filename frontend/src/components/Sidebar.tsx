"use client";

import { Home, Grid, Bookmark, Settings, LogOut, Edit3, MessageSquare } from "lucide-react";
import { cn } from "../../utils";
import { Logo } from "@/components/Logo";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { fetchRooms, fetchCurrentUser, type ChatRoom, type UserProfile as ApiUserProfile, logoutApi, createRoom } from "@/services/api";
import { TripContextModal, type TripContext } from "@/components/chat/TripContextModal";
import { clearAuth } from "@/services/errorHandler";

interface SidebarUserProfile {
    name: string;
    nickname: string;
    profile_picture: string | null;
}

type AppLanguage = "en" | "ko" | "ja";

const LANGUAGE_STORAGE_KEY = "triver:language:v1";

const SIDEBAR_I18N: Record<AppLanguage, Record<string, string>> = {
    en: {
        home: "Home",
        collection: "Collection",
        bookmark: "Bookmark",
        newChat: "+ New Chat",
        recentChats: "Recent Chats",
        profile: "Profile",
        signOut: "Sign out",
    },
    ko: {
        home: "홈",
        collection: "컬렉션",
        bookmark: "북마크",
        newChat: "+ 새 채팅",
        recentChats: "최근 채팅",
        profile: "프로필",
        signOut: "로그아웃",
    },
    ja: {
        home: "ホーム",
        collection: "コレクション",
        bookmark: "ブックマーク",
        newChat: "+ 新規チャット",
        recentChats: "最近のチャット",
        profile: "プロフィール",
        signOut: "ログアウト",
    },
};

type SidebarCacheState = {
    userProfile: SidebarUserProfile | null;
    rooms: ChatRoom[];
    loaded: boolean;
    inFlight: Promise<void> | null;
};

const sidebarCache: SidebarCacheState = {
    userProfile: null,
    rooms: [],
    loaded: false,
    inFlight: null,
};

const toSidebarUserProfile = (userData: ApiUserProfile): SidebarUserProfile => ({
    name: userData.name || "User",
    nickname: userData.nickname || "User",
    profile_picture: userData.profile_picture || null,
});

const getSidebarSnapshot = () => ({
    userProfile: sidebarCache.userProfile,
    rooms: sidebarCache.rooms,
});

const fetchAndCacheSidebarData = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const [userData, roomsData] = await Promise.all([fetchCurrentUser(), fetchRooms()]);
    sidebarCache.userProfile = toSidebarUserProfile(userData);
    sidebarCache.rooms = roomsData || [];
    sidebarCache.loaded = true;
};

const ensureSidebarDataLoaded = async () => {
    if (sidebarCache.loaded) return;

    if (!sidebarCache.inFlight) {
        sidebarCache.inFlight = fetchAndCacheSidebarData().finally(() => {
            sidebarCache.inFlight = null;
        });
    }

    await sidebarCache.inFlight;
};

const refreshSidebarRooms = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const roomsData = await fetchRooms();
    sidebarCache.rooms = roomsData || [];
    sidebarCache.loaded = true;
};

const refreshSidebarUserProfile = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const userData = await fetchCurrentUser();
    sidebarCache.userProfile = toSidebarUserProfile(userData);
    sidebarCache.loaded = true;
};

const resetSidebarCache = () => {
    sidebarCache.userProfile = null;
    sidebarCache.rooms = [];
    sidebarCache.loaded = false;
    sidebarCache.inFlight = null;
};

function SidebarContent() {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const [userProfile, setUserProfile] = useState<SidebarUserProfile | null>(() => sidebarCache.userProfile);
    const [rooms, setRooms] = useState<ChatRoom[]>(() => sidebarCache.rooms);
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [language, setLanguage] = useState<AppLanguage>("en");
    const [showTripModal, setShowTripModal] = useState(false);
    const [isTripLoading, setIsTripLoading] = useState(false);

    const canCollapse = true;
    const actuallyCollapsed = isCollapsed;

    const activeRoomIdParam = searchParams.get("roomId");
    const parsedActiveRoomId = activeRoomIdParam ? Number(activeRoomIdParam) : NaN;
    const activeRoomId = Number.isFinite(parsedActiveRoomId) ? parsedActiveRoomId : null;

    const handleAuthFailure = (error: unknown) => {
        if (!(error instanceof Error)) return;
        if (error?.message === "Unauthorized" || error?.message === "Session expired") {
            clearAuth();
            window.location.href = "/login";
        }
    };

    useEffect(() => {
        let cancelled = false;

        const applyLanguage = () => {
            const raw = localStorage.getItem(LANGUAGE_STORAGE_KEY);
            if (raw === "en" || raw === "ko" || raw === "ja") {
                setLanguage(raw);
            } else {
                setLanguage("en");
            }
        };
        applyLanguage();

        const onLang = () => applyLanguage();
        window.addEventListener("triver:language", onLang);

        const hydrateSidebar = async () => {
            try {
                await ensureSidebarDataLoaded();
                if (cancelled) return;

                const snapshot = getSidebarSnapshot();
                setUserProfile(snapshot.userProfile);
                setRooms(snapshot.rooms);
            } catch (error: unknown) {
                console.error("Failed to fetch sidebar data", error);
                handleAuthFailure(error);
            }
        };
        void hydrateSidebar();

        // ChatHome에서 방 생성/제목 변경 시 목록 갱신
        const onRoomsUpdated = async () => {
            try {
                await refreshSidebarRooms();
                if (cancelled) return;
                const snapshot = getSidebarSnapshot();
                setRooms(snapshot.rooms);
            } catch (error: unknown) {
                console.error("Failed to refresh rooms", error);
                handleAuthFailure(error);
            }
        };
        window.addEventListener("triver:rooms-updated", onRoomsUpdated);

        const onProfileUpdated = async () => {
            try {
                await refreshSidebarUserProfile();
                if (cancelled) return;
                const snapshot = getSidebarSnapshot();
                setUserProfile(snapshot.userProfile);
            } catch (error: unknown) {
                console.error("Failed to refresh sidebar profile", error);
                handleAuthFailure(error);
            }
        };
        window.addEventListener("triver:profile-updated", onProfileUpdated);

        return () => {
            cancelled = true;
            window.removeEventListener("triver:language", onLang);
            window.removeEventListener("triver:rooms-updated", onRoomsUpdated);
            window.removeEventListener("triver:profile-updated", onProfileUpdated);
        };
    }, []);

    const dict = SIDEBAR_I18N[language] ?? SIDEBAR_I18N.en;

    const menuItems = [
        { icon: Home, label: dict.home, path: "/explore" },
        { icon: Grid, label: dict.collection, path: "/collection" },
        { icon: Bookmark, label: dict.bookmark, path: "/bookmark" },
    ];

    // + 새 채팅 버튼 클릭 → 모달에서 컨텍스트 수집 후 방 생성
    const handleModalConfirm = async (context: TripContext) => {
        // 주의: 모달을 즉시 닫지 않고 로딩 스피너 표시 → API 완료 후 페이지 전환 시 자연 unmount
        setIsTripLoading(true);
        try {
            const newRoom = await createRoom("새로운 여행 계획");
            setRooms((prev) => {
                const next = [newRoom, ...prev];
                sidebarCache.rooms = next;
                sidebarCache.loaded = true;
                return next;
            });
            if ((context.travelDuration || "").trim()) {
                localStorage.setItem(
                    `triver:trip-context:${newRoom.id}`,
                    JSON.stringify(context)
                );
            } else {
                localStorage.setItem(`triver:auto-start-greeting:${newRoom.id}`, "1");
            }
            setShowTripModal(false);
            setIsTripLoading(false);
            // router.push 이후 페이지가 전환되면 컴포넌트가 unmount되므로
            // setShowTripModal(false)를 수동초출할 필요 없음
            router.push(`/chatbot?roomId=${newRoom.id}`);
        } catch (e) {
            console.error("Failed to create room from sidebar", e);
            setIsTripLoading(false);
            setShowTripModal(false);
            router.push("/chatbot");
        }
    };

    const handleSignOut = async () => {
        await logoutApi();
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        resetSidebarCache();
        router.push("/");
    };

    const displayName = userProfile?.nickname || userProfile?.name || "User";
    const displayImage = userProfile?.profile_picture || "";

    return (
        <aside className={cn(
            "h-full bg-white flex flex-col border-r border-gray-200 rounded-lg transition-all duration-300 relative",
            actuallyCollapsed ? "w-[80px]" : "w-64"
        )}>
            {/* Collapse Toggle Button - Only visible if we can collapse */}
            {canCollapse && (
                <button
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="absolute -right-3 top-8 bg-white border border-gray-200 rounded-full p-1 shadow-sm z-10 hover:bg-gray-50 text-gray-400 hover:text-black transition-colors"
                >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={cn("transition-transform duration-300", isCollapsed ? "rotate-180" : "")}>
                        <path d="M15 18l-6-6 6-6" />
                    </svg>
                </button>
            )}

            {/* Logo Area */}
            <div className={cn("p-6 pb-2 transition-all duration-300", actuallyCollapsed ? "px-0 flex justify-center mt-2" : "")}>
                {!actuallyCollapsed ? (
                    <Logo />
                ) : (
                    <div className="w-10 h-10 rounded-xl bg-black flex items-center justify-center text-white font-bold text-xl cursor-pointer">P</div>
                )}
            </div>

            {/* Navigation */}
            <div className={cn("mt-6 space-y-4 flex flex-col flex-1 min-h-0", actuallyCollapsed ? "px-2" : "px-3")}>
                {/* Main Tabs */}
                <nav className="space-y-1">
                    {menuItems.map((item) => (
                        <button
                            key={item.path}
                            onClick={() => router.push(item.path)}
                            className={cn(
                                "flex items-center transition-all duration-300 group relative",
                                actuallyCollapsed
                                    ? "w-full justify-center p-3 rounded-2xl"
                                    : "w-full gap-3 px-4 py-3 rounded-2xl text-[13px] font-medium",
                                pathname === item.path
                                    ? "text-black bg-gray-100 shadow-sm"
                                    : "text-gray-500 hover:bg-gray-50 hover:text-gray-900",
                            )}
                            title={actuallyCollapsed ? item.label : undefined}
                        >
                            {pathname === item.path && !actuallyCollapsed && (
                                <div className="absolute right-3 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-black" />
                            )}
                            <item.icon
                                size={16}
                                strokeWidth={1.5}
                                className={cn(
                                    "transition-colors",
                                    pathname === item.path ? "text-black" : "text-gray-400 group-hover:text-gray-600",
                                )}
                            />
                            {!actuallyCollapsed && (
                                <span className="tracking-wide">{item.label}</span>
                            )}
                        </button>
                    ))}
                </nav>

                {/* New Chat Button */}
                <div className={cn("pt-2", actuallyCollapsed ? "flex justify-center" : "")}>
                    <button
                        onClick={() => setShowTripModal(true)}
                        className={cn(
                            "flex items-center transition-all duration-300 group bg-black text-white hover:bg-gray-800 shadow-md",
                            actuallyCollapsed
                                ? "p-3 rounded-2xl"
                                : "w-full justify-between gap-3 px-4 py-3 rounded-2xl text-[13px] font-medium"
                        )}
                        title={actuallyCollapsed ? dict.newChat : undefined}
                    >
                        {actuallyCollapsed ? (
                            <Edit3 size={16} strokeWidth={1.5} />
                        ) : (
                            <div className="flex items-center gap-3">
                                <span className="tracking-wide">{dict.newChat}</span>
                            </div>
                        )}
                    </button>
                </div>

                {/* Chats History Section */}
                {!actuallyCollapsed ? (
                    <div className="pt-4 flex-1 min-h-0 overflow-y-auto custom-scrollbar">
                        <nav className="space-y-0.5">
                            {rooms.map((room) => {
                                const isActiveRoom = pathname === "/chatbot" && activeRoomId === room.id;
                                return (
                                    <button
                                        key={room.id}
                                        onClick={() => router.push(`/chatbot?roomId=${room.id}`)}
                                        className={cn(
                                            "w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-300 truncate",
                                            isActiveRoom
                                                ? "bg-gray-100 text-black"
                                                : "text-gray-500 hover:bg-gray-50 hover:text-gray-900"
                                        )}
                                    >
                                        <MessageSquare
                                            size={14}
                                            className={cn(
                                                "flex-shrink-0",
                                                isActiveRoom ? "text-black opacity-100" : "opacity-50"
                                            )}
                                        />
                                        <span className="truncate">{room.title}</span>
                                    </button>
                                );
                            })}
                        </nav>
                    </div>
                ) : (
                    <div className="pt-4 flex flex-col items-center">
                        <button
                            onClick={() => setIsCollapsed(false)}
                            className="p-3 text-gray-400 hover:text-black hover:bg-gray-50 rounded-2xl transition-colors"
                            title={dict.recentChats}
                        >
                            <MessageSquare size={16} strokeWidth={1.5} />
                        </button>
                    </div>
                )}
            </div>

            {/* User Profile */}
            <div className={cn("mt-auto border-t border-gray-100", actuallyCollapsed ? "p-3 flex flex-col gap-2 items-center" : "p-3")}>
                <div
                    onClick={() => router.push("/mypage")}
                    className={cn(
                        "flex items-center group cursor-pointer transition-all duration-300 rounded-2xl",
                        pathname === "/mypage" ? "bg-gray-100 shadow-sm" : "hover:bg-gray-50",
                        actuallyCollapsed ? "justify-center p-2" : "justify-between p-3"
                    )}
                    title={actuallyCollapsed ? dict.profile : undefined}
                >
                    <div className="flex items-center gap-3 overflow-hidden">
                        <div className="w-9 h-9 flex-shrink-0 rounded-full overflow-hidden flex items-center justify-center bg-gray-200 text-gray-400 font-bold text-xs ring-2 ring-white shadow-sm grayscale-[20%]">
                            {displayImage ? (
                                <img
                                    src={displayImage}
                                    alt="Profile"
                                    className="w-full h-full object-cover"
                                />
                            ) : (
                                displayName.charAt(0).toUpperCase()
                            )}
                        </div>
                        {!actuallyCollapsed && (
                            <div className="flex flex-col min-w-0">
                                <span className="text-[13px] font-semibold text-gray-900 leading-tight truncate w-32">{displayName}</span>
                            </div>
                        )}
                    </div>
                    {!actuallyCollapsed && (
                        <Settings
                            size={14}
                            className={cn(
                                "flex-shrink-0 transition-colors ml-2",
                                pathname === "/mypage" ? "text-black" : "text-gray-400 group-hover:text-black",
                            )}
                        />
                    )}
                </div>

                {!actuallyCollapsed ? (
                    <div className="mt-2 px-2 flex items-center justify-between text-[10px] text-gray-400 font-medium pt-2">
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                handleSignOut();
                            }}
                            className="flex items-center gap-1 hover:text-red-600 transition-colors"
                        >
                            <LogOut size={10} />
                            {dict.signOut}
                        </button>
                    </div>
                ) : (
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            handleSignOut();
                        }}
                        className="p-3 flex items-center justify-center rounded-2xl text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors w-full"
                        title={dict.signOut}
                    >
                        <LogOut size={16} strokeWidth={1.5} />
                    </button>
                )}
            </div>
            {/* 주의: 모달은 fixed 포지션이라 aside 안에 있어도 화면 전체를 덮습니다 */}
            <TripContextModal
                isOpen={showTripModal}
                onConfirm={handleModalConfirm}
                loading={isTripLoading}
                onClose={() => {
                    if (!isTripLoading) setShowTripModal(false);
                }}
            />
        </aside>
    );
}

export function Sidebar() {
    return (
        <Suspense
            fallback={
                <aside className="h-full w-64 bg-white border-r border-gray-200 rounded-lg animate-pulse" />
            }
        >
            <SidebarContent />
        </Suspense>
    );
}
