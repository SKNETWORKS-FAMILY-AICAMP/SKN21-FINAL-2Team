"use client";

import { Home, Grid, Bookmark, Settings, LogOut, Edit3, MessageSquare } from "lucide-react";
import { cn } from "../../utils";
import { Logo } from "@/components/Logo";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchRooms, fetchCurrentUser, ChatRoom } from "@/services/api";

interface UserProfile {
    name: string;
    nickname: string;
    profile_picture: string | null;
}

export function Sidebar() {
    const router = useRouter();
    const pathname = usePathname();
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const [rooms, setRooms] = useState<ChatRoom[]>([]);
    const [isCollapsed, setIsCollapsed] = useState(false);

    const canCollapse = pathname === "/explore";
    const actuallyCollapsed = isCollapsed && canCollapse;

    useEffect(() => {
        const fetchSidebarData = async () => {
            try {
                const token = localStorage.getItem("access_token");
                if (!token) return;

                // Load user profile and rooms in parallel
                const userData: any = await fetchCurrentUser();
                const roomsData = await fetchRooms();

                setUserProfile({
                    name: userData.name || "User",
                    nickname: userData.nickname || "User",
                    profile_picture: userData.profile_picture || null,
                });

                // Sort rooms to show the latest first if they aren't already
                setRooms(roomsData || []);
            } catch (error) {
                console.error("Failed to fetch sidebar data", error);
            }
        };

        fetchSidebarData();
    }, []);

    const menuItems = [
        { icon: Home, label: "Home", path: "/explore" },
        { icon: Grid, label: "Collection", path: "/collection" },
        { icon: Bookmark, label: "Bookmark", path: "/bookmark" },
    ];

    const handleSignOut = () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
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
                        onClick={() => router.push("/chatbot")}
                        className={cn(
                            "flex items-center transition-all duration-300 group bg-black text-white hover:bg-gray-800 shadow-md",
                            actuallyCollapsed
                                ? "p-3 rounded-2xl"
                                : "w-full justify-between gap-3 px-4 py-3 rounded-2xl text-[13px] font-medium"
                        )}
                        title={actuallyCollapsed ? "New Chat" : undefined}
                    >
                        {actuallyCollapsed ? (
                            <Edit3 size={16} strokeWidth={1.5} />
                        ) : (
                            <div className="flex items-center gap-3">
                                <span className="tracking-wide">+ New Chat</span>
                            </div>
                        )}
                    </button>
                </div>

                {/* Chats History Section */}
                {!actuallyCollapsed ? (
                    <div className="pt-4 flex-1 min-h-0 overflow-y-auto custom-scrollbar">
                        <nav className="space-y-0.5">
                            {rooms.map((room) => (
                                <button
                                    key={room.id}
                                    onClick={() => router.push(`/chatbot?roomId=${room.id}`)}
                                    className={cn(
                                        "w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-300 truncate",
                                        "text-gray-500 hover:bg-gray-50 hover:text-gray-900"
                                    )}
                                >
                                    <MessageSquare size={14} className="flex-shrink-0 opacity-50" />
                                    <span className="truncate">{room.title}</span>
                                </button>
                            ))}
                        </nav>
                    </div>
                ) : (
                    <div className="pt-4 flex flex-col items-center">
                        <button
                            onClick={() => setIsCollapsed(false)}
                            className="p-3 text-gray-400 hover:text-black hover:bg-gray-50 rounded-2xl transition-colors"
                            title="Recent Chats"
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
                    title={actuallyCollapsed ? "Profile" : undefined}
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
                            Sign out
                        </button>
                    </div>
                ) : (
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            handleSignOut();
                        }}
                        className="p-3 flex items-center justify-center rounded-2xl text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors w-full"
                        title="Sign out"
                    >
                        <LogOut size={16} strokeWidth={1.5} />
                    </button>
                )}
            </div>
        </aside>
    );
}
