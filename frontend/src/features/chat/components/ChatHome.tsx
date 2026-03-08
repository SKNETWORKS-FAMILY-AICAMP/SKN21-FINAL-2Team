"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { Sparkles, Loader2 } from "lucide-react";
import { useSearchParams, useRouter } from "next/navigation";

import { ChatMessage, fetchCurrentUser, verifyAndRefreshToken, UserProfile } from "@/services/api";
import { TripContextModal } from "@/features/chat/components/TripContextModal";
import { PlaceMapPanel } from "@/features/chat/components/PlaceMapPanel";
import { PlaceMapSheet } from "@/features/chat/components/PlaceMapSheet";
import { ChatMessageItem } from "@/features/chat/components/ChatMessageItem";
import { ChatHeader } from "@/features/chat/components/ChatHeader";
import { ChatInputArea } from "@/features/chat/components/ChatInputArea";
import { useChatRooms } from "@/features/chat/hooks/useChatRooms";
import { useChatMessages } from "@/features/chat/hooks/useChatMessages";
import { useChatMap } from "@/features/chat/hooks/useChatMap";
import { useSpeechRecognition } from "@/hooks/common/useSpeechRecognition";

import {
    clearPendingAutoStartMeta,
    hasAutoStartStarted,
    markAutoStartStarted,
    readPendingAutoStartMeta,
} from "@/services/autoStart";

export function ChatHome() {
    const searchParams = useSearchParams();
    const roomIdParam = searchParams.get("roomId");
    const parsedRouteRoomId = roomIdParam ? parseInt(roomIdParam, 10) : null;
    const fromDestinationParam = searchParams.get("fromDestination");

    const [inputText, setInputText] = useState("");
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const [showTripModal, setShowTripModal] = useState(false);
    const [isTripLoading, setIsTripLoading] = useState(false);
    const [attachedImageDataUrl, setAttachedImageDataUrl] = useState<string | null>(null);
    const [attachedFileName, setAttachedFileName] = useState<string>("");

    const [messages, setMessages] = useState<ChatMessage[]>([]);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const placeCardRefs = useRef<Record<string, HTMLDivElement | null>>({});
    const autoStartedRoomsRef = useRef<Set<number>>(new Set());

    const { isListening, sttPermission, handleToggleListening } = useSpeechRecognition({
        inputText,
        setInputText
    });

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // --- 1. Chat Rooms Hook ---
    const {
        rooms,
        setRooms,
        currentRoomId,
        currentRoomIdRef,
        setCurrentRoomId,
        roomLoadStatus,
        setRoomLoadStatus,
        roomLoadStatusRef,
        loadedRoomMessageCount,
        setLoadedRoomMessageCount,
        isInitializing,
        setIsInitializing,
        roomTripContext,
        setRoomTripContext,
        loadRoomMessages,
        handleCreateNewRoom,
        handleCreateRoomWithContext,
        updateRoomTitle,
        handleToggleRoomBookmark
    } = useChatRooms({
        parsedRouteRoomId,
        fromDestinationParam,
        setShowTripModal,
        setIsTripLoading,
        mergeHydratedMessages: (rId, nextMsgs) => mergeHydratedMessages(rId, nextMsgs),
        setMessages
    });

    // --- 2. Chat Messages Hook ---
    const {
        isTyping,
        isStreaming,
        showPipeline,
        pipelineSteps,
        streamBufferingReason,
        streamingMsgId,
        mergeHydratedMessages,
        streamMessageToRoom,
        runAutoStarterStream,
        handleStopMessage,
        handleTogglePlaceBookmark
    } = useChatMessages({
        setMessages,
        updateRoomTitle,
        clearPendingAutoStartMeta
    });

    // --- 3. Chat Map Hook ---
    const {
        selectedMapPlaceId,
        isMapSheetOpen,
        setIsMapSheetOpen,
        isMapPanelOpen,
        setIsMapPanelOpen,
        mapPanelWidth,
        mapPlaces,
        mapPlaceGroups,
        toMapId,
        startMapResizeDrag,
        focusPlaceCardFromMap,
        handleSelectMapPlace
    } = useChatMap({ messages, placeCardRefs });

    const currentRoom = currentRoomId ? rooms.find((r) => r.id === currentRoomId) : null;
    const isRouteRoomSynced = parsedRouteRoomId == null || currentRoomId === parsedRouteRoomId;

    const visibleMessages = useMemo(
        () => currentRoomId == null ? [] : messages.filter((msg) => msg.room_id === currentRoomId),
        [currentRoomId, messages]
    );

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

    // 초기화 과정
    useEffect(() => {
        const initializeChat = async () => {
            const paramId = parsedRouteRoomId;
            if (paramId && paramId === currentRoomIdRef.current && roomLoadStatusRef.current === "loaded") return;

            setIsInitializing(true);
            setRoomTripContext(null);
            setMessages([]);
            setRoomLoadStatus("loading");
            setLoadedRoomMessageCount(null);
            try {
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

                try {
                    const data = await fetchCurrentUser();
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

                // 방어 로직: useChatRooms의 첫 loadRoomMessages는 내부에서 수행될 경우
                // useRouter의 replace와 충돌 가능성이 있어 초기 진입 로직은 여기서 명확히.
                import("@/services/api").then(async ({ fetchRooms }) => {
                    const fetchedRooms = await fetchRooms();
                    setRooms(fetchedRooms);
                    // update rooms from initialize process
                    // rooms 상태 동기화를 위해 dispatch 사용 (useChatRooms 내부는 이미 세팅되어있으리라 가정)
                    const event = new CustomEvent("triver:rooms-updated");
                    window.dispatchEvent(event);

                    if (fromDestinationParam === "1" && localStorage.getItem("pendingDestination")) {
                        setShowTripModal(true);
                    } else if (roomIdParam) {
                        const parsedRoomId = parseInt(roomIdParam, 10);
                        setCurrentRoomId(parsedRoomId);
                        currentRoomIdRef.current = parsedRoomId;
                        await loadRoomMessages(parsedRoomId);
                    } else if (fetchedRooms.length > 0) {
                        const latestRoomId = fetchedRooms[0].id;
                        setCurrentRoomId(latestRoomId);
                        currentRoomIdRef.current = latestRoomId;
                        await loadRoomMessages(latestRoomId);
                        window.history.replaceState(null, "", `/chatbot?roomId=${latestRoomId}`);
                    } else {
                        setCurrentRoomId(null);
                        currentRoomIdRef.current = null;
                        setRoomLoadStatus("idle");
                        setLoadedRoomMessageCount(null);
                        setShowTripModal(true);
                    }
                });

            } catch (error) {
                console.error("Failed to initialize chat", error);
            } finally {
                setIsInitializing(false);
            }
        };

        initializeChat();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [fromDestinationParam, parsedRouteRoomId, roomIdParam]);

    // AutoStart 로직
    useEffect(() => {
        if (!currentRoomId || isInitializing || isStreaming || roomLoadStatus !== "loaded") return;
        if (autoStartedRoomsRef.current.has(currentRoomId)) return;

        const pendingMeta = readPendingAutoStartMeta(currentRoomId);
        if (!pendingMeta.mode) return;

        if (hasAutoStartStarted(currentRoomId)) {
            autoStartedRoomsRef.current.add(currentRoomId);
            return;
        }

        if (loadedRoomMessageCount == null) return;
        if (loadedRoomMessageCount > 0) {
            clearPendingAutoStartMeta(currentRoomId);
            return;
        }

        autoStartedRoomsRef.current.add(currentRoomId);
        markAutoStartStarted(currentRoomId);

        if (pendingMeta.mode === "combined" && pendingMeta.tripContext && pendingMeta.selectedPlaces.length > 0) {
            void runAutoStarterStream({
                roomId: currentRoomId,
                payload: {
                    mode: "combined",
                    trip_context: {
                        travel_duration: pendingMeta.tripContext.travelDuration,
                        adult_count: pendingMeta.tripContext.adultCount,
                        child_count: pendingMeta.tripContext.childCount,
                    },
                    selected_places: pendingMeta.selectedPlaces.map((p) => ({
                        name: p.name,
                        adress: p.adress,
                        place_id: p.place_id ?? 0,
                    })),
                    save_user_message: false,
                },
            });
            return;
        }

        if (pendingMeta.mode === "selected_places" && pendingMeta.selectedPlaces.length > 0) {
            void runAutoStarterStream({
                roomId: currentRoomId,
                payload: {
                    mode: "selected_places",
                    selected_places: pendingMeta.selectedPlaces.map((p) => ({
                        name: p.name,
                        adress: p.adress,
                        place_id: p.place_id ?? 0,
                    })),
                    save_user_message: false,
                },
            });
            return;
        }

        if (pendingMeta.mode === "trip_context" && pendingMeta.tripContext) {
            void runAutoStarterStream({
                roomId: currentRoomId,
                payload: {
                    mode: "trip_context",
                    trip_context: {
                        travel_duration: pendingMeta.tripContext.travelDuration,
                        adult_count: pendingMeta.tripContext.adultCount,
                        child_count: pendingMeta.tripContext.childCount,
                    },
                    save_user_message: false,
                },
            });
            return;
        }

        if (pendingMeta.mode === "greeting") {
            void runAutoStarterStream({
                roomId: currentRoomId,
                payload: {
                    mode: "greeting",
                    save_user_message: false,
                },
            });
        }
    }, [currentRoomId, isInitializing, isStreaming, loadedRoomMessageCount, roomLoadStatus, runAutoStarterStream]);

    const handleSendMessageWrapper = async () => {
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
                <ChatHeader
                    currentRoom={currentRoom}
                    currentRoomId={currentRoomId}
                    mapPlacesLength={mapPlaces.length}
                    isMapPanelOpen={isMapPanelOpen}
                    handleToggleRoomBookmark={handleToggleRoomBookmark}
                    setIsMapPanelOpen={setIsMapPanelOpen}
                />

                {isRouteRoomSynced && roomTripContext && roomTripContext.travelDuration && (
                    <div className="flex-none px-6 pb-2 bg-white">
                        <div className="rounded-2xl bg-gray-50 px-4 py-2 text-xs text-slate-600 border border-gray-100">
                            {roomTripContext.travelDuration} · 성인 {roomTripContext.adultCount ?? 0}명 / 어린이 {roomTripContext.childCount ?? 0}명
                        </div>
                    </div>
                )}

                <div className="flex-1 min-h-0 overflow-y-auto p-0 pb-44 custom-scrollbar">
                    <div className="w-full min-h-full flex flex-col px-4 lg:px-6 pt-4 space-y-6">
                        {visibleMessages.length === 0 && !isTyping && (
                            <div className="h-full flex flex-col items-center justify-center text-slate-400">
                                <Sparkles className="w-8 h-8 mb-4 opacity-40 text-slate-300" />
                                <p className="text-sm font-medium tracking-tight">채팅을 시작해보세요!</p>
                            </div>
                        )}

                        {visibleMessages.map((msg) => (
                            <ChatMessageItem
                                key={msg.id}
                                msg={msg}
                                isStreaming={isStreaming}
                                streamingMsgId={streamingMsgId}
                                showPipeline={showPipeline}
                                pipelineSteps={pipelineSteps}
                                streamBufferingReason={streamBufferingReason}
                                selectedMapPlaceId={selectedMapPlaceId}
                                toMapId={toMapId}
                                handleSelectMapPlace={handleSelectMapPlace}
                                handleTogglePlaceBookmark={handleTogglePlaceBookmark}
                                placeCardRefs={placeCardRefs}
                            />
                        ))}

                        <div ref={messagesEndRef} />
                    </div>
                </div>

                <ChatInputArea
                    inputText={inputText}
                    setInputText={setInputText}
                    handleSendMessage={handleSendMessageWrapper}
                    handleStopMessage={handleStopMessage}
                    isStreaming={isStreaming}
                    isListening={isListening}
                    sttPermission={sttPermission}
                    handleToggleListening={handleToggleListening}
                    setIsMapSheetOpen={setIsMapSheetOpen}
                    attachedImageDataUrl={attachedImageDataUrl}
                    attachedFileName={attachedFileName}
                    handleAttachFileChange={(e) => {
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
                    }}
                    setAttachedImageDataUrl={setAttachedImageDataUrl}
                    setAttachedFileName={setAttachedFileName}
                />
            </div>

            {/* Desktop Map Panel with Resizer */}
            {isMapPanelOpen && mapPlaces.length > 0 && (
                <>
                    <div
                        onMouseDown={startMapResizeDrag}
                        className="hidden lg:block w-1.5 cursor-col-resize hover:bg-blue-500/20 active:bg-blue-500/40 transition-colors z-20"
                    />
                    <aside
                        style={{ width: `${mapPanelWidth}%` }}
                        className="hidden lg:block min-w-[320px] max-w-[800px] border-l border-gray-100 bg-white z-10"
                    >
                        <PlaceMapPanel
                            className="h-full"
                            places={mapPlaces}
                            groups={mapPlaceGroups}
                            selectedMapPlaceId={selectedMapPlaceId}
                            onSelectPlace={handleSelectMapPlace}
                            onMarkerClick={focusPlaceCardFromMap}
                        />
                    </aside>
                </>
            )}

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
