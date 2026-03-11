"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Search, X } from "lucide-react";

import { DiaryPlaceSearchResult } from "@/services/api";
import {
  NaverLatLng,
  NaverMapInstance,
  NaverMarker,
  useNaverMap,
} from "@/features/chat/hooks/useNaverMap";

type DiaryLocationPickerModalProps = {
  isOpen: boolean;
  initialPlace: DiaryPlaceSearchResult | null;
  onClose: () => void;
  onConfirm: (place: DiaryPlaceSearchResult) => void;
};

const SEOUL_CITY_HALL = { latitude: 37.5665, longitude: 126.978 };
type NaverMapClickEvent = { coord?: NaverLatLng };

const isNaverMapClickEvent = (value: unknown): value is NaverMapClickEvent => {
  if (!value || typeof value !== "object") return false;
  return "coord" in value;
};

export function DiaryLocationPickerModal({
  isOpen,
  initialPlace,
  onClose,
  onConfirm,
}: DiaryLocationPickerModalProps) {
  const clientId = process.env.NEXT_PUBLIC_NAVER_MAP_CLIENT_ID;
  const { status, error: mapError, naver, retry } = useNaverMap(clientId);

  const mapRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<NaverMapInstance | null>(null);
  const markerRef = useRef<NaverMarker | null>(null);

  const [searchQuery, setSearchQuery] = useState(initialPlace?.adress ?? "");
  const [selectedPlace, setSelectedPlace] = useState<DiaryPlaceSearchResult | null>(initialPlace);
  const [searchResults, setSearchResults] = useState<DiaryPlaceSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mapInitError, setMapInitError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      markerRef.current?.setMap(null);
      markerRef.current = null;
      mapInstanceRef.current = null;
      return;
    }
    setSearchQuery(initialPlace?.adress ?? "");
    setSelectedPlace(initialPlace);
    setSearchResults([]);
    setError(null);
    setMapInitError(null);
  }, [initialPlace, isOpen]);

  useEffect(() => {
    if (!isOpen || status !== "ready" || !naver?.maps || !mapInstanceRef.current) return;

    const currentCenter = mapInstanceRef.current.getCenter();
    const rafId = window.requestAnimationFrame(() => {
      if (!mapInstanceRef.current) return;
      naver.maps.Event.trigger(mapInstanceRef.current, "resize");
      if (currentCenter) {
        mapInstanceRef.current.setCenter(currentCenter);
      }
    });

    return () => window.cancelAnimationFrame(rafId);
  }, [isOpen, naver, status]);

  const moveMarkerTo = useCallback((latLng: NaverLatLng) => {
    if (!naver?.maps || !mapInstanceRef.current) return;

    mapInstanceRef.current.setCenter(latLng);
    mapInstanceRef.current.setZoom(15);

    if (!markerRef.current) {
      markerRef.current = new naver.maps.Marker({
        position: latLng,
        map: mapInstanceRef.current,
      });
      return;
    }

    markerRef.current.setPosition(latLng);
    markerRef.current.setMap(mapInstanceRef.current);
  }, [naver]);

  const handleSelectFromMap = useCallback(async (location: NaverLatLng) => {
    if (!naver?.maps) return;

    try {
      setResolving(true);
      setError(null);
      moveMarkerTo(location);
      const result = await reverseGeocodeDiaryPlace(location.lat(), location.lng());
      if (!result) {
        setError("선택한 위치의 주소를 찾지 못했습니다.");
        return;
      }

      setSelectedPlace(result);
      setSearchQuery(result.adress);
    } catch {
      setError("선택한 위치의 주소를 찾지 못했습니다.");
    } finally {
      setResolving(false);
    }
  }, [moveMarkerTo, naver]);

  useEffect(() => {
    if (!isOpen || status !== "ready" || !naver?.maps || !mapRef.current) return;

    if (!mapInstanceRef.current) {
      const seed = initialPlace ?? selectedPlace ?? {
        adress: "",
        latitude: SEOUL_CITY_HALL.latitude,
        longitude: SEOUL_CITY_HALL.longitude,
      };

      mapInstanceRef.current = new naver.maps.Map(mapRef.current, {
        center: new naver.maps.LatLng(seed.latitude, seed.longitude),
        zoom: 14,
        minZoom: 7,
        maxZoom: 18,
      });

      naver.maps.Event.addListener(mapInstanceRef.current, "click", (...args: unknown[]) => {
        const event = args[0];
        if (!isNaverMapClickEvent(event)) return;
        const lat = event?.coord?.lat?.();
        const lng = event?.coord?.lng?.();
        if (typeof lat !== "number" || typeof lng !== "number") return;
        void handleSelectFromMapRef.current(new naver.maps.LatLng(lat, lng));
      });

      window.requestAnimationFrame(() => {
        if (!mapInstanceRef.current) return;
        naver.maps.Event.trigger(mapInstanceRef.current, "resize");
        mapInstanceRef.current.setCenter(new naver.maps.LatLng(seed.latitude, seed.longitude));
      });
    }
  }, [handleSelectFromMap, initialPlace, isOpen, naver, selectedPlace, status]);

  useEffect(() => {
    if (!isOpen || status !== "ready" || !naver?.maps || !mapInstanceRef.current) return;

    const timer = window.setTimeout(() => {
      const hasCanvas = Boolean(mapRef.current?.querySelector("canvas, img, svg"));
      if (!hasCanvas) {
        setMapInitError("지도를 불러오지 못했습니다. 네이버 지도 도메인 설정과 Dynamic Map 사용 여부를 확인해주세요.");
      }
    }, 1500);

    return () => window.clearTimeout(timer);
  }, [isOpen, naver, status]);

  useEffect(() => {
    if (!isOpen || status !== "ready" || !naver?.maps || !mapInstanceRef.current) return;

    const place = selectedPlace ?? initialPlace;
    if (!place) return;

    const latLng = new naver.maps.LatLng(place.latitude, place.longitude);
    mapInstanceRef.current.setCenter(latLng);
    mapInstanceRef.current.setZoom(15);

    if (!markerRef.current) {
      markerRef.current = new naver.maps.Marker({
        position: latLng,
        map: mapInstanceRef.current,
      });
    } else {
      markerRef.current.setPosition(latLng);
      markerRef.current.setMap(mapInstanceRef.current);
    }
  }, [initialPlace, isOpen, naver, selectedPlace, status]);

  const handleSearch = async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    const keyword = searchQuery.trim();
    if (!keyword) return;

    try {
      setSearching(true);
      setError(null);
      const res = await fetch(
        `https://dapi.kakao.com/v2/local/search/keyword.json?query=${encodeURIComponent(keyword)}`,
        { headers: { Authorization: `KakaoAK ${KAKAO_KEY}` } }
      );
      const data = await res.json();
      const results: DiaryPlaceSearchResult[] = (data.documents ?? []).map((doc: any) => ({
        name: doc.place_name || keyword,
        adress: doc.road_address_name || doc.address_name || keyword,
        latitude: parseFloat(doc.y),
        longitude: parseFloat(doc.x),
      }));
      setSearchResults(results);
      if (!results[0]) {
        setError("검색 결과가 없습니다.");
        return;
      }
    } catch {
      setError("장소 검색에 실패했습니다.");
    } finally {
      setSearching(false);
    }
  };

  const handleConfirm = () => {
    if (!selectedPlace) {
      setError("먼저 위치를 선택해주세요.");
      return;
    }
    onConfirm(selectedPlace);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-[28px] border border-zinc-800 bg-black shadow-2xl">
        <div className="flex flex-none items-center justify-between border-b border-zinc-800 px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">Location</p>
            <h3 className="mt-1 text-lg font-semibold text-white">Pick a place on the map</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white transition hover:bg-white/10"
            aria-label="Close location picker"
          >
            <X size={16} />
          </button>
        </div>

        <div className="grid min-h-0 flex-1 gap-0 md:grid-cols-[320px_minmax(0,1fr)]">
          <div className="flex flex-col overflow-y-auto border-b border-zinc-800 md:border-b-0 md:border-r">
            <div className="flex-1 p-5">
              <form className="space-y-3" onSubmit={handleSearch}>
                <label className="block text-xs font-medium uppercase tracking-[0.2em] text-zinc-500">
                  Search place or address
                </label>
                <input
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Seoul City Hall, Seongsu, Jeju Airport"
                  className="h-11 w-full rounded-full border border-zinc-800 bg-zinc-950 px-4 text-sm text-zinc-100 outline-none placeholder:text-zinc-600"
                />
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={searching}
                    className="inline-flex h-9 items-center gap-2 rounded-full bg-white px-4 text-sm font-semibold text-black transition hover:bg-zinc-200 disabled:opacity-60"
                  >
                    {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search size={14} />}
                    Search
                  </button>
                </div>
              </form>

              <p className="mt-4 text-xs leading-5 text-zinc-500">
                Search first, choose one result, then confirm the location for this diary.
              </p>

              {selectedPlace && (
                <div className="mt-4 flex items-center gap-3 rounded-2xl border border-zinc-700 bg-zinc-950/80 p-3">
                  <div className="rounded-full border border-zinc-800 bg-white/5 p-2 text-zinc-200 shrink-0">
                    <MapPin className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Selected</p>
                    <p className="mt-0.5 text-sm font-medium text-zinc-100 truncate">
                      {selectedPlace.name?.trim() || "Pinned location"}
                    </p>
                    <p className="text-xs leading-5 text-zinc-400 truncate">{selectedPlace.adress}</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleConfirm}
                    disabled={resolving}
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-black transition hover:bg-zinc-200 disabled:opacity-60"
                    aria-label="Use this location"
                  >
                    {resolving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check size={16} />}
                  </button>
                </div>
              )}

              {searchResults.length > 0 && (
                <div className="mt-4">
                  <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">
                    Search Results
                  </p>
                  <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
                    {searchResults.map((result, index) => {
                      const isActive =
                        selectedPlace?.adress === result.adress &&
                        selectedPlace?.latitude === result.latitude &&
                        selectedPlace?.longitude === result.longitude;

                      return (
                        <button
                          key={`${result.adress}-${result.latitude}-${result.longitude}-${index}`}
                          type="button"
                          onClick={() => handlePreviewPlace(result)}
                          className={`w-full rounded-2xl border px-3 py-3 text-left transition ${isActive
                              ? "border-white/30 bg-white/10"
                              : "border-zinc-800 bg-zinc-950/70 hover:border-zinc-700 hover:bg-zinc-900"
                            }`}
                        >
                          <p className="text-sm font-medium text-zinc-100">{result.name?.trim() || "Search result"}</p>
                          <p className="mt-1 text-xs leading-5 text-zinc-400">{result.adress}</p>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {(error || mapError || mapInitError) && (
                <p className="mt-4 text-sm text-rose-400">{error || mapError || mapInitError}</p>
              )}
            </div>

            {status === "error" && (
              <div className="flex flex-none justify-end border-t border-zinc-800 p-4">
                <button
                  type="button"
                  onClick={retry}
                  className="rounded-full border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-200 transition hover:bg-zinc-900"
                >
                  Retry map
                </button>
              </div>
            )}
          </div>

          <div className="relative min-h-[380px] bg-zinc-950">
            {status === "loading" && (
              <div className="absolute inset-0 flex items-center justify-center text-sm text-zinc-400">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading map...
              </div>
            )}
            {status === "ready" && <div ref={mapRef} className="absolute inset-0 h-full w-full" />}
            {status === "ready" && mapInitError && (
              <div className="absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-zinc-500">
                {mapInitError}
              </div>
            )}
            {status === "error" && (
              <div className="absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-zinc-500">
                {mapError}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
