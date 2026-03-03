"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { Moon, Sun } from "lucide-react";
import { fetchCurrentUser, updateCurrentUser } from "@/services/api";
import { useGoogleLogin } from "@react-oauth/google";

type AppLanguage = "en" | "ko" | "ja";

type ThemeMode = "light" | "dark";

type ProfileSettings = {
  nickname: string;
  bio: string;
  country: string;
  email: string;
  language: AppLanguage;
  travelNotes: string[];
  travelPreferences: [string, string, string];
};

const SETTINGS_STORAGE_KEY = "triver:profile-settings:v1";
const LANGUAGE_STORAGE_KEY = "triver:language:v1";
const THEME_STORAGE_KEY = "triver:theme:v1";
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

const TRAVEL_STYLE_EMOJI: Record<string, string> = {
  Relaxation: "🧘",
  Adventure: "🧗",
  Culture: "🏛️",
  Food: "🍜",
  Nature: "🌿",
  Luxury: "💎",
};

const formatTravelStyleOptionLabel = (opt: string) => {
  const emoji = TRAVEL_STYLE_EMOJI[opt] ?? "✨";
  return `${emoji} ${opt}`;
};

// TODO: Google 계정 확인(재인증) UI/연동 붙일 때 true로 전환
const ENABLE_GOOGLE_CONFIRM = true;

const I18N: Record<AppLanguage, Record<string, string>> = {
  en: {
    title: "Profile Settings",
    profilePicture: "Profile Picture",
    editNickname: "Edit Nickname",
    miniBio: "Mini Bio",
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

    deactivateTitle: "Deactivate Account",
    deactivateNote:
      "Note: Deactivating your account will temporarily hide your saved chats, information, and location bookmarks.",
    deactivateConfirmGoogle: "Confirm with Google",
    deactivateGoogleSoon: "(Coming soon) Google confirmation will be enabled later.",
    deactivateAgreement:
      "I understand that my account will be deactivated and access to Trivers will be paused.",
    deactivatePrimary: "Deactivate Account",
    deactivateCancel: "Cancel",
    deactivateFinalConfirm: "Are you sure you wanna deactivate your account?",
    yes: "Yes",
    no: "No",
    errConfirmEmail: "Please confirm your email",
    errConfirmAgreement: "Please confirm the account termination agreement",
  },
  ko: {
    title: "프로필 설정",
    profilePicture: "프로필 사진",
    editNickname: "닉네임 변경",
    miniBio: "한줄 소개",
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

    deactivateTitle: "계정 탈퇴",
    deactivateNote:
      "안내: 계정을 탈퇴하면 저장된 채팅, 정보, 위치 북마크가 일시적으로 숨겨집니다.",
    deactivateConfirmGoogle: "Google로 확인",
    deactivateGoogleSoon: "(준비중) Google 확인 기능은 추후 활성화됩니다.",
    deactivateAgreement: "계정이 탈퇴되고 Trivers 이용이 중지되는 것에 동의합니다.",
    deactivatePrimary: "계정 탈퇴",
    deactivateCancel: "취소",
    deactivateFinalConfirm: "정말 계정을 탈퇴하시겠습니까?",
    yes: "예",
    no: "아니오",
    errConfirmEmail: "이메일을 확인해주세요",
    errConfirmAgreement: "계정 탈퇴 동의 항목을 확인해주세요",
  },
  ja: {
    title: "プロフィール設定",
    profilePicture: "プロフィール画像",
    editNickname: "ニックネーム編集",
    miniBio: "ひとこと",
    country: "国/地域",
    switchLanguage: "言語切替",
    confirmedEmail: "確認済みメールアドレス",
    travelNotes: "旅行メモ",
    travelPreference: "旅行の好み",
    pref1: "旅行の好み 1",
    pref2: "旅行の好み 2",
    pref3: "旅行の好み 3",
    save: "保存",
    savedNotice: "保存しました。",
    deactivate: "アカウントを無効化 →",
    back: "マイページへ",

    deactivateTitle: "アカウントを無効化",
    deactivateNote:
      "注意：アカウントを無効化すると、保存したチャット、情報、位置ブックマークが一時的に非表示になります。",
    deactivateConfirmGoogle: "Googleで確認",
    deactivateGoogleSoon: "（準備中）Googleでの確認は後ほど利用できます。",
    deactivateAgreement: "アカウントが無効化され、Triversへのアクセスが一時停止されることを理解しました。",
    deactivatePrimary: "アカウントを無効化",
    deactivateCancel: "キャンセル",
    deactivateFinalConfirm: "本当にアカウントを無効化しますか？",
    yes: "はい",
    no: "いいえ",
    errConfirmEmail: "メールを確認してください",
    errConfirmAgreement: "退会に同意してください",
  },
};

const isAppLanguage = (value: unknown): value is AppLanguage =>
  value === "en" || value === "ko" || value === "ja";

const isThemeMode = (value: unknown): value is ThemeMode =>
  value === "dark" || value === "light";

const getStoredSettings = (): Partial<ProfileSettings> => {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    return parsed as Partial<ProfileSettings>;
  } catch {
    return {};
  }
};

const getStoredLanguage = (): AppLanguage => {
  if (typeof window === "undefined") return "en";
  const settings = getStoredSettings();
  if (isAppLanguage(settings.language)) return settings.language;
  const raw = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return isAppLanguage(raw) ? raw : "en";
};

const getStoredTheme = (): ThemeMode => {
  if (typeof window === "undefined") return "light";
  const raw = localStorage.getItem(THEME_STORAGE_KEY);
  return isThemeMode(raw) ? raw : "light";
};

const getStoredTravelPreferences = (): [string, string, string] => {
  const defaults: [string, string, string] = ["Relaxation", "Food", "Culture"];
  const settings = getStoredSettings();
  const prefs = settings.travelPreferences;
  if (
    Array.isArray(prefs)
    && prefs.length === 3
    && prefs.every((x) => typeof x === "string")
  ) {
    return [prefs[0], prefs[1], prefs[2]];
  }
  return defaults;
};

export default function MyPageSettingsPage() {
  const router = useRouter();

  const saveNoticeTimerRef = useRef<number | null>(null);

  const [profilePictureUrl, setProfilePictureUrl] = useState<string>("");
  const [language, setLanguage] = useState<AppLanguage>(() => getStoredLanguage());
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => getStoredTheme());
  const [nickname, setNickname] = useState<string>(() => {
    const s = getStoredSettings();
    return typeof s.nickname === "string" ? s.nickname : "Traveling_Trivers67";
  });
  const [bio, setBio] = useState<string>(() => {
    const s = getStoredSettings();
    return typeof s.bio === "string" ? s.bio : "Explorer Lvl.3";
  });
  const [country, setCountry] = useState<string>(() => {
    const s = getStoredSettings();
    return typeof s.country === "string" ? s.country : "Korea";
  });
  const [email, setEmail] = useState<string>(() => {
    const s = getStoredSettings();
    return typeof s.email === "string" ? s.email : "user@gmail.com";
  });
  const [travelNotes, setTravelNotes] = useState<string[]>(() => {
    const s = getStoredSettings();
    return Array.isArray(s.travelNotes)
      ? s.travelNotes.filter((x): x is string => typeof x === "string")
      : ["Religion", "Food Allergies"];
  });
  const [travelPreferences, setTravelPreferences] = useState<[string, string, string]>(() => getStoredTravelPreferences());
  const [saveNotice, setSaveNotice] = useState<string>("");

  const [deactivateOpen, setDeactivateOpen] = useState<boolean>(false);
  const [deactivateEmailConfirmed, setDeactivateEmailConfirmed] = useState<boolean>(false);
  const [deactivateAgreementChecked, setDeactivateAgreementChecked] = useState<boolean>(false);
  const [deactivateShowFinalConfirm, setDeactivateShowFinalConfirm] = useState<boolean>(false);
  const [deactivateEmailError, setDeactivateEmailError] = useState<string>("");
  const [deactivateAgreementError, setDeactivateAgreementError] = useState<string>("");
  const [googleConfirmBusy, setGoogleConfirmBusy] = useState<boolean>(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
  const GOOGLE_CALLBACK_URL = API_BASE.endsWith("/api")
    ? `${API_BASE}/auth/google/callback`
    : `${API_BASE}/api/auth/google/callback`;

  const t = useMemo(() => {
    const dict = I18N[language] ?? I18N.en;
    return (key: string) => dict[key] ?? I18N.en[key] ?? key;
  }, [language]);

  const isTravelStyleOptionDisabled = (slotIndex: number, opt: string) => {
    // Prevent duplicate selections across the 3 preference slots.
    return travelPreferences.some((v, i) => i !== slotIndex && v === opt);
  };

  const toggleThemeMode = () => {
    setThemeMode((prev) => {
      const next: ThemeMode = prev === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(THEME_STORAGE_KEY, next);
      } catch {
        // ignore
      }
      return next;
    });
  };

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
        const data = await fetchCurrentUser();
        if (typeof data?.profile_picture === "string") setProfilePictureUrl(data.profile_picture);
        if (typeof data?.email === "string") setEmail(data.email);

        // Hydrate Travel Preference from DB when available (no backend change required).
        const fromDb = [data?.extra_prefer1, data?.extra_prefer2, data?.extra_prefer3].filter(
          (x): x is string => typeof x === "string" && x.trim().length > 0,
        );
        if (fromDb.length === 3) {
          setTravelPreferences([fromDb[0], fromDb[1], fromDb[2]]);
        }
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
      bio,
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

    // Persist Travel Preference to DB (maps to existing user columns extra_prefer1~3).
    // Travel Notes는 현재 백엔드 스키마에 대응 컬럼이 없어 저장하지 않습니다.
    (async () => {
      try {
        await updateCurrentUser({
          extra_prefer1: travelPreferences[0],
          extra_prefer2: travelPreferences[1],
          extra_prefer3: travelPreferences[2],
        });
      } catch {
        // ignore: keep local saved settings even when API is unavailable
      }
    })();

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
    setDeactivateEmailConfirmed(!ENABLE_GOOGLE_CONFIRM);
    setDeactivateAgreementChecked(false);
    setDeactivateShowFinalConfirm(false);
    setDeactivateEmailError("");
    setDeactivateAgreementError("");
  };

  const triggerGoogleConfirm = useGoogleLogin({
    flow: "auth-code",
    scope: "openid email profile",
    onSuccess: async (codeResponse) => {
      setGoogleConfirmBusy(true);
      setDeactivateEmailError("");

      try {
        const res = await fetch(GOOGLE_CALLBACK_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ code: codeResponse.code }),
        });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || `HTTP error! status: ${res.status}`);
        }

        const data = await res.json();
        const { access_token, refresh_token, profile_picture, name, email: nextEmail } = data || {};

        if (typeof window !== "undefined") {
          if (access_token) localStorage.setItem("access_token", access_token);
          if (refresh_token) localStorage.setItem("refresh_token", refresh_token);
          if (profile_picture) localStorage.setItem("profile_picture", profile_picture);
          if (name) localStorage.setItem("user_name", name);
          if (nextEmail) localStorage.setItem("user_email", nextEmail);
        }

        if (typeof nextEmail === "string" && nextEmail.trim()) {
          setEmail(nextEmail);
        }

        setDeactivateEmailConfirmed(true);
        setDeactivateEmailError("");
      } catch (e) {
        console.error("Google confirm failed:", e);
        setDeactivateEmailConfirmed(false);
        setDeactivateEmailError("Google confirmation failed");
      } finally {
        setGoogleConfirmBusy(false);
      }
    },
    onError: () => {
      setDeactivateEmailConfirmed(false);
      setDeactivateEmailError("Google confirmation canceled");
    },
  });

  const confirmWithGoogle = () => {
    if (googleConfirmBusy) return;
    setDeactivateEmailError("");
    triggerGoogleConfirm();
  };

  const requestDeactivate = () => {
    let ok = true;

    if (ENABLE_GOOGLE_CONFIRM) {
      if (!deactivateEmailConfirmed) {
        setDeactivateEmailError(t("errConfirmEmail"));
        ok = false;
      } else {
        setDeactivateEmailError("");
      }
    } else {
      setDeactivateEmailError("");
    }

    if (!deactivateAgreementChecked) {
      setDeactivateAgreementError(t("errConfirmAgreement"));
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
  };

  const onChangePreference = (index: 0 | 1 | 2, value: string) => {
    setTravelPreferences((prev) => {
      const next: [string, string, string] = [prev[0], prev[1], prev[2]];
      next[index] = value;
      return next;
    });
  };

  return (
    <div
      className="flex w-full h-screen bg-gray-100 p-4 gap-4 overflow-hidden"
      style={themeMode === "dark" ? { filter: "invert(1) hue-rotate(180deg)" } : undefined}
    >
      <div className="flex-none h-full">
        <Sidebar />
      </div>

      <motion.main
        className="flex-1 h-full min-w-0 bg-white rounded-lg border border-gray-200 shadow-sm overflow-y-auto"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={language}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
          >
            <motion.header
              className="p-6 border-b border-gray-100 flex items-end justify-between"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, ease: "easeOut", delay: 0.05 }}
            >
              <div>
                <h1 className="text-2xl font-serif italic font-medium text-gray-900 mb-1">{t("title")}</h1>
                <p className="text-xs text-gray-500 font-medium tracking-wide uppercase">Profile</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  aria-label={themeMode === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                  aria-pressed={themeMode === "dark"}
                  onClick={toggleThemeMode}
                  className="w-10 h-10 rounded-lg border border-gray-200 bg-white text-gray-900 flex items-center justify-center hover:bg-gray-50 transition-colors"
                >
                  {themeMode === "dark" ? <Sun size={14} /> : <Moon size={14} />}
                </button>

                <button
                  type="button"
                  onClick={() => router.push("/mypage")}
                  className="bg-black text-white px-4 py-2.5 rounded-lg text-[10px] font-bold hover:opacity-90 transition-all uppercase tracking-wide"
                >
                  {t("back")}
                </button>
              </div>
            </motion.header>

            <div className="p-6 space-y-8">
              {/* Profile Settings */}
              <motion.section
                className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, ease: "easeOut", delay: 0.1 }}
              >
            <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-6">
              <div className="rounded-xl bg-gray-200 border border-gray-200 h-[220px] flex items-center justify-center text-gray-600 font-semibold">
                {profilePictureUrl ? (
                  <img
                    src={profilePictureUrl}
                    alt="Profile"
                    className="w-full h-full object-cover rounded-xl grayscale-[20%]"
                    style={themeMode === "dark" ? { filter: "invert(1) hue-rotate(180deg)" } : undefined}
                  />
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

                <div>
                  <div className="text-xs font-bold text-gray-900 mb-2">{t("miniBio")}</div>
                  <input
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    className="w-full h-10 px-3 rounded-lg bg-gray-100 border border-gray-200 text-sm font-medium text-gray-900"
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
          </motion.section>

          {/* Travel Notes */}
          <motion.section
            className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: "easeOut", delay: 0.15 }}
          >
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
          </motion.section>

          {/* Travel Preference */}
          <motion.section
            className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: "easeOut", delay: 0.2 }}
          >
            <h2 className="text-xl font-serif italic font-medium text-gray-900 mb-4">{t("travelPreference")}</h2>
            <div className="space-y-4 max-w-2xl">
              <div className="flex items-center justify-between gap-4">
                <div className="text-sm font-semibold text-gray-900">• {t("pref1")}</div>
                <select
                  value={travelPreferences[0]}
                  onChange={(e) => onChangePreference(0, e.target.value)}
                  className="w-[180px] h-10 px-3 rounded-lg bg-gray-100 border border-gray-200 text-sm font-semibold text-gray-900"
                >
                  {TRAVEL_STYLE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt} disabled={isTravelStyleOptionDisabled(0, opt)}>
                      {formatTravelStyleOptionLabel(opt)}
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
                    <option key={opt} value={opt} disabled={isTravelStyleOptionDisabled(1, opt)}>
                      {formatTravelStyleOptionLabel(opt)}
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
                    <option key={opt} value={opt} disabled={isTravelStyleOptionDisabled(2, opt)}>
                      {formatTravelStyleOptionLabel(opt)}
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
              </motion.section>
            </div>
          </motion.div>
        </AnimatePresence>
      </motion.main>

      <AnimatePresence>
        {deactivateOpen && (
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
              className="absolute inset-0 bg-black/30"
              onClick={() => setDeactivateOpen(false)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            />

            <motion.div
              className="relative z-10 w-full max-w-[520px] rounded-xl border border-gray-200 bg-white"
              initial={{ opacity: 0, y: 10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.98 }}
              transition={{ type: "spring", stiffness: 380, damping: 30 }}
            >
              <div className="p-6">
                <h2 className="text-3xl font-semibold text-gray-900 mb-4">{t("deactivateTitle")}</h2>
                <p className="text-sm text-gray-700 leading-relaxed mb-6">{t("deactivateNote")}</p>

                <div className="mb-6">
                  <button
                    type="button"
                    disabled={!ENABLE_GOOGLE_CONFIRM || googleConfirmBusy}
                    onClick={ENABLE_GOOGLE_CONFIRM ? confirmWithGoogle : undefined}
                    className={
                      ENABLE_GOOGLE_CONFIRM && !googleConfirmBusy
                        ? "bg-black text-white px-6 py-3 rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
                        : "bg-gray-200 text-gray-500 px-6 py-3 rounded-lg text-sm font-semibold cursor-not-allowed"
                    }
                  >
                    {t("deactivateConfirmGoogle")}
                  </button>

                  {!ENABLE_GOOGLE_CONFIRM && (
                    <div className="mt-2 text-xs text-gray-500 font-medium">{t("deactivateGoogleSoon")}</div>
                  )}

                  {ENABLE_GOOGLE_CONFIRM && deactivateEmailConfirmed && (
                    <div className="mt-2 text-xs text-gray-600 font-medium">{email}</div>
                  )}
                  {ENABLE_GOOGLE_CONFIRM && deactivateEmailError && (
                    <div className="mt-2 text-xs text-red-500 font-semibold">{deactivateEmailError}</div>
                  )}
                </div>

                <div className="flex items-center justify-between gap-4 mb-6">
                  <div className="text-sm text-gray-800 font-medium leading-snug">{t("deactivateAgreement")}</div>
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
                    {t("deactivatePrimary")}
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeactivateOpen(false)}
                    className="flex-1 bg-black text-white px-6 py-3 rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
                  >
                    {t("deactivateCancel")}
                  </button>
                </div>
              </div>
            </motion.div>

            <AnimatePresence>
              {deactivateShowFinalConfirm && (
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
                    onClick={() => setDeactivateShowFinalConfirm(false)}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                  />

                  <motion.div
                    className="relative z-10 w-full max-w-[420px] rounded-xl border border-gray-200 bg-white p-6"
                    initial={{ opacity: 0, y: 10, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.98 }}
                    transition={{ type: "spring", stiffness: 420, damping: 32 }}
                  >
                    <div className="text-lg font-semibold text-gray-900 mb-5">{t("deactivateFinalConfirm")}</div>
                    <div className="flex items-center justify-end gap-3">
                      <button
                        type="button"
                        onClick={() => setDeactivateShowFinalConfirm(false)}
                        className="bg-gray-200 text-gray-900 px-6 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-300 transition-colors"
                      >
                        {t("no")}
                      </button>
                      <button
                        type="button"
                        onClick={deactivateAccount}
                        className="bg-black text-white px-6 py-2.5 rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
                      >
                        {t("yes")}
                      </button>
                    </div>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
