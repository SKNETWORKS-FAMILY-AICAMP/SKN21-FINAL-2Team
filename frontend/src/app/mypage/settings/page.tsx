"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";

type AppLanguage = "en" | "ko" | "ja";

type ProfileSettings = {
  nickname: string;
  country: string;
  email: string;
  language: AppLanguage;
  travelNotes: string[];
  travelPreferences: [string, string, string];
};

const SETTINGS_STORAGE_KEY = "triver:profile-settings:v1";
const LANGUAGE_STORAGE_KEY = "triver:language:v1";

const COUNTRIES = [
  "Korea",
  "Japan",
  "United States",
  "Canada",
  "United Kingdom",
  "France",
  "Germany",
  "Italy",
  "Spain",
  "Portugal",
  "Netherlands",
  "Belgium",
  "Switzerland",
  "Austria",
  "Sweden",
  "Norway",
  "Denmark",
  "Finland",
  "Ireland",
  "Poland",
  "Czech Republic",
  "Hungary",
  "Greece",
  "Turkey",
  "Russia",
  "China",
  "Taiwan",
  "Hong Kong",
  "Singapore",
  "Thailand",
  "Vietnam",
  "Philippines",
  "Indonesia",
  "Malaysia",
  "India",
  "Australia",
  "New Zealand",
  "Mexico",
  "Brazil",
  "Argentina",
  "Chile",
  "South Africa",
  "Egypt",
  "United Arab Emirates",
  "Saudi Arabia",
];

const TRAVEL_NOTES = ["Religion", "Vegan", "Food Allergies", "Halal", "Gluten Free", "Culture"];
const TRAVEL_STYLE_OPTIONS = ["Relaxation", "Adventure", "Culture", "Food", "Nature", "Luxury"];

const I18N: Record<AppLanguage, Record<string, string>> = {
  en: {
    title: "Profile Settings",
    profilePicture: "Profile Picture",
    editNickname: "Edit Nickname",
    country: "Country",
    switchLanguage: "Switch Language",
    confirmedEmail: "Confirmed Email",
    travelNotes: "Travel Notes",
    travelPreference: "Travel Preference",
    pref1: "Travel Preference 1",
    pref2: "Travel Preference 2",
    pref3: "Travel Preference 3",
    save: "Save",
    deactivate: "Deactivate Account →",
    back: "Back to MyPage",
  },
  ko: {
    title: "프로필 설정",
    profilePicture: "프로필 사진",
    editNickname: "닉네임 변경",
    country: "국가",
    switchLanguage: "언어 변경",
    confirmedEmail: "확인된 이메일",
    travelNotes: "여행 특이사항",
    travelPreference: "여행 스타일 선호도",
    pref1: "여행 선호도 1",
    pref2: "여행 선호도 2",
    pref3: "여행 선호도 3",
    save: "저장",
    deactivate: "계정 탈퇴 →",
    back: "마이페이지로",
  },
  ja: {
    title: "プロフィール設定",
    profilePicture: "プロフィール画像",
    editNickname: "ニックネーム編集",
    country: "国",
    switchLanguage: "言語切替",
    confirmedEmail: "確認済みメール",
    travelNotes: "旅行メモ",
    travelPreference: "旅行の好み",
    pref1: "旅行の好み 1",
    pref2: "旅行の好み 2",
    pref3: "旅行の好み 3",
    save: "保存",
    deactivate: "アカウントを無効化 →",
    back: "マイページへ",
  },
};

export default function MyPageSettingsPage() {
  const router = useRouter();

  const [profilePictureUrl, setProfilePictureUrl] = useState<string>("");
  const [language, setLanguage] = useState<AppLanguage>("en");
  const [nickname, setNickname] = useState<string>("Kev_Trivers");
  const [country, setCountry] = useState<string>("Korea");
  const [email, setEmail] = useState<string>("user@gmail.com");
  const [travelNotes, setTravelNotes] = useState<string[]>(["Religion", "Food Allergies"]);
  const [travelPreferences, setTravelPreferences] = useState<[string, string, string]>([
    "Relaxation",
    "Food",
    "Culture",
  ]);

  const t = useMemo(() => {
    const dict = I18N[language] ?? I18N.en;
    return (key: string) => dict[key] ?? I18N.en[key] ?? key;
  }, [language]);

  useEffect(() => {
    try {
      const savedLang = (localStorage.getItem(LANGUAGE_STORAGE_KEY) || "") as AppLanguage;
      if (savedLang === "en" || savedLang === "ko" || savedLang === "ja") {
        setLanguage(savedLang);
      }

      const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<ProfileSettings>;
        if (typeof parsed.nickname === "string") setNickname(parsed.nickname);
        if (typeof parsed.country === "string") setCountry(parsed.country);
        if (typeof parsed.email === "string") setEmail(parsed.email);
        if (Array.isArray(parsed.travelNotes)) setTravelNotes(parsed.travelNotes.filter((x) => typeof x === "string"));
        if (Array.isArray(parsed.travelPreferences) && parsed.travelPreferences.length === 3) {
          const [a, b, c] = parsed.travelPreferences as any;
          if (typeof a === "string" && typeof b === "string" && typeof c === "string") {
            setTravelPreferences([a, b, c]);
          }
        }
        if (parsed.language === "en" || parsed.language === "ko" || parsed.language === "ja") {
          setLanguage(parsed.language);
        }
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const token = localStorage.getItem("access_token");
        if (!token) return;

        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/users/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!res.ok) return;
        const data = await res.json();
        if (typeof data?.profile_picture === "string") setProfilePictureUrl(data.profile_picture);
        if (typeof data?.email === "string") setEmail(data.email);
      } catch {
        // ignore
      }
    };
    fetchUser();
  }, []);

  const toggleNote = (note: string) => {
    setTravelNotes((prev) => (prev.includes(note) ? prev.filter((x) => x !== note) : [...prev, note]));
  };

  const handleSave = () => {
    const payload: ProfileSettings = {
      nickname,
      country,
      email,
      language,
      travelNotes,
      travelPreferences,
    };
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(payload));
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    window.dispatchEvent(new Event("triver:language"));
  };

  const onChangeLanguage = (next: AppLanguage) => {
    setLanguage(next);
    localStorage.setItem(LANGUAGE_STORAGE_KEY, next);
    window.dispatchEvent(new Event("triver:language"));
  };

  const onChangePreference = (index: 0 | 1 | 2, value: string) => {
    setTravelPreferences((prev) => {
      const next: [string, string, string] = [...prev] as any;
      next[index] = value;
      return next;
    });
  };

  return (
    <div className="flex w-full h-screen bg-gray-100 p-4 gap-4 overflow-hidden">
      <div className="flex-none h-full">
        <Sidebar />
      </div>

      <main className="flex-1 h-full min-w-0 bg-white rounded-lg border border-gray-200 overflow-y-auto">
        <header className="p-6 border-b border-gray-100 flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-serif italic font-medium text-gray-900 mb-1">{t("title")}</h1>
            <p className="text-xs text-gray-500 font-medium tracking-wide uppercase">Profile</p>
          </div>
          <button
            type="button"
            onClick={() => router.push("/mypage")}
            className="bg-black text-white px-4 py-2.5 rounded-lg text-[10px] font-bold hover:opacity-90 transition-all uppercase tracking-wide"
          >
            {t("back")}
          </button>
        </header>

        <div className="p-6 space-y-10 min-h-[120vh]">
          {/* Profile Settings */}
          <section className="rounded-xl border border-gray-200 bg-white p-6">
            <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-6">
              <div className="rounded-xl bg-gray-200 border border-gray-200 h-[220px] flex items-center justify-center text-gray-600 font-semibold">
                {profilePictureUrl ? (
                  <img src={profilePictureUrl} alt="Profile" className="w-full h-full object-cover rounded-xl grayscale-[20%]" />
                ) : (
                  <span>{t("profilePicture")}</span>
                )}
              </div>

              <div className="space-y-4">
                <div>
                  <div className="text-xs font-bold text-gray-900 mb-2">{t("editNickname")}</div>
                  <input
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    className="w-full sm:max-w-[280px] h-10 px-3 rounded-lg bg-gray-100 border border-gray-200 text-sm font-medium text-gray-900"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-end">
                  <div>
                    <div className="text-xs font-bold text-gray-900 mb-2">{t("country")}</div>
                    <select
                      value={country}
                      onChange={(e) => setCountry(e.target.value)}
                      className="w-full h-10 px-3 rounded-lg bg-gray-100 border border-gray-200 text-sm font-medium text-gray-900"
                    >
                      {COUNTRIES.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <div className="text-xs font-bold text-gray-900 mb-2">{t("switchLanguage")}</div>
                    <select
                      value={language}
                      onChange={(e) => onChangeLanguage(e.target.value as AppLanguage)}
                      className="w-full h-10 px-3 rounded-lg bg-gray-100 border border-gray-200 text-sm font-medium text-gray-900"
                    >
                      <option value="en">English</option>
                      <option value="ko">한국어</option>
                      <option value="ja">日本語</option>
                    </select>
                  </div>
                </div>

                <div>
                  <div className="text-xs font-bold text-gray-900 mb-2">{t("confirmedEmail")}</div>
                  <input
                    value={email}
                    readOnly
                    className="w-full h-10 px-3 rounded-lg bg-gray-100 border border-gray-200 text-sm font-medium text-gray-500"
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Travel Notes */}
          <section className="border-t border-gray-100 pt-8">
            <h2 className="text-xl font-serif italic font-medium text-gray-900 mb-4">{t("travelNotes")}</h2>
            <div className="flex flex-wrap gap-3">
              {TRAVEL_NOTES.map((note) => {
                const active = travelNotes.includes(note);
                return (
                  <button
                    key={note}
                    type="button"
                    onClick={() => toggleNote(note)}
                    className={
                      active
                        ? "px-6 py-2 rounded-full bg-black text-white text-xs font-semibold"
                        : "px-6 py-2 rounded-full bg-white text-gray-800 text-xs font-semibold border border-gray-200 hover:border-gray-400"
                    }
                  >
                    {note}
                  </button>
                );
              })}
            </div>
          </section>

          {/* Travel Preference */}
          <section className="border-t border-gray-100 pt-8">
            <h2 className="text-xl font-serif italic font-medium text-gray-900 mb-6">{t("travelPreference")}</h2>
            <div className="space-y-4 max-w-2xl">
              <div className="flex items-center justify-between gap-4">
                <div className="text-sm font-semibold text-gray-900">• {t("pref1")}</div>
                <select
                  value={travelPreferences[0]}
                  onChange={(e) => onChangePreference(0, e.target.value)}
                  className="w-[180px] h-10 px-3 rounded-lg bg-gray-100 border border-gray-200 text-sm font-semibold text-gray-900"
                >
                  {TRAVEL_STYLE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center justify-between gap-4">
                <div className="text-sm font-semibold text-gray-900">• {t("pref2")}</div>
                <select
                  value={travelPreferences[1]}
                  onChange={(e) => onChangePreference(1, e.target.value)}
                  className="w-[180px] h-10 px-3 rounded-lg bg-gray-100 border border-gray-200 text-sm font-semibold text-gray-900"
                >
                  {TRAVEL_STYLE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center justify-between gap-4">
                <div className="text-sm font-semibold text-gray-900">• {t("pref3")}</div>
                <select
                  value={travelPreferences[2]}
                  onChange={(e) => onChangePreference(2, e.target.value)}
                  className="w-[180px] h-10 px-3 rounded-lg bg-gray-100 border border-gray-200 text-sm font-semibold text-gray-900"
                >
                  {TRAVEL_STYLE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mt-8 flex items-center justify-end">
              <button
                type="button"
                onClick={handleSave}
                className="bg-gray-200 text-gray-900 px-10 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-300 transition-colors"
              >
                {t("save")}
              </button>
            </div>

            <div className="mt-2 flex justify-end">
              <button
                type="button"
                disabled
                className="text-xs text-gray-400 font-medium hover:opacity-90 disabled:cursor-not-allowed"
                title="Coming soon"
              >
                {t("deactivate")}
              </button>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
