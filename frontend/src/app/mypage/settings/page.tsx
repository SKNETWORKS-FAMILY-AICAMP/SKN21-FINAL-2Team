"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Sidebar } from "@/components/Sidebar";
import {
  fetchCountries,
  fetchCurrentUser,
  updateCurrentUser,
  type Country,
} from "@/services/api";

const TRAVEL_STYLE_OPTIONS = ["Relaxation", "Adventure", "Culture", "Food", "Nature", "Luxury"];
const SETTINGS_STORAGE_KEY = "triver:profile-settings:v1";

const FALLBACK_COUNTRIES: Country[] = [
  { code: "KR", name: "Korea" },
  { code: "JP", name: "Japan" },
  { code: "US", name: "United States" },
];

export default function SettingsPage() {
  const router = useRouter();

  const [nickname, setNickname] = useState("");
  const [countryCode, setCountryCode] = useState("KR");
  const [countries, setCountries] = useState<Country[]>([]);
  const [travelPreferences, setTravelPreferences] = useState<[string, string, string]>([
    "Relaxation",
    "Food",
    "Culture",
  ]);
  const [saveNotice, setSaveNotice] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // 유저 정보 불러오기
  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchCurrentUser();
        if (data?.nickname) setNickname(data.nickname);
        if (data?.country_code) setCountryCode(data.country_code.toUpperCase());

        const prefs = [data?.extra_prefer1, data?.extra_prefer2, data?.extra_prefer3].filter(
          (x): x is string => typeof x === "string" && x.trim().length > 0,
        );
        if (prefs.length === 3) setTravelPreferences([prefs[0], prefs[1], prefs[2]]);
      } catch {
        // ignore
      }
    };
    load();
  }, []);

  // 국가 목록 불러오기
  useEffect(() => {
    const load = async () => {
      try {
        const list = await fetchCountries();
        if (Array.isArray(list) && list.length) {
          setCountries(list.map((c) => ({ ...c, code: c.code.toUpperCase() })));
        } else {
          setCountries(FALLBACK_COUNTRIES);
        }
      } catch {
        setCountries(FALLBACK_COUNTRIES);
      }
    };
    load();
  }, []);

  const onChangePreference = (index: 0 | 1 | 2, value: string) => {
    setTravelPreferences((prev) => {
      const next: [string, string, string] = [prev[0], prev[1], prev[2]];
      next[index] = value;
      return next;
    });
  };

  const isOptionDisabled = (slotIndex: number, opt: string) =>
    travelPreferences.some((v, i) => i !== slotIndex && v === opt);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // DB 저장
      await updateCurrentUser({
        nickname,
        country_code: countryCode,
        extra_prefer1: travelPreferences[0],
        extra_prefer2: travelPreferences[1],
        extra_prefer3: travelPreferences[2],
      });
      // localStorage 동기화
      const stored = (() => {
        try {
          return JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) ?? "{}") as Record<string, unknown>;
        } catch {
          return {};
        }
      })();
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify({
          ...stored,
          nickname,
          countryCode,
          travelPreferences,
        }),
      );
      window.dispatchEvent(new Event("triver:profile-settings"));
      setSaveNotice("저장되었습니다.");
      setTimeout(() => setSaveNotice(""), 2500);
    } catch {
      setSaveNotice("저장 중 오류가 발생했습니다.");
      setTimeout(() => setSaveNotice(""), 2500);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex w-full h-screen bg-gray-100 p-4 gap-4 overflow-hidden">
      <div className="flex-none h-full">
        <Sidebar />
      </div>

      <motion.main
        className="flex-1 h-full min-w-0 bg-white rounded-lg border border-gray-200 shadow-sm overflow-y-auto"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
      >
        {/* 헤더 */}
        <header className="p-6 border-b border-gray-100 flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-serif italic font-medium text-gray-900 mb-1">
              Profile Settings
            </h1>
            <p className="text-xs text-gray-500 font-medium tracking-wide uppercase">Profile</p>
          </div>
          <button
            type="button"
            onClick={() => router.push("/mypage")}
            className="bg-black text-white px-4 py-2.5 rounded-lg text-[10px] font-bold hover:opacity-90 transition-all uppercase tracking-wide"
          >
            Back to MyPage
          </button>
        </header>

        <div className="p-6 space-y-6 max-w-2xl">
          {/* 닉네임 */}
          <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-gray-900">기본 정보</h2>

            <div>
              <label className="text-xs font-bold text-gray-700 mb-2 block">닉네임</label>
              <input
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                className="w-full sm:max-w-[320px] h-10 px-3 rounded-lg bg-gray-100 border border-gray-200 text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-black/20"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-gray-700 mb-2 block">국가</label>
              <select
                value={countryCode}
                onChange={(e) => setCountryCode(e.target.value)}
                className="w-full sm:max-w-[320px] h-10 px-3 rounded-lg bg-gray-100 border border-gray-200 text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-black/20"
              >
                {(countries.length ? countries : FALLBACK_COUNTRIES).map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </section>

          {/* 여행 선호도 */}
          <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
            <div>
              <h2 className="text-base font-bold text-gray-900">여행 스타일 선호도</h2>
              <p className="text-xs text-gray-400 mt-1">처음 설문에서 선택한 여행 스타일을 변경할 수 있습니다.</p>
            </div>

            {([0, 1, 2] as const).map((i) => (
              <div key={i} className="flex items-center justify-between gap-4">
                <span className="text-sm font-semibold text-gray-900">선호도 {i + 1}</span>
                <select
                  value={travelPreferences[i]}
                  onChange={(e) => onChangePreference(i, e.target.value)}
                  className="w-[180px] h-10 px-3 rounded-lg bg-gray-100 border border-gray-200 text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-black/20"
                >
                  {TRAVEL_STYLE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt} disabled={isOptionDisabled(i, opt)}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </section>

          {/* 저장 */}
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="bg-black text-white px-6 py-2.5 rounded-lg text-sm font-bold hover:opacity-90 transition-all disabled:opacity-50"
            >
              {isSaving ? "저장 중..." : "저장"}
            </button>
            {saveNotice && (
              <motion.span
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                className="text-sm text-green-600 font-medium"
              >
                {saveNotice}
              </motion.span>
            )}
          </div>
        </div>
      </motion.main>
    </div>
  );
}
