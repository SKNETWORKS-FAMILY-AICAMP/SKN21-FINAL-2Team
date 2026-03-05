"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Mic, MicOff, Square, User, Sparkles, Loader2, Bookmark, Paperclip } from "lucide-react";
import { motion } from "framer-motion";
import { createRoom, fetchRoom, fetchRooms, sendAutoStartChatRoomStream, sendChatMessageStream, UserProfile, ChatRoom, ChatMessage, fetchCurrentUser, verifyAndRefreshToken, updatePlaceBookmark, updateRoomBookmark } from "@/services/api";
import { PipelineProgress, PipelineSteps, StepStatus, createInitialPipelineSteps } from "./PipelineProgress";
import { useSearchParams, useRouter } from "next/navigation";
import ReactMarkdown from 'react-markdown';
import { TripContextModal, type TripContext } from "@/components/chat/TripContextModal";
import remarkGfm from 'remark-gfm';

const DEFAULT_PLACEHOLDER = "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200&q=80";

export function ChatHome() {
    type SttPermissionState = "unknown" | "prompt" | "granted" | "denied" | "unsupported";
    type SelectedPlaceSeed = {
        id?: number;
        place_id?: number | null;
        name?: string | null;
        adress?: string | null;
        image_path?: string | null;
        room_id?: number;
    };

    const searchParams = useSearchParams();
    const router = useRouter();
    const roomIdParam = searchParams.get("roomId");
    // 주의: Destinations에서 비로그인 Plan Trip → 로그인 → 여기로 오는 경우
    // pendingDestination이 localStorage에 있으면 모달을 먼저 표시합니다
    const fromDestinationParam = searchParams.get("fromDestination");

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
    const [roomTripContext, setRoomTripContext] = useState<TripContext | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const recognitionRef = useRef<SpeechRecognition | null>(null);
    const micPermissionStatusRef = useRef<PermissionStatus | null>(null);
    const isSendingRef = useRef(false);
    const autoStartedRoomsRef = useRef<Set<number>>(new Set());

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
                } catch {
                    window.location.href = "/login";
                    return;
                }

                // Load chat rooms
                const fetchedRooms = await fetchRooms();
                setRooms(fetchedRooms);

                // fromDestination=1: Destinations에서 비로그인 Plan Trip 후 로그인한 경우
                // pendingDestination이 있으면 방 생성 전에 모달을 먼저 표시
                if (fromDestinationParam === "1" && localStorage.getItem("pendingDestination")) {
                    setShowTripModal(true);
                } else if (roomIdParam) {
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

    // 모달에서 컨텍스트 확인 후 방 생성 (첫 방문 또는 Destinations에서 온 경우)
    const handleCreateRoomWithContext = async (context: TripContext) => {
        // 주의: 모달을 즉시 닫지 않고 로딩 스피너 표시 → router.replace 시 자연 unmount
        setIsTripLoading(true);
        try {
            const newRoom = await createRoom("새로운 여행 계획");
            setRooms((prev) => [newRoom, ...prev]);
            setCurrentRoomId(newRoom.id);
            setMessages([]);

            // 주의: fromDestination 경로로 온 경우 pendingDestination을 챗봇 autostart 형식으로 변환
            // autostart는 triver:selected-places:${roomId} 키를 읽어 장소 기반 추천을 시작합니다
            const pendingRaw = localStorage.getItem("pendingDestination");
            if (pendingRaw) {
                try {
                    const place = JSON.parse(pendingRaw);
                    // Destination 타입 → SelectedPlaceSeed 배열로 변환
                    const seedPlaces = [{
                        name: place.name,
                        adress: place.address, // 주의: autostart API는 adress(오타) 필드를 사용합니다
                        place_id: typeof place.id === "number" ? place.id : 0,
                    }];
                    localStorage.setItem(`triver:selected-places:${newRoom.id}`, JSON.stringify(seedPlaces));
                } catch {
                    // 파싱 실패 시 무시
                } finally {
                    localStorage.removeItem("pendingDestination"); // 사용 후 정리
                }
            }

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

    const updateRoomTitle = useCallback((roomId: number, roomTitle: string) => {
        setRooms((prev) => prev.map((r) => (r.id === roomId ? { ...r, title: roomTitle } : r)));
        window.dispatchEvent(new CustomEvent("triver:rooms-updated"));
    }, []);

    const streamMessageToRoom = useCallback(async ({
        roomId,
        message,
        saveUserMessage,
        optimisticUserText,
    }: {
        roomId: number;
        message: string;
        saveUserMessage: boolean;
        optimisticUserText?: string;
    }) => {
        if (isSendingRef.current) return;
        isSendingRef.current = true;

        if (optimisticUserText) {
            const optimisticUserMsg: ChatMessage = {
                id: Date.now(),
                room_id: roomId,
                message: optimisticUserText,
                role: "human",
                created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, optimisticUserMsg]);
        }

        setIsTyping(true);
        setIsStreaming(true);
        setShowPipeline(true);
        setPipelineSteps(createInitialPipelineSteps());

        const streamingId = Date.now() + 1;
        setStreamingMsgId(streamingId);
        const placeholderAiMsg: ChatMessage = {
            id: streamingId,
            room_id: roomId,
            message: "",
            role: "ai",
            created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, placeholderAiMsg]);

        try {
            await sendChatMessageStream(roomId, message, {
                onToken: (token) => {
                    setShowPipeline(false);
                    setMessages((prev) => {
                        let found = false;
                        const next = prev.map((m) => {
                            if (m.id !== streamingId) return m;
                            found = true;
                            return { ...m, message: (m.message || "") + token };
                        });

                        if (!found) {
                            next.push({
                                id: streamingId,
                                room_id: roomId,
                                message: token,
                                role: "ai",
                                created_at: new Date().toISOString(),
                            });
                        }
                        return next;
                    });
                },
                onStep: (step, status) => {
                    if ((step === "executor" || step === "executor_missing") && status === "done") return;
                    const mappedStatus: StepStatus = status === "start" ? "running" : status as StepStatus;
                    setPipelineSteps((prev) => ({
                        ...prev,
                        [step]: mappedStatus,
                    }));
                },
                onDone: (fullMessage, messageId, createdAt, _roomTitle, places) => {
                    setShowPipeline(false);
                    const finalMessage = (fullMessage || "").trim() || "추천 결과를 준비했어요.";
                    setMessages((prev) => {
                        let found = false;
                        const next = prev.map((m) => {
                            if (m.id !== streamingId) return m;
                            found = true;
                            return {
                                ...m,
                                id: messageId,
                                message: finalMessage,
                                created_at: createdAt || m.created_at,
                                places: places,
                            };
                        });

                        if (!found) {
                            next.push({
                                id: messageId,
                                room_id: roomId,
                                message: finalMessage,
                                role: "ai",
                                created_at: createdAt || new Date().toISOString(),
                                places: places,
                            });
                        }
                        return next;
                    });
                    setStreamingMsgId(null);
                },
                onRoomTitle: (roomTitle) => {
                    updateRoomTitle(roomId, roomTitle);
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
            }, null, null, { saveUserMessage });
        } catch (error) {
            console.error("Failed to send streamed message", error);
        } finally {
            setIsTyping(false);
            setIsStreaming(false);
            isSendingRef.current = false;
        }
    }, [updateRoomTitle]);

    const runAutoStarterStream = useCallback(async ({
        roomId,
        payload,
    }: {
        roomId: number;
        payload: {
            mode: "trip_context" | "selected_places" | "combined" | "greeting";
            trip_context?: { travel_duration: string; adult_count: number; child_count: number };
            selected_places?: { name?: string | null; adress?: string | null; place_id?: number }[];
            save_user_message?: boolean;
        };
    }) => {
        if (isSendingRef.current) return;
        isSendingRef.current = true;
        setIsTyping(true);
        setIsStreaming(true);
        setShowPipeline(true);
        setPipelineSteps(createInitialPipelineSteps());

        const streamingId = Date.now() + 1;
        setStreamingMsgId(streamingId);
        setMessages((prev) => [
            ...prev,
            {
                id: streamingId,
                room_id: roomId,
                message: "",
                role: "ai",
                created_at: new Date().toISOString(),
            },
        ]);

        try {
            await sendAutoStartChatRoomStream(roomId, payload, {
                onToken: (token) => {
                    setShowPipeline(false);
                    setMessages((prev) => {
                        let found = false;
                        const next = prev.map((m) => {
                            if (m.id !== streamingId) return m;
                            found = true;
                            return { ...m, message: (m.message || "") + token };
                        });
                        if (!found) {
                            next.push({
                                id: streamingId,
                                room_id: roomId,
                                message: token,
                                role: "ai",
                                created_at: new Date().toISOString(),
                            });
                        }
                        return next;
                    });
                },
                onStep: (step, status) => {
                    if ((step === "executor" || step === "executor_missing") && status === "done") return;
                    const mappedStatus: StepStatus = status === "start" ? "running" : status as StepStatus;
                    setPipelineSteps((prev) => ({ ...prev, [step]: mappedStatus }));
                },
                onDone: (fullMessage, messageId, createdAt, _roomTitle, places) => {
                    setShowPipeline(false);
                    const finalMessage = (fullMessage || "").trim() || "추천 결과를 준비했어요.";
                    setMessages((prev) => {
                        let found = false;
                        const next = prev.map((m) => {
                            if (m.id !== streamingId) return m;
                            found = true;
                            return {
                                ...m,
                                id: messageId,
                                message: finalMessage,
                                created_at: createdAt || m.created_at,
                                places: places,
                            };
                        });
                        if (!found) {
                            next.push({
                                id: messageId,
                                room_id: roomId,
                                message: finalMessage,
                                role: "ai",
                                created_at: createdAt || new Date().toISOString(),
                                places: places,
                            });
                        }
                        return next;
                    });
                    setStreamingMsgId(null);
                },
                onRoomTitle: (roomTitle) => updateRoomTitle(roomId, roomTitle),
                onError: (err) => {
                    console.error("Auto start stream error", err);
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === streamingId ? { ...m, message: "죄송합니다. 오류가 발생했습니다." } : m
                        )
                    );
                },
            });
        } catch (error) {
            console.error("Failed to run auto start stream", error);
        } finally {
            setIsTyping(false);
            setIsStreaming(false);
            isSendingRef.current = false;
        }
    }, [updateRoomTitle]);

    useEffect(() => {
        if (!currentRoomId) {
            setRoomTripContext(null);
            return;
        }

        const raw = localStorage.getItem(`triver:trip-context:${currentRoomId}`);
        if (!raw) {
            setRoomTripContext(null);
            return;
        }

        try {
            const parsed = JSON.parse(raw) as TripContext;
            setRoomTripContext(parsed);
        } catch {
            setRoomTripContext(null);
        }
    }, [currentRoomId]);

    useEffect(() => {
        if (!currentRoomId || isInitializing || isStreaming) return;
        if (messages.length > 0) return;
        if (autoStartedRoomsRef.current.has(currentRoomId)) return;

        const contextKey = `triver:trip-context:${currentRoomId}`;
        const selectedKey = `triver:selected-places:${currentRoomId}`;
        const greetingKey = `triver:auto-start-greeting:${currentRoomId}`;
        const startedKey = `triver:auto-start-started:${currentRoomId}`;
        const legacyTripStartedKey = `triver:trip-context-started:${currentRoomId}`;
        const legacySelectedStartedKey = `triver:selected-places-started:${currentRoomId}`;

        if (
            localStorage.getItem(startedKey) === "1" ||
            localStorage.getItem(legacyTripStartedKey) === "1" ||
            localStorage.getItem(legacySelectedStartedKey) === "1"
        ) {
            localStorage.setItem(startedKey, "1");
            return;
        }

        const contextRaw = localStorage.getItem(contextKey);
        const selectedRaw = localStorage.getItem(selectedKey);
        const shouldGreeting = localStorage.getItem(greetingKey) === "1";

        let context: TripContext | null = null;
        if (contextRaw) {
            try {
                context = JSON.parse(contextRaw) as TripContext;
            } catch (error) {
                console.error("Invalid trip context payload", error);
            }
        }

        let selectedPlaces: SelectedPlaceSeed[] = [];
        if (selectedRaw) {
            try {
                const parsed = JSON.parse(selectedRaw) as SelectedPlaceSeed[];
                if (Array.isArray(parsed)) selectedPlaces = parsed;
            } catch (error) {
                console.error("Invalid selected places payload", error);
            }
        }

        const hasContext = !!context;
        const hasSelectedPlaces = selectedPlaces.length > 0;
        if (!hasContext && !hasSelectedPlaces && !shouldGreeting) return;

        autoStartedRoomsRef.current.add(currentRoomId);
        localStorage.setItem(startedKey, "1");

        if (hasContext && hasSelectedPlaces) {
            void runAutoStarterStream({
                roomId: currentRoomId,
                payload: {
                    mode: "combined",
                    trip_context: {
                        travel_duration: context?.travelDuration || "",
                        adult_count: context?.adultCount ?? 0,
                        child_count: context?.childCount ?? 0,
                    },
                    selected_places: selectedPlaces.map((p) => ({
                        name: p.name,
                        adress: p.adress,
                        place_id: p.place_id ?? 0,
                    })),
                    save_user_message: false,
                },
            });
            return;
        }

        if (hasSelectedPlaces) {
            void runAutoStarterStream({
                roomId: currentRoomId,
                payload: {
                    mode: "selected_places",
                    selected_places: selectedPlaces.map((p) => ({
                        name: p.name,
                        adress: p.adress,
                        place_id: p.place_id ?? 0,
                    })),
                    save_user_message: false,
                },
            });
            return;
        }

        if (hasContext) {
            void runAutoStarterStream({
                roomId: currentRoomId,
                payload: {
                    mode: "trip_context",
                    trip_context: {
                        travel_duration: context?.travelDuration || "",
                        adult_count: context?.adultCount ?? 0,
                        child_count: context?.childCount ?? 0,
                    },
                    save_user_message: false,
                },
            });
            return;
        }

        if (shouldGreeting) {
            void runAutoStarterStream({
                roomId: currentRoomId,
                payload: {
                    mode: "greeting",
                    save_user_message: false,
                },
            });
        }
    }, [currentRoomId, isInitializing, isStreaming, messages, runAutoStarterStream]);

    const handleSendMessage = async () => {
        if (!inputText.trim() || !currentRoomId) return;

        const userText = inputText;
        setInputText("");
        await streamMessageToRoom({
            roomId: currentRoomId,
            message: userText,
            saveUserMessage: true,
            optimisticUserText: userText,
        });
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        const nativeEvent = e.nativeEvent as unknown as { isComposing?: boolean; keyCode?: number };
        if (nativeEvent.isComposing || nativeEvent.keyCode === 229) return;
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const displayName = userProfile?.nickname || userProfile?.name || "User";
    const displayImage = userProfile?.profile_picture || "";
    const currentRoom = currentRoomId ? rooms.find((r) => r.id === currentRoomId) : null;

    const handleToggleRoomBookmark = async () => {
        if (!currentRoomId || !currentRoom) return;
        try {
            const updatedRoom = await updateRoomBookmark(currentRoomId, !currentRoom.bookmark_yn);
            setRooms((prev) => prev.map((room) => (
                room.id === currentRoomId
                    ? { ...room, bookmark_yn: updatedRoom.bookmark_yn }
                    : room
            )));
            window.dispatchEvent(new CustomEvent("triver:rooms-updated"));
        } catch (error) {
            console.error("Failed to toggle room bookmark", error);
        }
    };

    const handleTogglePlaceBookmark = async (messageId: number, placeId: number, currentStatus: boolean) => {
        try {
            const updatedPlace = await updatePlaceBookmark(placeId, !currentStatus);
            setMessages(prev => prev.map(m => {
                if (m.id === messageId && m.places) {
                    return {
                        ...m,
                        places: m.places.map(p => p.id === placeId ? { ...p, bookmark_yn: updatedPlace.bookmark_yn } : p)
                    };
                }
                return m;
            }));
        } catch (error) {
            console.error("Failed to toggle bookmark", error);
        }
    };

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
<<<<<<< HEAD
        <div className="flex flex-col h-full min-h-0 bg-white relative rounded-2xl overflow-hidden">
            <header className="h-14 flex items-center justify-between px-6 bg-white z-10 sticky top-0">
                <div className="flex items-center gap-2 min-w-0">
                    <Sparkles size={16} className="text-slate-900 flex-none" />
                    <span className="font-semibold text-[17px] tracking-tight text-slate-900 truncate">{currentRoom?.title || "Travel Assistant"}</span>
                    <button
                        type="button"
                        onClick={handleToggleRoomBookmark}
                        className={`inline-flex items-center justify-center rounded-full p-1 transition-colors ${
                            currentRoom?.bookmark_yn ? "text-yellow-500 bg-yellow-50" : "text-gray-300 hover:text-yellow-500 hover:bg-gray-100"
                        }`}
                        title="채팅방 북마크 토글"
                        disabled={!currentRoomId}
                    >
                        <Bookmark size={13} fill={currentRoom?.bookmark_yn ? "currentColor" : "none"} />
                    </button>
=======
        <div className="flex flex-col h-full bg-white relative">
            <header className="flex-none p-6 border-b border-gray-100 flex items-center justify-between bg-white/80 backdrop-blur-sm z-10 sticky top-0">
                <div>
                    <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                        {currentRoom?.title || "New Trip Planning"}
                        <button
                            type="button"
                            onClick={handleToggleRoomBookmark}
                            className={`inline-flex items-center justify-center rounded-full p-1.5 transition-colors ${currentRoom?.bookmark_yn ? "text-yellow-500 bg-yellow-50" : "text-gray-300 hover:text-yellow-500 hover:bg-gray-100"
                                }`}
                            title="채팅방 북마크 토글"
                            disabled={!currentRoomId}
                        >
                            <Bookmark size={14} fill={currentRoom?.bookmark_yn ? "currentColor" : "none"} />
                        </button>
                        <Sparkles size={14} className="text-gray-400" />
                    </h2>
                    {roomTripContext && (
                        <p className="mt-1 text-xs text-gray-500 font-medium">
                            {roomTripContext.travelDuration} · 성인 {roomTripContext.adultCount ?? 0}명 / 어린이 {roomTripContext.childCount ?? 0}명
                        </p>
                    )}
>>>>>>> c0a6d391b2dd2e98d19a39cb3a681bcfc156b896
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-xs text-emerald-600 font-medium flex items-center gap-1.5 bg-emerald-50 border border-emerald-100 rounded-full px-2.5 py-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                        Online
                    </span>
                    <div className="w-9 h-9 rounded-full overflow-hidden flex items-center justify-center bg-gray-200 text-gray-500 font-bold text-xs ring-2 ring-white shadow-sm grayscale-[20%]">
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

            {roomTripContext && (
                <div className="flex-none px-6 pb-2 bg-white">
                    <div className="rounded-2xl bg-gray-50 px-4 py-2 text-xs text-slate-600 border border-gray-100">
                        {roomTripContext.travelDuration} · 성인 {roomTripContext.adultCount ?? 0}명 / 어린이 {roomTripContext.childCount ?? 0}명
                    </div>
                </div>
            )}

            <div className="flex-1 min-h-0 overflow-y-auto p-0 pb-44 custom-scrollbar bg-gray-50/30">
                <div className="w-full min-h-full flex flex-col px-4 pt-2 space-y-6">
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

                    if (msg.role === "human") {
                        return (
                            <motion.div
                                key={msg.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex justify-end w-full px-4"
                            >
                                <div className="bg-black text-white px-5 py-3 rounded-2xl rounded-tr-sm max-w-[85%] md:max-w-[66%] shadow-sm">
                                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.message}</p>
                                    <div className="text-[9px] mt-2 font-medium text-gray-300/70 text-right">
                                        {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                    </div>
                                </div>
                            </motion.div>
                        );
                    }

                    return (
                        <div key={msg.id} className="flex flex-col gap-3 mb-2 w-full px-4">
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex items-start gap-3 w-full"
                            >
                                <div className="w-8 h-8 rounded-full bg-black flex items-center justify-center flex-shrink-0 shadow-sm mt-1">
                                    <Sparkles size={14} className="text-white" />
                                </div>

                                <div className="flex-1 min-w-0 w-full overflow-hidden md:max-w-[64%]">
                                    {!!msg.message && (
                                        <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-none px-5 py-4 shadow-sm inline-block w-full mb-3">
                                            <div className="prose prose-sm max-w-none prose-slate prose-p:my-3 prose-p:leading-7 prose-pre:bg-slate-50 prose-pre:text-slate-900">
                                                <ReactMarkdown
                                                    remarkPlugins={[remarkGfm]}
                                                    components={{
                                                        a: (props) => (
                                                            <a
                                                                {...props}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                            />
                                                        ),
                                                    }}
                                                >
                                                    {msg.message}
                                                </ReactMarkdown>
                                            </div>
                                        </div>
                                    )}

                                    {msg.places && msg.places.length > 0 && (
                                        <div className="mt-1 w-full">
                                            <h5 className="text-[11px] font-semibold text-slate-400 uppercase tracking-[0.08em] mb-2 ml-1">
                                                Recommended Places
                                            </h5>
                                            <div className="flex overflow-x-auto pb-3 gap-3 snap-x custom-scrollbar -mx-1 px-1">
                                                {msg.places.map((place) => (
                                                    <div
                                                        key={place.id}
                                                        className="snap-start flex-shrink-0 relative w-[176px] bg-white rounded-2xl overflow-hidden border border-gray-100 shadow-sm group"
                                                    >
                                                        <div className="relative h-[110px] bg-gray-100">
                                                            <img
                                                                src={place.image_path || DEFAULT_PLACEHOLDER}
                                                                alt={place.name || "Place image"}
                                                                className="absolute inset-0 m-0 w-full h-full object-cover object-center transition-transform duration-500 group-hover:scale-105"
                                                            />
                                                            <div className="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-transparent pointer-events-none" />
                                                            <button
                                                                onClick={() => handleTogglePlaceBookmark(msg.id, place.id, !!place.bookmark_yn)}
                                                                className={`absolute top-2 right-2 p-1.5 rounded-full transition-colors ${place.bookmark_yn ? "text-yellow-500 bg-yellow-50" : "text-gray-300 bg-white/90 hover:text-yellow-500 hover:bg-gray-100"}`}
                                                            >
                                                                <Bookmark size={13} fill={place.bookmark_yn ? "currentColor" : "none"} />
                                                            </button>
                                                        </div>
                                                        <div className="p-3">
                                                            <h4 className="font-semibold text-gray-900 leading-tight line-clamp-1 text-[12px]">
                                                                {place.name}
                                                            </h4>
                                                            <p className="text-[10px] text-gray-500 mt-1 line-clamp-1">{place.adress}</p>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    <div className="text-[9px] mt-2 font-medium opacity-50 text-gray-400">
                                        {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                    </div>
                                </div>
                            </motion.div>
                        </div>
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
            </div>

            <div className="absolute bottom-0 left-0 right-0 bg-white border-t border-gray-100 p-4 z-20">
                <div className="w-full mx-auto relative px-2">
                    <div className="flex items-end gap-2 bg-white border border-gray-200 rounded-[28px] p-2 pr-2 shadow-sm focus-within:ring-2 focus-within:ring-black/5 focus-within:border-gray-300 transition-all">
                        <button
                            type="button"
                            className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-200/50 transition-colors"
                            title="첨부 파일 (준비 중)"
                            disabled
                        >
                            <Paperclip size={20} />
                        </button>

                        <textarea
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            onKeyDown={handleKeyPress}
                            placeholder="Ask Triver regarding your next destination..."
                            className="flex-1 bg-transparent border-none outline-none resize-none py-3 max-h-[120px] text-sm text-gray-800 placeholder:text-gray-400 custom-scrollbar"
                            rows={1}
                            style={{ minHeight: "44px" }}
                        />

                        <button
                            onClick={handleToggleListening}
                            className={`p-2.5 rounded-full transition-all duration-300 relative ${micButtonClass}`}
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

                        <motion.button
                            initial={false}
                            animate={{ scale: inputText.trim() && !isTyping ? 1 : 0.98, opacity: 1 }}
                            onClick={handleSendMessage}
                            disabled={!inputText.trim() || isTyping}
                            className={`p-2.5 rounded-full transition-all duration-300 shadow-md ${inputText.trim() && !isTyping ? "bg-black text-white hover:bg-gray-800" : "bg-gray-200 text-gray-400 cursor-not-allowed"}`}
                        >
                            <Send size={18} />
                        </motion.button>
                    </div>

                    <p className="text-[10px] text-center text-gray-300 mt-2">
                        Triver AI can make mistakes. Please check important info.
                    </p>
                </div>
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
