"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { MapPin, RefreshCw, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { NaverInfoWindow, NaverMapInstance, NaverMarker, useNaverMap } from "./useNaverMap";

export type ChatMapPlace = {
  mapId: string;
  name: string;
  adress?: string | null;
  latitude: number;
  longitude: number;
  map_url?: string | null;
};

export type ChatMapPlaceGroup = {
  groupId: string;
  label: string;
  places: ChatMapPlace[];
};

type PlaceMapPanelProps = {
  places: ChatMapPlace[];
  groups?: ChatMapPlaceGroup[];
  selectedMapPlaceId: string | null;
  onSelectPlace: (mapId: string) => void;
  onMarkerClick: (mapId: string) => void;
  className?: string;
  showHeader?: boolean;
};

const SEOUL_BOUNDS = {
  minLat: 37.4133,
  maxLat: 37.7151,
  minLng: 126.7341,
  maxLng: 127.2693,
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
  groups,
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

  const groupedPlaces = useMemo(() => {
    if (groups?.length) {
      return groups.filter((group) => group.places.length > 0);
    }
    return [{ groupId: "all", label: "All recommendations", places: sortedPlaces }];
  }, [groups, sortedPlaces]);

  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScrollability = useCallback(() => {
    if (scrollContainerRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = scrollContainerRef.current;
      setCanScrollLeft(scrollLeft > 0);
      setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 1);
    }
  }, []);

  useEffect(() => {
    checkScrollability();
    window.addEventListener("resize", checkScrollability);
    return () => window.removeEventListener("resize", checkScrollability);
  }, [checkScrollability, groupedPlaces]);

  const scrollBy = (direction: "left" | "right") => {
    if (scrollContainerRef.current) {
      const scrollAmount = direction === "left" ? -200 : 200;
      scrollContainerRef.current.scrollBy({ left: scrollAmount, behavior: "smooth" });
    }
  };

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

      const enforceSeoulBounds = () => {
        const map = mapInstanceRef.current;
        if (!map) return;
        const center = map.getCenter();
        const clampedLat = Math.min(SEOUL_BOUNDS.maxLat, Math.max(SEOUL_BOUNDS.minLat, center.lat()));
        const clampedLng = Math.min(SEOUL_BOUNDS.maxLng, Math.max(SEOUL_BOUNDS.minLng, center.lng()));
        if (Math.abs(clampedLat - center.lat()) > 0.000001 || Math.abs(clampedLng - center.lng()) > 0.000001) {
          map.setCenter(new naver.maps.LatLng(clampedLat, clampedLng));
        }
      };

      naver.maps.Event.addListener(mapInstanceRef.current, "dragend", enforceSeoulBounds);
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
            <div className="relative flex-1 min-h-[320px]">
              <div ref={mapRef} className="h-full min-h-[320px] w-full" />

              {/* Floating Carousel at the bottom */}
              <div className="absolute left-0 right-0 bottom-4 z-10 px-4 group/carousel">
                {canScrollLeft && (
                  <button
                    type="button"
                    onClick={() => scrollBy("left")}
                    className="absolute left-6 top-1/2 -translate-y-1/2 z-20 w-8 h-8 flex items-center justify-center rounded-full bg-white/90 shadow-md border border-gray-200 text-gray-700 hover:bg-white transition-all opacity-0 group-hover/carousel:opacity-100"
                    aria-label="이전 장소 보기"
                  >
                    <ChevronLeft size={18} />
                  </button>
                )}

                <div
                  ref={scrollContainerRef}
                  onScroll={checkScrollability}
                  className="flex overflow-x-auto gap-3 pt-2 pb-2 snap-x custom-scrollbar relative scroll-smooth"
                >
                  {groupedPlaces.map((group) => (
                    group.places.map((place) => {
                      const isSelected = place.mapId === selectedMapPlaceId;
                      const searchUrl = place.map_url || `https://map.naver.com/v5/search/${encodeURIComponent(place.name)}`;
                      return (
                        <div
                          key={`${group.groupId}:${place.mapId}`}
                          role="button"
                          tabIndex={0}
                          onClick={() => {
                            onSelectPlace(place.mapId);
                            onMarkerClick(place.mapId);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              onSelectPlace(place.mapId);
                              onMarkerClick(place.mapId);
                            }
                          }}
                          className={`group/card snap-center flex-shrink-0 w-[160px] text-left rounded-[20px] border p-3 pt-3.5 backdrop-blur-xl transition-all duration-300 shadow-sm hover:shadow-md hover:-translate-y-1 relative cursor-pointer ${isSelected
                            ? "border-black bg-white/95 ring-2 ring-black/10"
                            : "border-white/50 bg-white/80 hover:bg-white/95 hover:border-gray-300"
                            }`}
                        >
                          <a
                            href={searchUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="absolute top-2.5 right-2.5 text-gray-400 hover:text-blue-500 transition-colors bg-white/50 hover:bg-white/80 rounded-full p-1 opacity-0 group-hover/card:opacity-100 focus:opacity-100"
                            title="네이버 지도 객체 검색"
                          >
                            <ExternalLink size={14} />
                          </a>

                          <div className="pr-4">
                            <div className="text-[13px] font-bold text-gray-900 truncate leading-tight mb-1">{place.name}</div>
                            {!!place.adress && (
                              <div className="text-[11px] font-medium text-gray-500 truncate">{place.adress}</div>
                            )}
                          </div>
                        </div>
                      );
                    })
                  ))}
                  {!groupedPlaces.length && (
                    <p className="text-xs text-center w-full text-gray-800 bg-white/80 backdrop-blur-md rounded-xl py-3 shadow-sm mx-auto">
                      No places found for map overlay.
                    </p>
                  )}
                </div>

                {canScrollRight && (
                  <button
                    type="button"
                    onClick={() => scrollBy("right")}
                    className="absolute right-6 top-1/2 -translate-y-1/2 z-20 w-8 h-8 flex items-center justify-center rounded-full bg-white/90 shadow-md border border-gray-200 text-gray-700 hover:bg-white transition-all opacity-0 group-hover/carousel:opacity-100"
                    aria-label="다음 장소 보기"
                  >
                    <ChevronRight size={18} />
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
