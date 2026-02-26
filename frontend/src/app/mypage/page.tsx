"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Languages,
  Ticket,
  CheckCircle2,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { SettingsModal } from "@/components/SettingsModal";

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
  title: string;
  subtitle: string;
  dateLabel: string;
  details: { label: string; value: string }[];
};

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
}: {
  open: boolean;
  trip: TripSummary | null;
  onClose: () => void;
}) {
  if (!open || !trip) return null;

  const detail = trip.detail;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Close"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />

      <div className="relative z-10 w-full max-w-xl rounded-xl bg-white border border-gray-200 shadow-lg overflow-hidden flex flex-col">
        <div className="p-6 pb-4">
          <h2 className="text-3xl font-bold text-gray-900 text-center">Journey Detail</h2>
        </div>

        <div className="px-6 pb-4">
          <div className="rounded-xl border border-gray-200 bg-white p-5 max-h-[55vh] overflow-y-auto">
            <p className="text-xs text-gray-700 leading-relaxed">
              {detail?.intro ?? "(Mock) 챗봇 동선/추천 요약이 여기에 표시됩니다."}
            </p>

            {detail && (
              <ol className="mt-4 space-y-4 text-xs text-gray-800">
                <li>
                  <div className="font-bold">1. Restaurants Options</div>
                  <ul className="mt-2 space-y-1 list-disc pl-5">
                    {detail.restaurantOptions.map((r) => (
                      <li key={r.name}>
                        <span className="font-bold">{r.name}</span>: {r.desc}
                      </li>
                    ))}
                  </ul>
                </li>
                <li>
                  <div className="font-bold">2. Local Tourist Attractions</div>
                  <ul className="mt-2 space-y-1 list-disc pl-5">
                    {detail.attractions.map((a) => (
                      <li key={a.name}>
                        <span className="font-bold">{a.name}</span>: {a.desc}
                      </li>
                    ))}
                  </ul>
                </li>
              </ol>
            )}

            {!detail && (
              <div className="mt-4 space-y-2">
                {(trip.messages || []).map((m, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg border ${m.role === "assistant" ? "bg-gray-50 border-gray-200" : "bg-white border-gray-200"}`}
                  >
                    <div className="text-[9px] font-bold uppercase tracking-widest text-gray-400 mb-1">
                      {m.role === "assistant" ? "Assistant" : "User"}
                    </div>
                    <div className="text-xs text-gray-800 leading-relaxed">{m.text}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="px-6 pb-6">
          <button
            type="button"
            onClick={onClose}
            className="w-full bg-black text-white py-3 rounded-lg text-sm font-semibold"
          >
            Menu
          </button>
        </div>
      </div>
    </div>
  );
}

function computeDna(preferences: string[]) {
  const set = new Set(preferences);

  const foodDriven = set.has("Food") ? 5 : set.has("Luxury") ? 4 : 3;
  const calmExplorer = set.has("Relaxation") ? 5 : set.has("Nature") ? 4 : 3;
  const cultureCurious = set.has("Culture") ? 5 : set.has("Adventure") ? 4 : 3;

  return [
    { label: "Food-Driven", score: foodDriven },
    { label: "Calm Explorer", score: calmExplorer },
    { label: "Culture Curious", score: cultureCurious },
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
  const [userProfile, setUserProfile] = useState({
    nickname: "",
    bio: "Explorer Lvl.3",
    preferences: ["Relaxation", "Food"],
    profile_picture: "",
  });

  const [activeTrip, setActiveTrip] = useState<TripSummary | null>(null);
  const [activeReservation, setActiveReservation] = useState<ReservationItem | null>(null);

  useEffect(() => {
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
  }, []);

  const handleSaveSettings = (nickname: string, bio: string, preferences: string[]) => {
    setUserProfile((prev) => ({ ...prev, nickname, bio, preferences }));
  };

  const trips: TripSummary[] = [
    {
      id: "trip-1",
      title: "Trip to Busan",
      messages: [
        { role: "user", text: "부산 1박2일로 동선 추천해줘" },
        { role: "assistant", text: "해운대 → 광안리 → 자갈치시장 중심으로 동선을 제안드릴게요." },
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

  const reservations: ReservationItem[] = [
    {
      id: "res-1",
      title: "KTX Busan",
      subtitle: "Seoul → Busan",
      dateLabel: "10:00AM · 2026.02.23",
      details: [
        { label: "Type", value: "Train" },
        { label: "Provider", value: "Korail" },
        { label: "From", value: "Seoul Station" },
        { label: "To", value: "Busan Station" },
        { label: "Departure", value: "10:00AM" },
      ],
    },
  ];

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
              <h1 className="text-2xl font-serif italic font-medium text-gray-900 mb-1">Traveler's Profile</h1>
              <p className="text-xs text-gray-500 font-medium tracking-wide uppercase">Traveler Profile</p>
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
                  <div className="w-20 h-20 rounded-xl overflow-hidden border border-gray-100 shadow-sm flex items-center justify-center bg-gray-200 text-gray-400">
                    {userProfile.profile_picture ? (
                      <img
                        src={userProfile.profile_picture}
                        alt="Profile"
                        className="w-full h-full object-cover grayscale-[20%]"
                      />
                    ) : (
                      <span className="font-medium text-xs">No Image</span>
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
                    Settings
                  </button>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg border border-gray-100/50">
                    <div className="flex items-center gap-2">
                      <Languages size={14} className="text-gray-400" />
                      <div className="flex flex-col">
                        <span className="text-[10px] font-bold text-gray-900 uppercase">Language</span>
                        <span className="text-[9px] text-gray-500">English (US)</span>
                      </div>
                    </div>
                    <button className="text-[9px] font-bold text-black border-b border-black leading-none pb-0.5 hover:opacity-70">Change</button>
                  </div>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="p-5 rounded-xl border border-gray-200 bg-white hover:border-gray-300 transition-colors"
              >
                <div className="mb-3 border-b border-gray-50 pb-2">
                  <h3 className="font-bold text-xs text-gray-900 uppercase tracking-widest">Triver's Travel DNA</h3>
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
                  <p className="text-sm font-bold text-gray-900">You are a</p>
                  <p className="text-base font-extrabold text-gray-900">{topTrait.label}</p>
                  <p className="text-sm font-bold text-gray-900">Traveler!</p>
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
                      <Sparkles size={10} className="text-white" /> Today's Recommendation
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
                    <MessageSquare size={12} /> Start Planning
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
                    <h3 className="font-bold text-xs text-gray-900 uppercase tracking-widest">Scheduled Journey</h3>
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
                          <span className="text-[9px] text-gray-400 font-bold uppercase tracking-wider">Open</span>
                        </div>
                        <p className="mt-1 text-[10px] text-gray-500">
                          Tap to view related chat summary (mock).
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
                    <h3 className="font-bold text-xs text-gray-900 uppercase tracking-widest">Reservation</h3>
                  </div>
                  <div className="space-y-2.5 flex-1 max-h-[210px] overflow-y-auto pr-1">
                    {reservations.map((res) => (
                      <button
                        key={res.id}
                        type="button"
                        onClick={() => setActiveReservation(res)}
                        className="w-full group p-2.5 rounded-lg border border-gray-100 hover:border-gray-300 hover:bg-gray-50 transition-all cursor-pointer flex items-center justify-between text-left"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-md bg-gray-100 flex items-center justify-center text-gray-500 group-hover:bg-white group-hover:text-black transition-colors border border-gray-200">
                            <Ticket size={12} />
                          </div>
                          <div>
                            <h4 className="text-[11px] font-bold text-gray-900 leading-tight">{res.title}</h4>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <span className="text-[9px] text-gray-400 font-medium uppercase">{res.subtitle}</span>
                              <span className="text-[9px] text-gray-300">•</span>
                              <span className="text-[9px] text-gray-400 font-mono">{res.dateLabel}</span>
                            </div>
                          </div>
                        </div>
                        <CheckCircle2 size={14} className="text-black" />
                      </button>
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
      />

      <SimpleModal
        open={!!activeReservation}
        title={activeReservation ? activeReservation.title : "Reservation"}
        onClose={() => setActiveReservation(null)}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {(activeReservation?.details || []).map((d) => (
            <div key={d.label} className="p-3 rounded-lg border border-gray-200 bg-white">
              <div className="text-[9px] font-bold uppercase tracking-widest text-gray-400">{d.label}</div>
              <div className="text-xs font-semibold text-gray-900 mt-1">{d.value}</div>
            </div>
          ))}
        </div>
        <div className="mt-3 text-[10px] text-gray-500">
          (Mock) 나중에 Google Calendar 연동 후 예약 상세를 불러올 예정입니다.
        </div>
      </SimpleModal>
    </div>
  );
}
