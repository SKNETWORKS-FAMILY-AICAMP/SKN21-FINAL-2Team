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
        const globalSeen = new Set<string>();

        for (const msg of messages) {
            if (msg.role !== "ai" || !msg.places?.length) continue;
            const groupPlaces: ChatMapPlace[] = [];

            for (const place of msg.places) {
                const lat = Number(place.latitude ?? 0);
                const lng = Number(place.longitude ?? 0);
                if (!Number.isFinite(lat) || !Number.isFinite(lng) || lat === 0 || lng === 0) continue;

                const mapId = toMapId(place);
                if (!allowedMapIds.has(mapId) || globalSeen.has(mapId)) continue;
                globalSeen.add(mapId);

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

    const handleSelectMapPlace = useCallback((mapId: string) => {
        setSelectedMapPlaceId(mapId);
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
