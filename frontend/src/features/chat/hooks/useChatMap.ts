import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import { ChatMessage, ChatPlaceItem } from "@/services/api";
import { ChatMapPlace, ChatMapPlaceGroup } from "@/features/chat/components/PlaceMapPanel";

const DEFAULT_MAP_PANEL_WIDTH = 34;

export function useChatMap({
    messages,
    placeCardRefs
}: {
    messages: ChatMessage[];
    placeCardRefs: React.MutableRefObject<Record<string, HTMLDivElement | null>>;
}) {
    const [selectedMapPlaceIdRaw, setSelectedMapPlaceId] = useState<string | null>(null);
    const [focusMessageId, setFocusMessageId] = useState<number | null>(null);
    const [prevLatestAiMessageId, setPrevLatestAiMessageId] = useState<number | null>(null);

    const [isMapSheetOpen, setIsMapSheetOpen] = useState(false);
    const [isMapPanelOpenRaw, setIsMapPanelOpenRaw] = useState(true);
    const [isMapResizing, setIsMapResizing] = useState(false);
    const [mapPanelWidth, setMapPanelWidth] = useState(DEFAULT_MAP_PANEL_WIDTH);
    const resizeStartXRef = useRef(0);
    const resizeStartWidthRef = useRef(DEFAULT_MAP_PANEL_WIDTH);
    const stopMapResizeDragRef = useRef<() => void>(() => {});

    const toMapId = useCallback((place: ChatPlaceItem) => {
        if (typeof place.place_id === "number" && Number.isFinite(place.place_id) && place.place_id > 0) {
            return `pid:${place.place_id}`;
        }
        const safeName = (place.name || "").trim().toLowerCase();
        return `mid:${place.id}:${safeName}`;
    }, []);

    const latestAiMessageId = useMemo(() => {
        for (let i = messages.length - 1; i >= 0; i--) {
            const msg = messages[i];
            if (msg.role === "ai" && msg.places && msg.places.length > 0) {
                return msg.id;
            }
        }
        return null;
    }, [messages]);

    useEffect(() => {
        if (latestAiMessageId !== prevLatestAiMessageId) {
            setPrevLatestAiMessageId(latestAiMessageId);
            setFocusMessageId(latestAiMessageId ?? null);
        }
    }, [latestAiMessageId, prevLatestAiMessageId]);
        
    const activeMessage = useMemo(() => {
        if (focusMessageId !== null) {
            const msg = messages.find((m) => m.id === focusMessageId);
            if (msg && msg.role === "ai" && msg.places && msg.places.length > 0) {
                return msg;
            }
        }
        if (latestAiMessageId !== null) {
            return messages.find((m) => m.id === latestAiMessageId) || null;
        }
        return null;
    }, [messages, focusMessageId, latestAiMessageId]);

    const mapPlaces = useMemo<ChatMapPlace[]>(() => {
        if (!activeMessage || !activeMessage.places) return [];
        
        const dedup = new Map<string, ChatMapPlace>();
        for (const place of activeMessage.places) {
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
        }
        return Array.from(dedup.values());
    }, [activeMessage, toMapId]);

    const mapPlaceGroups = useMemo<ChatMapPlaceGroup[]>(() => {
        if (!mapPlaces.length || !activeMessage) return [];

        return [{
            groupId: `msg:${activeMessage.id}`,
            label: `AI Reply · ${new Date(activeMessage.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
            places: mapPlaces,
        }];
    }, [activeMessage, mapPlaces]);

    const hasMapPlaces = mapPlaces.length > 0 && messages.length > 0;
    const isMapPanelOpen = hasMapPlaces && isMapPanelOpenRaw;
    const selectedMapPlaceId = useMemo(() => {
        if (!mapPlaces.length) return null;
        if (selectedMapPlaceIdRaw && mapPlaces.some((place) => place.mapId === selectedMapPlaceIdRaw)) {
            return selectedMapPlaceIdRaw;
        }
        return mapPlaces[0].mapId;
    }, [mapPlaces, selectedMapPlaceIdRaw]);

    const handleMapResizeDrag = useCallback((e: MouseEvent) => {
        const deltaX = e.clientX - resizeStartXRef.current;
        const nextWidth = resizeStartWidthRef.current - (deltaX / window.innerWidth) * 100;
        const clampedWidth = Math.min(Math.max(nextWidth, 20), 50);

        if (typeof window !== "undefined" && "requestAnimationFrame" in window) {
            window.requestAnimationFrame(() => {
                setMapPanelWidth(clampedWidth);
            });
            return;
        }

        setMapPanelWidth(clampedWidth);
    }, []);

    const setIsMapPanelOpen = useCallback((open: boolean) => {
        if (open) {
            setMapPanelWidth(DEFAULT_MAP_PANEL_WIDTH);
        }
        setIsMapPanelOpenRaw(open);
    }, []);

    const stopMapResizeDrag = useCallback(() => {
        setIsMapResizing(false);
        document.removeEventListener("mousemove", handleMapResizeDrag);
        document.removeEventListener("mouseup", stopMapResizeDragRef.current);
        document.body.style.cursor = "default";
        document.body.style.userSelect = "";
    }, [handleMapResizeDrag]);

    useEffect(() => {
        stopMapResizeDragRef.current = stopMapResizeDrag;
    }, [stopMapResizeDrag]);

    const startMapResizeDrag = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        setIsMapResizing(true);
        resizeStartXRef.current = e.clientX;
        resizeStartWidthRef.current = mapPanelWidth;
        document.addEventListener("mousemove", handleMapResizeDrag);
        document.addEventListener("mouseup", stopMapResizeDrag);
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
    }, [handleMapResizeDrag, mapPanelWidth, stopMapResizeDrag]);

    const focusPlaceCardFromMap = useCallback((mapId: string) => {
        const target = placeCardRefs.current[mapId];
        if (target) {
            target.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }, [placeCardRefs]);

    const handleSelectMapPlace = useCallback((mapId: string, messageId?: number) => {
        setSelectedMapPlaceId(mapId);
        if (messageId !== undefined) {
            setFocusMessageId(messageId);
        }
    }, []);

    return {
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
    };
}
