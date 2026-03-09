import { useState, useCallback, useMemo, useEffect } from "react";
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
    const [selectedMapPlaceId, setSelectedMapPlaceId] = useState<string | null>(null);
    const [isMapSheetOpen, setIsMapSheetOpen] = useState(false);
    const [isMapPanelOpen, setIsMapPanelOpenRaw] = useState(false);
    const [mapPanelWidth, setMapPanelWidth] = useState(DEFAULT_MAP_PANEL_WIDTH);

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

    useEffect(() => {
        if (mapPlaces.length > 0 && messages.length > 0) {
            setIsMapPanelOpenRaw(true);
        } else if (mapPlaces.length === 0) {
            setIsMapPanelOpenRaw(false);
        }
    }, [mapPlaces.length, messages.length]);

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

    const handleMapResizeDrag = useCallback((e: MouseEvent) => {
        const newWidth = ((window.innerWidth - e.clientX) / window.innerWidth) * 100;
        setMapPanelWidth(Math.min(Math.max(newWidth, 20), 50));
    }, []);

    const setIsMapPanelOpen = useCallback((open: boolean) => {
        if (open) {
            setMapPanelWidth(DEFAULT_MAP_PANEL_WIDTH);
        }
        setIsMapPanelOpenRaw(open);
    }, []);

    const stopMapResizeDrag = useCallback(() => {
        document.removeEventListener("mousemove", handleMapResizeDrag);
        document.removeEventListener("mouseup", stopMapResizeDrag);
        document.body.style.cursor = "default";
    }, [handleMapResizeDrag]);

    const startMapResizeDrag = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        document.addEventListener("mousemove", handleMapResizeDrag);
        document.addEventListener("mouseup", stopMapResizeDrag);
        document.body.style.cursor = "col-resize";
    }, [handleMapResizeDrag, stopMapResizeDrag]);

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
        mapPanelWidth,
        mapPlaces,
        mapPlaceGroups,
        toMapId,
        startMapResizeDrag,
        focusPlaceCardFromMap,
        handleSelectMapPlace
    };
}
