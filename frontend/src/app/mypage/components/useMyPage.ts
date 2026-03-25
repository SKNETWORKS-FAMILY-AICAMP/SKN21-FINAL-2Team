import { useState, useEffect } from "react";
import type { ReservationItem, TripSummary } from "../types";
import {
  fetchBookmarkedRooms,
  fetchReservations,
  createReservation,
  deleteReservation,
  fetchTodayRecommendation,
  fetchCurrentUser,
  fetchRooms,
  updateCurrentUser,
  type TodayRecommendationItem,
  type ReservationRecord,
} from "@/services/api";

function formatKstDate(dateLike?: string | null) {
  if (!dateLike) return "-";
  const parsed = new Date(dateLike);
  if (Number.isNaN(parsed.getTime())) return "-";
  return parsed.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function mapReservationRecordToItem(item: ReservationRecord): ReservationItem {
  const dynamicDetails = item.details
    ? Object.entries(item.details).map(([k, v]) => ({ label: k, value: String(v) }))
    : [];

  return {
    id: `reservation-${item.id}`,
    reservationId: item.id,
    category: (item.category as ReservationItem["category"]) || "etc",
    title: item.name?.trim() || "Reservation",
    subtitle: "Saved Reservation",
    dateLabel: formatKstDate(item.date || item.created_at),
    reservationImageUrl: item.image_path ?? undefined,
    identifierLabel: "Reservation ID",
    identifierValue: String(item.id),
    details: dynamicDetails,
  };
}

export function useMyPage() {
  const [userProfile, setUserProfile] = useState({
    nickname: "",
    bio: "",
    countryCode: "",
    preferences: [] as string[],
    profile_picture: "",
    birthday: "",
  });
  const [userInsight, setUserInsight] = useState({
    planPrefer: "",
    vibePrefer: "",
    placesPrefer: "",
  });
  const [draftInsight, setDraftInsight] = useState({
    planPrefer: "",
    vibePrefer: "",
    placesPrefer: "",
  });
  const [todayRecommendation, setTodayRecommendation] = useState<TodayRecommendationItem | null>(null);
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [reservations, setReservations] = useState<ReservationItem[]>([]);
  const [bookmarkedRoomCount, setBookmarkedRoomCount] = useState<number>(0);
  
  const [isEditingPreferences, setIsEditingPreferences] = useState<boolean>(false);
  const [isSavingPreferences, setIsSavingPreferences] = useState<boolean>(false);
  const [draftExtraPreferences, setDraftExtraPreferences] = useState<string[]>([]);
  const [showPreferenceSavedPopup, setShowPreferenceSavedPopup] = useState<boolean>(false);
  
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
  const [activeTrip, setActiveTrip] = useState<TripSummary | null>(null);
  const [activeReservation, setActiveReservation] = useState<ReservationItem | null>(null);
  const [reservationToDelete, setReservationToDelete] = useState<ReservationItem | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchDashboardData = async () => {
      try {
        const [user, roomsData, reservationsData, bookmarkedRooms, todayRec] = await Promise.all([
          fetchCurrentUser(),
          fetchRooms(),
          fetchReservations(),
          fetchBookmarkedRooms(),
          fetchTodayRecommendation(),
        ]);
        if (cancelled) return;

        const extraPreferMigrationMap: Record<string, string> = {
          "Halal": "할랄",
          "Kosher": "코셔",
          "Vegan": "비건",
          "Wheelchair Accessible": "휠체어 이용 가능",
          "Pets": "반려동물",
        };
        const dbPrefs = [user.extra_prefer1, user.extra_prefer2, user.extra_prefer3]
          .filter((x): x is string => typeof x === "string" && x.trim().length > 0)
          .map((x) => extraPreferMigrationMap[x] ?? x);

        setUserProfile({
          nickname: user.nickname || user.name || "User",
          bio: user.email || "",
          countryCode: user.country_code || "",
          profile_picture: user.profile_picture || "",
          birthday: user.birthday || "",
          preferences: dbPrefs,
        });
        setUserInsight({
          planPrefer: user.plan_prefer || "",
          vibePrefer: user.vibe_prefer || "",
          placesPrefer: user.places_prefer || "",
        });
        setDraftInsight({
          planPrefer: user.plan_prefer || "",
          vibePrefer: user.vibe_prefer || "",
          placesPrefer: user.places_prefer || "",
        });
        setDraftExtraPreferences(dbPrefs);

        const roomSummaries = (Array.isArray(roomsData) ? roomsData : []).map((room) => ({
          id: String(room.id),
          title: room.title || `Chat #${room.id}`,
          createdAt: room.created_at,
          messages: [],
        }));

        setTrips(roomSummaries);
        setBookmarkedRoomCount(Array.isArray(bookmarkedRooms) ? bookmarkedRooms.length : 0);
        setReservations((Array.isArray(reservationsData) ? reservationsData : []).map(mapReservationRecordToItem));
        setTodayRecommendation(todayRec ?? null);
      } catch (error) {
        console.warn("Failed to fetch mypage dashboard data", error);
      }
    };

    fetchDashboardData();
    const onProfileSettings = () => fetchDashboardData();
    window.addEventListener("triver:profile-settings", onProfileSettings);

    return () => {
      cancelled = true;
      window.removeEventListener("triver:profile-settings", onProfileSettings);
    };
  }, []);

  const handleAddReservation = async () => {
    try {
      const created = await createReservation({
        category: "etc",
        name: "새 예약",
        date: new Date().toISOString().slice(0, 10),
        image_path: "",
      });
      const mapped = mapReservationRecordToItem(created);
      setReservations((prev) => [mapped, ...prev]);
      setActiveReservation(mapped);
    } catch (error) {
      console.error("Failed to create new reservation draft", error);
    }
  };

  const handleDeleteReservation = async (id: string) => {
    const target = reservations.find((r) => r.id === id);
    if (!target) return;
    try {
      await deleteReservation(target.reservationId);
      setReservations((prev) => prev.filter((r) => r.id !== id));
      if (activeReservation?.id === id) setActiveReservation(null);
    } catch (error) {
      console.error("Failed to delete reservation", error);
    }
  };

  const requestDeleteReservation = (reservation: ReservationItem) => {
    setReservationToDelete(reservation);
  };

  const cancelDeleteReservation = () => {
    setReservationToDelete(null);
  };

  const confirmDeleteReservation = () => {
    if (!reservationToDelete) return;
    void handleDeleteReservation(reservationToDelete.id);
    setReservationToDelete(null);
  };

  const handleOpenSettings = () => {
    setSettingsOpen(true);
  };

  const toggleDraftExtraPreference = (value: string) => {
    setDraftExtraPreferences((prev) => {
      if (prev.includes(value)) return prev.filter((v) => v !== value);
      if (prev.length >= 3) return prev;
      return [...prev, value];
    });
  };

  const handleTogglePreferenceEdit = async () => {
    if (!isEditingPreferences) {
      setDraftInsight(userInsight);
      setDraftExtraPreferences(userProfile.preferences);
      setIsEditingPreferences(true);
      return;
    }

    setIsSavingPreferences(true);
    try {
      await updateCurrentUser({
        plan_prefer: draftInsight.planPrefer || null,
        vibe_prefer: draftInsight.vibePrefer || null,
        places_prefer: draftInsight.placesPrefer || null,
        extra_prefer1: draftExtraPreferences[0] || null,
        extra_prefer2: draftExtraPreferences[1] || null,
        extra_prefer3: draftExtraPreferences[2] || null,
      });

      setUserInsight(draftInsight);
      setUserProfile((prev) => ({ ...prev, preferences: draftExtraPreferences }));
      setIsEditingPreferences(false);
      setShowPreferenceSavedPopup(true);
    } catch (error) {
      console.error("Failed to update preferences", error);
    } finally {
      setIsSavingPreferences(false);
    }
  };

  const handleCancelPreferenceEdit = () => {
    setDraftInsight(userInsight);
    setDraftExtraPreferences(userProfile.preferences);
    setIsEditingPreferences(false);
  };

  return {
    state: {
      userProfile,
      userInsight,
      draftInsight,
      todayRecommendation,
      trips,
      reservations,
      bookmarkedRoomCount,
      isEditingPreferences,
      isSavingPreferences,
      draftExtraPreferences,
      showPreferenceSavedPopup,
      settingsOpen,
      activeTrip,
      activeReservation,
      reservationToDelete,
    },
    actions: {
      setUserProfile,
      setDraftInsight,
      setReservations,
      setShowPreferenceSavedPopup,
      setSettingsOpen,
      setActiveTrip,
      setActiveReservation,
      handleAddReservation,
      handleDeleteReservation,
      requestDeleteReservation,
      cancelDeleteReservation,
      confirmDeleteReservation,
      handleOpenSettings,
      toggleDraftExtraPreference,
      handleTogglePreferenceEdit,
      handleCancelPreferenceEdit,
    }
  };
}
