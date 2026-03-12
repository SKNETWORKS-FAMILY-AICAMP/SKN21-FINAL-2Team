"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Check, ArrowRight, User, Globe, MessageSquare, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { fetchCountries, updateCurrentUser } from "@/services/api";
import { getNicknameValidationError, type GenderType } from "./utils/validation";
import { useTranslation } from "@/i18n/useTranslation";
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from "@/i18n";

export function SignUpProfilePage() {
  const router = useRouter();
  const { t, language, setLanguage } = useTranslation();
  const [agreed, setAgreed] = useState(false);
  const [nickname, setNickname] = useState("");
  const [nicknameError, setNicknameError] = useState(""); // 닉네임 에러 키
  const [gender, setGender] = useState("");

  // 사용자 정보 State
  const [userInfo] = useState(() => {
    if (typeof window === "undefined") {
      return { name: "", email: "", picture: "" };
    }
    return {
      name: localStorage.getItem("user_name") || "",
      email: localStorage.getItem("user_email") || "",
      picture: localStorage.getItem("profile_picture") || "",
    };
  });
  const [countries, setCountries] = useState<{ code: string, name: string }[]>([]);
  const [countryCode, setCountryCode] = useState("");

  useEffect(() => {
    fetchCountries().then(setCountries).catch(console.error);
  }, []);

  // 주의: 한글과 영문/숫자의 차지하는 너비가 다르므로 가중치(1.6배)를 주어 글자수를 계산합니다.
  const handleNicknameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setNickname(val);
    setNicknameError(getNicknameValidationError(val));
  };

  // 에러가 없을 때만 폼이 유효하도록 조건 추가
  const isFormValid = nickname && !nicknameError && gender && agreed && countryCode;

  const genderOptions: { key: GenderType; labelKey: string }[] = [
    { key: "male", labelKey: "profile.genderMale" },
    { key: "female", labelKey: "profile.genderFemale" },
    { key: "other", labelKey: "profile.genderOther" },
  ];

  const handleComplete = async () => {
    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        alert(t("signup.loginRequired"));
        router.push("/signup");
        return;
      }

      const genderValue: GenderType = gender as GenderType;
      await updateCurrentUser({
        nickname,
        gender: genderValue,
        country_code: countryCode,
        language,
      });

      // 성공 시 설문 조사 페이지로 이동
      router.push("/survey");

    } catch (error) {
      console.error("Profile Update Failed:", error);
      alert(t("signup.profileSaveFailed"));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("profile_picture");
    localStorage.removeItem("user_name");
    localStorage.removeItem("user_email");
    router.replace("/signup");
  };

  const firstName = userInfo.name.split(" ")[0];

  return (
    <div className="min-h-screen w-full bg-white flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-xl"
      >
        <div className="mb-10 text-center">
          {userInfo.picture && (
            <img src={userInfo.picture} alt="Profile" className="w-20 h-20 rounded-full mx-auto mb-4 object-cover border-2 border-white shadow-md" />
          )}
          <h1 className="text-3xl font-semibold text-gray-900 mb-2">
            {t("profile.title").replace("{name}", firstName)}
          </h1>
          <p className="text-sm text-gray-500 font-normal">
            {t("profile.subtitle")}
          </p>
        </div>

        <div className="bg-white rounded-3xl border border-gray-100 shadow-[0_8px_30px_-4px_rgba(0,0,0,0.04)] p-8 md:p-10 space-y-8">
          {/* Read-only Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 opacity-60 pointer-events-none grayscale">
            <div className="space-y-2">
              <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wide">{t("profile.fullName")}</label>
              <div className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-3 text-sm text-gray-500 font-medium">
                {userInfo.name}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wide">{t("profile.email")}</label>
              <div className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-3 text-sm text-gray-500 font-medium">
                {userInfo.email}
              </div>
            </div>
          </div>

          <div className="h-px bg-gray-100 w-full" />

          {/* Editable Section */}
          <div className="space-y-6">
            {/* Nickname */}
            <div className="space-y-2">
              <label className="text-[11px] font-bold text-gray-900 uppercase tracking-wide flex items-center gap-2">
                <User size={12} /> {t("profile.nickname")}
              </label>
              <input
                type="text"
                value={nickname}
                onChange={handleNicknameChange}
                placeholder={t("profile.nicknamePlaceholder")}
                className={`w-full bg-white border rounded-xl px-4 py-3.5 text-sm focus:outline-none transition-all placeholder:text-gray-300 placeholder:font-normal ${nicknameError
                  ? "border-red-500 text-red-900 focus:border-red-500 focus:ring-1 focus:ring-red-500/20"
                  : "border-gray-200 text-gray-900 focus:border-black focus:ring-1 focus:ring-black/10"
                  }`}
              />
              {nicknameError && (
                <p className="text-xs text-red-500 mt-1 pl-1">{t(nicknameError)}</p>
              )}
            </div>

            {/* Gender */}
            <div className="space-y-2">
              <label className="text-[11px] font-bold text-gray-900 uppercase tracking-wide">{t("profile.gender")}</label>
              <div className="grid grid-cols-3 gap-3">
                {genderOptions.map((option) => (
                  <button
                    key={option.key}
                    onClick={() => setGender(option.key)}
                    className={`py-3 px-4 rounded-xl text-sm font-medium transition-all border ${gender === option.key
                      ? "bg-black text-white border-black shadow-md"
                      : "bg-white text-gray-500 border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                      }`}
                  >
                    {t(option.labelKey)}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Country */}
              <div className="space-y-2">
                <label className="text-[11px] font-bold text-gray-900 uppercase tracking-wide flex items-center gap-2">
                  <Globe size={12} /> {t("profile.country")}
                </label>
                <div className="relative">
                  <select
                    className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3.5 text-sm text-gray-900 focus:outline-none focus:border-black focus:ring-1 focus:ring-black/10 transition-all appearance-none cursor-pointer"
                    onChange={(e) => setCountryCode(e.target.value)}
                  >
                    <option value="">{t("profile.countryPlaceholder")}</option>
                    {countries.map((c) => (
                      <option key={c.code} value={c.code}>{c.name}</option>
                    ))}
                  </select>
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none">
                    <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
              </div>

              {/* Language */}
              <div className="space-y-2">
                <label className="text-[11px] font-bold text-gray-900 uppercase tracking-wide flex items-center gap-2">
                  <MessageSquare size={12} /> {t("profile.language")}
                </label>
                <div className="relative">
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
                    className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3.5 text-sm text-gray-900 focus:outline-none focus:border-black focus:ring-1 focus:ring-black/10 transition-all appearance-none cursor-pointer"
                  >
                    {SUPPORTED_LANGUAGES.map((lang) => (
                      <option key={lang.code} value={lang.code}>{lang.label}</option>
                    ))}
                  </select>
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none">
                    <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            {/* Privacy Checkbox */}
            <div
              className="flex items-start gap-3 p-4 rounded-xl bg-gray-50 border border-transparent hover:border-gray-200 cursor-pointer transition-colors"
              onClick={() => setAgreed(!agreed)}
            >
              <div className={`mt-0.5 w-5 h-5 rounded-md border flex items-center justify-center transition-colors ${agreed ? "bg-black border-black" : "bg-white border-gray-300"}`}>
                {agreed && <Check size={12} className="text-white" />}
              </div>
              <p className="text-[11px] text-gray-500 leading-relaxed select-none">
                {t("profile.privacyConsent")}
                <span className="block mt-1 text-gray-400">{t("profile.privacyNote")}</span>
              </p>
            </div>
          </div>

          <button
            disabled={!isFormValid}
            onClick={handleComplete}
            className={`w-full py-4 rounded-xl font-bold text-sm tracking-wide flex items-center justify-center gap-2 transition-all duration-300 ${isFormValid
              ? "bg-black text-white hover:bg-gray-800 shadow-lg hover:shadow-xl translate-y-0"
              : "bg-gray-100 text-gray-400 cursor-not-allowed"
              }`}
          >
            {t("profile.continueButton")} <ArrowRight size={16} />
          </button>
        </div>

        <div className="text-center mt-8 flex flex-col items-center gap-4">
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-[12px] font-medium text-gray-400 hover:text-gray-600 transition-colors"
          >
            <LogOut size={14} />
            {t("signup.switchAccount")}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
