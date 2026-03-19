"use client";

import { useCallback, useState } from "react";
import {
  fetchDirections,
  fetchTransitDirections,
  DirectionsPlace,
  DirectionsResult,
  DirectionsOption,
  TransitDirectionsResult,
  TransitSegment,
} from "@/services/api";

export type TransportMode = "driving" | "transit";

export interface RouteInfo {
  distance: number;   // m
  duration: number;   // driving: ms, transit: 분
  tollFare: number;
  fuelPrice: number;
}

export interface TransitInfo {
  duration: number;       // 분
  fare: number;           // 원
  transfers: number;
  distance: number;
  segments: TransitSegment[];
}

export function useDirections() {
  const [routePath, setRoutePath] = useState<[number, number][] | null>(null);
  const [routeInfo, setRouteInfo] = useState<RouteInfo | null>(null);
  const [transitInfo, setTransitInfo] = useState<TransitInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [option, setOption] = useState<DirectionsOption>("trafast");
  const [mode, setMode] = useState<TransportMode>("driving");

  const togglePlace = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const calculateRoute = useCallback(
    async (places: DirectionsPlace[]) => {
      if (places.length < 2) return;
      setIsLoading(true);
      setError(null);
      try {
        if (mode === "driving") {
          const result: DirectionsResult = await fetchDirections(places, option);
          setRoutePath(result.path);
          setRouteInfo({
            distance: result.distance,
            duration: result.duration,
            tollFare: result.toll_fare,
            fuelPrice: result.fuel_price,
          });
          setTransitInfo(null);
        } else {
          const result: TransitDirectionsResult = await fetchTransitDirections(places);
          // 대중교통: 정류장 좌표들을 합쳐서 폴리라인으로 사용
          const allPath: [number, number][] = [];
          for (const seg of result.segments) {
            if (seg.path && seg.path.length > 0) {
              allPath.push(...seg.path);
            }
          }
          setRoutePath(allPath.length > 0 ? allPath : null);
          setTransitInfo({
            duration: result.duration,
            fare: result.fare,
            transfers: result.transfers,
            distance: result.distance,
            segments: result.segments,
          });
          setRouteInfo(null);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "경로 조회 실패");
        setRoutePath(null);
        setRouteInfo(null);
        setTransitInfo(null);
      } finally {
        setIsLoading(false);
      }
    },
    [option, mode],
  );

  const clearRoute = useCallback(() => {
    setRoutePath(null);
    setRouteInfo(null);
    setTransitInfo(null);
    setError(null);
  }, []);

  const clearAll = useCallback(() => {
    clearRoute();
    setSelectedIds(new Set());
  }, [clearRoute]);

  return {
    routePath,
    routeInfo,
    transitInfo,
    isLoading,
    error,
    selectedIds,
    option,
    setOption,
    mode,
    setMode,
    togglePlace,
    calculateRoute,
    clearRoute,
    clearAll,
  };
}
