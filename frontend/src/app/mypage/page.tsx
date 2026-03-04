"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useGoogleLogin } from "@react-oauth/google";
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
import {
  fetchBookmarkedRooms,
  fetchCountries,
  fetchReservations,
  createReservation,
  deleteReservation,
  fetchCurrentUser,
  fetchRoom,
  fetchRooms,
  updateCurrentUser,
  updateReservation,
  type Country,
  type ReservationRecord,
} from "@/services/api";

type AppLanguage = "en" | "ko" | "ja";

const LANGUAGE_STORAGE_KEY = "triver:language:v1";
const SURVEY_IMAGE_MAP: Record<string, string> = {
  "빽빽한 일정": "/image/planning.jpg",
  "느슨한 일정": "/image/noplan.png",
  "붐비는 도시": "/image/crowded.jpg",
  "한적한 자연": "/image/lonely.jpg",
  "맛집": "/image/kfood.jpg",
  "역사적 명소": "/image/khistorical.jpg",
  "K-culture": "/image/kculture.png",
};
const SURVEY_ITEM_LABELS: Record<"plan" | "vibe" | "places", string> = {
  plan: "Travel Schedule",
  vibe: "Travel Vibe",
  places: "Interests",
};
const SPECIAL_EXTRA_PREFER_OPTIONS = [
  "Halal",
  "Kosher",
  "Vegan",
  "Wheelchair Accessible",
];
const SNAPSHOT_OPTIONS: Record<"plan" | "vibe" | "places", string[]> = {
  plan: ["빽빽한 일정", "느슨한 일정"],
  vibe: ["붐비는 도시", "한적한 자연"],
  places: ["맛집", "역사적 명소", "K-culture"],
};
const EXTRA_PREFER_OPTIONS = SPECIAL_EXTRA_PREFER_OPTIONS;

const MYPAGE_I18N: Record<AppLanguage, Record<string, string>> = {
  en: {
    headerTitle: "MyPage",
    headerSubtitle: "Traveler Profile",
    settings: "Settings",
    noImage: "No Image",
    todayRec: "Today's Recommendation",
    startPlanning: "Start Planning",
    scheduledJourney: "Recent Planning Sessions",
    reservation: "Reservation",
    noScheduledJourneys: "No scheduled journeys yet.",
    noReservations: "No reservations yet.",
    open: "Open",
    tripHint: "Tap to view related chat summary.",
    dnaTitle: "Traveler Snapshot",
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
    scheduledJourney: "최근 여행 플래닝 세션",
    reservation: "예약",
    noScheduledJourneys: "예정된 여정이 없습니다.",
    noReservations: "예약이 없습니다.",
    open: "열기",
    tripHint: "관련 채팅 요약 보기",
    dnaTitle: "여행자 스냅샷",
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
    scheduledJourney: "最近の旅行プランセッション",
    reservation: "予約",
    noScheduledJourneys: "予定された旅程はありません。",
    noReservations: "予約はありません。",
    open: "開く",
    tripHint: "関連チャット要約を見る。",
    dnaTitle: "旅行者スナップショット",
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
  createdAt?: string;
  messages: { role: "user" | "assistant"; text: string }[];
};

type ReservationItem = {
  id: string;
  reservationId: number;
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
        className="absolute inset-0 bg-black/45 backdrop-blur-[2px]"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-xl rounded-3xl bg-white border border-gray-200 shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
          <h3 className="text-[11px] font-bold text-gray-900 uppercase tracking-widest">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full border border-gray-200 bg-white text-gray-600 flex items-center justify-center hover:bg-gray-50"
          >
            <X size={14} />
          </button>
        </div>
        <div className="p-6">{children}</div>
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
  const transcript = useMemo(() => {
    if (!trip) return [] as ChatTranscriptMessage[];
    return trip.messages;
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
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-2"
                >
                  {transcript.length === 0 && (
                    <div className="text-xs text-gray-500 text-center py-6">No chat history in this room.</div>
                  )}
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
  onSavePhoto: (nextUrl: string | null) => Promise<void> | void;
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
  const [previewOpen, setPreviewOpen] = useState(false);
  const initialPhotoUrl = (typeof photoUrl === "string" && photoUrl.trim().length
    ? photoUrl
    : (typeof reservation?.reservationImageUrl === "string" && reservation.reservationImageUrl.trim().length
      ? reservation.reservationImageUrl
      : null));

  const categoryLabel = reservation ? getReservationCategoryLabel(reservation.category) : "Reservation";
  const effectivePhotoUrl = (draftPhotoUrl ?? initialPhotoUrl) || undefined;

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
                onClick={() => {
                  if (effectivePhotoUrl) {
                    setPreviewOpen(true);
                    return;
                  }
                  fileInputRef.current?.click();
                }}
                className="w-full rounded-xl border border-gray-200 bg-gray-200 text-gray-900 overflow-hidden"
                aria-label="Upload reservation image"
              >
                {effectivePhotoUrl ? (
                  <div className="h-[220px] bg-gray-100 flex items-center justify-center">
                    <img src={effectivePhotoUrl} alt="Reservation" className="w-full h-full object-contain" />
                  </div>
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

            </div>

            <div className="px-6 pb-6">
                <button
                  type="button"
                  onClick={async () => {
                    await onSavePhoto(draftPhotoUrl ?? initialPhotoUrl);
                    onClose();
                  }}
                className="w-full bg-black text-white py-3 rounded-lg text-sm font-semibold"
              >
                {menuLabel}
              </button>
            </div>
          </motion.div>

          <AnimatePresence>
            {previewOpen && !!effectivePhotoUrl && (
              <motion.div
                className="fixed inset-0 z-[60] flex items-center justify-center p-4"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <button
                  type="button"
                  aria-label="Close preview"
                  className="absolute inset-0 bg-black/75"
                  onClick={() => setPreviewOpen(false)}
                />
                <motion.div
                  className="relative z-10 w-full max-w-4xl max-h-[90vh] rounded-2xl bg-black/95 p-4 border border-white/20"
                  initial={{ opacity: 0, y: 8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 8, scale: 0.98 }}
                >
                  <button
                    type="button"
                    aria-label="Close preview"
                    onClick={() => setPreviewOpen(false)}
                    className="absolute right-3 top-3 w-8 h-8 rounded-full border border-white/30 text-white bg-black/40 flex items-center justify-center"
                  >
                    <X size={14} />
                  </button>
                  <div className="w-full h-[80vh] max-h-[80vh] flex items-center justify-center">
                    <img src={effectivePhotoUrl} alt="Original reservation" className="max-w-full max-h-full object-contain" />
                  </div>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default function MyPage() {
  const router = useRouter();
  const [language, setLanguage] = useState<AppLanguage>("en");
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
  const [todayRecommendation, setTodayRecommendation] = useState({ title: "", description: "" });
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [reservations, setReservations] = useState<ReservationItem[]>([]);
  const [bookmarkedRoomCount, setBookmarkedRoomCount] = useState<number>(0);

  const [calendarLinkNotice, setCalendarLinkNotice] = useState<string>("");
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
  const [settingsSaving, setSettingsSaving] = useState<boolean>(false);
  const [countryOptions, setCountryOptions] = useState<Country[]>([]);
  const [settingsDraft, setSettingsDraft] = useState({
    nickname: "",
    countryCode: "",
    profilePicture: "",
  });
  const settingsPhotoInputRef = useRef<HTMLInputElement | null>(null);
  const [isEditingPreferences, setIsEditingPreferences] = useState<boolean>(false);
  const [isSavingPreferences, setIsSavingPreferences] = useState<boolean>(false);
  const [draftExtraPreferences, setDraftExtraPreferences] = useState<string[]>([]);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
  const CALENDAR_LINKED_STORAGE_KEY = "triver:gcal-linked:v1";

  const t = useMemo(() => {
    const dict = MYPAGE_I18N[language] ?? MYPAGE_I18N.en;
    return (key: string) => dict[key] ?? MYPAGE_I18N.en[key] ?? key;
  }, [language]);

  const [activeTrip, setActiveTrip] = useState<TripSummary | null>(null);
  const [activeReservation, setActiveReservation] = useState<ReservationItem | null>(null);
  const [addReservationOpen, setAddReservationOpen] = useState<boolean>(false);
  const [addReservationName, setAddReservationName] = useState<string>("");
  const [addReservationImage, setAddReservationImage] = useState<string>("");
  const [addReservationError, setAddReservationError] = useState<string>("");
  const addReservationPhotoInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let cancelled = false;

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

    const fetchDashboardData = async () => {
      try {
        const [user, roomsData, reservationsData, bookmarkedRooms] = await Promise.all([
          fetchCurrentUser(),
          fetchRooms(),
          fetchReservations(),
          fetchBookmarkedRooms(),
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
        setSettingsDraft({
          nickname: user.nickname || user.name || "User",
          countryCode: user.country_code || "",
          profilePicture: user.profile_picture || "",
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

        const latestRoom = roomSummaries[0];
        if (!latestRoom) {
          setTodayRecommendation({ title: "", description: "" });
          return;
        }

        const roomDetail = await fetchRoom(Number(latestRoom.id));
        if (cancelled) return;

        const messages = Array.isArray(roomDetail?.messages) ? roomDetail.messages : [];
        const lastAi = [...messages]
          .reverse()
          .find((m) => m?.role === "ai" && typeof m.message === "string" && m.message.trim().length > 0);

        const clean = lastAi?.message ? lastAi.message.replace(/\s+/g, " ").trim() : "";

        setTodayRecommendation({
          title: (roomDetail?.title || "").trim(),
          description: clean,
        });
      } catch (error) {
        console.warn("Failed to fetch mypage dashboard data", error);
      }
    };

    fetchDashboardData();
    const onProfileSettings = () => fetchDashboardData();
    window.addEventListener("triver:profile-settings", onProfileSettings);

    try {
      const linked = localStorage.getItem(CALENDAR_LINKED_STORAGE_KEY);
      if (linked === "true") {
        setCalendarLinkNotice("Google Calendar linked");
      }
    } catch {
      // ignore
    }

    return () => {
      cancelled = true;
      window.removeEventListener("triver:language", onLang);
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
        if (!cancelled) {
          setCountryOptions([
            { code: "KR", name: "Korea" },
            { code: "JP", name: "Japan" },
            { code: "US", name: "United States" },
          ]);
        }
      }
    };
    loadCountries();
    return () => {
      cancelled = true;
    };
  }, []);

  const connectGoogleCalendar = useGoogleLogin({
    flow: "auth-code",
    scope: "https://www.googleapis.com/auth/calendar.readonly",
    onSuccess: async (codeResponse) => {
      try {
        setCalendarLinkNotice("Linking Google Calendar...");
        const res = await fetch(`${API_BASE}/auth/google/callback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ code: codeResponse.code }),
        });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || "Failed to link Google Calendar");
        }

        const data = await res.json();
        if (data?.access_token) {
          localStorage.setItem("access_token", data.access_token);
        }
        if (data?.refresh_token) {
          localStorage.setItem("refresh_token", data.refresh_token);
        }
        localStorage.setItem(CALENDAR_LINKED_STORAGE_KEY, "true");
        setCalendarLinkNotice("Google Calendar linked");

        // NOTE: Actual reservation sync will call a dedicated Calendar endpoint later.
        // For now we only ensure the account has granted Calendar scope.
      } catch (e) {
        console.error(e);
        setCalendarLinkNotice("Failed to link Google Calendar");
      }
    },
    onError: () => {
      setCalendarLinkNotice("Google Calendar link canceled");
    },
  });

  const reservationIndexById = useMemo(() => {
    const map: Record<string, number> = {};
    reservations.forEach((r, idx) => {
      map[r.id] = idx;
    });
    return map;
  }, [reservations]);

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
      const created = await createReservation({
        category: "transportation",
        name: trimmedName,
        date: new Date().toISOString().slice(0, 10),
        image_path: addReservationImage,
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

  const handleOpenSettings = () => {
    setSettingsDraft({
      nickname: userProfile.nickname,
      countryCode: userProfile.countryCode,
      profilePicture: userProfile.profile_picture,
    });
    setSettingsOpen(true);
  };

  const handleSaveSettingsPopup = async () => {
    setSettingsSaving(true);
    try {
      const payload = {
        nickname: settingsDraft.nickname.trim() || null,
        country_code: settingsDraft.countryCode || null,
        profile_picture: settingsDraft.profilePicture || null,
      };
      await updateCurrentUser(payload);
      setUserProfile((prev) => ({
        ...prev,
        nickname: settingsDraft.nickname.trim() || prev.nickname,
        countryCode: settingsDraft.countryCode,
        profile_picture: settingsDraft.profilePicture,
      }));
      setSettingsOpen(false);
    } catch (error) {
      console.error("Failed to update user settings", error);
    } finally {
      setSettingsSaving(false);
    }
  };

  return (
    <div className="flex w-full min-h-screen bg-gray-100 p-3 sm:p-4 gap-4 lg:h-screen lg:flex-row flex-col lg:overflow-hidden">
      <div className="flex-none lg:h-full max-w-full">
        <div className="h-full">
          <Sidebar />
        </div>
      </div>
      <main className="flex-1 min-w-0 bg-white rounded-lg lg:h-full lg:overflow-y-auto">
        <div className="p-4 sm:p-6">
          <header className="mb-6">
            <h1 className="text-2xl font-serif italic font-medium text-gray-900 mb-1">{t("headerTitle")}</h1>
            <p className="text-xs text-gray-500 font-medium tracking-wide uppercase">{t("headerSubtitle")}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="px-2.5 py-1 rounded-full bg-gray-100 text-[10px] font-bold text-gray-700">
                Rooms {trips.length}
              </span>
              <span className="px-2.5 py-1 rounded-full bg-gray-100 text-[10px] font-bold text-gray-700">
                Saved Rooms {bookmarkedRoomCount}
              </span>
              <span className="px-2.5 py-1 rounded-full bg-gray-100 text-[10px] font-bold text-gray-700">
                Reservations {reservations.length}
              </span>
            </div>
          </header>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 pb-8">
            <div className="xl:col-span-2">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-6 sm:p-8 rounded-3xl border border-gray-200 bg-white shadow-sm"
              >
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 mb-8">
                  <div className="flex items-center gap-5 min-w-0">
                    <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-full overflow-hidden border-4 border-gray-50 shadow-sm flex items-center justify-center bg-gray-200 text-gray-400 flex-none">
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
                    <div className="min-w-0">
                      <h2 className="text-2xl sm:text-3xl font-serif font-bold text-gray-900 truncate">
                        {userProfile.nickname}
                      </h2>
                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-xs text-gray-500 font-medium tracking-wide truncate">{userProfile.bio}</span>
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleOpenSettings}
                    className="h-10 px-4 rounded-full border border-gray-300 bg-white text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all"
                  >
                    {t("settings")}
                  </button>
                </div>

                <hr className="border-gray-100 mb-8" />

                <div className="space-y-8">
                  <div>
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <h3 className="text-xl font-bold text-gray-900">Travel Preferences</h3>
                      <button
                        type="button"
                        onClick={handleTogglePreferenceEdit}
                        disabled={isSavingPreferences}
                        className={`h-10 px-4 rounded-full border text-xs font-bold transition-all disabled:opacity-60 ${
                          isEditingPreferences
                            ? "border-gray-900 bg-black text-white hover:opacity-90"
                            : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                        }`}
                      >
                        {isEditingPreferences ? (isSavingPreferences ? "Saving..." : "Done") : "Edit"}
                      </button>
                    </div>
                    <p className="text-sm text-gray-500">Customize your travel DNA with your key interests.</p>
                  </div>

                  <div>
                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">{t("dnaTitle")}</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {[
                        { key: "plan" as const, label: SURVEY_ITEM_LABELS.plan, value: isEditingPreferences ? draftInsight.planPrefer : userInsight.planPrefer },
                        { key: "vibe" as const, label: SURVEY_ITEM_LABELS.vibe, value: isEditingPreferences ? draftInsight.vibePrefer : userInsight.vibePrefer },
                        { key: "places" as const, label: SURVEY_ITEM_LABELS.places, value: isEditingPreferences ? draftInsight.placesPrefer : userInsight.placesPrefer },
                      ].map((item) => {
                        const imageSrc = SURVEY_IMAGE_MAP[item.value] ?? "/image/noplan.png";
                        return (
                          <div key={item.key} className="space-y-2">
                            <div className="relative h-40 rounded-2xl overflow-hidden border border-gray-200 shadow-sm">
                              <img src={imageSrc} alt={item.value || item.label} className="w-full h-full object-cover" />
                              <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/30 to-transparent" />
                              <div className="absolute inset-x-0 bottom-0 p-4">
                                <p className="text-[10px] text-white/80 font-bold uppercase tracking-wider">{item.label}</p>
                                <p className="text-sm text-white font-bold mt-1">{item.value || "-"}</p>
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
                                    className={`px-2 py-1.5 rounded-full text-[11px] font-semibold border transition-colors ${
                                      (item.key === "plan" && draftInsight.planPrefer === opt)
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

                  <div>
                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Extra Prefer</h4>
                    <div className="flex flex-wrap gap-2.5">
                      {(isEditingPreferences
                        ? EXTRA_PREFER_OPTIONS
                        : (userProfile.preferences.length ? userProfile.preferences : ["No preference selected"])).map((pref) => (
                        <button
                          key={pref}
                          type="button"
                          onClick={() => isEditingPreferences && toggleDraftExtraPreference(pref)}
                          disabled={!isEditingPreferences && pref === "No preference selected"}
                          className={`px-4 py-2 rounded-full text-sm font-medium border shadow-sm transition-colors ${
                            isEditingPreferences
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

            <div className="flex flex-col gap-6">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="p-8 rounded-3xl bg-black text-white relative overflow-hidden group shadow-xl min-h-[260px] flex flex-col justify-between"
              >
                <div className="absolute top-0 right-0 w-80 h-80 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3 group-hover:bg-white/15 transition-colors duration-700"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-2 text-white/50 text-[10px] font-bold uppercase tracking-[0.2em] mb-5">
                    <Sparkles size={12} className="text-white" />
                    {t("todayRec")}
                  </div>
                  <h2 className="text-2xl font-serif italic font-light mb-3 tracking-wide leading-tight">
                    {todayRecommendation.title || "No recent journey yet"}
                  </h2>
                  <p className="text-white/70 text-sm font-light leading-relaxed">
                    {todayRecommendation.description || "Start a chat to build your next travel story."}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => router.push("/chatbot")}
                  className="relative z-10 w-full flex items-center justify-center gap-2 bg-white text-black px-4 py-4 rounded-xl text-xs font-bold hover:bg-gray-200 transition-all uppercase tracking-wide mt-6"
                >
                  <MessageSquare size={16} />
                  {t("startPlanning")}
                </button>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="p-6 sm:p-8 rounded-3xl border border-gray-200 bg-white flex flex-col flex-1 shadow-sm"
              >
                <div className="flex items-center justify-between mb-6">
                  <h3 className="font-bold text-sm text-gray-900 uppercase tracking-widest flex items-center gap-2">
                    <Ticket size={16} />
                    {t("reservation")}
                  </h3>
                  <button
                    type="button"
                    onClick={handleAddReservation}
                    className="text-[11px] font-bold text-gray-700 uppercase tracking-wider hover:opacity-70"
                  >
                    Add
                  </button>
                </div>

                {!!calendarLinkNotice && <div className="mb-3 text-[10px] text-gray-400 font-medium">{calendarLinkNotice}</div>}

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
                                <span className="text-[10px] text-gray-400 font-mono truncate">{res.dateLabel}</span>
                              </div>
                            </div>
                          </div>
                        </button>
                        <div className="flex items-center gap-2 flex-none">
                          <CheckCircle2 size={14} className="text-black" />
                          <button
                            type="button"
                            onClick={() => requestDeleteReservation(res)}
                            className="text-[10px] font-bold text-gray-700 uppercase tracking-wider hover:opacity-70"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="h-full min-h-[120px] flex items-center justify-center rounded-xl border border-dashed border-gray-200 bg-gray-50 text-[11px] text-gray-400 font-medium">
                      {t("noReservations")}
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
        title={t("journeyDetail")}
        menuLabel={t("menu")}
      />

      <ReservationDetailModal
        key={`${activeReservation?.id ?? "none"}-${activeReservation ? "open" : "closed"}`}
        open={!!activeReservation}
        reservation={activeReservation}
        photoUrl={activeReservation?.reservationImageUrl}
        onSavePhoto={async (nextUrl) => {
          if (!activeReservation) return;
          try {
            const updated = await updateReservation(activeReservation.reservationId, {
              image_path: nextUrl || null,
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
              const reader = new FileReader();
              reader.onload = () => {
                const next = typeof reader.result === "string" ? reader.result : "";
                if (!next) return;
                setAddReservationImage(next);
                setAddReservationError("");
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

      <SimpleModal open={settingsOpen} title="Settings" onClose={() => setSettingsOpen(false)}>
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
                  <span className="text-[10px] font-semibold">{t("noImage")}</span>
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

          <div className="pt-1 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setSettingsOpen(false)}
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
      </SimpleModal>
    </div>
  );
}
