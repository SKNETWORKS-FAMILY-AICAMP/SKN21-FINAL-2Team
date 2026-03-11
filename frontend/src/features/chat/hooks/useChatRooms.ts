import { useState, useRef, useCallback, useEffect, type Dispatch, type SetStateAction } from "react";
import { useRouter } from "next/navigation";
import {
    ChatMessage,
    ChatRoom,
    createRoom,
    fetchRoom,
    updateRoomBookmark
} from "@/services/api";
import {
    setPendingAutoStartMeta,
    type StoredSelectedPlaceSeed
} from "@/services/autoStart";
import { type TripContext } from "@/features/chat/components/TripContextModal";

export function useChatRooms({
    setShowTripModal,
    setIsTripLoading,
    mergeHydratedMessages,
    setMessages
}: {
    setShowTripModal: (show: boolean) => void;
    setIsTripLoading: (loading: boolean) => void;
    mergeHydratedMessages: (roomId: number, nextMessages: ChatMessage[]) => void;
    setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
}) {
    const router = useRouter();
    const [rooms, setRooms] = useState<ChatRoom[]>([]);
    const [currentRoomId, setCurrentRoomId] = useState<number | null>(null);
    const [roomLoadStatus, setRoomLoadStatus] = useState<"idle" | "loading" | "loaded">("idle");
    const [loadedRoomMessageCount, setLoadedRoomMessageCount] = useState<number | null>(null);
    const [isInitializing, setIsInitializing] = useState(true);
    const [roomTripContext, setRoomTripContext] = useState<TripContext | null>(null);

    const currentRoomIdRef = useRef<number | null>(null);
    const roomLoadStatusRef = useRef<"idle" | "loading" | "loaded">("idle");
    const latestRoomRequestRef = useRef<{ roomId: number | null; requestId: number }>({ roomId: null, requestId: 0 });

    useEffect(() => {
        currentRoomIdRef.current = currentRoomId;
    }, [currentRoomId]);

    useEffect(() => {
        roomLoadStatusRef.current = roomLoadStatus;
    }, [roomLoadStatus]);

    const loadRoomMessages = useCallback(async (roomId: number) => {
        const requestId = latestRoomRequestRef.current.requestId + 1;
        latestRoomRequestRef.current = { roomId, requestId };

        try {
            const roomData = await fetchRoom(roomId);
            const nextMessages = roomData.messages || [];
            if (
                latestRoomRequestRef.current.roomId !== roomId ||
                latestRoomRequestRef.current.requestId !== requestId ||
                currentRoomIdRef.current !== roomId
            ) {
                return;
            }

            mergeHydratedMessages(roomId, nextMessages);
            setLoadedRoomMessageCount(nextMessages.length);
        } catch (error) {
            console.error("Failed to load room messages", error);
            if (
                latestRoomRequestRef.current.roomId !== roomId ||
                latestRoomRequestRef.current.requestId !== requestId ||
                currentRoomIdRef.current !== roomId
            ) {
                return;
            }
            setMessages([]);
            setLoadedRoomMessageCount(null);
        } finally {
            if (
                latestRoomRequestRef.current.roomId === roomId &&
                latestRoomRequestRef.current.requestId === requestId &&
                currentRoomIdRef.current === roomId
            ) {
                setRoomLoadStatus("loaded");
            }
        }
    }, [mergeHydratedMessages, setMessages]);

    const handleCreateNewRoom = useCallback(async () => {
        try {
            const newRoom = await createRoom("새로운 여행 계획");

            setPendingAutoStartMeta(newRoom.id, { mode: "greeting" });

            setRooms((prev) => [newRoom, ...prev]);
            setCurrentRoomId(null);
            currentRoomIdRef.current = null;
            setMessages([]);
            setRoomLoadStatus("loading");
            setLoadedRoomMessageCount(null);
            window.dispatchEvent(new CustomEvent("triver:rooms-updated"));
            router.replace(`/chatbot?roomId=${newRoom.id}`);
        } catch (error) {
            console.error("Failed to create a new room", error);
        }
    }, [router, setMessages]);

    const handleCreateRoomWithContext = useCallback(async (context: TripContext) => {
        setIsTripLoading(true);
        try {
            const newRoom = await createRoom("새로운 여행 계획");
            let selectedPlaces: StoredSelectedPlaceSeed[] = [];

            const pendingRaw = localStorage.getItem("pendingDestination");
            if (pendingRaw) {
                try {
                    const place = JSON.parse(pendingRaw);
                    selectedPlaces = [{
                        name: place.name,
                        adress: place.address || place.adress,
                        place_id: typeof place.id === "number" ? place.id : 0,
                    }];
                } catch {
                } finally {
                    localStorage.removeItem("pendingDestination");
                }
            }

            if ((context.travelDuration || "").trim()) {
                setPendingAutoStartMeta(newRoom.id, {
                    mode: selectedPlaces.length > 0 ? "combined" : "trip_context",
                    tripContext: context,
                    selectedPlaces,
                });
            } else {
                setPendingAutoStartMeta(newRoom.id, {
                    mode: selectedPlaces.length > 0 ? "selected_places" : "greeting",
                    selectedPlaces,
                });
            }

            setRooms((prev) => [newRoom, ...prev]);
            setCurrentRoomId(null);
            currentRoomIdRef.current = null;
            setMessages([]);
            setRoomLoadStatus("loading");
            setLoadedRoomMessageCount(null);

            setShowTripModal(false);
            setIsTripLoading(false);
            window.dispatchEvent(new CustomEvent("triver:rooms-updated"));
            router.replace(`/chatbot?roomId=${newRoom.id}`);
        } catch (error) {
            console.error("Failed to create a new room with context", error);
            setIsTripLoading(false);
            setShowTripModal(false);
            void handleCreateNewRoom();
        }
    }, [handleCreateNewRoom, router, setIsTripLoading, setMessages, setShowTripModal]);

    const updateRoomTitle = useCallback((roomId: number, roomTitle: string) => {
        setRooms((prev) => prev.map((r) => (r.id === roomId ? { ...r, title: roomTitle } : r)));
        window.dispatchEvent(new CustomEvent("triver:rooms-updated"));
    }, []);

    const handleToggleRoomBookmark = async () => {
        const currentRoom = currentRoomId ? rooms.find((r) => r.id === currentRoomId) : null;
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

    return {
        rooms,
        setRooms,
        currentRoomId,
        setCurrentRoomId,
        currentRoomIdRef,
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
    };
}
