"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type NaverMapStatus = "idle" | "loading" | "ready" | "error";
export type NaverLatLng = { lat: () => number; lng: () => number };
export type NaverMapInstance = {
  setCenter: (latLng: NaverLatLng) => void;
  setZoom: (zoom: number) => void;
  fitBounds: (bounds: NaverLatLngBounds, padding?: { top: number; right: number; bottom: number; left: number }) => void;
};
export type NaverMarker = {
  getPosition: () => NaverLatLng;
  setMap: (map: NaverMapInstance | null) => void;
};
export type NaverInfoWindow = {
  setContent: (content: string) => void;
  open: (map: NaverMapInstance, marker: NaverMarker) => void;
  close: () => void;
};
export type NaverLatLngBounds = {
  extend: (latLng: NaverLatLng) => void;
};

export type NaverMapsNamespace = {
  maps: {
    Map: new (element: HTMLElement, options: Record<string, unknown>) => NaverMapInstance;
    LatLng: new (latitude: number, longitude: number) => NaverLatLng;
    Marker: new (options: Record<string, unknown>) => NaverMarker;
    InfoWindow: new (options: Record<string, unknown>) => NaverInfoWindow;
    LatLngBounds: new () => NaverLatLngBounds;
    Size: new (width: number, height: number) => unknown;
    Point: new (x: number, y: number) => unknown;
    Event: {
      addListener: (target: unknown, eventName: string, listener: () => void) => void;
    };
  };
};

const NAVER_MAP_SCRIPT_ID = "triver-naver-map-sdk";

export function useNaverMap(clientId?: string) {
  const normalizedClientId = clientId?.trim() || "";
  const [status, setStatus] = useState<NaverMapStatus>("idle");
  const [error, setError] = useState<string>("");
  const [retryCount, setRetryCount] = useState(0);

  const retry = useCallback(() => {
    const existing = document.getElementById(NAVER_MAP_SCRIPT_ID);
    if (existing?.parentNode) existing.parentNode.removeChild(existing);
    setStatus("idle");
    setError("");
    setRetryCount((prev) => prev + 1);
  }, []);

  useEffect(() => {
    if (!normalizedClientId) {
      return;
    }

    if (typeof window === "undefined") return;
    const commit = (nextStatus: NaverMapStatus, nextError = "") => {
      queueMicrotask(() => {
        setStatus(nextStatus);
        setError(nextError);
      });
    };

    const naverWindow = window as Window & { naver?: NaverMapsNamespace };
    const naver = naverWindow.naver;
    if (naver?.maps) {
      commit("ready");
      return;
    }

    commit("loading");

    const existing = document.getElementById(NAVER_MAP_SCRIPT_ID) as HTMLScriptElement | null;
    if (existing) {
      const onLoad = () => {
        const loadedNaver = naverWindow.naver;
        if (loadedNaver?.maps) {
          setStatus("ready");
          setError("");
        } else {
          setStatus("error");
          setError("Naver Maps SDK loaded, but maps object is unavailable.");
        }
      };
      const onError = () => {
        setStatus("error");
        setError("Failed to load Naver Maps SDK.");
      };
      existing.addEventListener("load", onLoad);
      existing.addEventListener("error", onError);
      return () => {
        existing.removeEventListener("load", onLoad);
        existing.removeEventListener("error", onError);
      };
    }

    const script = document.createElement("script");
    script.id = NAVER_MAP_SCRIPT_ID;
    script.src = `https://openapi.map.naver.com/openapi/v3/maps.js?ncpClientId=${encodeURIComponent(normalizedClientId)}`;
    script.async = true;

    script.onload = () => {
      const loadedNaver = naverWindow.naver;
      if (loadedNaver?.maps) {
        setStatus("ready");
        setError("");
      } else {
        setStatus("error");
        setError("Naver Maps SDK loaded, but maps object is unavailable.");
      }
    };

    script.onerror = () => {
      setStatus("error");
      setError("Failed to load Naver Maps SDK.");
    };

    document.head.appendChild(script);
  }, [normalizedClientId, retryCount]);

  const naver = useMemo<NaverMapsNamespace | null>(() => {
    if (typeof window === "undefined") return null;
    return (window as Window & { naver?: NaverMapsNamespace }).naver ?? null;
  }, [status]);

  if (!normalizedClientId) {
    return {
      status: "error" as const,
      error: "NEXT_PUBLIC_NAVER_MAP_CLIENT_ID is not configured.",
      naver: null,
      retry,
    };
  }

  return { status, error, naver, retry };
}
