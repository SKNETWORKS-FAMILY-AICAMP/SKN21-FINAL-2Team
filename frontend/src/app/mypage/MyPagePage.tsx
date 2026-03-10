"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Ticket,
  TrainFront,
  Hotel,
  UtensilsCrossed,
  CheckCircle2,
  MessageSquare,
  Sparkles,
} from "lucide-react";

import { Sidebar } from "@/components/navigation/Sidebar";
import { JourneyDetailModal } from "./components/JourneyDetailModal";
import { ReservationDetailModal } from "./components/ReservationDetailModal";
import { SimpleModal } from "./components/SimpleModal";
import {
  SURVEY_IMAGE_MAP,
  SURVEY_ITEM_LABELS,
  SNAPSHOT_OPTIONS,
  EXTRA_PREFER_OPTIONS,
} from "./constants";
import type { ReservationItem, TripSummary } from "./types";

import {
  fetchBookmarkedRooms,
  fetchCountries,
  fetchReservations,
  createReservation,
  deleteReservation,
  fetchTodayRecommendations,
  fetchCurrentUser,
  fetchRooms,
  updateCurrentUser,
  updateReservation,
  uploadImageDataUrl,
  resetCurrentUserProfilePictureToGoogle,
  deactivateCurrentUser,
  logoutApi,
  type Country,
  type ReservationRecord,
  type TodayRecommendationItem,
} from "@/services/api";
import { clearAuth } from "@/services/errorHandler";

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

function mapReservationRecordToItem(item: ReservationRecord): ReservationItem {
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
    details: [
      { label: "Category", value: item.category || "-" },
      { label: "Created At", value: formatKstDate(item.created_at) },
    ],
  };
}

function ReservationLogo({ category }: { category: ReservationItem["category"] }) {
  const common = { size: 14 };
  switch (category) {
    case "transportation":
      return <TrainFront {...common} />;
    case "hotel":
      return <Hotel {...common} />;
    case "restaurant":
      return <UtensilsCrossed {...common} />;
    case "activity":
      return <Ticket {...common} />;
    default:
      return <Ticket {...common} />;
  }
}

export function MyPagePage() {
  const router = useRouter();
  const [userProfile, setUserProfile] = useState({
    nickname: "",
    bio: "",
    countryCode: "",
    preferences: [] as string[],
    profile_picture: "",
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
  const [todayRecommendations, setTodayRecommendations] = useState<TodayRecommendationItem[]>([]);
  const [selectedRecommendationId, setSelectedRecommendationId] = useState<string>("");
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [reservations, setReservations] = useState<ReservationItem[]>([]);
  const [bookmarkedRoomCount, setBookmarkedRoomCount] = useState<number>(0);
  const [isEditingPreferences, setIsEditingPreferences] = useState<boolean>(false);
  const [isSavingPreferences, setIsSavingPreferences] = useState<boolean>(false);
  const [draftExtraPreferences, setDraftExtraPreferences] = useState<string[]>([]);
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
  const [settingsSaving, setSettingsSaving] = useState<boolean>(false);
  const [settingsResettingPhoto, setSettingsResettingPhoto] = useState<boolean>(false);
  const [settingsModalView, setSettingsModalView] = useState<"settings" | "deactivate">("settings");
  const [deactivateGoogleConfirmed, setDeactivateGoogleConfirmed] = useState<boolean>(false);
  const [deactivateAgreementConfirmed, setDeactivateAgreementConfirmed] = useState<boolean>(false);
  const [deactivateSubmitAttempted, setDeactivateSubmitAttempted] = useState<boolean>(false);
  const [deactivateSubmitting, setDeactivateSubmitting] = useState<boolean>(false);
  const [deactivateError, setDeactivateError] = useState<string>("");
  const [deactivateConfirmOpen, setDeactivateConfirmOpen] = useState<boolean>(false);
  const [countryOptions, setCountryOptions] = useState<Country[]>([]);
  const [settingsDraft, setSettingsDraft] = useState({
    nickname: "",
    countryCode: "",
    profilePicture: "",
  });
  const settingsPhotoInputRef = useRef<HTMLInputElement | null>(null);

  const [activeTrip, setActiveTrip] = useState<TripSummary | null>(null);
  const [activeReservation, setActiveReservation] = useState<ReservationItem | null>(null);
  const [addReservationOpen, setAddReservationOpen] = useState<boolean>(false);
  const [addReservationName, setAddReservationName] = useState<string>("");
  const [addReservationImage, setAddReservationImage] = useState<string>("");
  const [addReservationError, setAddReservationError] = useState<string>("");
  const addReservationPhotoInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchDashboardData = async () => {
      try {
        const [user, roomsData, reservationsData, bookmarkedRooms, todayRecs] = await Promise.all([
          fetchCurrentUser(),
          fetchRooms(),
          fetchReservations(),
          fetchBookmarkedRooms(),
          fetchTodayRecommendations(),
        ]);
        if (cancelled) return;

        const dbPrefs = [user.extra_prefer1, user.extra_prefer2, user.extra_prefer3].filter(
          (x): x is string => typeof x === "string" && x.trim().length > 0,
        );

        setUserProfile({
          nickname: user.nickname || user.name || "User",
          bio: user.email || "",
          countryCode: user.country_code || "",
          profile_picture: user.profile_picture || "",
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
        const recs = Array.isArray(todayRecs) ? todayRecs : [];
        setTodayRecommendations(recs);
        setSelectedRecommendationId((prev) => prev || recs[0]?.id || "");
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

  useEffect(() => {
    let cancelled = false;
    const loadCountries = async () => {
      try {
        const items = await fetchCountries();
        if (!cancelled) setCountryOptions(Array.isArray(items) ? items : []);
      } catch (error) {
        console.warn("Failed to fetch countries", error);
      }
    };
    void loadCountries();
    return () => {
      cancelled = true;
    };
  }, []);

  const [reservationToDelete, setReservationToDelete] = useState<ReservationItem | null>(null);

  const handleAddReservation = () => {
    setAddReservationName("");
    setAddReservationImage("");
    setAddReservationError("");
    setAddReservationOpen(true);
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

  const closeSettingsModal = () => {
    setSettingsOpen(false);
    setSettingsModalView("settings");
    setDeactivateGoogleConfirmed(false);
    setDeactivateAgreementConfirmed(false);
    setDeactivateSubmitAttempted(false);
    setDeactivateSubmitting(false);
    setDeactivateError("");
    setDeactivateConfirmOpen(false);
  };

  const handleOpenSettings = () => {
    setSettingsDraft({
      nickname: userProfile.nickname,
      countryCode: userProfile.countryCode,
      profilePicture: userProfile.profile_picture,
    });
    setSettingsModalView("settings");
    setDeactivateGoogleConfirmed(false);
    setDeactivateAgreementConfirmed(false);
    setDeactivateSubmitAttempted(false);
    setDeactivateSubmitting(false);
    setDeactivateError("");
    setSettingsOpen(true);
  };

  // [Feature] 회원탈퇴 — Settings 뷰에서 탈퇴 뷰로 전환
  const handleOpenDeactivateAccount = () => {
    setSettingsModalView("deactivate");
    setDeactivateGoogleConfirmed(false);
    setDeactivateAgreementConfirmed(false);
    setDeactivateSubmitAttempted(false);
    setDeactivateSubmitting(false);
    setDeactivateError("");
    setDeactivateConfirmOpen(false);
  };

  // [Feature] 회원탈퇴 — 탈퇴 뷰에서 취소하고 Settings 뷰로 복귀
  const handleCancelDeactivateAccount = () => {
    setSettingsModalView("settings");
    setDeactivateGoogleConfirmed(false);
    setDeactivateAgreementConfirmed(false);
    setDeactivateSubmitAttempted(false);
    setDeactivateSubmitting(false);
    setDeactivateError("");
    setDeactivateConfirmOpen(false);
  };

  // [Feature] 회원탈퇴 — 체크박스 검증 후 최종 확인 팝업 열기
  const handleRequestDeactivateAccount = () => {
    setDeactivateSubmitAttempted(true);
    setDeactivateError("");
    if (!deactivateGoogleConfirmed || !deactivateAgreementConfirmed) return;
    setDeactivateConfirmOpen(true);
  };

  // [Feature] 회원탈퇴 — 최종 확인 팝업에서 "아니요" 클릭 시 팝업 닫기
  const handleCancelDeactivateConfirm = () => {
    setDeactivateConfirmOpen(false);
  };

  // [Feature] 회원탈퇴 — 최종 확인 후 서버 탈퇴 API 호출 → 로그아웃 → 랜딩페이지 이동
  const handleConfirmDeactivateAccount = async () => {
    setDeactivateSubmitting(true);
    setDeactivateError("");
    try {
      await deactivateCurrentUser();
      await logoutApi();
      clearAuth();
      closeSettingsModal();
      window.location.href = "/";
    } catch (error) {
      console.error("Failed to deactivate account", error);
      setDeactivateError("회원 탈퇴에 실패했습니다.");
      setDeactivateConfirmOpen(false);
    } finally {
      setDeactivateSubmitting(false);
    }
  };

  const handleSaveSettingsPopup = async () => {
    setSettingsSaving(true);
    try {
      const resolvedProfilePicture = settingsDraft.profilePicture?.startsWith("data:image/")
        ? await uploadImageDataUrl(settingsDraft.profilePicture, "profile")
        : settingsDraft.profilePicture;
      await updateCurrentUser({
        nickname: settingsDraft.nickname.trim() || null,
        country_code: settingsDraft.countryCode || null,
        profile_picture: resolvedProfilePicture || null,
      });
      setUserProfile((prev) => ({
        ...prev,
        nickname: settingsDraft.nickname.trim() || prev.nickname,
        countryCode: settingsDraft.countryCode,
        profile_picture: resolvedProfilePicture || "",
      }));
      window.dispatchEvent(new Event("triver:profile-updated"));
      setSettingsOpen(false);
    } catch (error) {
      console.error("Failed to update user settings", error);
    } finally {
      setSettingsSaving(false);
    }
  };

  const handleResetProfilePhotoToGoogle = async () => {
    setSettingsResettingPhoto(true);
    try {
      const updated = await resetCurrentUserProfilePictureToGoogle();
      const nextPicture = updated.profile_picture || "";
      setSettingsDraft((prev) => ({ ...prev, profilePicture: nextPicture }));
      setUserProfile((prev) => ({ ...prev, profile_picture: nextPicture }));
      window.dispatchEvent(new Event("triver:profile-updated"));
    } catch (error) {
      console.error("Failed to reset profile photo to Google", error);
    } finally {
      setSettingsResettingPhoto(false);
    }
  };

  const handleSaveManualReservation = async () => {
    const trimmedName = addReservationName.trim();
    if (!trimmedName) {
      setAddReservationError("Please enter reservation name.");
      return;
    }
    if (!addReservationImage) {
      setAddReservationError("Please attach reservation image.");
      return;
    }

    try {
      const resolvedImagePath = addReservationImage.startsWith("data:image/")
        ? await uploadImageDataUrl(addReservationImage, "reservations")
        : addReservationImage;
      const created = await createReservation({
        category: "transportation",
        name: trimmedName,
        date: new Date().toISOString().slice(0, 10),
        image_path: resolvedImagePath,
      });
      const mapped = mapReservationRecordToItem(created);
      setReservations((prev) => [mapped, ...prev]);
      setAddReservationOpen(false);
    } catch (error) {
      console.error("Failed to create reservation", error);
      setAddReservationError("Failed to save reservation.");
    }
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
    } catch (error) {
      console.error("Failed to update preferences", error);
    } finally {
      setIsSavingPreferences(false);
    }
  };

  return (
    <div className="flex w-full min-h-screen bg-gray-100 p-3 sm:p-4 gap-4 lg:h-screen lg:flex-row flex-col lg:overflow-hidden">
      <div className="flex-none lg:h-full max-w-full">
        <div className="h-full">
          <Sidebar />
        </div>
      </div>
      <main className="flex-1 min-w-0 bg-white rounded-lg lg:h-full lg:overflow-y-auto text-gray-900">
        <div className="p-4 sm:p-6">
          <header className="mb-6">
            <h1 className="page-title text-gray-900 mb-2">My Page</h1>
            <p className="page-subtitle">Traveler Profile</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="px-2.5 py-1 rounded-full bg-gray-100 text-[11px] font-semibold text-gray-700">
                Rooms {trips.length}
              </span>
              <span className="px-2.5 py-1 rounded-full bg-gray-100 text-[11px] font-semibold text-gray-700">
                Saved Rooms {bookmarkedRoomCount}
              </span>
              <span className="px-2.5 py-1 rounded-full bg-gray-100 text-[11px] font-semibold text-gray-700">
                Reservations {reservations.length}
              </span>
            </div>
          </header>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 pb-8">
            <div className="xl:col-span-2">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 sm:p-6 sm:pb-4 rounded-3xl border border-gray-200 bg-white shadow-sm flex flex-col"
              >
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-3">
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full overflow-hidden border-4 border-gray-50 shadow-sm flex items-center justify-center bg-gray-200 text-gray-400 flex-none">
                      {userProfile.profile_picture ? (
                        <img
                          src={userProfile.profile_picture}
                          alt="Profile"
                          className="w-full h-full object-cover grayscale-[20%]"
                        />
                      ) : (
                        <span className="font-medium text-[10px]">No Image</span>
                      )}
                    </div>
                    <div className="min-w-0">
                      <h2 className="text-lg sm:text-xl font-bold text-gray-900 truncate">
                        {userProfile.nickname}
                      </h2>
                      <div className="flex items-center mt-0.5">
                        <span className="text-xs text-gray-500 truncate">{userProfile.bio}</span>
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleOpenSettings}
                    className="h-10 px-4 rounded-full border border-gray-300 bg-white text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all"
                  >
                    Settings
                  </button>
                </div>

                <hr className="border-gray-100 my-3" />

                <div className="space-y-8">
                  <div>
                    <div className="flex items-center justify-between gap-3 mb-1">
                      <h3 className="text-xl font-semibold text-gray-900 tracking-tight">Travel Preferences</h3>
                      <button
                        type="button"
                        onClick={handleTogglePreferenceEdit}
                        disabled={isSavingPreferences}
                        className={`h-10 px-4 rounded-full border text-xs font-bold transition-all disabled:opacity-60 ${isEditingPreferences
                          ? "border-gray-900 bg-black text-white hover:opacity-90"
                          : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                          }`}
                      >
                        {isEditingPreferences ? (isSavingPreferences ? "Saving..." : "Done") : "Edit"}
                      </button>
                    </div>
                    <p className="text-sm text-gray-500">여행 계획에 반영되는 사용자님의 선호도를 설정해보세요!</p>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-[0.14em] mb-4">Traveler Snapshot</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {[
                        { key: "plan" as const, label: SURVEY_ITEM_LABELS.plan, value: isEditingPreferences ? draftInsight.planPrefer : userInsight.planPrefer },
                        { key: "vibe" as const, label: SURVEY_ITEM_LABELS.vibe, value: isEditingPreferences ? draftInsight.vibePrefer : userInsight.vibePrefer },
                        { key: "places" as const, label: SURVEY_ITEM_LABELS.places, value: isEditingPreferences ? draftInsight.placesPrefer : userInsight.placesPrefer },
                      ].map((item) => {
                        const imageSrc = SURVEY_IMAGE_MAP[item.value] ?? "/image/noplan.png";
                        return (
                          <div key={item.key} className="space-y-2">
                            <div className="relative h-48 rounded-2xl overflow-hidden border border-gray-200 shadow-sm">
                              <img src={imageSrc} alt={item.value || item.label} className="w-full h-full object-cover" />
                              <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/30 to-transparent" />
                              <div className="absolute inset-x-0 bottom-0 p-4">
                                <p className="text-[10px] text-white/80 font-semibold uppercase tracking-[0.12em]">{item.label}</p>
                                <p className="text-sm text-white font-semibold mt-1">{item.value || "-"}</p>
                              </div>
                            </div>
                            {isEditingPreferences && (
                              <div className={`grid gap-1.5 ${SNAPSHOT_OPTIONS[item.key].length === 2 ? "grid-cols-2" : "grid-cols-3"}`}>
                                {SNAPSHOT_OPTIONS[item.key].map((opt) => (
                                  <button
                                    key={`${item.key}-${opt}`}
                                    type="button"
                                    onClick={() => {
                                      setDraftInsight((prev) => ({
                                        ...prev,
                                        ...(item.key === "plan" ? { planPrefer: opt } : {}),
                                        ...(item.key === "vibe" ? { vibePrefer: opt } : {}),
                                        ...(item.key === "places" ? { placesPrefer: opt } : {}),
                                      }));
                                    }}
                                    className={`px-2 py-1.5 rounded-full text-[11px] font-medium border transition-colors ${(item.key === "plan" && draftInsight.planPrefer === opt)
                                      || (item.key === "vibe" && draftInsight.vibePrefer === opt)
                                      || (item.key === "places" && draftInsight.placesPrefer === opt)
                                      ? "bg-black text-white border-black"
                                      : "bg-white text-gray-700 border-gray-200 hover:border-gray-400"
                                      }`}
                                  >
                                    {opt}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="mt-6">
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-[0.14em] mb-4">Extra Prefer</h4>
                    <div className="flex flex-wrap gap-2.5">
                      {(isEditingPreferences
                        ? EXTRA_PREFER_OPTIONS
                        : (userProfile.preferences.length ? userProfile.preferences : ["No preference selected"])).map((pref) => (
                          <button
                            key={pref}
                            type="button"
                            onClick={() => isEditingPreferences && toggleDraftExtraPreference(pref)}
                            disabled={!isEditingPreferences && pref === "No preference selected"}
                            className={`px-4 py-2 rounded-full text-sm font-medium border shadow-sm transition-colors ${isEditingPreferences
                              ? draftExtraPreferences.includes(pref)
                                ? "bg-black text-white border-black"
                                : "bg-white text-gray-700 border-gray-200 hover:border-gray-400"
                              : "bg-gray-900 text-white border-gray-900"
                              }`}
                          >
                            {pref}
                          </button>
                        ))}
                    </div>
                    {isEditingPreferences && (
                      <p className="mt-2 text-[11px] text-gray-500">Up to 3 selections</p>
                    )}
                  </div>
                </div>
              </motion.div>
            </div>

            <div className="flex flex-col gap-6 h-full">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="p-5 rounded-3xl bg-black text-white relative overflow-hidden group shadow-xl flex flex-col justify-between"
              >
                <div className="absolute top-0 right-0 w-80 h-80 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3 group-hover:bg-white/15 transition-colors duration-700"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-2 text-white text-xl font-semibold mb-4">
                    <Sparkles size={20} className="text-white" />
                    Today&apos;s Recommendation
                  </div>
                  {todayRecommendations.length > 0 ? (
                    <>
                      {(() => {
                        const selected = todayRecommendations.find((r) => r.id === selectedRecommendationId)
                          || todayRecommendations[0];
                        return (
                          <>
                            <h2 className="text-xl font-semibold mb-2 tracking-tight leading-tight">
                              {selected?.title}
                            </h2>
                            <p className="text-white/75 text-[13px] leading-relaxed line-clamp-2">
                              {selected?.description}
                            </p>
                          </>
                        );
                      })()}
                      <div className="mt-4 space-y-2">
                        {(todayRecommendations.slice(0, 3)).map((rec) => (
                          <button
                            key={rec.id}
                            type="button"
                            onClick={() => setSelectedRecommendationId(rec.id)}
                            className={`w-full text-left px-3 py-2.5 rounded-xl text-[11px] font-medium border transition-colors ${rec.id === selectedRecommendationId
                              ? "bg-white/15 text-white border-white/30"
                              : "bg-white/5 text-white/80 border-white/10 hover:bg-white/10"
                              }`}
                          >
                            {rec.title}
                          </button>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="rounded-2xl border border-dashed border-white/30 bg-white/5 p-4">
                      <h2 className="text-lg font-semibold mb-1 tracking-tight leading-tight">
                        No recommendation yet
                      </h2>
                      <p className="text-white/80 text-[13px] leading-relaxed">
                        Start a chat first. We will suggest new topics from your saved conversation summaries.
                      </p>
                      <p className="text-white/50 text-[10px] mt-2">
                        Recommendations appear when chat history summary is stored.
                      </p>
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => router.push("/chatbot")}
                  className="relative z-10 w-full flex items-center justify-center gap-2 bg-white text-black px-4 py-3 rounded-xl text-xs font-semibold hover:bg-gray-200 transition-all uppercase tracking-[0.12em] mt-4"
                >
                  <MessageSquare size={16} />
                  {todayRecommendations.length > 0 ? "Start Planning" : "Start Chat"}
                </button>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="p-6 sm:p-8 rounded-3xl border border-gray-200 bg-white flex flex-col flex-1 shadow-sm overflow-hidden"
              >
                <div className="flex items-center justify-between gap-3 mb-6">
                  <h3 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                    <Ticket size={20} />
                    Reservation
                  </h3>
                  <button
                    type="button"
                    onClick={handleAddReservation}
                    className="text-[11px] font-semibold text-gray-700 uppercase tracking-[0.12em] hover:opacity-70"
                  >
                    Add
                  </button>
                </div>

                <div className="space-y-3 flex-1 overflow-y-auto pr-1">
                  {reservations.length ? (
                    reservations.map((res) => (
                      <div
                        key={res.id}
                        className="group p-4 rounded-2xl border border-gray-100 hover:border-gray-300 hover:bg-gray-50 transition-all flex items-center justify-between gap-3"
                      >
                        <button
                          type="button"
                          onClick={() => setActiveReservation(res)}
                          className="flex-1 min-w-0 cursor-pointer text-left"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-500 group-hover:bg-white group-hover:text-black transition-colors border border-gray-200">
                              <ReservationLogo category={res.category} />
                            </div>
                            <div className="min-w-0">
                              <h4 className="text-sm font-bold leading-tight text-gray-900 truncate">{res.title}</h4>
                              <div className="flex items-center gap-1.5 mt-1 min-w-0">
                                <span className="text-[10px] text-gray-500 font-medium uppercase truncate">{res.subtitle}</span>
                                <span className="text-[10px] text-gray-300">•</span>
                                <span className="text-[10px] text-gray-400 font-medium truncate">{res.dateLabel}</span>
                              </div>
                            </div>
                          </div>
                        </button>
                        <div className="flex items-center gap-2 flex-none">
                          <CheckCircle2 size={14} className="text-black" />
                          <button
                            type="button"
                            onClick={() => requestDeleteReservation(res)}
                            className="text-[10px] font-semibold text-gray-700 uppercase tracking-[0.12em] hover:opacity-70"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="h-full min-h-[120px] flex items-center justify-center rounded-xl border border-dashed border-gray-200 bg-gray-50 text-[11px] text-gray-400 font-medium">
                      No reservations yet.
                    </div>
                  )}
                </div>
              </motion.div>
            </div>
          </div>
        </div>
      </main>

      <JourneyDetailModal
        open={!!activeTrip}
        trip={activeTrip}
        onClose={() => setActiveTrip(null)}
      />

      <ReservationDetailModal
        key={`${activeReservation?.id ?? "none"}-${activeReservation ? "open" : "closed"}`}
        open={!!activeReservation}
        reservation={activeReservation}
        photoUrl={activeReservation?.reservationImageUrl}
        onSavePhoto={async (nextUrl) => {
          if (!activeReservation) return;
          try {
            const resolvedImagePath = (nextUrl && nextUrl.startsWith("data:image/"))
              ? await uploadImageDataUrl(nextUrl, "reservations")
              : nextUrl;
            const updated = await updateReservation(activeReservation.reservationId, {
              image_path: resolvedImagePath || null,
            });
            const mapped = mapReservationRecordToItem(updated);
            setReservations((prev) => prev.map((item) => (
              item.reservationId === mapped.reservationId ? mapped : item
            )));
            setActiveReservation(mapped);
          } catch (error) {
            console.error("Failed to update reservation image", error);
          }
        }}
        onClose={() => setActiveReservation(null)}
      />

      <AnimatePresence>
        {!!reservationToDelete && (
          <motion.div
            className="fixed inset-0 z-[70] flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            <motion.button
              type="button"
              aria-label="Close"
              className="absolute inset-0 bg-black/40"
              onClick={cancelDeleteReservation}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            />

            <motion.div
              className="relative z-10 w-full max-w-[420px] rounded-xl bg-white shadow-lg overflow-hidden"
              initial={{ opacity: 0, y: 10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.98 }}
              transition={{ type: "spring", stiffness: 420, damping: 32 }}
            >
              <div className="p-6">
                <div className="text-lg font-semibold text-gray-900">
                  Are you sure you wanna delete this reservation?
                </div>
                <div className="mt-5 flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={cancelDeleteReservation}
                    className="bg-gray-200 text-gray-900 px-6 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-300 transition-colors"
                  >
                    No
                  </button>
                  <button
                    type="button"
                    onClick={confirmDeleteReservation}
                    className="bg-black text-white px-6 py-2.5 rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
                  >
                    Yes
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <SimpleModal open={addReservationOpen} title="Add Reservation" onClose={() => setAddReservationOpen(false)}>
        <div className="space-y-4">
          <input
            ref={addReservationPhotoInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (!file) return;


              const supportedMimeTypes = new Set(["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]);
              const lowerName = (file.name || "").toLowerCase();
              const supportedByExt =
                lowerName.endsWith(".jpg")
                || lowerName.endsWith(".jpeg")
                || lowerName.endsWith(".png")
                || lowerName.endsWith(".webp")
                || lowerName.endsWith(".gif");
              const isSupported = supportedMimeTypes.has(file.type) || supportedByExt;

              if (!isSupported) {
                setAddReservationImage("");
                setAddReservationError("Only supported image formats can be uploaded: JPG, PNG, WEBP, GIF.");
                e.currentTarget.value = "";
                return;
              }

              const reader = new FileReader();
              reader.onload = () => {
                const next = typeof reader.result === "string" ? reader.result : "";
                if (!next) return;
                setAddReservationImage(next);
                setAddReservationError("");
              };
              reader.onerror = () => {
                setAddReservationImage("");
                setAddReservationError("Failed to read this image file. Please try a different image.");
              };
              reader.readAsDataURL(file);
              e.currentTarget.value = "";
            }}
          />

          <button
            type="button"
            onClick={() => addReservationPhotoInputRef.current?.click()}
            className="w-full rounded-2xl border border-gray-200 bg-gray-50 overflow-hidden text-left"
          >
            {addReservationImage ? (
              <div className="w-full h-48 bg-gray-100 flex items-center justify-center">
                <img src={addReservationImage} alt="Reservation preview" className="w-full h-full object-contain" />
              </div>
            ) : (
              <div className="h-40 flex items-center justify-center text-sm text-gray-500 font-medium">
                Click to attach image
              </div>
            )}
          </button>

          <div className="space-y-2">
            <label className="text-[11px] font-bold uppercase tracking-wider text-gray-500">Reservation Name</label>
            <input
              value={addReservationName}
              onChange={(e) => {
                setAddReservationName(e.target.value);
                setAddReservationError("");
              }}
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm bg-gray-50"
              placeholder="e.g. Seoul > Busan train ticket"
            />
          </div>

          {!!addReservationError && (
            <div className="text-xs font-semibold text-red-600">{addReservationError}</div>
          )}

          <div className="pt-1 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setAddReservationOpen(false)}
              className="h-10 px-4 rounded-full border border-gray-300 bg-white text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSaveManualReservation}
              className="h-10 px-4 rounded-full border border-gray-900 bg-black text-white text-xs font-bold hover:opacity-90 transition-all"
            >
              Save
            </button>
          </div>
        </div>
      </SimpleModal>

      <SimpleModal
        open={settingsOpen}
        // [Feature] Settings 모달 타이틀 — 설정 뷰와 회원탈퇴 뷰를 구분
        title={settingsModalView === "settings" ? "Settings" : "회원 탈퇴"}
        onClose={closeSettingsModal}
      >
        {settingsModalView === "settings" ? (
          <div className="space-y-5">
            <input
              ref={settingsPhotoInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = () => {
                  const next = typeof reader.result === "string" ? reader.result : "";
                  if (!next) return;
                  setSettingsDraft((prev) => ({ ...prev, profilePicture: next }));
                };
                reader.readAsDataURL(file);
                e.currentTarget.value = "";
              }}
            />

            <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full overflow-hidden border border-gray-200 bg-white flex items-center justify-center text-gray-400">
                  {settingsDraft.profilePicture ? (
                    <img src={settingsDraft.profilePicture} alt="Profile" className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-[10px] font-semibold">No Image</span>
                  )}
                </div>
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-2">Profile Photo</p>
                  <button
                    type="button"
                    onClick={() => settingsPhotoInputRef.current?.click()}
                    className="h-9 px-4 rounded-full border border-gray-300 bg-white text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all"
                  >
                    Change Photo
                  </button>
                  <button
                    type="button"
                    onClick={handleResetProfilePhotoToGoogle}
                    disabled={settingsResettingPhoto}
                    className="h-9 ml-2 px-4 rounded-full border border-gray-300 bg-white text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all disabled:opacity-60"
                  >
                    {settingsResettingPhoto ? "Restoring..." : "Use Google Photo"}
                  </button>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-gray-200 bg-white p-4 space-y-4">
              <div className="space-y-2">
                <label className="text-[11px] font-bold uppercase tracking-wider text-gray-500">Nickname</label>
                <input
                  value={settingsDraft.nickname}
                  onChange={(e) => setSettingsDraft((prev) => ({ ...prev, nickname: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm bg-gray-50"
                  placeholder="Nickname"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[11px] font-bold uppercase tracking-wider text-gray-500">Country</label>
                <select
                  value={settingsDraft.countryCode}
                  onChange={(e) => setSettingsDraft((prev) => ({ ...prev, countryCode: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm bg-gray-50"
                >
                  <option value="">Select country</option>
                  {countryOptions.map((country) => (
                    <option key={country.code} value={country.code}>
                      {country.name} ({country.code})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="pt-1 flex items-center justify-between gap-2">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleOpenDeactivateAccount}
                  className="text-[10px] font-semibold text-gray-500 hover:text-gray-700 transition-colors"
                >
                  회원 탈퇴
                </button>
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={closeSettingsModal}
                  className="h-10 px-4 rounded-full border border-gray-300 bg-white text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveSettingsPopup}
                  disabled={settingsSaving}
                  className="h-10 px-4 rounded-full border border-gray-900 bg-black text-white text-xs font-bold hover:opacity-90 disabled:opacity-60 transition-all"
                >
                  {settingsSaving ? "Saving..." : "Save"}
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* [Feature] 회원탈퇴 뷰 — Google 계정 확인 + 탈퇴 동의 체크 후 탈퇴 요청 */
          <div className="space-y-5">
            {/* [Feature] Google 계정 확인 체크박스 — 본인 계정이 맞는지 확인 */}
            <div className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-gray-500">Google 계정 확인</p>
                <p className="text-sm font-semibold text-gray-900 mt-1 break-all">
                  {userProfile.bio || "알 수 없는 계정"}
                </p>
              </div>
              <label className="flex items-start gap-2 text-sm text-gray-800">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={deactivateGoogleConfirmed}
                  onChange={(e) => setDeactivateGoogleConfirmed(e.target.checked)}
                />
                <span>본인의 Google 계정이 맞음을 확인합니다.</span>
              </label>
              {deactivateSubmitAttempted && !deactivateGoogleConfirmed && (
                <div className="text-xs font-semibold text-red-600">Google 계정을 확인해 주세요.</div>
              )}
            </div>

            {/* [Feature] 탈퇴 약관 동의 체크박스 — 동의 없이는 탈퇴 진행 불가 */}
            <div className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-gray-500">탈퇴 약관 동의</p>
                <p className="text-xs text-gray-500 mt-1">탈퇴를 진행하기 전에 반드시 동의해 주세요.</p>
              </div>
              <label className="flex items-start gap-2 text-sm text-gray-800">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={deactivateAgreementConfirmed}
                  onChange={(e) => setDeactivateAgreementConfirmed(e.target.checked)}
                />
                <span>회원 탈퇴 약관에 동의합니다.</span>
              </label>
              {deactivateSubmitAttempted && !deactivateAgreementConfirmed && (
                <div className="text-xs font-semibold text-red-600">탈퇴 약관에 동의해 주세요.</div>
              )}
            </div>

            {/* [Feature] 탈퇴 실패 시 에러 메시지 표시 */}
            {!!deactivateError && <div className="text-xs font-semibold text-red-600">{deactivateError}</div>}

            {/* [Feature] 취소 / 탈퇴하기 버튼 */}
            <div className="pt-1 flex justify-end gap-2">
              <button
                type="button"
                onClick={handleCancelDeactivateAccount}
                className="h-10 px-4 rounded-full border border-gray-300 bg-white text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all"
              >
                취소
              </button>
              <button
                type="button"
                onClick={handleRequestDeactivateAccount}
                disabled={deactivateSubmitting}
                className="h-10 px-4 rounded-full border border-gray-900 bg-black text-white text-xs font-bold hover:opacity-90 disabled:opacity-60 transition-all"
              >
                탈퇴하기
              </button>
            </div>
          </div>
        )}
      </SimpleModal>

      {/* [Feature] 회원탈퇴 최종 확인 팝업 — 탈퇴 버튼 클릭 후 한 번 더 확인 */}
      <SimpleModal
        open={deactivateConfirmOpen}
        title="확인"
        onClose={handleCancelDeactivateConfirm}
        zIndex={60}
      >
        <div className="space-y-4">
          <p className="text-sm font-bold text-gray-900">정말 탈퇴하시겠습니까?</p>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={handleCancelDeactivateConfirm}
              disabled={deactivateSubmitting}
              className="h-10 px-4 rounded-full border border-gray-300 bg-white text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all disabled:opacity-60"
            >
              아니요
            </button>
            <button
              type="button"
              onClick={handleConfirmDeactivateAccount}
              disabled={deactivateSubmitting}
              className="h-10 px-4 rounded-full border border-gray-900 bg-black text-white text-xs font-bold hover:opacity-90 disabled:opacity-60 transition-all"
            >
              {deactivateSubmitting ? "탈퇴 중..." : "네"}
            </button>
          </div>
        </div>
      </SimpleModal>
    </div>
  );
}
