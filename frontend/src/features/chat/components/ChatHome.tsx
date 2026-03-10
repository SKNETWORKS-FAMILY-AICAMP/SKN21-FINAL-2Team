"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { Sparkles, Loader2 } from "lucide-react";
import { useSearchParams, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

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

type RoomDraft = {
    text: string;
    imageDataUrl: string | null;
    fileName: string;
    location: string | null;
    locationLabel: string;
};

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
    const [attachedLocation, setAttachedLocation] = useState<string | null>(null);
    const [attachedLocationLabel, setAttachedLocationLabel] = useState<string>("");
    const [isLocating, setIsLocating] = useState(false);

    const [messages, setMessages] = useState<ChatMessage[]>([]);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const placeCardRefs = useRef<Record<string, HTMLDivElement | null>>({});
    const autoStartedRoomsRef = useRef<Set<number>>(new Set());
    const roomDraftsRef = useRef<Record<number, RoomDraft>>({});
    const previousRoomIdRef = useRef<number | null>(null);
    const scrollStateRef = useRef<{
        roomId: number | null;
        messageCount: number;
        lastMessageId: number | null;
        lastMessageTextLength: number;
        wasStreaming: boolean;
    }>({
        roomId: null,
        messageCount: 0,
        lastMessageId: null,
        lastMessageTextLength: 0,
        wasStreaming: false,
    });
    const initializingIdRef = useRef<string | number | null>(null);


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
        isMapResizing,
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
        const lastMessage = visibleMessages[visibleMessages.length - 1];
        const nextState = {
            roomId: currentRoomId,
            messageCount: visibleMessages.length,
            lastMessageId: lastMessage?.id ?? null,
            lastMessageTextLength: (lastMessage?.message || "").length,
            wasStreaming: isStreaming,
        };
        const prevState = scrollStateRef.current;
        const shouldScroll = Boolean(
            nextState.roomId !== prevState.roomId ||
            nextState.messageCount !== prevState.messageCount ||
            (isStreaming && (
                nextState.lastMessageId !== prevState.lastMessageId ||
                nextState.lastMessageTextLength !== prevState.lastMessageTextLength ||
                !prevState.wasStreaming
            ))
        );

        if (shouldScroll) {
            scrollToBottom();
        }

        scrollStateRef.current = nextState;
    }, [currentRoomId, isStreaming, visibleMessages]);

    useEffect(() => {
        const previousRoomId = previousRoomIdRef.current;
        if (previousRoomId != null) {
            roomDraftsRef.current[previousRoomId] = {
                text: inputText,
                imageDataUrl: attachedImageDataUrl,
                fileName: attachedFileName,
                location: attachedLocation,
                locationLabel: attachedLocationLabel,
            };
        }

        const nextDraft = currentRoomId != null
            ? roomDraftsRef.current[currentRoomId]
            : undefined;

        setInputText(nextDraft?.text ?? "");
        setAttachedImageDataUrl(nextDraft?.imageDataUrl ?? null);
        setAttachedFileName(nextDraft?.fileName ?? "");
        setAttachedLocation(nextDraft?.location ?? null);
        setAttachedLocationLabel(nextDraft?.locationLabel ?? "");
        previousRoomIdRef.current = currentRoomId;
    }, [currentRoomId]);

    // 초기화 과정
    useEffect(() => {
        const initializeChat = async () => {
            const paramId = parsedRouteRoomId;
            const paramStr = roomIdParam;

            // 이미 같은 ID로 초기화 중이거나 완료된 경우 중복 실행 방지
            if (paramId != null) {
                if (paramId === currentRoomIdRef.current && roomLoadStatusRef.current === "loaded") return;
                if (paramId === initializingIdRef.current) return;
            } else if (paramStr === null) {
                // ID가 없는 경우(신규 진입) 이미 초기화 진행 중인지 체크
                if (initializingIdRef.current === "NEW_SESSION") return;
            }

            initializingIdRef.current = paramId ?? "NEW_SESSION";

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
                initializingIdRef.current = null;
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
        if (!userText && !attachedImageDataUrl && !attachedLocation) return;

        const fallbackParts = [
            attachedFileName ? `[이미지 첨부] ${attachedFileName}` : attachedImageDataUrl ? "[이미지 첨부]" : "",
            attachedLocationLabel ? `[위치 첨부] ${attachedLocationLabel}` : attachedLocation ? "[위치 첨부]" : "",
        ].filter(Boolean);
        const messageToSend = userText || (fallbackParts.length > 0 ? `${fallbackParts.join(" ")} 분석해줘.` : "메시지를 분석해줘.");
        const optimisticText = userText || fallbackParts.join(" ");
        const currentAttachment = attachedImageDataUrl;
        const currentLocation = attachedLocation;

        setInputText("");
        setAttachedImageDataUrl(null);
        setAttachedFileName("");
        setAttachedLocation(null);
        setAttachedLocationLabel("");
        roomDraftsRef.current[currentRoomId] = {
            text: "",
            imageDataUrl: null,
            fileName: "",
            location: null,
            locationLabel: "",
        };

        await streamMessageToRoom({
            roomId: currentRoomId,
            message: messageToSend,
            saveUserMessage: true,
            optimisticUserText: optimisticText,
            imageDataUrl: currentAttachment,
            location: currentLocation,
        });
    };

    const handleAttachLocation = useCallback(async () => {
        if (typeof window === "undefined" || !("geolocation" in navigator)) {
            window.alert("이 브라우저에서는 위치 첨부를 지원하지 않습니다.");
            return;
        }

        setIsLocating(true);
        try {
            const position = await new Promise<GeolocationPosition>((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 60000,
                });
            });

            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;
            setAttachedLocation(`${latitude}, ${longitude}`);
            setAttachedLocationLabel("현재 위치");
        } catch (error) {
            console.error("Failed to get current location", error);
            window.alert("현재 위치를 가져오지 못했습니다. 위치 권한을 확인해주세요.");
        } finally {
            setIsLocating(false);
        }
    }, []);

    if (isInitializing) {
        return (
            <div className="flex w-full h-full items-center justify-center bg-white">
                <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
        );
    }

    return (
        <div className={cn(
            "flex h-full min-h-0 bg-white relative rounded-[24px] overflow-hidden shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100",
            isMapPanelOpen ? "lg:rounded-l-[32px] lg:rounded-r-none" : "lg:rounded-[32px]"
        )}>
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
                    <div className="flex-none px-3 pb-2 sm:px-4 lg:px-6 bg-white">
                        <div className="rounded-2xl bg-gray-50 px-4 py-2 text-xs text-slate-600 border border-gray-100">
                            {roomTripContext.travelDuration} · 성인 {roomTripContext.adultCount ?? 0}명 / 어린이 {roomTripContext.childCount ?? 0}명
                        </div>
                    </div>
                )}

                <div className="flex-1 min-h-0 overflow-y-auto p-0 pb-48 sm:pb-44 custom-scrollbar">
                    <div className="w-full min-h-full flex flex-col px-3 sm:px-4 lg:px-6 pt-3 sm:pt-4 space-y-5 sm:space-y-6">
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
                                compactPlaces={isMapPanelOpen}
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
                    isLocating={isLocating}
                    sttPermission={sttPermission}
                    handleToggleListening={handleToggleListening}
                    setIsMapSheetOpen={setIsMapSheetOpen}
                    attachedImageDataUrl={attachedImageDataUrl}
                    attachedFileName={attachedFileName}
                    attachedLocationLabel={attachedLocationLabel}
                    handleAttachLocation={handleAttachLocation}
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
                    clearAttachedLocation={() => {
                        setAttachedLocation(null);
                        setAttachedLocationLabel("");
                    }}
                />
            </div>

            {/* Desktop Map Panel with Resizer */}
            {mapPlaces.length > 0 && (
                <>
                    <div
                        onMouseDown={startMapResizeDrag}
                        className={cn(
                            "hidden lg:block w-1.5 z-20",
                            isMapPanelOpen
                                ? "cursor-col-resize hover:bg-blue-500/20 active:bg-blue-500/40 opacity-100"
                                : "pointer-events-none opacity-0"
                        )}
                    />
                    <aside
                        style={{ width: isMapPanelOpen ? `${mapPanelWidth}%` : "0px" }}
                        className={cn(
                            "hidden lg:block max-w-[800px] bg-white z-10 overflow-hidden",
                            isMapResizing ? "transition-none" : "transition-[width] duration-200 ease-out",
                            isMapPanelOpen ? "border-l border-gray-100" : "border-l-0"
                        )}
                    >
                        <div
                            className={cn(
                                "h-full min-w-[320px]",
                                isMapResizing ? "transition-none" : "transition-transform duration-200 ease-out",
                                isMapPanelOpen ? "translate-x-0" : "translate-x-full"
                            )}
                        >
                            <PlaceMapPanel
                                className="h-full"
                                places={mapPlaces}
                                groups={mapPlaceGroups}
                                selectedMapPlaceId={selectedMapPlaceId}
                                onSelectPlace={handleSelectMapPlace}
                                onMarkerClick={focusPlaceCardFromMap}
                                isPanelOpen={isMapPanelOpen}
                                panelWidth={mapPanelWidth}
                                isResizing={isMapResizing}
                            />
                        </div>
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
