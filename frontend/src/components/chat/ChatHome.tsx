"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Mic, MicOff, Square, User, Sparkles, Loader2 } from "lucide-react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { createRoom, fetchRoom, fetchRooms, sendChatMessageStream, UserProfile, ChatRoom, ChatMessage, fetchCurrentUser, verifyAndRefreshToken } from "@/services/api";
import { PipelineProgress, PipelineSteps, StepStatus, createInitialPipelineSteps } from "./PipelineProgress";
import { useSearchParams, useRouter } from "next/navigation";
import ReactMarkdown from 'react-markdown';
import { TripContextModal, type TripContext } from "@/components/chat/TripContextModal";
import remarkGfm from 'remark-gfm';

export function ChatHome() {
    type SttPermissionState = "unknown" | "prompt" | "granted" | "denied" | "unsupported";

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
    const [isListening, setIsListening] = useState(false);
    const [showTripModal, setShowTripModal] = useState(false);
    const [isTripLoading, setIsTripLoading] = useState(false);
    const [sttPermission, setSttPermission] = useState<SttPermissionState>("unknown");
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const recognitionRef = useRef<SpeechRecognition | null>(null);
    const micPermissionStatusRef = useRef<PermissionStatus | null>(null);

    const getSpeechRecognitionAPI = () =>
        (window.SpeechRecognition || window.webkitSpeechRecognition) as SpeechRecognitionConstructor | undefined;

    const syncMicPermission = useCallback(async () => {
        const SpeechRecognitionAPI = getSpeechRecognitionAPI();
        if (!SpeechRecognitionAPI) {
            setSttPermission("unsupported");
            return;
        }

        if (!navigator.permissions?.query) {
            setSttPermission((prev) => (prev === "unknown" || prev === "unsupported" ? "prompt" : prev));
            return;
        }

        try {
            const status = await navigator.permissions.query({ name: "microphone" as PermissionName });
            if (status.state === "granted") setSttPermission("granted");
            else if (status.state === "denied") setSttPermission("denied");
            else setSttPermission("prompt");

            if (micPermissionStatusRef.current && micPermissionStatusRef.current !== status) {
                micPermissionStatusRef.current.onchange = null;
            }
            status.onchange = () => { void syncMicPermission(); };
            micPermissionStatusRef.current = status;
        } catch {
            setSttPermission((prev) => (prev === "unknown" || prev === "unsupported" ? "prompt" : prev));
        }
    }, []);

    // 음성 인식(STT) 토글 핸들러
    const handleToggleListening = useCallback(async () => {
        // 이미 녹음 중이면 중지
        if (isListening && recognitionRef.current) {
            recognitionRef.current.stop();
            setIsListening(false);
            return;
        }

        // Web Speech API 지원 확인
        const SpeechRecognitionAPI = getSpeechRecognitionAPI();

        if (!SpeechRecognitionAPI) {
            setSttPermission("unsupported");
            alert("이 브라우저는 음성 인식을 지원하지 않습니다. Chrome 브라우저를 사용해주세요.");
            return;
        }

        // 녹음 시작 시점의 기존 입력 텍스트를 기준점으로 저장
        const baseText = inputText;

        // 음성 인식 시작
        const recognition = new SpeechRecognitionAPI();
        recognition.lang = "ko-KR";
        recognition.interimResults = true;
        recognition.continuous = true;
        recognition.maxAlternatives = 1;
        recognitionRef.current = recognition;

        let finalTranscript = "";

        recognition.onstart = () => {
            setIsListening(true);
            setSttPermission("granted");
        };

        recognition.onresult = (event: SpeechRecognitionEvent) => {
            let interim = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interim += transcript;
                }
            }
            // baseText 위에 최종 + 중간 결과를 덮어쓰기 (중복 방지)
            const separator = baseText && !baseText.endsWith(" ") ? " " : "";
            setInputText(baseText + separator + finalTranscript + interim);
        };

        recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
            console.error("Speech recognition error:", event.error);
            if (event.error === "not-allowed" || event.error === "service-not-allowed") {
                setSttPermission("denied");
            }
            setIsListening(false);
        };

        recognition.onend = () => {
            setIsListening(false);
            recognitionRef.current = null;
            // 최종 결과만 남기도록: 중간 결과 제거하고 baseText + finalTranscript만 유지
            const separator = baseText && !baseText.endsWith(" ") ? " " : "";
            setInputText((baseText + separator + finalTranscript).trim());
        };

        try {
            recognition.start();
        } catch (error) {
            console.error("Speech recognition start failed:", error);
            setIsListening(false);
            await syncMicPermission();
        }
    }, [isListening, inputText, syncMicPermission]);

    // 컴포넌트 언마운트 시 음성 인식 정리
    useEffect(() => {
        syncMicPermission();

        const onFocus = () => { void syncMicPermission(); };
        const onVisibilityChange = () => {
            if (document.visibilityState === "visible") {
                void syncMicPermission();
            }
        };

        window.addEventListener("focus", onFocus);
        document.addEventListener("visibilitychange", onVisibilityChange);

        return () => {
            if (recognitionRef.current) {
                recognitionRef.current.stop();
            }
            const cleanupStatus = micPermissionStatusRef.current;
            if (cleanupStatus) {
                cleanupStatus.onchange = null;
            }
            window.removeEventListener("focus", onFocus);
            document.removeEventListener("visibilitychange", onVisibilityChange);
        };
    }, [syncMicPermission]);

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
                    const auth = await verifyAndRefreshToken();
                    if (auth.refreshed) {
                        window.location.reload();
                        return;
                    }
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
                    // 방이 없을 때(첫 방문) → 여행 컨텍스트 모달을 먼저 표시
                    setShowTripModal(true);
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
            window.dispatchEvent(new CustomEvent("triver:rooms-updated"));
            router.replace(`/chatbot?roomId=${newRoom.id}`);
        } catch (error) {
            console.error("Failed to create a new room", error);
        }
    };

    // 모달에서 컨텍스트 확인 후 방 생성 (첫 방문 시)
    const handleCreateRoomWithContext = async (context: TripContext) => {
        // 주의: 모달을 즉시 닫지 않고 로딩 스피너 표시 → router.replace 시 자연 unmount
        setIsTripLoading(true);
        try {
            const newRoom = await createRoom("새로운 여행 계획");
            setRooms((prev) => [newRoom, ...prev]);
            setCurrentRoomId(newRoom.id);
            setMessages([]);
            if (context.travelDuration || context.groupSize) {
                localStorage.setItem(
                    `triver:trip-context:${newRoom.id}`,
                    JSON.stringify(context)
                );
            }
            window.dispatchEvent(new CustomEvent("triver:rooms-updated"));
            router.replace(`/chatbot?roomId=${newRoom.id}`);
        } catch (error) {
            console.error("Failed to create a new room with context", error);
            setIsTripLoading(false);
            setShowTripModal(false);
            // 에러 시 컨텍스트 없이 기본 방 생성
            handleCreateNewRoom();
        }
    };

    const handleSendMessage = async () => {
        if (!inputText.trim() || !currentRoomId) return;

        // 첫 번째 메시지일 때 저장된 여행 컨텍스트를 AI 메시지 앞에 부착
        let userText = inputText;
        if (messages.length === 0) {
            const ctxRaw = localStorage.getItem(`triver:trip-context:${currentRoomId}`);
            if (ctxRaw) {
                try {
                    const ctx = JSON.parse(ctxRaw) as TripContext;
                    if (ctx.travelDuration || ctx.groupSize) {
                        userText = `[여행 정보 - 기간: ${ctx.travelDuration || "미정"}, 인원: ${ctx.groupSize || "미정"}]\n\n${inputText}`;
                    }
                } catch { /* 컨텍스트 파싱 실패 시 무시 */ }
                // 주의: 사용한 컨텍스트는 삭제해서 다음 메시지에 중복 적용되지 않도록
                localStorage.removeItem(`triver:trip-context:${currentRoomId}`);
            }
        }
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
                onRoomTitle: (roomTitle) => {
                    // Intent 완료 직후 즉시 제목 업데이트 (파이프라인 완료 전)
                    setRooms(prev => prev.map(r =>
                        r.id === currentRoomId ? { ...r, title: roomTitle } : r
                    ));
                    window.dispatchEvent(new CustomEvent("triver:rooms-updated"));
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
    const micButtonClass = isListening
        ? "text-white bg-red-500 hover:bg-red-600 shadow-[0_0_15px_rgba(239,68,68,0.5)]"
        : sttPermission === "denied"
            ? "text-red-600 bg-red-50 border border-red-200 hover:bg-red-100"
            : sttPermission === "unsupported"
                ? "text-gray-300 bg-gray-100 cursor-not-allowed"
                : "text-gray-400 hover:text-black hover:bg-gray-100";

    const micButtonTitle = isListening
        ? "음성 인식 중지"
        : sttPermission === "denied"
            ? "마이크 권한 거부됨 - 다시 시도"
            : sttPermission === "unsupported"
                ? "브라우저 미지원"
                : "음성으로 입력";

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
                        {currentRoomId && rooms.find(r => r.id === currentRoomId)?.title || "New Trip Planning"} <Sparkles size={14} className="text-gray-400" />
                    </h2>
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
                        <button
                            onClick={handleToggleListening}
                            className={`p-2 rounded-full transition-all duration-300 relative ${micButtonClass}`}
                            title={micButtonTitle}
                            disabled={sttPermission === "unsupported"}
                        >
                            {isListening ? (
                                <>
                                    <Square size={14} fill="currentColor" strokeWidth={0} />
                                    <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white animate-pulse" />
                                </>
                            ) : sttPermission === "denied" ? (
                                <MicOff size={18} strokeWidth={1.5} />
                            ) : (
                                <Mic size={18} strokeWidth={1.5} />
                            )}
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

            {/* 주의: TripContextModal은 fixed 포지션으로 화면 전체를 덮습니다 */}
            <TripContextModal
                isOpen={showTripModal}
                onConfirm={handleCreateRoomWithContext}
                loading={isTripLoading}
                onClose={() => {
                    if (!isTripLoading) {
                        setShowTripModal(false);
                        // 건너뛰기 없이 그냥 닫으면 컨텍스트 없이 기본 방 생성으로 폴백
                        handleCreateNewRoom();
                    }
                }}
            />
        </div>
    );
}
