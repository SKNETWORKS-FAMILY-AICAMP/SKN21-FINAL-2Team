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

    const toMapPlace = useCallback((place: ChatPlaceItem): ChatMapPlace | null => {
        const lat = Number(place.latitude ?? 0);
        const lng = Number(place.longitude ?? 0);
        if (!Number.isFinite(lat) || !Number.isFinite(lng) || lat === 0 || lng === 0) return null;
        return {
            mapId: toMapId(place),
            name: (place.name || "").trim() || "Recommended place",
            adress: place.adress,
            latitude: lat,
            longitude: lng,
            map_url: place.map_url,
        };
    }, [toMapId]);

    const mapPlaceGroups = useMemo<ChatMapPlaceGroup[]>(() => {
        const groups: ChatMapPlaceGroup[] = [];
        let msgIndex = 0;
        for (const msg of messages) {
            if (msg.role !== "ai" || !msg.places?.length) continue;
            const seen = new Set<string>();
            const groupPlaces: ChatMapPlace[] = [];
            for (const place of msg.places) {
                const mp = toMapPlace(place);
                if (!mp || seen.has(mp.mapId)) continue;
                seen.add(mp.mapId);
                groupPlaces.push(mp);
            }
            if (!groupPlaces.length) continue;
            msgIndex++;
            groups.push({
                groupId: `msg:${msg.id}`,
                label: `답변 ${msgIndex} · ${new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
                places: groupPlaces,
            });
        }
        return groups;
    }, [messages, toMapPlace]);

    const mapPlaces = useMemo<ChatMapPlace[]>(() => {
        const dedup = new Map<string, ChatMapPlace>();
        for (const group of mapPlaceGroups) {
            for (const place of group.places) {
                if (!dedup.has(place.mapId)) dedup.set(place.mapId, place);
            }
        }
        return Array.from(dedup.values());
    }, [mapPlaceGroups]);

    // 새 메시지 도착 시 fit 대상: activeMessage의 장소만
    const focusPlaces = useMemo<ChatMapPlace[]>(() => {
        if (!activeMessage?.places?.length) return [];
        const seen = new Set<string>();
        const result: ChatMapPlace[] = [];
        for (const place of activeMessage.places) {
            const mp = toMapPlace(place);
            if (!mp || seen.has(mp.mapId)) continue;
            seen.add(mp.mapId);
            result.push(mp);
        }
        return result;
    }, [activeMessage, toMapPlace]);

    const hasMapPlaces = mapPlaces.length > 0 && messages.length > 0;
    const isMapPanelOpen = hasMapPlaces && isMapPanelOpenRaw;
    const selectedMapPlaceId = useMemo(() => {
        if (!mapPlaces.length) return null;
        if (selectedMapPlaceIdRaw && mapPlaces.some((p) => p.mapId === selectedMapPlaceIdRaw)) {
            return selectedMapPlaceIdRaw;
        }
        // 기본값: 활성 메시지의 첫 번째 장소
        if (activeMessage?.places) {
            for (const place of activeMessage.places) {
                const mid = toMapId(place);
                if (mapPlaces.some((p) => p.mapId === mid)) return mid;
            }
        }
        return mapPlaces[0].mapId;
    }, [mapPlaces, selectedMapPlaceIdRaw, activeMessage, toMapId]);

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
        focusPlaces,
        mapPlaceGroups,
        toMapId,
        startMapResizeDrag,
        focusPlaceCardFromMap,
        handleSelectMapPlace
    };
}
