"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Mic, User, Sparkles } from "lucide-react";
import Image from "next/image";
import { motion } from "framer-motion";

interface Message {
    id: number;
    content: string;
    sender: "user" | "bot";
    timestamp: string;
}

interface UserProfile {
    name: string;
    nickname: string;
    profile_picture: string | null;
}

export function ChatHome() {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: 1,
            content: "Welcome to Triver. Where are we heading next?",
            sender: "bot",
            timestamp: "10:00 AM",
        },
    ]);
    const [inputText, setInputText] = useState("");
    const [isTyping, setIsTyping] = useState(false);
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

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

    const handleSendMessage = async () => {
        if (!inputText.trim()) return;

        const userMsg: Message = {
            id: Date.now(),
            content: inputText,
            sender: "user",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };

        setMessages((prev) => [...prev, userMsg]);
        setInputText("");
        setIsTyping(true);

        // 백엔드 API 호출 (실제 구현 시 연결)
        setTimeout(() => {
            const botMsg: Message = {
                id: Date.now() + 1,
                content: "백엔드 API와 연결 후 실제 응답이 표시됩니다.",
                sender: "bot",
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            };
            setMessages((prev) => [...prev, botMsg]);
            setIsTyping(false);
        }, 1500);
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const displayName = userProfile?.nickname || userProfile?.name || "User";
    const displayImage = userProfile?.profile_picture || "";

    return (
        <div className="flex flex-col h-full bg-white relative">
            <header className="flex-none p-6 border-b border-gray-100 flex items-center justify-between bg-white/80 backdrop-blur-sm z-10 sticky top-0">
                <div>
                    <h2 className="text-xl font-serif font-medium text-gray-900 flex items-center gap-2">
                        New Trip Planning <Sparkles size={14} className="text-gray-400" />
                    </h2>
                    <p className="text-xs text-gray-400 font-medium tracking-wide uppercase mt-1">Session #8821 • SEOUL</p>
                </div>
                <div className="flex -space-x-2">
                    <div className="w-8 h-8 bg-black text-white flex items-center justify-center text-xs font-serif italic border-2 border-white rounded-full shadow-sm">T</div>
                    <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-full overflow-hidden flex items-center justify-center bg-gray-200 text-gray-400 font-bold text-xs sm:text-sm ring-2 ring-white shadow-sm grayscale-[20%]">
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
                </div>
            </header>

            <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6 scroll-smooth">
                {messages.map((msg) => (
                    <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`flex items-end gap-3 ${msg.sender === "user" ? "flex-row-reverse" : "flex-row"}`}
                    >
                        <div className={`w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-full shadow-sm text-white text-xs ${msg.sender === "user" ? "bg-gray-900" : "bg-black"}`}>
                            {msg.sender === "user" ? (
                                userProfile?.profile_picture ? (
                                    <img src={userProfile.profile_picture} className="w-full h-full object-cover rounded-full grayscale" alt="User" />
                                ) : (
                                    <User size={14} />
                                )
                            ) : (
                                <span className="font-serif italic text-sm">T</span>
                            )}
                        </div>
                        <div className={`max-w-[75%] md:max-w-[60%] p-4 text-[13px] leading-relaxed shadow-sm ${msg.sender === "user" ? "bg-gray-900 text-white rounded-[24px] rounded-br-sm" : "bg-white border border-gray-100 text-gray-800 rounded-[24px] rounded-bl-sm"}`}>
                            {msg.content}
                            <div className={`text-[9px] mt-2 font-medium opacity-50 ${msg.sender === "user" ? "text-gray-400 text-right" : "text-gray-400"}`}>{msg.timestamp}</div>
                        </div>
                    </motion.div>
                ))}

                {isTyping && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex items-end gap-3">
                        <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-full bg-black text-white shadow-sm">
                            <span className="font-serif italic text-sm">T</span>
                        </div>
                        <div className="bg-white border border-gray-100 p-4 rounded-[24px] rounded-bl-sm flex gap-1 shadow-sm">
                            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></span>
                        </div>
                    </motion.div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="flex-none p-6 md:p-8 pt-2 bg-white/90 backdrop-blur-md">
                <div className="relative max-w-4xl mx-auto">
                    <textarea
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        onKeyDown={handleKeyPress}
                        placeholder="Ask Triver regarding your next destination..."
                        className="w-full bg-gray-50 border-0 text-gray-900 placeholder-gray-400 text-sm rounded-[28px] px-6 py-4 pr-32 focus:outline-none focus:ring-2 focus:ring-black/5 focus:bg-white resize-none h-[60px] shadow-sm transition-all duration-300"
                    />
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
                        <button className="p-2 text-gray-400 hover:text-black hover:bg-gray-100 rounded-full transition-colors">
                            <Mic size={18} strokeWidth={1.5} />
                        </button>
                        <button
                            onClick={handleSendMessage}
                            disabled={!inputText.trim()}
                            className={`p-2 rounded-full transition-all duration-300 shadow-md ${inputText.trim() ? "bg-black text-white hover:scale-105" : "bg-gray-200 text-gray-400 cursor-not-allowed"}`}
                        >
                            <Send size={16} strokeWidth={2} />
                        </button>
                    </div>
                </div>
                <p className="text-center text-[10px] text-gray-300 mt-3 font-medium">
                    Triver AI can make mistakes. Consider checking important information.
                </p>
            </div>
        </div>
    );
}
