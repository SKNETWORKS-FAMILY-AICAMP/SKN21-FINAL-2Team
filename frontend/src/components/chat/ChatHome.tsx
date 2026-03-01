"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Mic, User, Sparkles, Loader2 } from "lucide-react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { createRoom, fetchRoom, fetchRooms, sendChatMessageStream, UserProfile, ChatRoom, ChatMessage, fetchCurrentUser, verifyAndRefreshToken } from "@/services/api";
import { PipelineProgress, PipelineSteps, StepStatus, createInitialPipelineSteps } from "./PipelineProgress";
import { useSearchParams, useRouter } from "next/navigation";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function ChatHome() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const roomIdParam = searchParams.get("roomId");

    const [rooms, setRooms] = useState<ChatRoom[]>([]);
    const [currentRoomId, setCurrentRoomId] = useState<number | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputText, setInputText] = useState("");
    const [isTyping, setIsTyping] = useState(false);
    const [isStreaming, setIsStreaming] = useState(false);
    const [showPipeline, setShowPipeline] = useState(false);
    const [pipelineSteps, setPipelineSteps] = useState<PipelineSteps>(createInitialPipelineSteps());
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const [isInitializing, setIsInitializing] = useState(true);
    const [streamingMsgId, setStreamingMsgId] = useState<number | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

    // Re-run initialization or room switch when roomIdParam changes
    useEffect(() => {
        const initializeChat = async () => {
            setIsInitializing(true);
            try {
                // 토큰 유효성 검증 (만료 시 자동 refresh 시도)
                try {
                    await verifyAndRefreshToken();
                } catch {
                    window.location.href = "/login";
                    return;
                }

                // Load user profile
                try {
                    const data = await fetchCurrentUser();
                    setUserProfile(data);
                } catch (err) {
                    window.location.href = "/login";
                    return;
                }

                // Load chat rooms
                const fetchedRooms = await fetchRooms();
                setRooms(fetchedRooms);

                if (roomIdParam) {
                    const parsedRoomId = parseInt(roomIdParam, 10);
                    setCurrentRoomId(parsedRoomId);
                    await loadRoomMessages(parsedRoomId);
                } else if (fetchedRooms.length > 0) {
                    // Load the most recent room
                    const latestRoomId = fetchedRooms[0].id;
                    setCurrentRoomId(latestRoomId);
                    await loadRoomMessages(latestRoomId);
                    // Update URL without refreshing the page
                    router.replace(`/chatbot?roomId=${latestRoomId}`);
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
    }, [roomIdParam, router]);

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
        setIsStreaming(true);
        setShowPipeline(true);
        setPipelineSteps(createInitialPipelineSteps());

        // Optimistically add user message
        const optimisticUserMsg: ChatMessage = {
            id: Date.now(),
            room_id: currentRoomId,
            message: userText,
            role: "human",
            created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, optimisticUserMsg]);

        // AI 메시지를 빈 상태로 미리 추가 (토큰이 올 때마다 업데이트)
        const streamingId = Date.now() + 1;
        setStreamingMsgId(streamingId);
        const placeholderAiMsg: ChatMessage = {
            id: streamingId,
            room_id: currentRoomId,
            message: "",
            role: "ai",
            created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, placeholderAiMsg]);

        try {
            await sendChatMessageStream(currentRoomId, userText, {
                onToken: (token) => {
                    // 첫 토큰 수신 시 파이프라인 숨김
                    setShowPipeline(false);
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === streamingId
                                ? { ...m, message: m.message + token }
                                : m
                        )
                    );
                },
                onStep: (step, status) => {
                    // executor의 done은 무시 → 첫 토큰 도착까지 "답변 생성 중" 유지
                    if ((step === "executor" || step === "executor_missing") && status === "done") return;
                    // 백엔드 "start" → 프론트 "running" 매핑
                    const mappedStatus: StepStatus = status === "start" ? "running" : status as StepStatus;
                    setPipelineSteps((prev) => ({
                        ...prev,
                        [step]: mappedStatus,
                    }));
                },
                onDone: (_fullMessage, messageId, createdAt) => {
                    // 서버에서 확정된 ID와 타임스탬프로 교체
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === streamingId
                                ? { ...m, id: messageId, created_at: createdAt || m.created_at }
                                : m
                        )
                    );
                    setStreamingMsgId(null);
                },
                onError: (err) => {
                    console.error("Stream error", err);
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === streamingId
                                ? { ...m, message: "죄송합니다. 오류가 발생했습니다." }
                                : m
                        )
                    );
                },
            });
        } catch (error) {
            console.error("Failed to send message", error);
        } finally {
            setIsTyping(false);
            setIsStreaming(false);
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

                {messages.map((msg) => {
                    // 스트리밍 중 빈 AI 메시지는 숨김 (파이프라인만 보이도록)
                    if (isStreaming && msg.id === streamingMsgId && !msg.message && showPipeline) {
                        return null;
                    }
                    // 스트리밍 중 빈 AI 메시지는 숨김 (토큰 도착 후 보임)
                    if (isStreaming && msg.id === streamingMsgId && !msg.message) {
                        return null;
                    }

                    return (
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
                                {(() => {
                                    if (msg.role === "ai") {
                                        return (
                                            <div className="prose prose-sm max-w-none prose-slate prose-p:leading-relaxed prose-pre:bg-slate-50 prose-pre:text-slate-900">
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                    {msg.message}
                                                </ReactMarkdown>
                                            </div>
                                        );
                                    }
                                    return <div className="whitespace-pre-wrap">{msg.message}</div>;
                                })()}
                                <div className={`text-[9px] mt-2 font-medium opacity-50 ${msg.role === "human" ? "text-gray-400 text-right" : "text-gray-400"}`}>
                                    {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                </div>
                            </div>
                        </motion.div>
                    );
                })}

                {/* 파이프라인 진행 표시 — messages.map과 독립적으로 표시 */}
                {showPipeline && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="flex items-start gap-3"
                    >
                        <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-full bg-black text-white shadow-sm">
                            <span className="font-serif italic text-sm">T</span>
                        </div>
                        <PipelineProgress steps={pipelineSteps} visible={true} />
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

