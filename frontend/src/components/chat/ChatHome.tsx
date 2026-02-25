"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Mic, User, Sparkles, Loader2 } from "lucide-react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { createRoom, fetchRoom, fetchRooms, sendChatMessage, UserProfile, ChatRoom, ChatMessage } from "@/services/api";

export function ChatHome() {
    const [rooms, setRooms] = useState<ChatRoom[]>([]);
    const [currentRoomId, setCurrentRoomId] = useState<number | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputText, setInputText] = useState("");
    const [isTyping, setIsTyping] = useState(false);
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const [isInitializing, setIsInitializing] = useState(true);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

    useEffect(() => {
        const initializeChat = async () => {
            try {
                const token = localStorage.getItem("access_token");
                if (!token) return;

                // Load user profile
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/users/me`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });

                if (res.ok) {
                    const data = await res.json();
                    setUserProfile(data);
                }

                // Load chat rooms
                const fetchedRooms = await fetchRooms();
                setRooms(fetchedRooms);

                if (fetchedRooms.length > 0) {
                    // Load the most recent room
                    const latestRoomId = fetchedRooms[0].id;
                    setCurrentRoomId(latestRoomId);
                    await loadRoomMessages(latestRoomId);
                } else {
                    // Create a new room if none exist
                    handleCreateNewRoom();
                }
            } catch (error) {
                console.error("Failed to initialize chat", error);
            } finally {
                setIsInitializing(false);
            }
        };

        initializeChat();
    }, []);

    const loadRoomMessages = async (roomId: number) => {
        try {
            const roomData = await fetchRoom(roomId);
            setMessages(roomData.messages || []);
        } catch (error) {
            console.error("Failed to load room messages", error);
        }
    };

    const handleCreateNewRoom = async () => {
        try {
            const newRoom = await createRoom("새로운 여행 계획");
            setRooms((prev) => [newRoom, ...prev]);
            setCurrentRoomId(newRoom.id);
            setMessages([]);
        } catch (error) {
            console.error("Failed to create a new room", error);
        }
    };

    const handleSendMessage = async () => {
        if (!inputText.trim() || !currentRoomId) return;

        const userText = inputText;
        setInputText("");
        setIsTyping(true);

        try {
            // Optimistically add user message to UI
            const optimisticUserMsg: ChatMessage = {
                id: Date.now(),
                room_id: currentRoomId,
                message: userText,
                role: "human",
                created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, optimisticUserMsg]);

            // Call API
            const botResponseMsg = await sendChatMessage(currentRoomId, userText);

            // The backend returns the bot's message. 
            // We should reload the room to ensure we have the persistent IDs, or just append it.
            // Appending is faster.
            setMessages((prev) => [...prev, botResponseMsg]);

        } catch (error) {
            console.error("Failed to send message", error);
            // Optionally, show an error message in the UI
        } finally {
            setIsTyping(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const displayName = userProfile?.nickname || userProfile?.name || "User";
    const displayImage = userProfile?.profile_picture || "";

    if (isInitializing) {
        return (
            <div className="flex w-full h-full items-center justify-center bg-white">
                <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-white relative">
            <header className="flex-none p-6 border-b border-gray-100 flex items-center justify-between bg-white/80 backdrop-blur-sm z-10 sticky top-0">
                <div>
                    <h2 className="text-xl font-serif font-medium text-gray-900 flex items-center gap-2">
                        New Trip Planning <Sparkles size={14} className="text-gray-400" />
                    </h2>
                    <p className="text-xs text-gray-400 font-medium tracking-wide flex items-center gap-2 mt-1">
                        <span>Current Room: {currentRoomId && rooms.find(r => r.id === currentRoomId)?.title || "새 채팅"}</span>
                        <button onClick={handleCreateNewRoom} className="px-2 py-0.5 border border-gray-200 rounded-md hover:bg-gray-50 text-[10px]">새로 시작</button>
                    </p>
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
                {messages.length === 0 && !isTyping && (
                    <div className="h-full flex flex-col items-center justify-center text-gray-400">
                        <Sparkles className="w-8 h-8 mb-4 opacity-50" />
                        <p className="text-sm font-medium">채팅을 시작해보세요!</p>
                    </div>
                )}

                {messages.map((msg) => (
                    <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`flex items-end gap-3 ${msg.role === "human" ? "flex-row-reverse" : "flex-row"}`}
                    >
                        <div className={`w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-full shadow-sm text-white text-xs ${msg.role === "human" ? "bg-gray-900" : "bg-black"}`}>
                            {msg.role === "human" ? (
                                userProfile?.profile_picture ? (
                                    <img src={userProfile.profile_picture} className="w-full h-full object-cover rounded-full grayscale" alt="User" />
                                ) : (
                                    <User size={14} />
                                )
                            ) : (
                                <span className="font-serif italic text-sm">T</span>
                            )}
                        </div>
                        <div className={`max-w-[75%] md:max-w-[60%] p-4 text-[13px] leading-relaxed shadow-sm ${msg.role === "human" ? "bg-gray-900 text-white rounded-[24px] rounded-br-sm" : "bg-white border border-gray-100 text-gray-800 rounded-[24px] rounded-bl-sm"}`}>
                            {/* Simple text rendering for now. In reality you might want React Markdown for AI output. */}
                            <div className="whitespace-pre-wrap">{msg.message}</div>
                            <div className={`text-[9px] mt-2 font-medium opacity-50 ${msg.role === "human" ? "text-gray-400 text-right" : "text-gray-400"}`}>
                                {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </div>
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
                            disabled={!inputText.trim() || isTyping}
                            className={`p-2 rounded-full transition-all duration-300 shadow-md ${inputText.trim() && !isTyping ? "bg-black text-white hover:scale-105" : "bg-gray-200 text-gray-400 cursor-not-allowed"}`}
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

