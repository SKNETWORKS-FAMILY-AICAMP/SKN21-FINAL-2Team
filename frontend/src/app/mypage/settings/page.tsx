"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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
    savedNotice: "Your information has been saved.",
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
    savedNotice: "저장되었습니다.",
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
    savedNotice: "保存しました。",
    deactivate: "アカウントを無効化 →",
    back: "マイページへ",
  },
};

export default function MyPageSettingsPage() {
  const router = useRouter();

  const saveNoticeTimerRef = useRef<number | null>(null);

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
  const [saveNotice, setSaveNotice] = useState<string>("");

  const [deactivateOpen, setDeactivateOpen] = useState<boolean>(false);
  const [deactivateEmailConfirmed, setDeactivateEmailConfirmed] = useState<boolean>(false);
  const [deactivateAgreementChecked, setDeactivateAgreementChecked] = useState<boolean>(false);
  const [deactivateShowFinalConfirm, setDeactivateShowFinalConfirm] = useState<boolean>(false);
  const [deactivateEmailError, setDeactivateEmailError] = useState<string>("");
  const [deactivateAgreementError, setDeactivateAgreementError] = useState<string>("");

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
    return () => {
      if (saveNoticeTimerRef.current) {
        window.clearTimeout(saveNoticeTimerRef.current);
      }
    };
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
    window.dispatchEvent(new Event("triver:profile-settings"));

    setSaveNotice(t("savedNotice"));
    if (saveNoticeTimerRef.current) {
      window.clearTimeout(saveNoticeTimerRef.current);
    }
    saveNoticeTimerRef.current = window.setTimeout(() => {
      setSaveNotice("");
    }, 2500);
  };

  const openDeactivateModal = () => {
    setDeactivateOpen(true);
    setDeactivateEmailConfirmed(false);
    setDeactivateAgreementChecked(false);
    setDeactivateShowFinalConfirm(false);
    setDeactivateEmailError("");
    setDeactivateAgreementError("");
  };

  const confirmWithGoogle = async () => {
    setDeactivateEmailError("");

    const isValidEmail = (value: string) => /\S+@\S+\.\S+/.test(value);
    const isPlaceholderEmail = (value: string) => value.trim().toLowerCase() === "user@gmail.com";

    let token: string | null = null;
    try {
      token = localStorage.getItem("access_token");
    } catch {
      token = null;
    }

    if (!token) {
      setDeactivateEmailConfirmed(false);
      setDeactivateEmailError("Please confirm your email");
      return;
    }

    const candidates: string[] = [];
    if (typeof email === "string" && !isPlaceholderEmail(email)) candidates.push(email);

    try {
      const fromLocal = localStorage.getItem("user_email");
      if (fromLocal) candidates.push(fromLocal);
    } catch {
      // ignore
    }

    const best = candidates.find((c) => typeof c === "string" && isValidEmail(c) && !isPlaceholderEmail(c));
    if (best) {
      setEmail(best);
      setDeactivateEmailConfirmed(true);
      setDeactivateEmailError("");
      return;
    }

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("bad response");
      const data = await res.json();
      if (typeof data?.email === "string" && isValidEmail(data.email) && !isPlaceholderEmail(data.email)) {
        setEmail(data.email);
        setDeactivateEmailConfirmed(true);
        setDeactivateEmailError("");
        return;
      }
    } catch {
      // ignore
    }

    setDeactivateEmailConfirmed(false);
    setDeactivateEmailError("Please confirm your email");
  };

  const requestDeactivate = () => {
    let ok = true;

    if (!deactivateEmailConfirmed) {
      setDeactivateEmailError("Please confirm your email");
      ok = false;
    } else {
      setDeactivateEmailError("");
    }

    if (!deactivateAgreementChecked) {
      setDeactivateAgreementError("Please confirm the account termination agreement");
      ok = false;
    } else {
      setDeactivateAgreementError("");
    }

    if (!ok) return;
    setDeactivateShowFinalConfirm(true);
  };

  const deactivateAccount = () => {
    try {
      const keysToRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (!k) continue;
        if (
          k.startsWith("triver:") ||
          k === "access_token" ||
          k === "refresh_token" ||
          k === "user_email" ||
          k === "user_name" ||
          k === "profile_picture"
        ) {
          keysToRemove.push(k);
        }
      }
      keysToRemove.forEach((k) => localStorage.removeItem(k));
    } catch {
      // ignore
    }

    window.dispatchEvent(new Event("triver:language"));
    window.dispatchEvent(new Event("triver:profile-settings"));

    setDeactivateOpen(false);
    setDeactivateShowFinalConfirm(false);
    router.push("/");
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

            {saveNotice && (
              <div className="mt-2 flex justify-end">
                <div className="text-[11px] text-gray-500 font-medium">{saveNotice}</div>
              </div>
            )}

            <div className="mt-2 flex justify-end">
              <button
                type="button"
                onClick={openDeactivateModal}
                className="text-xs text-gray-700 font-medium hover:opacity-90"
              >
                {t("deactivate")}
              </button>
            </div>
          </section>
        </div>
      </main>

      {deactivateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-[520px] rounded-xl border border-gray-200 bg-white">
            <div className="p-6">
              <h2 className="text-3xl font-semibold text-gray-900 mb-4">Deactivate Account</h2>
              <p className="text-sm text-gray-700 leading-relaxed mb-6">
                Note: Deactivating your account will temporarily hide your saved chats, information, and location bookmarks.
              </p>

              <div className="mb-6">
                <button
                  type="button"
                  onClick={confirmWithGoogle}
                  className="bg-black text-white px-6 py-3 rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
                >
                  Confirm with Google
                </button>
                {deactivateEmailConfirmed && (
                  <div className="mt-2 text-xs text-gray-600 font-medium">{email}</div>
                )}
                {deactivateEmailError && <div className="mt-2 text-xs text-red-500 font-semibold">{deactivateEmailError}</div>}
              </div>

              <div className="flex items-center justify-between gap-4 mb-6">
                <div className="text-sm text-gray-800 font-medium leading-snug">
                  I understand that my account will be deactivated and access to Trivers will be paused.
                </div>
                <input
                  type="checkbox"
                  checked={deactivateAgreementChecked}
                  onChange={(e) => {
                    setDeactivateAgreementChecked(e.target.checked);
                    if (e.target.checked) setDeactivateAgreementError("");
                  }}
                  className="h-6 w-6 accent-black"
                />
              </div>
              {deactivateAgreementError && (
                <div className="-mt-4 mb-6 text-xs text-red-500 font-semibold">{deactivateAgreementError}</div>
              )}

              <div className="flex items-center justify-between gap-4">
                <button
                  type="button"
                  onClick={requestDeactivate}
                  className="flex-1 bg-black text-white px-6 py-3 rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
                >
                  Deactivate Account
                </button>
                <button
                  type="button"
                  onClick={() => setDeactivateOpen(false)}
                  className="flex-1 bg-black text-white px-6 py-3 rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>

          {deactivateShowFinalConfirm && (
            <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4">
              <div className="w-full max-w-[420px] rounded-xl border border-gray-200 bg-white p-6">
                <div className="text-lg font-semibold text-gray-900 mb-5">Are you sure you wanna deactivate your account?</div>
                <div className="flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setDeactivateShowFinalConfirm(false)}
                    className="bg-gray-200 text-gray-900 px-6 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-300 transition-colors"
                  >
                    No
                  </button>
                  <button
                    type="button"
                    onClick={deactivateAccount}
                    className="bg-black text-white px-6 py-2.5 rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
                  >
                    Yes
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
