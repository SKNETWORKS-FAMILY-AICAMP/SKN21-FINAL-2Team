"use client";

import { Home, Grid, Bookmark, Settings, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/Logo";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";

interface UserProfile {
    name: string;
    nickname: string;
    profile_picture: string | null;
}

export function Sidebar() {
    const router = useRouter();
    const pathname = usePathname();
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);

    useEffect(() => {
        const fetchUserProfile = async () => {
            try {
                const token = localStorage.getItem("access_token");
                if (!token) return;

                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/users/me`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });

                if (res.ok) {
                    const data = await res.json();
                    setUserProfile({
                        name: data.name,
                        nickname: data.nickname,
                        profile_picture: data.profile_picture,
                    });
                }
            } catch (error) {
                console.error("Failed to fetch user profile", error);
            }
        };

        fetchUserProfile();
    }, []);

    const menuItems = [
        { icon: Home, label: "Home", path: "/chatbot" },
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
        <aside className="w-64 h-full bg-white flex flex-col border-r border-gray-200 rounded-lg">
            {/* Logo Area */}
            <div className="p-6 pb-2">
                <Logo />
            </div>

            {/* Navigation */}
            <div className="px-3 flex-1 mt-8">
                <nav className="space-y-1">
                    {menuItems.map((item) => (
                        <button
                            key={item.path}
                            onClick={() => router.push(item.path)}
                            className={cn(
                                "w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-[13px] font-medium transition-all duration-300 group relative",
                                pathname === item.path
                                    ? "text-black bg-gray-100 shadow-sm"
                                    : "text-gray-500 hover:bg-gray-50 hover:text-gray-900",
                            )}
                        >
                            {pathname === item.path && (
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
                            <span className="tracking-wide">{item.label}</span>
                        </button>
                    ))}
                </nav>
            </div>

            {/* User Profile */}
            <div className="p-3 mt-auto border-t border-gray-100">
                <div
                    onClick={() => router.push("/mypage")}
                    className={cn(
                        "flex items-center justify-between group cursor-pointer p-3 rounded-2xl transition-all duration-300",
                        pathname === "/mypage" ? "bg-gray-100 shadow-sm" : "hover:bg-gray-50",
                    )}
                >
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full overflow-hidden flex items-center justify-center bg-gray-200 text-gray-400 font-bold text-xs ring-2 ring-white shadow-sm grayscale-[20%]">
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
                        <div className="flex flex-col">
                            <span className="text-[13px] font-semibold text-gray-900 leading-tight truncate w-32">{displayName}</span>
                        </div>
                    </div>
                    <Settings
                        size={14}
                        className={cn(
                            "transition-colors",
                            pathname === "/mypage" ? "text-black" : "text-gray-400 group-hover:text-black",
                        )}
                    />
                </div>

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
            </div>
        </aside>
    );
}
