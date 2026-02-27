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
import { Sidebar } from "@/components/Sidebar";
import { SettingsModal } from "@/components/SettingsModal";

type AppLanguage = "en" | "ko" | "ja";

type TripMessage = {
  role: "user" | "assistant";
  text: string;
};

type TripSummary = {
  id: string;
  title: string;
  messages: TripMessage[];
  detail?: {
    intro: string;
    restaurantOptions?: { name: string; desc: string }[];
    attractions?: { name: string; desc: string }[];
  };
};

type ReservationCategory = "transportation" | "hotel" | "food" | "ticket";

type ReservationItem = {
  id: string;
  category: ReservationCategory;
  title: string;
  subtitle: string;
  dateLabel: string;
  identifierLabel: string;
  identifierValue: string;
  destinationLabel: string;
  durationLabel: string;
  details: { label: string; value: string }[];
};

type DnaTrait = { label: string; score: number };

const LANGUAGE_STORAGE_KEY = "triver:language:v1";

const MYPAGE_I18N: Record<AppLanguage, Record<string, string>> = {
  en: {
    headerTitle: "My Page",
    headerSubtitle: "Your travel profile",
    noImage: "No Image",
    settings: "Settings",

    dnaTitle: "TRIVER'S TRAVEL DNA",
    youAreA: "You are a",
    traveler: "traveler",

    todayRec: "TODAY'S RECOMMENDATION",
    startPlanning: "Start Planning",

    scheduledJourney: "Scheduled Journey",
    journeyDetail: "Journey Detail",
    open: "Open",
    tripHint: "Tap to view the chat-style itinerary summary.",

    reservation: "Reservation",
    reservationDetails: "Reservation Details",
    reservationImage: "Reservation Image",
    clickToUpload: "Click to upload",
    destination: "Destination",
    durationTime: "Duration / Time",

    menu: "Menu",
  },
  ko: {
    headerTitle: "마이페이지",
    headerSubtitle: "나의 여행 프로필",
    noImage: "이미지 없음",
    settings: "설정",

    dnaTitle: "TRIVER'S TRAVEL DNA",
    youAreA: "당신은",
    traveler: "여행자",

    todayRec: "오늘의 추천",
    startPlanning: "플래닝 시작",

    scheduledJourney: "예정된 여행",
    journeyDetail: "여정 상세",
    open: "열기",
    tripHint: "눌러서 채팅형 요약을 확인하세요.",

    reservation: "예약",
    reservationDetails: "예약 상세",
    reservationImage: "예약 이미지",
    clickToUpload: "클릭해서 업로드",
    destination: "목적지",
    durationTime: "기간 / 시간",

    menu: "메뉴",
  },
  ja: {
    headerTitle: "マイページ",
    headerSubtitle: "旅行プロフィール",
    noImage: "画像なし",
    settings: "設定",

    dnaTitle: "TRIVER'S TRAVEL DNA",
    youAreA: "あなたは",
    traveler: "旅行者",

    todayRec: "本日のおすすめ",
    startPlanning: "プラン開始",

    scheduledJourney: "予定の旅",
    journeyDetail: "旅程詳細",
    open: "開く",
    tripHint: "タップしてチャット形式の要約を確認します。",

    reservation: "予約",
    reservationDetails: "予約詳細",
    reservationImage: "予約画像",
    clickToUpload: "クリックしてアップロード",
    destination: "目的地",
    durationTime: "期間 / 時間",

    menu: "メニュー",
  },
};

export default function MyPage() {
  const router = useRouter();
  const [language, setLanguage] = useState<AppLanguage>("en");
  const [userProfile, setUserProfile] = useState({
    nickname: "",
    bio: "Explorer Lvl.3",
    preferences: ["Relaxation", "Food"],
    profile_picture: "",
  });

  const SETTINGS_STORAGE_KEY = "triver:profile-settings:v1";

  const t = useMemo(() => {
    const dict = MYPAGE_I18N[language] ?? MYPAGE_I18N.en;
    return (key: string) => dict[key] ?? MYPAGE_I18N.en[key] ?? key;
  }, [language]);

  const [activeTrip, setActiveTrip] = useState<TripSummary | null>(null);
  const [activeReservation, setActiveReservation] = useState<ReservationItem | null>(null);
  const [reservationPhotoById, setReservationPhotoById] = useState<Record<string, string>>({});

  useEffect(() => {
    const applyLanguage = () => {
      const raw = localStorage.getItem(LANGUAGE_STORAGE_KEY);
      if (raw === "en" || raw === "ko" || raw === "ja") {
        setLanguage(raw);
      } else {
        setLanguage("en");
      }
    };
    applyLanguage();

    const onLang = () => applyLanguage();
    window.addEventListener("triver:language", onLang);

    const applySavedSettings = () => {
      try {
        const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
        if (!raw) return;
        const parsed = JSON.parse(raw) as any;

        const nextNickname = typeof parsed?.nickname === "string" ? parsed.nickname : undefined;
        const nextBio = typeof parsed?.bio === "string" ? parsed.bio : undefined;
        const nextPrefs = Array.isArray(parsed?.travelPreferences)
          ? (parsed.travelPreferences.filter((x: unknown) => typeof x === "string") as string[])
          : Array.isArray(parsed?.preferences)
            ? (parsed.preferences.filter((x: unknown) => typeof x === "string") as string[])
            : undefined;

        setUserProfile((prev) => ({
          ...prev,
          nickname: nextNickname ?? prev.nickname,
          bio: nextBio ?? prev.bio,
          preferences: nextPrefs && nextPrefs.length ? nextPrefs.slice(0, 3) : prev.preferences,
        }));
      } catch {
        // ignore
      }
    };

    const onProfileSettings = () => applySavedSettings();
    window.addEventListener("triver:profile-settings", onProfileSettings);

    // Load local saved settings first (frontend-only prototype)
    applySavedSettings();

    const fetchUserProfile = async () => {
      try {
        const token = localStorage.getItem("access_token");
        if (!token) return;

        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/users/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (res.ok) {
          const data = await res.json();
          setUserProfile((prev) => ({
            ...prev,
            nickname: data.nickname || data.name || "User",
            profile_picture: data.profile_picture || "",
          }));
        }
      } catch (error) {
        console.error("Failed to fetch user profile", error);
      }
    };

    fetchUserProfile();

    return () => {
      window.removeEventListener("triver:language", onLang);
      window.removeEventListener("triver:profile-settings", onProfileSettings);
    };
  }, []);

  const handleSaveSettings = (nickname: string, bio: string, preferences: string[]) => {
    setUserProfile((prev) => ({ ...prev, nickname, bio, preferences }));

    // Keep Settings page and MyPage in sync for the prototype
    try {
      const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
      const parsed = raw ? (JSON.parse(raw) as any) : {};
      const next = {
        ...parsed,
        nickname,
        bio,
        // Settings page expects a fixed-length tuple, but we keep it flexible here.
        travelPreferences: preferences.slice(0, 3),
      };
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore
    }
  };

  const trips: TripSummary[] = [
    {
      id: "trip-1",
      title: "Trip to Busan (Mock)",
      messages: [
        { role: "user", text: "Recommend me a travel destination from Busan" },
        { role: "assistant", text: "Haeundae → Gwangalli → Jagalchi Market 중심으로 동선을 제안드릴게요." },
        { role: "assistant", text: "(예시) Day1: 해운대/더베이101, Day2: 감천문화마을/자갈치" },
      ],
      detail: {
        intro: 
          "Based on your preference with enjoying the Seaside view, as well as your recently bookings for both KTX and Park Hyatt Busan. Here are some recommendations",
        restaurantOptions: [
          { name: "Haeundae Restaurant", desc: "Which is lovely for the local seafood delights." },
          { name: "Gunamross", desc: "A clean restaurant with variety of options of Seafoods" },
        ],
        attractions: [
          { name: "Gamcheon Culture Village", desc: "a very colorful and vibrant historical town for both locals and tourist visitors." },
          { name: "BIFF Square", desc: "For a movie buffs, as well as those who’s searching for local delights and street food, this is a cool place to visit!" },
        ],
      },
    },
  ];

  const [reservations, setReservations] = useState<ReservationItem[]>(() => [
    {
      id: "res-1",
      category: "transportation",
      title: "KTX Busan",
      subtitle: "Seoul → Busan",
      dateLabel: "10:00AM · 2026.02.23",
      identifierLabel: "Transportation ID",
      identifierValue: "KTX 67459",
      destinationLabel: "Seoul → Busan",
      durationLabel: "10:00AM ~ 12:00PM",
      details: [
        { label: "Type", value: "Train" },
        { label: "Provider", value: "Korail" },
        { label: "From", value: "Seoul Station" },
        { label: "To", value: "Busan Station" },
        { label: "Departure", value: "10:00AM" },
      ],
    },
    {
      id: "res-2",
      category: "hotel",
      title: "Park Hyatt Busan",
      subtitle: "Haeundae · Busan",
      dateLabel: "Check-in · 2026.02.23",
      identifierLabel: "Hotel Booking ID",
      identifierValue: "PHB 19824",
      destinationLabel: "Busan",
      durationLabel: "2026.02.23 ~ 2026.02.24",
      details: [
        { label: "Type", value: "Hotel" },
        { label: "Guests", value: "2" },
        { label: "Room", value: "Deluxe" },
        { label: "Check-in", value: "3:00PM" },
        { label: "Check-out", value: "11:00AM" },
      ],
    },
  ]);

  const reservationIndexById = useMemo(() => {
    const map: Record<string, number> = {};
    reservations.forEach((r, idx) => {
      map[r.id] = idx;
    });
    return map;
  }, [reservations]);

  const [reservationToDelete, setReservationToDelete] = useState<ReservationItem | null>(null);

  const handleAddReservation = () => {
  };

  const handleDeleteReservation = (id: string) => {
    setReservations((prev) => prev.filter((r) => r.id !== id));
    if (activeReservation?.id === id) setActiveReservation(null);
  };

  const requestDeleteReservation = (reservation: ReservationItem) => {
    setReservationToDelete(reservation);
  };

  const cancelDeleteReservation = () => {
    setReservationToDelete(null);
  };

  const confirmDeleteReservation = () => {
    if (!reservationToDelete) return;
    handleDeleteReservation(reservationToDelete.id);
    setReservationToDelete(null);
  };

  const dnaTraits = computeDna(userProfile.preferences);
  const topTrait = getTopTrait(dnaTraits);

  const renderStars = (score: number, max = 5) => {
    const safe = Math.max(0, Math.min(max, score));
    return "★".repeat(safe) + "☆".repeat(max - safe);
  };

  return (
    <div className="flex w-full h-screen bg-gray-100 p-4 gap-4 overflow-hidden">
      <div className="flex-none h-full">
        <Sidebar />
      </div>
      <main className="flex-1 h-full min-w-0 bg-white rounded-lg overflow-y-auto">
        <div className="p-6">
          <header className="mb-6 flex items-end justify-between border-b border-gray-100 pb-4">
            <div>
              <h1 className="text-2xl font-serif italic font-medium text-gray-900 mb-1">{t("headerTitle")}</h1>
              <p className="text-xs text-gray-500 font-medium tracking-wide uppercase">{t("headerSubtitle")}</p>
            </div>
            <SettingsModal
              initialNickname={userProfile.nickname}
              initialBio={userProfile.bio}
              initialPreferences={userProfile.preferences}
              onSave={handleSaveSettings}
            />
          </header>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pb-8">
            <div className="space-y-4">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-5 rounded-xl border border-gray-200 bg-white hover:border-gray-300 transition-colors"
              >
                <div className="flex items-center gap-4 mb-5">
                  <div className="w-24 h-24 rounded-xl overflow-hidden border border-gray-100 shadow-sm flex items-center justify-center bg-gray-200 text-gray-400">
                    {userProfile.profile_picture ? (
                      <img
                        src={userProfile.profile_picture}
                        alt="Profile"
                        className="w-full h-full object-cover grayscale-[20%]"
                      />
                    ) : (
                      <span className="font-medium text-xs">{t("noImage")}</span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-base text-gray-900">{userProfile.nickname}</h3>
                    <p className="text-[10px] text-gray-500 font-medium mt-1">{userProfile.bio}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => router.push("/mypage/settings")}
                    className="whitespace-nowrap bg-black text-white px-3 py-2 rounded-lg text-[10px] font-bold hover:opacity-90 transition-all uppercase tracking-wide"
                  >
                    {t("settings")}
                  </button>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="p-5 rounded-xl border border-gray-200 bg-white hover:border-gray-300 transition-colors"
              >
                <div className="mb-3 border-b border-gray-50 pb-2">
                  <h3 className="font-bold text-xs text-gray-900 uppercase tracking-widest">{t("dnaTitle")}</h3>
                </div>
                <div className="space-y-1.5">
                  {dnaTraits.map((trait) => (
                    <div key={trait.label} className="flex items-center justify-between">
                      <span className="text-xs text-gray-700 font-medium">{trait.label}</span>
                      <span className="text-xs text-gray-900 font-bold tracking-wide">{renderStars(trait.score)}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-4 text-center">
                  <p className="text-sm font-bold text-gray-900">{t("youAreA")}</p>
                  <p className="text-base font-extrabold text-gray-900">{topTrait.label}</p>
                  <p className="text-sm font-bold text-gray-900">{t("traveler")}</p>
                </div>
              </motion.div>
            </div>

            <div className="space-y-4 lg:col-span-2">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="p-6 rounded-xl bg-black text-white relative overflow-hidden group shadow-lg"
              >
                <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 group-hover:bg-white/10 transition-colors duration-700"></div>
                <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                  <div>
                    <div className="flex items-center gap-2 text-white/50 text-[9px] font-bold uppercase tracking-[0.2em] mb-3">
                      <Sparkles size={10} className="text-white" /> {t("todayRec")}
                    </div>
                    <h2 className="text-xl font-serif italic font-light mb-2 tracking-wide">Seongsu-dong K-Beauty Tour</h2>
                    <p className="text-white/60 text-xs font-light max-w-md leading-relaxed">
                      Continuing from session #8821. Focusing on flagship stores and hidden cafes.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => router.push("/chatbot")}
                    className="whitespace-nowrap flex items-center gap-2 bg-white text-black px-4 py-2.5 rounded-lg text-[10px] font-bold hover:bg-gray-200 transition-all uppercase tracking-wide"
                  >
                    <MessageSquare size={12} /> {t("startPlanning")}
                  </button>
                </div>
              </motion.div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="p-5 rounded-xl border border-gray-200 bg-white hover:border-gray-300 transition-colors flex flex-col min-h-[320px]"
                >
                  <div className="flex items-center justify-between mb-5 border-b border-gray-50 pb-2">
                    <h3 className="font-bold text-xs text-gray-900 uppercase tracking-widest">{t("scheduledJourney")}</h3>
                  </div>
                  <div className="space-y-2.5 flex-1">
                    {trips.map((trip) => (
                      <button
                        key={trip.id}
                        type="button"
                        onClick={() => setActiveTrip(trip)}
                        className="w-full text-left p-2.5 rounded-lg border border-gray-100 hover:border-gray-300 hover:bg-gray-50 transition-all"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-bold text-gray-900 leading-tight">{trip.title}</span>
                          <span className="text-[9px] text-gray-400 font-bold uppercase tracking-wider">{t("open")}</span>
                        </div>
                        <p className="mt-1 text-[10px] text-gray-500">
                          {t("tripHint")}
                        </p>
                      </button>
                    ))}
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="p-5 rounded-xl border border-gray-200 bg-white flex flex-col hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-center justify-between mb-5 border-b border-gray-50 pb-2">
                    <h3 className="font-bold text-xs text-gray-900 uppercase tracking-widest">{t("reservation")}</h3>
                    <button
                      type="button"
                      disabled
                      onClick={handleAddReservation}
                      className="text-[10px] font-bold text-gray-400 uppercase tracking-wider cursor-not-allowed"
                    >
                      Add
                    </button>
                  </div>
                  <div className="space-y-2.5 flex-1 max-h-[210px] overflow-y-auto pr-1">
                    {reservations.map((res) => (
                      <div
                        key={res.id}
                        className="w-full group p-2.5 rounded-lg border border-gray-100 hover:border-gray-300 hover:bg-gray-50 transition-all flex items-center justify-between gap-2"
                      >
                        <button
                          type="button"
                          onClick={() => setActiveReservation(res)}
                          className="flex-1 min-w-0 cursor-pointer flex items-center justify-between text-left"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="w-8 h-8 rounded-md bg-gray-100 flex items-center justify-center text-gray-500 group-hover:bg-white group-hover:text-black transition-colors border border-gray-200">
                              <ReservationLogo category={res.category} />
                            </div>
                            <div className="min-w-0">
                              <h4 className="text-[11px] font-bold text-gray-900 leading-tight truncate">{res.title}</h4>
                              <div className="flex items-center gap-1.5 mt-0.5 min-w-0">
                                <span className="text-[9px] text-gray-400 font-medium uppercase truncate">{res.subtitle}</span>
                                <span className="text-[9px] text-gray-300">•</span>
                                <span className="text-[9px] text-gray-400 font-mono truncate">{res.dateLabel}</span>
                              </div>
                            </div>
                          </div>
                          <CheckCircle2 size={14} className="text-black flex-none" />
                        </button>

                        <button
                          type="button"
                          onClick={() => requestDeleteReservation(res)}
                          className="flex-none text-[10px] font-bold text-gray-700 uppercase tracking-wider hover:opacity-70"
                        >
                          Delete
                        </button>
                      </div>
                    ))}
                  </div>
                </motion.div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <JourneyDetailModal
        open={!!activeTrip}
        trip={activeTrip}
        onClose={() => setActiveTrip(null)}
        title={t("journeyDetail")}
        menuLabel={t("menu")}
      />

      <ReservationDetailModal
        open={!!activeReservation}
        reservation={activeReservation}
        photoUrl={activeReservation ? reservationPhotoById[activeReservation.id] : undefined}
        onPickPhoto={(file) => {
          if (!activeReservation) return;
          const reader = new FileReader();
          reader.onload = () => {
            const url = typeof reader.result === "string" ? reader.result : "";
            if (!url) return;
            setReservationPhotoById((prev) => ({ ...prev, [activeReservation.id]: url }));
          };
          reader.readAsDataURL(file);
        }}
        onClose={() => setActiveReservation(null)}
        title={t("reservationDetails")}
        menuLabel={t("menu")}
        labels={{
          reservationImage: t("reservationImage"),
          clickToUpload: t("clickToUpload"),
          reservationOne: formatReservationOrdinalLabel(
            language,
            ((activeReservation && reservationIndexById[activeReservation.id]) ?? 0) + 1,
          ),
          destination: t("destination"),
          durationTime: t("durationTime"),
        }}
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
    </div>
  );
}

type ChatTranscriptMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
};

function formatReservationOrdinalLabel(language: AppLanguage, n: number) {
  const safe = Math.max(1, Math.floor(n));
  switch (language) {
    case "ko":
      return `예약 ${safe}`;
    case "ja":
      return `予約 ${safe}`;
    default:
      return `Reservation ${safe}`;
  }
}

function computeDna(preferences: string[]): DnaTrait[] {
  const normalized = new Set(preferences.map((p) => String(p)));

  const hasFood = normalized.has("Food");
  const hasLuxury = normalized.has("Luxury");
  const hasRelaxation = normalized.has("Relaxation");
  const hasNature = normalized.has("Nature");
  const hasCulture = normalized.has("Culture");
  const hasAdventure = normalized.has("Adventure");

  return [
    {
      label: "Food-Driven",
      score: hasFood ? 5 : hasLuxury ? 4 : 3,
    },
    {
      label: "Calm Explorer",
      score: hasRelaxation ? 5 : hasNature ? 4 : 3,
    },
    {
      label: "Culture Curious",
      score: hasCulture ? 5 : hasAdventure ? 4 : 3,
    },
  ];
}

function getTopTrait(traits: DnaTrait[]): DnaTrait {
  if (!traits.length) return { label: "", score: 0 };
  return traits.reduce((best, cur) => (cur.score > best.score ? cur : best), traits[0]);
}

function ReservationLogo({ category }: { category: ReservationCategory }) {
  switch (category) {
    case "transportation":
      return <TrainFront size={16} />;
    case "hotel":
      return <Hotel size={16} />;
    case "food":
      return <UtensilsCrossed size={16} />;
    case "ticket":
    default:
      return <Ticket size={16} />;
  }
}

function loadJourneyChatTranscript(tripId: string): ChatTranscriptMessage[] | null {
  try {
    const raw = localStorage.getItem(`triver:journey-chat:v1:${tripId}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as any;
    if (!Array.isArray(parsed)) return null;
    const cleaned = parsed
      .map((m: any, idx: number) => ({
        id: typeof m?.id === "string" ? m.id : `m-${idx}`,
        role: m?.role === "user" || m?.role === "assistant" ? m.role : null,
        text: typeof m?.text === "string" ? m.text : "",
      }))
      .filter((m: any) => (m.role === "user" || m.role === "assistant") && m.text);
    return cleaned.length ? (cleaned as ChatTranscriptMessage[]) : null;
  } catch {
    return null;
  }
}

function buildMockJourneyTranscript(trip: TripSummary): ChatTranscriptMessage[] {
  const base: ChatTranscriptMessage[] = trip.messages.map((m, idx) => ({
    id: `base-${idx}`,
    role: m.role,
    text: m.text,
  }));

  const extra: ChatTranscriptMessage[] = [];
  if (trip.detail?.intro) {
    extra.push({ id: "detail-intro", role: "assistant", text: trip.detail.intro });
  }

  if (trip.detail?.restaurantOptions?.length) {
    extra.push({
      id: "detail-rest-header",
      role: "assistant",
      text: "Restaurant options:",
    });
    trip.detail.restaurantOptions.forEach((r, idx) => {
      extra.push({
        id: `detail-rest-${idx}`,
        role: "assistant",
        text: `- ${r.name}: ${r.desc}`,
      });
    });
  }

  if (trip.detail?.attractions?.length) {
    extra.push({
      id: "detail-att-header",
      role: "assistant",
      text: "Attractions:",
    });
    trip.detail.attractions.forEach((a, idx) => {
      extra.push({
        id: `detail-att-${idx}`,
        role: "assistant",
        text: `- ${a.name}: ${a.desc}`,
      });
    });
  }

  return [...base, ...extra];
}

function LoadingIndicator() {
  const dotBase = "w-2 h-2 rounded-full";
  const off = "#E5E7EB"; // gray-200
  const on = "#22C55E"; // green-500

  return (
    <div className="flex items-center gap-2">
      {[0, 1, 2].map((i) => (
        <motion.span
          // eslint-disable-next-line react/no-array-index-key
          key={i}
          className={dotBase}
          style={{ backgroundColor: off }}
          animate={{ backgroundColor: [off, on, off] }}
          transition={{
            duration: 0.9,
            ease: "easeInOut",
            repeat: Infinity,
            delay: i * 0.18,
          }}
        />
      ))}
    </div>
  );
}

function JourneyDetailModal({
  open,
  trip,
  onClose,
  title,
  menuLabel,
}: {
  open: boolean;
  trip: TripSummary | null;
  onClose: () => void;
  title: string;
  menuLabel: string;
}) {
  const [phase, setPhase] = useState<"loading" | "ready">("loading");
  const [visibleCount, setVisibleCount] = useState(0);
  const listRef = useRef<HTMLDivElement | null>(null);

  const transcript = useMemo(() => {
    if (!trip) return [];
    return loadJourneyChatTranscript(trip.id) ?? buildMockJourneyTranscript(trip);
  }, [trip]);

  useEffect(() => {
    if (!open || !trip) return;
    setPhase("loading");
    setVisibleCount(0);
    const timer = window.setTimeout(() => {
      setPhase("ready");
    }, 3000);
    return () => window.clearTimeout(timer);
  }, [open, trip]);

  useEffect(() => {
    if (!open) return;
    if (phase !== "ready") return;
    if (!transcript.length) return;

    setVisibleCount(0);
    let idx = 0;
    const interval = window.setInterval(() => {
      idx += 1;
      setVisibleCount((prev) => {
        const next = Math.min(transcript.length, Math.max(prev, idx));
        return next;
      });
      if (idx >= transcript.length) {
        window.clearInterval(interval);
      }
    }, 180);

    return () => window.clearInterval(interval);
  }, [open, phase, transcript.length]);

  useEffect(() => {
    if (!open) return;
    if (phase !== "ready") return;
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [open, phase, visibleCount]);

  if (!open || !trip) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[60] flex items-center justify-center p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
      >
        <motion.button
          type="button"
          aria-label="Close"
          className="absolute inset-0 bg-black/40"
          onClick={onClose}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        />

        <motion.div
          className="relative z-10 w-full max-w-[720px] rounded-2xl bg-white shadow-lg overflow-hidden"
          initial={{ opacity: 0, y: 10, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.98 }}
          transition={{ type: "spring", stiffness: 420, damping: 34 }}
        >
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <div className="min-w-0">
              <div className="text-[10px] font-bold uppercase tracking-widest text-gray-400">{menuLabel}</div>
              <div className="text-base font-semibold text-gray-900 truncate">{title}</div>
              <div className="text-xs text-gray-500 truncate mt-0.5">{trip.title}</div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex-none bg-black text-white px-3 py-2 rounded-lg text-[10px] font-bold hover:opacity-90 transition-opacity uppercase tracking-wide"
            >
              Close
            </button>
          </div>

          <div className="p-5">
            {phase === "loading" ? (
              <div className="w-full rounded-xl bg-white shadow-sm p-6 flex items-center justify-center">
                <LoadingIndicator />
              </div>
            ) : (
              <div
                ref={listRef}
                className="max-h-[420px] overflow-y-auto pr-1 space-y-3"
              >
                <AnimatePresence initial={false}>
                  {transcript.slice(0, visibleCount).map((m) => (
                    <motion.div
                      key={m.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 6 }}
                      transition={{ duration: 0.18 }}
                      className={m.role === "user" ? "flex justify-end" : "flex justify-start"}
                    >
                      <div
                        className={
                          m.role === "user"
                            ? "max-w-[85%] rounded-2xl bg-black text-white px-4 py-3 text-sm whitespace-pre-wrap"
                            : "max-w-[85%] rounded-2xl bg-white shadow-sm text-gray-900 px-4 py-3 text-sm whitespace-pre-wrap"
                        }
                      >
                        {m.text}
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

function ReservationDetailModal({
  open,
  reservation,
  photoUrl,
  onPickPhoto,
  onClose,
  title,
  menuLabel,
  labels,
}: {
  open: boolean;
  reservation: ReservationItem | null;
  photoUrl?: string;
  onPickPhoto: (file: File) => void;
  onClose: () => void;
  title: string;
  menuLabel: string;
  labels: {
    reservationImage: string;
    clickToUpload: string;
    reservationOne: string;
    destination: string;
    durationTime: string;
  };
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  if (!open || !reservation) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[60] flex items-center justify-center p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
      >
        <motion.button
          type="button"
          aria-label="Close"
          className="absolute inset-0 bg-black/40"
          onClick={onClose}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        />

        <motion.div
          className="relative z-10 w-full max-w-[780px] rounded-2xl bg-white shadow-lg overflow-hidden"
          initial={{ opacity: 0, y: 10, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.98 }}
          transition={{ type: "spring", stiffness: 420, damping: 34 }}
        >
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <div className="min-w-0">
              <div className="text-[10px] font-bold uppercase tracking-widest text-gray-400">{menuLabel}</div>
              <div className="text-base font-semibold text-gray-900 truncate">{title}</div>
              <div className="text-xs text-gray-500 truncate mt-0.5">{labels.reservationOne}</div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex-none bg-black text-white px-3 py-2 rounded-lg text-[10px] font-bold hover:opacity-90 transition-opacity uppercase tracking-wide"
            >
              Close
            </button>
          </div>

          <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-2">
                {labels.reservationImage}
              </div>

              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                className="w-full aspect-[4/3] rounded-xl bg-gray-50 border border-gray-100 hover:border-gray-300 transition-colors overflow-hidden flex items-center justify-center"
              >
                {photoUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={photoUrl} alt="Reservation" className="w-full h-full object-cover" />
                ) : (
                  <div className="text-center">
                    <div className="text-xs font-semibold text-gray-800">{labels.clickToUpload}</div>
                    <div className="text-[10px] text-gray-400 mt-1">{reservation.identifierValue}</div>
                  </div>
                )}
              </button>
              <input
                ref={inputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  onPickPhoto(file);
                  e.currentTarget.value = "";
                }}
              />
            </div>

            <div className="space-y-4">
              <div className="rounded-xl border border-gray-100 p-4">
                <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500">{labels.destination}</div>
                <div className="mt-1 text-sm font-semibold text-gray-900">{reservation.destinationLabel}</div>
              </div>
              <div className="rounded-xl border border-gray-100 p-4">
                <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
                  {labels.durationTime}
                </div>
                <div className="mt-1 text-sm font-semibold text-gray-900">{reservation.durationLabel}</div>
              </div>

              <div className="rounded-xl border border-gray-100 p-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-sm font-bold text-gray-900 truncate">{reservation.title}</div>
                    <div className="text-[11px] text-gray-500 truncate mt-0.5">{reservation.subtitle}</div>
                  </div>
                  <div className="w-9 h-9 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-700 flex-none">
                    <ReservationLogo category={reservation.category} />
                  </div>
                </div>

                <div className="mt-3 grid grid-cols-1 gap-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500 font-medium">{reservation.identifierLabel}</span>
                    <span className="text-gray-900 font-mono font-semibold">{reservation.identifierValue}</span>
                  </div>

                  {reservation.details.map((d) => (
                    <div key={d.label} className="flex items-center justify-between text-xs">
                      <span className="text-gray-500 font-medium">{d.label}</span>
                      <span className="text-gray-900 font-semibold">{d.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
