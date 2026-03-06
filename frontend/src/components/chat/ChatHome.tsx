"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { Send, Mic, MicOff, Square, User, Sparkles, Loader2, Bookmark, Paperclip, Map as MapIcon } from "lucide-react";
import { motion } from "framer-motion";
import { createRoom, fetchRoom, fetchRooms, sendAutoStartChatRoomStream, sendChatMessageStream, UserProfile, ChatRoom, ChatMessage, ChatPlaceItem, fetchCurrentUser, verifyAndRefreshToken, updatePlaceBookmark, updateRoomBookmark } from "@/services/api";
import { PipelineProgress, PipelineSteps, StepStatus, createInitialPipelineSteps } from "./PipelineProgress";
import { useSearchParams, useRouter } from "next/navigation";
import { TripContextModal, type TripContext } from "@/components/chat/TripContextModal";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { PlaceMapPanel, type ChatMapPlace, type ChatMapPlaceGroup } from "./PlaceMapPanel";
import { PlaceMapSheet } from "./PlaceMapSheet";
import { ChatMessageItem } from "./ChatMessageItem";
import { BrandMark } from "@/components/Logo";

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
    const [showTripModal, setShowTripModal] = useState(false);
    const [isTripLoading, setIsTripLoading] = useState(false);
    const [roomTripContext, setRoomTripContext] = useState<TripContext | null>(null);
    const [selectedMapPlaceId, setSelectedMapPlaceId] = useState<string | null>(null);
    const [isMapSheetOpen, setIsMapSheetOpen] = useState(false);
    const [attachedImageDataUrl, setAttachedImageDataUrl] = useState<string | null>(null);
    const [attachedFileName, setAttachedFileName] = useState<string>("");
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const placeCardRefs = useRef<Record<string, HTMLDivElement | null>>({});
    const fileInputRef = useRef<HTMLInputElement>(null);
    const inputTextareaRef = useRef<HTMLTextAreaElement>(null);
    const streamAbortControllerRef = useRef<AbortController | null>(null);
    const stopRequestedRef = useRef(false);
    const { isListening, sttPermission, handleToggleListening } = useSpeechRecognition({
        inputText,
        setInputText
    });

    const isSendingRef = useRef(false);
    const autoStartedRoomsRef = useRef<Set<number>>(new Set());

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

    useEffect(() => {
        const textarea = inputTextareaRef.current;
        if (!textarea) return;
        const maxHeight = 180;
        textarea.style.height = "auto";
        const nextHeight = Math.min(textarea.scrollHeight, maxHeight);
        textarea.style.height = `${nextHeight}px`;
        textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
    }, [inputText]);

    // Re-run initialization or room switch when roomIdParam changes
    useEffect(() => {
        const initializeChat = async () => {
            // 주의: 이미 보고 있는 방이라면 (방 생성 직후 라우팅으로 인한) 불필요한 전체 초기화를 막습니다.
            const paramId = roomIdParam ? parseInt(roomIdParam, 10) : null;
            if (paramId && paramId === currentRoomId) return;

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
                    window.location.href = "/signup";
                    return;
                }

                // Load user profile
                try {
                    const data = await fetchCurrentUser();

                    // 주의: 가입(is_join)이나 설문(is_prefer)을 완료하지 않고 챗봇 페이지로 억지로 진입한 경우 방어
                    if (!data.is_join) {
                        window.location.href = "/signup/profile";
                        return;
                    }
                    if (!data.is_prefer) {
                        window.location.href = "/survey";
                        return;
                    }

                    setUserProfile(data);
                } catch {
                    window.location.href = "/signup";
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

            // 주의: 빈 방 생성 시 기본 인사말 스트림을 띄우기 위해 로컬스토리지에 미리 세팅
            localStorage.setItem(`triver:auto-start-greeting:${newRoom.id}`, "1");

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

            // 주의: 상태(setCurrentRoomId)를 변경하기 전에 로컬 스토리지에 컨텍스트를 먼저 세팅해야,
            // 렌더링 후 실행되는 Autostart useEffect가 데이터를 문제없이 읽을 수 있습니다.
            const pendingRaw = localStorage.getItem("pendingDestination");
            if (pendingRaw) {
                try {
                    const place = JSON.parse(pendingRaw);
                    // Destination 타입 → SelectedPlaceSeed 배열로 변환
                    const seedPlaces = [{
                        name: place.name,
                        adress: place.address || place.adress, // API 응답에 따라 address 또는 adress 일 수 있음
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

            setRooms((prev) => [newRoom, ...prev]);
            setCurrentRoomId(newRoom.id);
            setMessages([]);

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
        imageDataUrl,
    }: {
        roomId: number;
        message: string;
        saveUserMessage: boolean;
        optimisticUserText?: string;
        imageDataUrl?: string | null;
    }) => {
        if (isSendingRef.current) return;
        isSendingRef.current = true;
        stopRequestedRef.current = false;
        const abortController = new AbortController();
        streamAbortControllerRef.current = abortController;

        if (optimisticUserText) {
            const optimisticUserMsg: ChatMessage = {
                id: Date.now(),
                room_id: roomId,
                message: optimisticUserText,
                role: "human",
                image_path: imageDataUrl ?? null,
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
            }, imageDataUrl ?? null, null, { saveUserMessage, signal: abortController.signal });
        } catch (error) {
            const isAbort =
                stopRequestedRef.current ||
                ((error as { name?: string })?.name === "AbortError");
            if (!isAbort) {
                console.error("Failed to send streamed message", error);
                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === streamingId
                            ? { ...m, message: "죄송합니다. 오류가 발생했습니다." }
                            : m
                    )
                );
            } else {
                setMessages((prev) =>
                    prev.filter((m) => !(m.id === streamingId && !(m.message || "").trim()))
                );
            }
        } finally {
            setIsTyping(false);
            setIsStreaming(false);
            setShowPipeline(false);
            setStreamingMsgId(null);
            isSendingRef.current = false;
            if (streamAbortControllerRef.current === abortController) {
                streamAbortControllerRef.current = null;
            }
            stopRequestedRef.current = false;
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

        // 주의: 만약 이미 메시지가 리스트에 있는데 넘겨줄(context/places) 데이터가 아무것도 없다면, 진짜 빈 일반 방이므로 실행 무시
        if (messages.length > 0 && !hasContext && !hasSelectedPlaces) {
            return;
        }

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
        if (!currentRoomId) return;
        const userText = inputText.trim();
        if (!userText && !attachedImageDataUrl) return;

        const messageToSend = userText || "첨부한 이미지를 분석해줘.";
        const optimisticText = userText || (attachedFileName ? `[이미지 첨부] ${attachedFileName}` : "[이미지 첨부]");
        const currentAttachment = attachedImageDataUrl;
        setInputText("");
        setAttachedImageDataUrl(null);
        setAttachedFileName("");
        await streamMessageToRoom({
            roomId: currentRoomId,
            message: messageToSend,
            saveUserMessage: true,
            optimisticUserText: optimisticText,
            imageDataUrl: currentAttachment,
        });
    };

    const handleStopMessage = () => {
        if (!isStreaming) return;
        stopRequestedRef.current = true;
        streamAbortControllerRef.current?.abort();
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        const nativeEvent = e.nativeEvent as unknown as { isComposing?: boolean; keyCode?: number };
        if (nativeEvent.isComposing || nativeEvent.keyCode === 229) return;
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const handleAttachClick = () => {
        fileInputRef.current?.click();
    };

    const handleAttachFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        if (!file.type.startsWith("image/")) {
            window.alert("이미지 파일만 첨부할 수 있어요.");
            e.target.value = "";
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            const dataUrl = typeof reader.result === "string" ? reader.result : null;
            setAttachedImageDataUrl(dataUrl);
            setAttachedFileName(file.name);
        };
        reader.readAsDataURL(file);
        e.target.value = "";
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

    const toMapId = useCallback((place: ChatPlaceItem) => {
        if (typeof place.place_id === "number" && Number.isFinite(place.place_id) && place.place_id > 0) {
            return `pid:${place.place_id}`;
        }
        const safeName = (place.name || "").trim().toLowerCase();
        return `mid:${place.id}:${safeName}`;
    }, []);

    const mapPlaces = useMemo<ChatMapPlace[]>(() => {
        const dedup = new Map<string, ChatMapPlace>();
        for (const msg of messages) {
            if (msg.role !== "ai") continue;
            if (!msg.places?.length) continue;
            for (const place of msg.places) {
                const lat = Number(place.latitude ?? 0);
                const lng = Number(place.longitude ?? 0);
                if (!Number.isFinite(lat) || !Number.isFinite(lng) || lat === 0 || lng === 0) continue;

                const mapId = toMapId(place);
                if (dedup.has(mapId)) continue;

                dedup.set(mapId, {
                    mapId,
                    name: (place.name || "").trim() || "Recommended place",
                    adress: place.adress,
                    latitude: lat,
                    longitude: lng,
                    map_url: place.map_url,
                });
                if (dedup.size >= 30) break;
            }
            if (dedup.size >= 30) break;
        }
        return Array.from(dedup.values());
    }, [messages, toMapId]);

    const mapPlaceGroups = useMemo<ChatMapPlaceGroup[]>(() => {
        if (!mapPlaces.length) return [];

        const allowedMapIds = new Set(mapPlaces.map((place) => place.mapId));
        const groups: ChatMapPlaceGroup[] = [];
        const globalSeen = new Set<string>(); // 전체 메시지에 걸쳐 맵 ID 중복 추적

        for (const msg of messages) {
            if (msg.role !== "ai" || !msg.places?.length) continue;
            const groupPlaces: ChatMapPlace[] = [];

            for (const place of msg.places) {
                const lat = Number(place.latitude ?? 0);
                const lng = Number(place.longitude ?? 0);
                if (!Number.isFinite(lat) || !Number.isFinite(lng) || lat === 0 || lng === 0) continue;

                const mapId = toMapId(place);
                if (!allowedMapIds.has(mapId) || globalSeen.has(mapId)) continue;
                globalSeen.add(mapId); // 추가된 장소는 전역 seen에 기록

                groupPlaces.push({
                    mapId,
                    name: (place.name || "").trim() || "Recommended place",
                    adress: place.adress,
                    latitude: lat,
                    longitude: lng,
                    map_url: place.map_url,
                });
            }

            if (!groupPlaces.length) continue;
            groups.push({
                groupId: `msg:${msg.id}`,
                label: `AI Reply · ${new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
                places: groupPlaces,
            });
        }

        return groups;
    }, [messages, mapPlaces, toMapId]);

    useEffect(() => {
        if (!mapPlaces.length) {
            setSelectedMapPlaceId(null);
            return;
        }
        setSelectedMapPlaceId((prev) => {
            if (prev && mapPlaces.some((p) => p.mapId === prev)) return prev;
            return mapPlaces[0].mapId;
        });
    }, [mapPlaces]);

    const focusPlaceCardFromMap = useCallback((mapId: string) => {
        const target = placeCardRefs.current[mapId];
        if (target) {
            target.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }, []);

    const handleSelectMapPlace = useCallback((mapId: string) => {
        setSelectedMapPlaceId(mapId);
    }, []);

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
        <div className="flex h-full min-h-0 bg-white relative rounded-[32px] overflow-hidden shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100">
            <div className="flex-1 min-w-0 min-h-0 flex flex-col relative bg-slate-50/30">
                <header className="h-14 flex items-center justify-between px-6 bg-white/70 backdrop-blur-md z-10 sticky top-0 border-b border-white/50">
                    <div className="flex items-center gap-2 min-w-0">
                        <Sparkles size={16} className="text-slate-900 flex-none" />
                        <span className="font-semibold text-[17px] tracking-tight text-slate-900 truncate">{currentRoom?.title || "Travel Assistant"}</span>
                        <button
                            type="button"
                            onClick={handleToggleRoomBookmark}
                            className={`inline-flex items-center justify-center rounded-full p-1 transition-colors ${currentRoom?.bookmark_yn ? "text-yellow-500 bg-yellow-50" : "text-gray-300 hover:text-yellow-500 hover:bg-gray-100"
                                }`}
                            title="채팅방 북마크 토글"
                            disabled={!currentRoomId}
                        >
                            <Bookmark size={13} fill={currentRoom?.bookmark_yn ? "currentColor" : "none"} />
                        </button>
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

                {roomTripContext && roomTripContext.travelDuration && (
                    <div className="flex-none px-6 pb-2 bg-white">
                        <div className="rounded-2xl bg-gray-50 px-4 py-2 text-xs text-slate-600 border border-gray-100">
                            {roomTripContext.travelDuration} · 성인 {roomTripContext.adultCount ?? 0}명 / 어린이 {roomTripContext.childCount ?? 0}명
                        </div>
                    </div>
                )}

                <div className="flex-1 min-h-0 overflow-y-auto p-0 pb-44 custom-scrollbar">
                    <div className="w-full min-h-full flex flex-col px-4 lg:px-6 pt-4 space-y-6">
                        {messages.length === 0 && !isTyping && (
                            <div className="h-full flex flex-col items-center justify-center text-slate-400">
                                <Sparkles className="w-8 h-8 mb-4 opacity-40 text-slate-300" />
                                <p className="text-sm font-medium tracking-tight">채팅을 시작해보세요!</p>
                            </div>
                        )}

                        {messages.map((msg) => (
                            <ChatMessageItem
                                key={msg.id}
                                msg={msg}
                                isStreaming={isStreaming}
                                streamingMsgId={streamingMsgId}
                                showPipeline={showPipeline}
                                selectedMapPlaceId={selectedMapPlaceId}
                                toMapId={toMapId}
                                handleSelectMapPlace={handleSelectMapPlace}
                                handleTogglePlaceBookmark={handleTogglePlaceBookmark}
                                placeCardRefs={placeCardRefs}
                            />
                        ))}

                        {showPipeline && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="flex items-start gap-3"
                            >
                                <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-full bg-black text-white shadow-sm">
                                    <BrandMark tone="light" size={14} />
                                </div>
                                <PipelineProgress steps={pipelineSteps} visible={true} />
                            </motion.div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                </div>

                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white to-white/0 pt-8 pb-4 px-4 z-20 pointer-events-none">
                    <div className="w-full mx-auto relative px-2 pointer-events-auto max-w-4xl">
                        <div className="bg-white/60 backdrop-blur-xl border border-slate-200/60 rounded-[28px] p-1.5 pr-1.5 shadow-[0_8px_30px_-4px_rgba(0,0,0,0.08)] focus-within:ring-4 focus-within:ring-slate-900/5 focus-within:border-slate-300 focus-within:bg-white/90 transition-all duration-300">
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                className="hidden"
                                onChange={handleAttachFileChange}
                            />

                            {attachedFileName && (
                                <div className="px-3 pt-2 pb-1">
                                    <div className="inline-flex items-center gap-2 rounded-full bg-slate-900 text-white text-xs pl-1.5 pr-2 py-1.5 max-w-[340px]">
                                        {attachedImageDataUrl && (
                                            <img
                                                src={attachedImageDataUrl}
                                                alt="첨부 이미지"
                                                className="w-6 h-6 rounded-full object-cover border border-white/20"
                                            />
                                        )}
                                        <span className="truncate">{attachedFileName}</span>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setAttachedImageDataUrl(null);
                                                setAttachedFileName("");
                                            }}
                                            className="text-white/80 hover:text-white transition-colors"
                                            aria-label="첨부 파일 제거"
                                        >
                                            ×
                                        </button>
                                    </div>
                                </div>
                            )}

                            <div className="flex items-center gap-2">
                                <button
                                    type="button"
                                    onClick={handleAttachClick}
                                    className="p-2.5 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors ml-1"
                                    title="이미지 첨부"
                                >
                                    <Paperclip size={18} />
                                </button>

                                <textarea
                                    ref={inputTextareaRef}
                                    value={inputText}
                                    onChange={(e) => setInputText(e.target.value)}
                                    onKeyDown={handleKeyPress}
                                    placeholder="어디로 떠나고 싶으신가요?"
                                    className="flex-1 bg-transparent border-none outline-none resize-none text-[15px] leading-[1.5] font-medium text-slate-800 placeholder:text-slate-400 custom-scrollbar py-2"
                                    rows={1}
                                    style={{ minHeight: "44px", maxHeight: "180px" }}
                                />

                                <button
                                    type="button"
                                    onClick={() => setIsMapSheetOpen(true)}
                                    className="p-2.5 rounded-full transition-all duration-300 text-slate-500 hover:text-black hover:bg-slate-100 lg:hidden"
                                    title="지도 보기"
                                >
                                    <MapIcon size={18} />
                                </button>

                                <button
                                    onClick={handleToggleListening}
                                    className={`p-2.5 rounded-full transition-all duration-300 relative ${micButtonClass}`}
                                    title={micButtonTitle}
                                    disabled={sttPermission === "unsupported"}
                                >
                                    {isListening ? (
                                        <>
                                            <Square size={16} fill="currentColor" strokeWidth={0} />
                                            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white animate-pulse shadow-sm shadow-red-500/50" />
                                        </>
                                    ) : sttPermission === "denied" ? (
                                        <MicOff size={18} strokeWidth={1.5} />
                                    ) : (
                                        <Mic size={18} strokeWidth={1.5} />
                                    )}
                                </button>

                                {isStreaming ? (
                                    <motion.button
                                        initial={false}
                                        animate={{ scale: 1, opacity: 1 }}
                                        onClick={handleStopMessage}
                                        className="p-2.5 rounded-full transition-all duration-300 shadow-md bg-red-500 text-white shadow-red-500/20 hover:shadow-red-500/40 hover:-translate-y-0.5"
                                        title="중지"
                                    >
                                        <Square size={16} fill="currentColor" strokeWidth={0} />
                                    </motion.button>
                                ) : (
                                    <motion.button
                                        initial={false}
                                        animate={{ scale: (inputText.trim() || attachedImageDataUrl) ? 1 : 0.9, opacity: (inputText.trim() || attachedImageDataUrl) ? 1 : 0.7 }}
                                        onClick={handleSendMessage}
                                        disabled={!inputText.trim() && !attachedImageDataUrl}
                                        className={`p-2.5 rounded-full transition-all duration-300 shadow-md ${(inputText.trim() || attachedImageDataUrl) ? "bg-black text-white shadow-black/20 hover:shadow-black/40 hover:-translate-y-0.5" : "bg-slate-100 text-slate-300 cursor-not-allowed shadow-none"}`}
                                        title="전송"
                                    >
                                        <Send size={18} />
                                    </motion.button>
                                )}
                            </div>
                        </div>

                        <p className="text-[11px] text-center text-slate-400 mt-3 font-medium tracking-wide">
                            Triver AI can make mistakes. Please check important info.
                        </p>
                    </div>
                </div>
            </div>

            <aside className="hidden lg:block w-[34%] min-w-[320px] max-w-[460px] border-l border-gray-100 bg-white">
                <PlaceMapPanel
                    className="h-full"
                    places={mapPlaces}
                    groups={mapPlaceGroups}
                    selectedMapPlaceId={selectedMapPlaceId}
                    onSelectPlace={handleSelectMapPlace}
                    onMarkerClick={focusPlaceCardFromMap}
                />
            </aside>

            <PlaceMapSheet
                open={isMapSheetOpen}
                onClose={() => setIsMapSheetOpen(false)}
                places={mapPlaces}
                groups={mapPlaceGroups}
                selectedMapPlaceId={selectedMapPlaceId}
                onSelectPlace={handleSelectMapPlace}
                onMarkerClick={focusPlaceCardFromMap}
            />

            <TripContextModal
                isOpen={showTripModal}
                onConfirm={handleCreateRoomWithContext}
                loading={isTripLoading}
                onClose={() => {
                    if (!isTripLoading) {
                        setShowTripModal(false);
                        handleCreateNewRoom();
                    }
                }}
            />
        </div>
    );
}
