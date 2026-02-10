"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus, MessageSquare, Settings } from "lucide-react";

export default function Sidebar() {
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <div
            className={`relative flex flex-col h-screen bg-gray-900 text-white transition-all duration-300 ease-in-out ${isExpanded ? "w-64" : "w-16"
                }`}
            onMouseEnter={() => setIsExpanded(true)}
            onMouseLeave={() => setIsExpanded(false)}
        >
            <div className="flex flex-col flex-1 p-2 gap-4">
                {/* New Chat Button */}
                <button
                    className={`flex items-center justify-center p-3 rounded-lg text-white hover:bg-gray-700 transition-colors ${isExpanded ? "bg-gray-800" : ""
                        }`}
                    title="새로운 채팅"
                >
                    <Plus size={24} />
                    {isExpanded && <span className="ml-3 font-medium whitespace-nowrap">새로운 채팅</span>}
                </button>

                {/* Separator */}
                <div className="border-t border-gray-700 my-2" />

                {/* Navigation Items (Example) */}
                <nav className="flex flex-col gap-2">
                    <Link
                        href="/"
                        className="flex items-center p-3 rounded-lg hover:bg-gray-800 transition-colors"
                        title="홈"
                    >
                        <MessageSquare size={24} />
                        {isExpanded && <span className="ml-3 whitespace-nowrap">이전 채팅 내역 1</span>}
                    </Link>
                    <Link
                        href="/"
                        className="flex items-center p-3 rounded-lg hover:bg-gray-800 transition-colors"
                        title="설정"
                    >
                        <Settings size={24} />
                        {isExpanded && <span className="ml-3 whitespace-nowrap">설정</span>}
                    </Link>
                </nav>
            </div>
        </div>
    );
}
