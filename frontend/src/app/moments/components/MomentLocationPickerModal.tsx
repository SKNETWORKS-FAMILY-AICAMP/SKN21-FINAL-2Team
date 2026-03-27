"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
// [Feature] 모달 transition animation 적용
import { AnimatePresence, motion } from "framer-motion";
import { Check, Loader2, MapPin, Search, X } from "lucide-react";

import { MomentPlaceSearchResult as DiaryPlaceSearchResult } from "@/services/api";
import {
  NaverLatLng,
  NaverMapInstance,
  NaverMarker,
  useNaverMap,
} from "@/features/chat/hooks/useNaverMap";
import { useTranslation } from "@/i18n/useTranslation";

type MomentLocationPickerModalProps = {
  isOpen: boolean;
  initialPlace: DiaryPlaceSearchResult | null;
  onClose: () => void;
  onConfirm: (place: DiaryPlaceSearchResult) => void;
};

const SEOUL_CITY_HALL = { latitude: 37.5665, longitude: 126.978 };
const KAKAO_KEY = process.env.NEXT_PUBLIC_KAKAO_REST_API_KEY ?? "";

export function MomentLocationPickerModal({
  isOpen,
  initialPlace,
  onClose,
  onConfirm,
}: MomentLocationPickerModalProps) {
  const clientId = process.env.NEXT_PUBLIC_NAVER_MAP_CLIENT_ID || "";
  const { t, language } = useTranslation();
  const { status, error: mapError, naver, retry } = useNaverMap(clientId, { language });

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
    try {
      setResolving(true);
      setError(null);
      moveMarkerTo(location);

      const res = await fetch(
        `https://dapi.kakao.com/v2/local/geo/coord2address.json?x=${location.lng()}&y=${location.lat()}`,
        { headers: { Authorization: `KakaoAK ${KAKAO_KEY}` } }
      );
      const data = await res.json();
      const doc = data.documents?.[0];
      if (!doc) {
        setError(t("location.addressNotFound"));
        return;
      }
      const adress =
        doc.road_address?.address_name || doc.address?.address_name;
      if (!adress) {
        setError(t("location.addressNotFound"));
        return;
      }
      const name =
        doc.road_address?.building_name?.trim() ||
        [doc.road_address?.region_2depth_name, doc.road_address?.region_3depth_name]
          .filter(Boolean).join(" ") ||
        doc.address?.region_3depth_name ||
        null;

      setSelectedPlace({ name, adress, latitude: location.lat(), longitude: location.lng() });
      setSearchQuery(adress);
      setSearchResults([]);
    } catch {
      setError(t("location.addressNotFound"));
    } finally {
      setResolving(false);
    }
  }, [moveMarkerTo]);

  // ref to always call the latest handleSelectFromMap from the map click listener
  const handleSelectFromMapRef = useRef(handleSelectFromMap);
  useEffect(() => {
    handleSelectFromMapRef.current = handleSelectFromMap;
  }, [handleSelectFromMap]);

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

      naver.maps.Event.addListener(mapInstanceRef.current, "click", (event: any) => {
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
  }, [initialPlace, isOpen, naver, selectedPlace, status]);

  useEffect(() => {
    if (!isOpen || status !== "ready" || !naver?.maps || !mapInstanceRef.current) return;

    const timer = window.setTimeout(() => {
      const hasCanvas = Boolean(mapRef.current?.querySelector("canvas, img, svg"));
      if (!hasCanvas) {
        setMapInitError(t("location.mapInitError"));
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
        setError(t("location.noResults"));
        return;
      }
    } catch {
      setError(t("location.searchFailed"));
    } finally {
      setSearching(false);
    }
  };

  const handlePreviewPlace = (place: DiaryPlaceSearchResult) => {
    setSelectedPlace(place);
    setSearchQuery(place.adress);
    setError(null);
    if (!naver?.maps) return;
    moveMarkerTo(new naver.maps.LatLng(place.latitude, place.longitude));
  };

  const handleConfirm = () => {
    if (!selectedPlace) {
      setError(t("location.selectFirst"));
      return;
    }
    onConfirm(selectedPlace);
  };

  return (
    // [Feature] 부드러운 페이드 인/아웃 애니메이션
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[70] bg-black/30 backdrop-blur-md"
            onClick={onClose}
          />

          {/* Modal Container */}
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 10 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 10 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="fixed inset-0 z-[71] flex items-center justify-center p-4 pointer-events-none"
          >
            <div
              className="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-[2.5rem] bg-white border border-gray-100 shadow-[0_32px_80px_-16px_rgba(0,0,0,0.08)] pointer-events-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex flex-none items-center justify-between border-b border-gray-50 px-8 py-6">
                <div className="flex items-center gap-3">
                   <div className="w-10 h-10 bg-black rounded-xl flex items-center justify-center shadow-lg">
                      <MapPin size={18} className="text-white" />
                   </div>
                   <div className="flex items-center gap-2 mt-0.5">
                      <h2 className="text-[14px] font-bold text-[#8b98a5] uppercase">
                          {t("location.label")}
                      </h2>
                      <span className="w-1 h-3 rounded-full bg-black/10 mx-1" />
                      <p className="text-[15px] font-bold text-gray-900">
                          {t("location.pickOnMap")}
                      </p>
                   </div>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="p-2.5 text-gray-400 hover:text-gray-800 hover:bg-black/[0.03] rounded-full transition-all"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Body */}
              <div className="grid min-h-0 flex-1 gap-0 md:grid-cols-[340px_minmax(0,1fr)]">
                {/* Search Sidebar */}
                <div className="flex flex-col overflow-y-auto border-b border-gray-100 md:border-b-0 md:border-r bg-gray-50/30">
                  <div className="flex-1 p-6">
                    <form className="space-y-4" onSubmit={handleSearch}>
                      <label className="block text-[11px] font-bold text-[#8b98a5] uppercase px-1">
                        {t("location.searchLabel")}
                      </label>
                      <div className="relative">
                        <input
                          value={searchQuery}
                          onChange={(event) => setSearchQuery(event.target.value)}
                          placeholder={t("location.searchPlaceholder")}
                          className="h-12 w-full rounded-2xl border border-gray-100 bg-white pl-5 pr-12 text-sm text-gray-700 outline-none shadow-sm focus:border-black/20 transition-all"
                        />
                        <button
                          type="submit"
                          disabled={searching}
                          className="absolute right-1.5 top-1/2 -translate-y-1/2 flex h-9 w-9 items-center justify-center rounded-xl bg-black text-white shadow-sm hover:bg-gray-800 disabled:opacity-50 transition-all"
                        >
                          {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search size={16} />}
                        </button>
                      </div>
                    </form>

                    <p className="mt-4 px-1 text-xs leading-relaxed text-gray-400">
                      {t("location.helperText")}
                    </p>

                    {selectedPlace && (
                      <div className="mt-8 rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
                        <div className="flex items-center gap-3 mb-4">
                          <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center text-gray-400">
                            <MapPin size={14} />
                          </div>
                          <p className="text-[11px] font-bold text-[#8b98a5] uppercase">{t("location.selected")}</p>
                        </div>
                        <div className="mb-5">
                          <p className="text-[15px] font-bold text-gray-900 truncate">
                            {selectedPlace.name?.trim() || t("location.fixedPlace")}
                          </p>
                          <p className="mt-1 text-xs leading-relaxed text-gray-500 line-clamp-2">{selectedPlace.adress}</p>
                        </div>
                        <button
                          type="button"
                          onClick={handleConfirm}
                          disabled={resolving}
                          className="w-full py-3.5 rounded-xl bg-black text-white text-sm font-bold shadow-md hover:bg-gray-800 disabled:opacity-50 flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
                        >
                          {resolving ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                           {t("common.confirm") || "Confirm"}
                        </button>
                      </div>
                    )}

                    {searchResults.length > 0 && (
                      <div className="mt-8">
                        <p className="mb-3 px-1 text-[11px] font-bold text-[#8b98a5] uppercase">
                          {t("location.searchResults")}
                        </p>
                        <div className="max-h-64 space-y-2 overflow-y-auto pr-2 custom-scrollbar">
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
                                className={`w-full rounded-2xl border p-4 text-left transition-all ${isActive
                                    ? "border-black/10 bg-white shadow-sm ring-1 ring-black/5"
                                    : "border-gray-50 bg-white/50 hover:bg-white hover:border-gray-100"
                                  }`}
                              >
                                <p className={`text-sm font-bold ${isActive ? "text-black" : "text-gray-700"}`}>
                                    {result.name?.trim() || t("location.searchResults")}
                                </p>
                                <p className="mt-1 text-xs leading-relaxed text-gray-400">{result.adress}</p>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {(error || mapError || mapInitError) && (
                      <p className="mt-6 px-1 text-sm text-red-500 font-medium">{error || mapError || mapInitError}</p>
                    )}
                  </div>
                </div>

                {/* Map Section */}
                <div className="relative min-h-[400px] bg-gray-50">
                  {status === "loading" && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 gap-3">
                      <Loader2 className="h-6 w-6 animate-spin" />
                      <p className="text-xs font-medium">{t("location.loadingMap")}</p>
                    </div>
                  )}
                  {status === "ready" && <div ref={mapRef} className="absolute inset-0 h-full w-full" />}
                  {status === "error" && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center p-10 text-center gap-4">
                       <p className="text-sm text-gray-400 font-medium">{mapError}</p>
                       <button
                        type="button"
                        onClick={retry}
                        className="px-5 py-2.5 rounded-full bg-white border border-gray-100 text-xs font-bold text-gray-600 shadow-sm hover:bg-gray-50 transition-all"
                      >
                        {t("location.reloadMap")}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
