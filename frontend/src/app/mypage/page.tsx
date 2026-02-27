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
  X,
} from "lucide-react";
import { Sidebar } from "@/components/Sidebar";

type AppLanguage = "en" | "ko" | "ja";

const LANGUAGE_STORAGE_KEY = "triver:language:v1";

const MYPAGE_I18N: Record<AppLanguage, Record<string, string>> = {
  en: {
    headerTitle: "MyPage",
    headerSubtitle: "Traveler Profile",
    settings: "Settings",
    noImage: "No Image",
    todayRec: "Today's Recommendation",
    startPlanning: "Start Planning",
    scheduledJourney: "Scheduled Journey",
    reservation: "Reservation",
    open: "Open",
    tripHint: "Tap to view related chat summary (mock).",
    dnaTitle: "Triver's Travel DNA",
    youAreA: "You are a",
    traveler: "Traveler!",
    journeyDetail: "Journey Detail",
    reservationDetails: "Reservation Details",
    reservationImage: "Reservation Image",
    clickToUpload: "(Click here to upload if no image is available)",
    reservationOne: "Reservation 1:",
    destination: "Destination",
    durationTime: "Duration Time",
    menu: "Menu",
    save: "Save",
    removePhoto: "Remove photo",
  },
  ko: {
    headerTitle: "나의 페이지",
    headerSubtitle: "여행자 프로필",
    settings: "설정",
    noImage: "이미지 없음",
    todayRec: "오늘의 추천",
    startPlanning: "계획 시작",
    scheduledJourney: "예정된 여정",
    reservation: "예약",
    open: "열기",
    tripHint: "관련 채팅 요약 보기 (데모).",
    dnaTitle: "Triver's Travel DNA",
    youAreA: "당신은",
    traveler: "여행자!",
    journeyDetail: "여정 상세",
    reservationDetails: "예약 상세",
    reservationImage: "예매내역 사진",
    clickToUpload: "(사진이 없을 땐 여기를 클릭해 업로드)",
    reservationOne: "예약 1:",
    destination: "목적지",
    durationTime: "소요 시간",
    menu: "메뉴",
    save: "저장",
    removePhoto: "사진 삭제",
  },
  ja: {
    headerTitle: "マイページ",
    headerSubtitle: "旅行者プロフィール",
    settings: "設定",
    noImage: "画像なし",
    todayRec: "今日のおすすめ",
    startPlanning: "プラン開始",
    scheduledJourney: "予定された旅程",
    reservation: "予約",
    open: "開く",
    tripHint: "関連チャット要約を見る（mock）。",
    dnaTitle: "Triver's Travel DNA",
    youAreA: "あなたは",
    traveler: "旅行者！",
    journeyDetail: "旅の詳細",
    reservationDetails: "予約詳細",
    reservationImage: "予約画像",
    clickToUpload: "(画像がない場合はクリックしてアップロード)",
    reservationOne: "予約1：",
    destination: "目的地",
    durationTime: "所要時間",
    menu: "メニュー",
    save: "保存",
    removePhoto: "写真を削除",
  },
};

type TripSummary = {
  id: string;
  title: string;
  messages: { role: "user" | "assistant"; text: string }[];
  detail?: {
    intro: string;
    restaurantOptions: { name: string; desc: string }[];
    attractions: { name: string; desc: string }[];
  };
};

type ReservationItem = {
  id: string;
  category: "transportation" | "hotel" | "restaurant" | "activity" | "etc";
  title: string;
  subtitle: string;
  dateLabel: string;
  reservationImageUrl?: string;
  identifierLabel?: string;
  identifierValue?: string;
  destinationLabel?: string;
  durationLabel?: string;
  details: { label: string; value: string }[];
};

function formatReservationOrdinalLabel(language: AppLanguage, n: number) {
  const safe = Math.max(1, Math.floor(n));
  if (language === "ko") return `예약 ${safe}:`;
  if (language === "ja") return `予約${safe}：`;
  return `Reservation ${safe}:`;
}

type ChatTranscriptMessage = {
  role: "user" | "assistant";
  text: string;
};

const JOURNEY_CHAT_STORAGE_PREFIX = "triver:journey-chat:v1:";

function loadJourneyChatTranscript(tripId: string): ChatTranscriptMessage[] | null {
  try {
    const raw = localStorage.getItem(`${JOURNEY_CHAT_STORAGE_PREFIX}${tripId}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return null;
    const normalized = parsed
      .map((m: any) => ({ role: m?.role, text: m?.text }))
      .filter(
        (m: any): m is ChatTranscriptMessage =>
          (m.role === "user" || m.role === "assistant") && typeof m.text === "string" && m.text.trim().length > 0,
      );
    return normalized.length ? normalized : null;
  } catch {
    return null;
  }
}

function buildMockJourneyTranscript(trip: TripSummary): ChatTranscriptMessage[] {
  const userSeed = trip.messages?.find((m) => m.role === "user")?.text;
  const baseUser = userSeed || "Show me recommendations.";

  if (trip.detail) {
    const restaurants = trip.detail.restaurantOptions.map((r) => `- ${r.name}: ${r.desc}`).join("\n");
    const attractions = trip.detail.attractions.map((a) => `- ${a.name}: ${a.desc}`).join("\n");

    const merged = [
      trip.detail.intro,
      restaurants ? `1. Restaurants Options\n${restaurants}` : "",
      attractions ? `2. Local Tourist Attractions\n${attractions}` : "",
    ]
      .filter((x) => typeof x === "string" && x.trim().length > 0)
      .join("\n\n");

    // NOTE: mock transcript is intentionally a single bubble.
    return [{ role: "assistant", text: merged || baseUser }];
  }

  // If no detail exists, still return a single bubble.
  const fallbackAssistant = trip.messages?.filter((m) => m.role === "assistant").map((m) => m.text).join("\n\n");
  return [{ role: "assistant", text: fallbackAssistant?.trim().length ? fallbackAssistant : baseUser }];
}

function LoadingIndicator() {
  return (
    <div className="relative h-9 w-32 rounded-full bg-gray-200 shadow-sm overflow-hidden">
      <div className="absolute inset-0 flex items-center justify-center gap-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="relative w-5 h-5 rounded-full bg-gray-500/60">
            <motion.div
              className="absolute inset-0 rounded-full bg-green-500"
              animate={{ opacity: [0.15, 1, 0.15] }}
              transition={{ duration: 1.2, ease: "easeInOut", repeat: Infinity, delay: i * 0.22 }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function getReservationCategoryLabel(category: ReservationItem["category"]) {
  switch (category) {
    case "transportation":
      return "Transportation";
    case "hotel":
      return "Hotel";
    case "restaurant":
      return "Restaurant";
    case "activity":
      return "Activity";
    default:
      return "Reservation";
  }
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

function SimpleModal({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Close"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-2xl rounded-xl bg-white border border-gray-200 shadow-lg overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <h3 className="text-xs font-bold text-gray-900 uppercase tracking-widest">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-[10px] font-bold text-black border-b border-black leading-none pb-0.5 hover:opacity-70"
          >
            Close
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
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

  useEffect(() => {
    if (!open || !trip) return;
    setPhase("loading");
    const timeoutId = window.setTimeout(() => setPhase("ready"), 3000);
    return () => window.clearTimeout(timeoutId);
  }, [open, trip?.id]);

  const transcript = useMemo(() => {
    if (!trip) return [] as ChatTranscriptMessage[];
    const stored = loadJourneyChatTranscript(trip.id);
    return stored ?? buildMockJourneyTranscript(trip);
  }, [trip]);

  return (
    <AnimatePresence>
      {open && trip && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
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
            className="relative z-10 w-full max-w-xl rounded-xl bg-white border border-gray-200 shadow-lg overflow-hidden flex flex-col"
            initial={{ opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 380, damping: 30 }}
          >
            <div className="p-6 pb-4">
              <h2 className="text-3xl font-bold text-gray-900 text-center">{title}</h2>
            </div>

            <div className="px-6 pb-4">
              <div className="relative rounded-xl border border-gray-200 bg-white p-5 max-h-[55vh] overflow-y-auto">
                <AnimatePresence mode="wait">
                  {phase === "loading" ? (
                    <motion.div
                      key="loading"
                      className="min-h-[220px]"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <div className="absolute left-4 bottom-4">
                        <LoadingIndicator />
                      </div>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="messages"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="space-y-2"
                    >
                      {transcript.map((m, idx) => {
                        const isUser = m.role === "user";
                        return (
                          <motion.div
                            key={`${m.role}-${idx}-${m.text.slice(0, 12)}`}
                            initial={{ opacity: 0, y: 8, scale: 0.98 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            transition={{ duration: 0.25, delay: idx * 0.08 }}
                            className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                          >
                            <div
                              className={
                                isUser
                                  ? "max-w-[85%] rounded-2xl rounded-br-md bg-black text-white px-4 py-3 text-xs leading-relaxed shadow-sm"
                                  : "max-w-[85%] rounded-2xl rounded-bl-md bg-gray-100 text-gray-900 px-4 py-3 text-xs leading-relaxed shadow-sm"
                              }
                            >
                              <div className="whitespace-pre-wrap">{m.text}</div>
                            </div>
                          </motion.div>
                        );
                      })}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            <div className="px-6 pb-6">
              <button
                type="button"
                onClick={onClose}
                className="w-full bg-black text-white py-3 rounded-lg text-sm font-semibold"
              >
                {menuLabel}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function ReservationDetailModal({
  open,
  reservation,
  photoUrl,
  onSavePhoto,
  onClose,
  title,
  menuLabel,
  labels,
}: {
  open: boolean;
  reservation: ReservationItem | null;
  photoUrl?: string;
  onSavePhoto: (nextUrl: string | null) => void;
  onClose: () => void;
  title: string;
  menuLabel: string;
  labels: {
    reservationImage: string;
    clickToUpload: string;
    reservationOne: string;
    destination: string;
    durationTime: string;
    removePhoto: string;
  };
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [draftPhotoUrl, setDraftPhotoUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !reservation) return;
    const initial = photoUrl || reservation.reservationImageUrl || null;
    setDraftPhotoUrl(typeof initial === "string" && initial.trim().length ? initial : null);
  }, [open, reservation, photoUrl]);

  const categoryLabel = reservation ? getReservationCategoryLabel(reservation.category) : "Reservation";
  const effectivePhotoUrl = draftPhotoUrl || undefined;

  return (
    <AnimatePresence>
      {open && reservation && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
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
            className="relative z-10 w-full max-w-sm rounded-xl bg-white border border-gray-200 shadow-lg overflow-hidden flex flex-col"
            initial={{ opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 380, damping: 30 }}
          >
            <div className="relative p-6 pb-4">
              <button
                type="button"
                aria-label="Close"
                onClick={onClose}
                className="absolute right-4 top-4 w-9 h-9 rounded-lg border border-gray-200 bg-white text-gray-700 flex items-center justify-center hover:bg-gray-50"
              >
                <X size={16} />
              </button>
              <h2 className="text-3xl font-bold text-gray-900 text-center">{title}</h2>
            </div>

            <div className="px-6 pb-4 max-h-[60vh] overflow-y-auto">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const reader = new FileReader();
                  reader.onload = () => {
                    const url = typeof reader.result === "string" ? reader.result : "";
                    if (!url) return;
                    setDraftPhotoUrl(url);
                  };
                  reader.readAsDataURL(file);
                  e.currentTarget.value = "";
                }}
              />

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full rounded-xl border border-gray-200 bg-gray-200 text-gray-900 overflow-hidden"
                aria-label="Upload reservation image"
              >
                {effectivePhotoUrl ? (
                  <img src={effectivePhotoUrl} alt="Reservation" className="w-full h-[180px] object-cover" />
                ) : (
                  <div className="h-[180px] flex flex-col items-center justify-center">
                    <div className="text-lg font-bold">{labels.reservationImage}</div>
                    <div className="text-xs text-gray-700 mt-1">{labels.clickToUpload}</div>
                  </div>
                )}
              </button>

              {!!effectivePhotoUrl && (
                <div className="mt-2 flex items-center justify-end">
                  <button
                    type="button"
                    onClick={() => setDraftPhotoUrl(null)}
                    className="text-[11px] font-semibold text-gray-600 hover:text-black"
                  >
                    {labels.removePhoto}
                  </button>
                </div>
              )}

              <div className="mt-4 space-y-1 text-sm text-gray-900">
                <div className="font-semibold flex items-center gap-2">
                  <span>{labels.reservationOne}</span>
                  <span className="inline-flex items-center justify-center w-6 h-6 rounded-md bg-gray-100 border border-gray-200 text-gray-700">
                    <ReservationLogo category={reservation.category} />
                  </span>
                  <span>{categoryLabel}</span>
                </div>
                {reservation.identifierLabel && reservation.identifierValue && (
                  <div>
                    {reservation.identifierLabel}: <span className="font-semibold">{reservation.identifierValue}</span>
                  </div>
                )}
                {reservation.destinationLabel && (
                  <div>
                    {labels.destination}: <span className="font-semibold">{reservation.destinationLabel}</span>
                  </div>
                )}
                {reservation.durationLabel && (
                  <div>
                    {labels.durationTime}: <span className="font-semibold">{reservation.durationLabel}</span>
                  </div>
                )}
              </div>

              {!!reservation.details?.length && (
                <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {reservation.details.map((d) => (
                    <div key={d.label} className="p-3 rounded-lg border border-gray-200 bg-white">
                      <div className="text-[9px] font-bold uppercase tracking-widest text-gray-400">{d.label}</div>
                      <div className="text-xs font-semibold text-gray-900 mt-1">{d.value}</div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-3 text-[10px] text-gray-500">
                (Mock) 나중에 Google Calendar 연동 후 이미지/상세정보를 불러오고, 예약 타입에 따라 로고/필드를 자동으로 매핑할 예정입니다.
              </div>
            </div>

            <div className="px-6 pb-6">
              <button
                type="button"
                onClick={() => {
                  onSavePhoto(draftPhotoUrl);
                  onClose();
                }}
                className="w-full bg-black text-white py-3 rounded-lg text-sm font-semibold"
              >
                {menuLabel}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function computeDna(preferences: string[]) {
  const set = new Set(preferences);

  const foodDriven = set.has("Food") ? 5 : set.has("Luxury") ? 4 : 3;
  const calmExplorer = set.has("Relaxation") ? 5 : set.has("Nature") ? 4 : 3;
  const cultureCurious = set.has("Culture") ? 5 : set.has("Adventure") ? 4 : 3;

  return [
    { label: "🍜 Food-Driven", score: foodDriven },
    { label: "🌿 Calm Explorer", score: calmExplorer },
    { label: "🎭 Culture Curious", score: cultureCurious },
  ];
}

function getTopTrait(traits: { label: string; score: number }[]) {
  const sorted = [...traits].sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return a.label.localeCompare(b.label);
  });
  return sorted[0] ?? { label: "Traveler", score: 0 };
}

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
            nickname: prev.nickname || data.nickname || data.name || "User",
            profile_picture: data.profile_picture || prev.profile_picture || "",
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
    const filled = "★".repeat(safe);
    const empty = "☆".repeat(max - safe);
    return (
      <span className="whitespace-nowrap">
        <span className="text-yellow-400">{filled}</span>
        <span className="text-gray-300">{empty}</span>
      </span>
    );
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
          </header>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pb-8">
            <div className="space-y-4">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-5 rounded-xl border border-gray-200 bg-white shadow-sm hover:border-gray-300 transition-colors"
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
                    className="whitespace-nowrap mt-2 bg-black text-white px-3 py-2 rounded-lg text-[10px] font-bold hover:opacity-90 transition-all uppercase tracking-wide"
                  >
                    {t("settings")}
                  </button>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="p-5 rounded-xl border border-gray-200 bg-white shadow-sm hover:border-gray-300 transition-colors"
              >
                <div className="mb-3 border-b border-gray-50 pb-2">
                  <h3 className="font-bold text-xs text-gray-900 uppercase tracking-widest">{t("dnaTitle")}</h3>
                </div>
                <div className="space-y-1.5">
                  {dnaTraits.map((trait) => (
                    <div key={trait.label} className="flex items-center justify-between">
                      <span className="text-xs text-gray-700 font-medium">{trait.label}</span>
                      <span className="text-xs font-bold tracking-wide">{renderStars(trait.score)}</span>
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
                  className="p-5 rounded-xl border border-gray-200 bg-white shadow-sm hover:border-gray-300 transition-colors flex flex-col min-h-[320px]"
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
                  className="p-5 rounded-xl border border-gray-200 bg-white shadow-sm flex flex-col hover:border-gray-300 transition-colors"
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
        onSavePhoto={(nextUrl) => {
          if (!activeReservation) return;
          setReservationPhotoById((prev) => {
            const next = { ...prev };
            if (!nextUrl) {
              delete next[activeReservation.id];
              return next;
            }
            next[activeReservation.id] = nextUrl;
            return next;
          });
        }}
        onClose={() => setActiveReservation(null)}
        title={t("reservationDetails")}
        menuLabel={t("save")}
        labels={{
          reservationImage: t("reservationImage"),
          clickToUpload: t("clickToUpload"),
          reservationOne: formatReservationOrdinalLabel(
            language,
            ((activeReservation && reservationIndexById[activeReservation.id]) ?? 0) + 1,
          ),
          destination: t("destination"),
          durationTime: t("durationTime"),
          removePhoto: t("removePhoto"),
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
