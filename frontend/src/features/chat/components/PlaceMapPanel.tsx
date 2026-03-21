"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { MapPin, RefreshCw, ChevronLeft, ChevronRight, ExternalLink, Navigation, Loader2, Car, TrainFront } from "lucide-react";
import { NaverInfoWindow, NaverMapInstance, NaverMarker, NaverPolyline, useNaverMap } from "../hooks/useNaverMap";
import { useTranslation } from "@/i18n/useTranslation";
import type { DirectionsOption } from "@/services/api";
import type { RouteInfo, TransitInfo, TransportMode } from "../hooks/useDirections";

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
  focusPlaces?: ChatMapPlace[];
  groups?: ChatMapPlaceGroup[];
  selectedMapPlaceId: string | null;
  onSelectPlace: (mapId: string) => void;
  onMarkerClick: (mapId: string) => void;
  className?: string;
  showHeader?: boolean;
  isPanelOpen?: boolean;
  panelWidth?: number;
  isResizing?: boolean;
  // 길찾기 관련
  dirSelectedIds?: Set<string>;
  onToggleDirPlace?: (mapId: string) => void;
  routePath?: [number, number][] | null;
  routeInfo?: RouteInfo | null;
  dirOption?: DirectionsOption;
  onDirOptionChange?: (option: DirectionsOption) => void;
  onRequestDirections?: () => void;
  onClearRoute?: () => void;
  isDirLoading?: boolean;
  dirError?: string | null;
  // 대중교통
  transitInfo?: TransitInfo | null;
  transportMode?: TransportMode;
  onTransportModeChange?: (mode: TransportMode) => void;
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
  focusPlaces,
  groups,
  selectedMapPlaceId,
  onSelectPlace,
  onMarkerClick,
  className,
  showHeader = true,
  isPanelOpen = true,
  panelWidth,
  isResizing = false,
  dirSelectedIds,
  onToggleDirPlace,
  routePath,
  routeInfo,
  dirOption = "trafast",
  onDirOptionChange,
  onRequestDirections,
  onClearRoute,
  isDirLoading = false,
  dirError,
  transitInfo,
  transportMode = "driving",
  onTransportModeChange,
}: PlaceMapPanelProps) {
  const clientId = process.env.NEXT_PUBLIC_NAVER_MAP_CLIENT_ID || "";
  const { language } = useTranslation();
  const { status, error, naver, retry } = useNaverMap(clientId, { language });

  const mapRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<NaverMapInstance | null>(null);
  const markersRef = useRef<Map<string, NaverMarker>>(new Map());
  const infoWindowRef = useRef<NaverInfoWindow | null>(null);
  const polylineRef = useRef<NaverPolyline | null>(null);

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

  const groupedPlacesKey = groupedPlaces.map(g => g.groupId + g.places.length).join('|');

  useEffect(() => {
    checkScrollability();
    window.addEventListener("resize", checkScrollability);
    return () => window.removeEventListener("resize", checkScrollability);
  }, [checkScrollability, groupedPlacesKey]);

  useEffect(() => {
    if (!isPanelOpen || status !== "ready" || !naver?.maps || !mapInstanceRef.current) return;

    const map = mapInstanceRef.current;
    const currentCenter = map.getCenter();

    const rafId = window.requestAnimationFrame(() => {
      naver.maps.Event.trigger(map, "resize");
      if (currentCenter) {
        map.setCenter(currentCenter);
      }
    });

    return () => {
      window.cancelAnimationFrame(rafId);
    };
  }, [isPanelOpen, panelWidth, isResizing, naver, status]);

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
        backgroundColor: "transparent",
        borderColor: "transparent",
        borderWidth: 0,
        disableAnchor: true,
        pixelOffset: new naver.maps.Point(0, -4),
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

    // fitBounds: focusPlaces(새 메시지 장소)가 있으면 그것만, 없으면 전체
    const fitTargets = (focusPlaces && focusPlaces.length > 0) ? focusPlaces : sortedPlaces;
    if (fitTargets.length === 1) {
      map.setCenter(new naver.maps.LatLng(fitTargets[0].latitude, fitTargets[0].longitude));
      map.setZoom(14);
    } else if (fitTargets.length > 1) {
      const fitBounds = new naver.maps.LatLngBounds();
      fitTargets.forEach((p) => fitBounds.extend(new naver.maps.LatLng(p.latitude, p.longitude)));
      map.fitBounds(fitBounds, { top: 50, right: 40, bottom: 50, left: 40 });
    }

    if (selectedMapPlaceId && infoWindowRef.current) {
      const selected = sortedPlaces.find((p) => p.mapId === selectedMapPlaceId);
      const marker = markersRef.current.get(selectedMapPlaceId);
      if (selected && marker) {
        const content = `
          <div style="position: relative; padding-bottom: 11px; pointer-events: none; transform: translateY(-2px); filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1));">
            <div style="background-color: #ffffff; padding: 6px 12px; border-radius: 6px; border: 1px solid #e5e7eb; color: #111827; font-size: 13px; font-weight: 600; max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: center;">
              ${escapeHtml(selected.name)}
            </div>
            <div style="position: absolute; bottom: 5px; left: 50%; margin-left: -7px; transform: rotate(45deg); width: 14px; height: 14px; background-color: #ffffff; border-right: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb; clip-path: polygon(100% 0, 100% 100%, 0 100%);"></div>
          </div>
        `;
        infoWindowRef.current.setContent(content);
        infoWindowRef.current.open(map, marker);
      } else {
        infoWindowRef.current.close();
      }
    } else if (infoWindowRef.current) {
      infoWindowRef.current.close();
    }
  }, [status, naver, sortedPlaces, focusPlaces, selectedMapPlaceId, onMarkerClick, onSelectPlace]);

  // 폴리라인 렌더링
  useEffect(() => {
    if (polylineRef.current) {
      polylineRef.current.setMap(null);
      polylineRef.current = null;
    }

    if (!routePath || routePath.length < 2 || !naver?.maps || !mapInstanceRef.current) return;

    const path = routePath.map(([lng, lat]) => new naver.maps.LatLng(lat, lng));
    polylineRef.current = new naver.maps.Polyline({
      map: mapInstanceRef.current,
      path,
      strokeColor: "#2563eb",
      strokeWeight: 5,
      strokeOpacity: 0.85,
      strokeStyle: "solid",
      strokeLineCap: "round",
      strokeLineJoin: "round",
    });

    // 경로에 맞게 지도 범위 조정
    const bounds = new naver.maps.LatLngBounds();
    path.forEach((p) => bounds.extend(p));
    mapInstanceRef.current.fitBounds(bounds, { top: 60, right: 40, bottom: 120, left: 40 });
  }, [routePath, naver]);

  const dirSelectedCount = dirSelectedIds?.size ?? 0;

  const OPTION_LABELS: Record<DirectionsOption, string> = {
    trafast: "빠른길",
    tracomfort: "편한길",
    traoptimal: "최적",
    tradistance: "최단거리",
  };

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
    <div className={`flex flex-col h-full min-h-0 min-w-0 bg-white ${className}`}>
      {showHeader && (
        <div className="flex-none px-4 py-3 border-b border-gray-100 bg-white z-10">
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
        <div className="flex-1 flex flex-col min-h-0 relative">
          <div className="flex-1 relative min-h-[320px]">
            <div ref={mapRef} className="absolute inset-0 w-full h-full" />

            {/* 경로 정보 오버레이 — 자동차 */}
            {routeInfo && (
              <div className="absolute top-3 left-3 z-20 bg-white/95 backdrop-blur-md rounded-2xl shadow-lg border border-gray-200 px-4 py-2.5 flex items-center gap-3">
                <Car size={14} className="text-blue-600 flex-shrink-0" />
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-bold text-gray-900">
                    {routeInfo.distance >= 1000
                      ? `${(routeInfo.distance / 1000).toFixed(1)}km`
                      : `${routeInfo.distance}m`}
                  </span>
                </div>
                <div className="w-px h-4 bg-gray-300" />
                <span className="text-sm font-semibold text-gray-700">
                  {routeInfo.duration >= 3600000
                    ? `${Math.floor(routeInfo.duration / 3600000)}시간 ${Math.round((routeInfo.duration % 3600000) / 60000)}분`
                    : `${Math.round(routeInfo.duration / 60000)}분`}
                </span>
                {routeInfo.tollFare > 0 && (
                  <>
                    <div className="w-px h-4 bg-gray-300" />
                    <span className="text-xs text-gray-500">톨비 {routeInfo.tollFare.toLocaleString()}원</span>
                  </>
                )}
                <button type="button" onClick={onClearRoute} className="ml-1 text-gray-400 hover:text-gray-600 text-xs font-medium">✕</button>
              </div>
            )}

            {/* 경로 정보 오버레이 — 대중교통 */}
            {transitInfo && (
              <div className="absolute top-3 left-3 z-20 bg-white/95 backdrop-blur-md rounded-2xl shadow-lg border border-gray-200 px-4 py-2.5 max-w-[320px]">
                <div className="flex items-center gap-3 mb-2">
                  <TrainFront size={14} className="text-green-600 flex-shrink-0" />
                  <span className="text-sm font-bold text-gray-900">
                    {transitInfo.duration >= 60
                      ? `${Math.floor(transitInfo.duration / 60)}시간 ${transitInfo.duration % 60}분`
                      : `${transitInfo.duration}분`}
                  </span>
                  <div className="w-px h-4 bg-gray-300" />
                  <span className="text-sm font-semibold text-gray-700">{transitInfo.fare.toLocaleString()}원</span>
                  {transitInfo.transfers > 0 && (
                    <>
                      <div className="w-px h-4 bg-gray-300" />
                      <span className="text-xs text-gray-500">환승 {transitInfo.transfers}회</span>
                    </>
                  )}
                  <button type="button" onClick={onClearRoute} className="ml-1 text-gray-400 hover:text-gray-600 text-xs font-medium">✕</button>
                </div>
                {/* 구간 상세 */}
                <div className="flex flex-wrap gap-1">
                  {transitInfo.segments.filter(s => s.traffic_type !== 3).map((seg, i) => (
                    <span
                      key={i}
                      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                        seg.traffic_type === 1
                          ? "bg-blue-100 text-blue-700"
                          : "bg-green-100 text-green-700"
                      }`}
                    >
                      {seg.traffic_type === 1 ? seg.lane_name : seg.bus_no}
                      <span className="font-normal opacity-70">{seg.station_count}정거장</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 에러 표시 */}
            {dirError && (
              <div className="absolute top-3 left-3 z-20 bg-red-50/95 backdrop-blur-md rounded-2xl shadow-lg border border-red-200 px-4 py-2.5">
                <span className="text-sm text-red-600">{dirError}</span>
              </div>
            )}

            {/* 길찾기 컨트롤 바 */}
            {onToggleDirPlace && (
              <div className="absolute top-3 right-3 z-20 flex items-center gap-2">
                {/* 자동차 / 대중교통 모드 전환 */}
                {onTransportModeChange && dirSelectedCount >= 2 && (
                  <div className="flex h-8 rounded-lg border border-gray-200 bg-white/95 backdrop-blur-md overflow-hidden shadow-sm">
                    <button
                      type="button"
                      onClick={() => onTransportModeChange("driving")}
                      className={`px-2.5 flex items-center gap-1 text-xs font-medium transition-colors ${
                        transportMode === "driving"
                          ? "bg-blue-600 text-white"
                          : "text-gray-600 hover:bg-gray-100"
                      }`}
                    >
                      <Car size={13} />
                    </button>
                    <button
                      type="button"
                      onClick={() => onTransportModeChange("transit")}
                      className={`px-2.5 flex items-center gap-1 text-xs font-medium transition-colors ${
                        transportMode === "transit"
                          ? "bg-green-600 text-white"
                          : "text-gray-600 hover:bg-gray-100"
                      }`}
                    >
                      <TrainFront size={13} />
                    </button>
                  </div>
                )}
                {dirSelectedCount >= 2 && transportMode === "driving" && (
                  <select
                    value={dirOption}
                    onChange={(e) => onDirOptionChange?.(e.target.value as DirectionsOption)}
                    className="h-8 px-2 rounded-lg border border-gray-200 bg-white/95 backdrop-blur-md text-xs font-medium text-gray-700 shadow-sm"
                  >
                    {(Object.entries(OPTION_LABELS) as [DirectionsOption, string][]).map(([val, label]) => (
                      <option key={val} value={val}>{label}</option>
                    ))}
                  </select>
                )}
                <button
                  type="button"
                  onClick={onRequestDirections}
                  disabled={dirSelectedCount < 2 || isDirLoading}
                  className={`h-8 px-3 rounded-lg text-white text-xs font-semibold shadow-sm disabled:opacity-40 disabled:cursor-not-allowed transition-colors inline-flex items-center gap-1.5 ${
                    transportMode === "transit"
                      ? "bg-green-600 hover:bg-green-700"
                      : "bg-blue-600 hover:bg-blue-700"
                  }`}
                >
                  {isDirLoading ? <Loader2 size={13} className="animate-spin" /> : <Navigation size={13} />}
                  길찾기{dirSelectedCount > 0 ? ` (${dirSelectedCount})` : ""}
                </button>
              </div>
            )}

            {/* Floating Carousel at the bottom */}
            <div className="absolute left-0 right-0 bottom-3 sm:bottom-4 z-10 px-3 sm:px-4 group/carousel">
              {canScrollLeft && (
                <button
                  type="button"
                  onClick={() => scrollBy("left")}
                  className="absolute left-4 sm:left-6 top-1/2 -translate-y-1/2 z-20 w-8 h-8 flex items-center justify-center rounded-full bg-white/90 shadow-md border border-gray-200 text-gray-700 hover:bg-white transition-all opacity-0 group-hover/carousel:opacity-100"

                >
                  <ChevronLeft size={18} />
                </button>
              )}

              <div
                ref={scrollContainerRef}
                onScroll={checkScrollability}
                className="flex overflow-x-auto gap-2.5 sm:gap-3 pt-2 pb-2 pr-2 snap-x custom-scrollbar relative scroll-smooth"
              >
                {groupedPlaces.map((group) => (
                  group.places.map((place) => {
                    const isSelected = place.mapId === selectedMapPlaceId;
                    const isDirChecked = dirSelectedIds?.has(place.mapId) ?? false;
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
                        className={`group/card snap-center flex-shrink-0 w-[min(76vw,220px)] sm:w-[160px] text-left rounded-[20px] border p-3 pt-3.5 backdrop-blur-xl transition-all duration-300 shadow-sm hover:shadow-md hover:-translate-y-1 relative cursor-pointer ${isSelected
                          ? "border-black bg-white/95 ring-2 ring-black/10"
                          : isDirChecked
                            ? "border-blue-400 bg-blue-50/90 ring-1 ring-blue-200"
                            : "border-white/50 bg-white/80 hover:bg-white/95 hover:border-gray-300"
                          }`}
                      >
                        {/* 길찾기 체크박스 */}
                        {onToggleDirPlace && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onToggleDirPlace(place.mapId);
                            }}
                            className={`absolute top-2.5 left-2.5 w-5 h-5 rounded-md border-2 flex items-center justify-center transition-colors ${
                              isDirChecked
                                ? "bg-blue-600 border-blue-600 text-white"
                                : "border-gray-300 bg-white/80 hover:border-blue-400"
                            }`}
                            title="길찾기에 포함"
                          >
                            {isDirChecked && (
                              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                                <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                              </svg>
                            )}
                          </button>
                        )}

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

                        <div className={onToggleDirPlace ? "pl-5 pr-4" : "pr-4"}>
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
                  className="absolute right-4 sm:right-6 top-1/2 -translate-y-1/2 z-20 w-8 h-8 flex items-center justify-center rounded-full bg-white/90 shadow-md border border-gray-200 text-gray-700 hover:bg-white transition-all opacity-0 group-hover/carousel:opacity-100"

                >
                  <ChevronRight size={18} />
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
