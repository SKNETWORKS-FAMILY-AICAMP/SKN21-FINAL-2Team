"use client";

import { useEffect, useMemo, useRef } from "react";
import { MapPin, RefreshCw } from "lucide-react";
import { NaverInfoWindow, NaverMapInstance, NaverMarker, useNaverMap } from "./useNaverMap";

export type ChatMapPlace = {
  mapId: string;
  name: string;
  adress?: string | null;
  latitude: number;
  longitude: number;
  map_url?: string | null;
};

type PlaceMapPanelProps = {
  places: ChatMapPlace[];
  selectedMapPlaceId: string | null;
  onSelectPlace: (mapId: string) => void;
  onMarkerClick: (mapId: string) => void;
  className?: string;
  showHeader?: boolean;
};

function escapeHtml(raw: string) {
  return raw
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function PlaceMapPanel({
  places,
  selectedMapPlaceId,
  onSelectPlace,
  onMarkerClick,
  className,
  showHeader = true,
}: PlaceMapPanelProps) {
  const clientId = process.env.NEXT_PUBLIC_NAVER_MAP_CLIENT_ID;
  const { status, error, naver, retry } = useNaverMap(clientId);

  const mapRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<NaverMapInstance | null>(null);
  const markersRef = useRef<Map<string, NaverMarker>>(new Map());
  const infoWindowRef = useRef<NaverInfoWindow | null>(null);

  const sortedPlaces = useMemo(() => {
    return [...places].sort((a, b) => a.name.localeCompare(b.name));
  }, [places]);

  useEffect(() => {
    if (status !== "ready" || !naver?.maps || !mapRef.current) return;

    if (!mapInstanceRef.current) {
      const first = sortedPlaces[0];
      mapInstanceRef.current = new naver.maps.Map(mapRef.current, {
        center: new naver.maps.LatLng(first?.latitude ?? 37.5665, first?.longitude ?? 126.978),
        zoom: 12,
        minZoom: 6,
        maxZoom: 18,
      });
      infoWindowRef.current = new naver.maps.InfoWindow({
        backgroundColor: "#111827",
        borderColor: "#111827",
        anchorSize: new naver.maps.Size(10, 10),
        pixelOffset: new naver.maps.Point(0, -8),
      });
    }

    const map = mapInstanceRef.current;

    markersRef.current.forEach((marker) => marker.setMap(null));
    markersRef.current.clear();

    const bounds = new naver.maps.LatLngBounds();

    sortedPlaces.forEach((place) => {
      const isSelected = place.mapId === selectedMapPlaceId;
      const marker = new naver.maps.Marker({
        position: new naver.maps.LatLng(place.latitude, place.longitude),
        map,
        icon: {
          content: `<div style="width:${isSelected ? 18 : 14}px;height:${isSelected ? 18 : 14}px;border-radius:999px;background:${isSelected ? "#2563eb" : "#111827"};border:2px solid #fff;box-shadow:0 6px 16px rgba(15,23,42,0.35);"></div>`,
          anchor: new naver.maps.Point(isSelected ? 9 : 7, isSelected ? 9 : 7),
        },
        zIndex: isSelected ? 100 : 10,
      });

      naver.maps.Event.addListener(marker, "click", () => {
        onSelectPlace(place.mapId);
        onMarkerClick(place.mapId);
      });

      markersRef.current.set(place.mapId, marker);
      bounds.extend(marker.getPosition());
    });

    if (sortedPlaces.length === 1) {
      const only = sortedPlaces[0];
      map.setCenter(new naver.maps.LatLng(only.latitude, only.longitude));
      map.setZoom(14);
    } else if (sortedPlaces.length > 1) {
      map.fitBounds(bounds, { top: 50, right: 40, bottom: 50, left: 40 });
    }

    if (selectedMapPlaceId && infoWindowRef.current) {
      const selected = sortedPlaces.find((p) => p.mapId === selectedMapPlaceId);
      const marker = markersRef.current.get(selectedMapPlaceId);
      if (selected && marker) {
        const content = `<div style="padding:6px 8px;color:#fff;font-size:12px;font-weight:600;max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(selected.name)}</div>`;
        infoWindowRef.current.setContent(content);
        infoWindowRef.current.open(map, marker);
      } else {
        infoWindowRef.current.close();
      }
    } else if (infoWindowRef.current) {
      infoWindowRef.current.close();
    }
  }, [status, naver, sortedPlaces, selectedMapPlaceId, onMarkerClick, onSelectPlace]);

  if (!clientId) {
    return (
      <div className={className}>
        <div className="h-full flex items-center justify-center p-6 text-center text-sm text-gray-500">
          NEXT_PUBLIC_NAVER_MAP_CLIENT_ID is not configured.
        </div>
      </div>
    );
  }

  if (!sortedPlaces.length) {
    return (
      <div className={className}>
        <div className="h-full flex flex-col items-center justify-center p-6 text-center text-sm text-gray-500 gap-2">
          <MapPin size={18} className="text-gray-400" />
          추천 장소 좌표가 없어 지도를 표시할 수 없습니다.
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="h-full flex flex-col">
        {showHeader && (
          <div className="flex-none px-4 py-3 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-900">Map</h3>
            <p className="text-[11px] text-gray-500 mt-1">Recommended places from AI response</p>
          </div>
        )}

        {status === "loading" && (
          <div className="flex-1 flex items-center justify-center text-sm text-gray-500">Loading map...</div>
        )}

        {status === "error" && (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 p-6 text-center">
            <p className="text-sm text-gray-500">{error || "Failed to load map."}</p>
            <button
              type="button"
              onClick={retry}
              className="h-9 px-4 rounded-full border border-gray-300 bg-white text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-all inline-flex items-center gap-2"
            >
              <RefreshCw size={12} /> Retry
            </button>
          </div>
        )}

        {status === "ready" && (
          <>
            <div ref={mapRef} className="flex-1 min-h-[260px]" />
            <div className="flex-none border-t border-gray-100 p-3 space-y-2 max-h-[200px] overflow-y-auto">
              {sortedPlaces.map((place) => (
                <button
                  key={place.mapId}
                  type="button"
                  onClick={() => {
                    onSelectPlace(place.mapId);
                    onMarkerClick(place.mapId);
                  }}
                  className={`w-full text-left rounded-xl border px-3 py-2 transition-colors ${
                    place.mapId === selectedMapPlaceId
                      ? "border-black bg-gray-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <div className="text-xs font-semibold text-gray-900 truncate">{place.name}</div>
                  {!!place.adress && <div className="text-[10px] text-gray-500 truncate mt-0.5">{place.adress}</div>}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
