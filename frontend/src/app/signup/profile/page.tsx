"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Check, ArrowRight, User, Globe, MessageSquare } from "lucide-react";
import { useRouter } from "next/navigation";

export default function ProfilePage() {
  const router = useRouter();
  const [agreed, setAgreed] = useState(false);
  const [nickname, setNickname] = useState("");
  const [gender, setGender] = useState("");

  // 사용자 정보 State
  const [userInfo, setUserInfo] = useState({
    name: "",
    email: "",
    picture: "",
  });
  const [countries, setCountries] = useState<{ code: string, name: string }[]>([]);
  const [countryCode, setCountryCode] = useState("");

  useEffect(() => {
    // localStorage에서 정보 로드
    const name = localStorage.getItem("user_name") || "";
    const email = localStorage.getItem("user_email") || "";
    const picture = localStorage.getItem("profile_picture") || "";

    setUserInfo({ name, email, picture });

    import("@/services/api").then(({ fetchCountries }) => {
      fetchCountries().then(setCountries).catch(console.error);
    });
  }, []);

  const isFormValid = nickname && gender && agreed && countryCode;

  const handleComplete = async () => {
    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        alert("로그인이 필요합니다.");
        router.push("/login");
        return;
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
      const res = await fetch(`${apiUrl}/api/users/me`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          nickname,
          gender: gender.toLowerCase(), // "Male" -> "male"
          country_code: countryCode,
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to update profile");
      }

      // 성공 시 설문 조사 페이지로 이동
      router.push("/survey");

    } catch (error) {
      console.error("Profile Update Failed:", error);
      alert("프로필 저장에 실패했습니다.");
    }
  };

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
          <h1 className="text-3xl font-serif italic font-light text-gray-900 mb-2">
            One last step, {userInfo.name.split(" ")[0]}
          </h1>
          <p className="text-sm text-gray-500 font-light">
            Help us personalize your travel experience.
          </p>
        </div>

        <div className="bg-white rounded-3xl border border-gray-100 shadow-[0_8px_30px_-4px_rgba(0,0,0,0.04)] p-8 md:p-10 space-y-8">
          {/* Read-only Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 opacity-60 pointer-events-none grayscale">
            <div className="space-y-2">
              <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wide">Full Name</label>
              <div className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-3 text-sm text-gray-500 font-medium">
                {userInfo.name}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wide">Email Address</label>
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
                <User size={12} /> Nickname
              </label>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                placeholder="How should we call you?"
                className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3.5 text-sm text-gray-900 focus:outline-none focus:border-black focus:ring-1 focus:ring-black/10 transition-all placeholder:text-gray-300 placeholder:font-light"
              />
            </div>

            {/* Gender */}
            <div className="space-y-2">
              <label className="text-[11px] font-bold text-gray-900 uppercase tracking-wide">Gender</label>
              <div className="grid grid-cols-3 gap-3">
                {["Male", "Female", "Other"].map((option) => (
                  <button
                    key={option}
                    onClick={() => setGender(option)}
                    className={`py-3 px-4 rounded-xl text-sm font-medium transition-all border ${gender === option
                      ? "bg-black text-white border-black shadow-md"
                      : "bg-white text-gray-500 border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                      }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Country */}
              <div className="space-y-2">
                <label className="text-[11px] font-bold text-gray-900 uppercase tracking-wide flex items-center gap-2">
                  <Globe size={12} /> Country
                </label>
                <div className="relative">
                  <select
                    className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3.5 text-sm text-gray-900 focus:outline-none focus:border-black focus:ring-1 focus:ring-black/10 transition-all appearance-none cursor-pointer"
                    onChange={(e) => setCountryCode(e.target.value)} // State update
                  >
                    <option value="">Select Country</option>
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
                  <MessageSquare size={12} /> Language
                </label>
                <div className="relative">
                  <select className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3.5 text-sm text-gray-900 focus:outline-none focus:border-black focus:ring-1 focus:ring-black/10 transition-all appearance-none cursor-pointer">
                    <option value="en">English (US)</option>
                    <option value="ko">Korean</option>
                    <option value="ja">Japanese</option>
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
                I agree to the collection and use of personal information for service provision.
                <span className="block mt-1 text-gray-400">Your data is secured and will never be shared without consent.</span>
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
            Continue to Persona Setup <ArrowRight size={16} />
          </button>
        </div>

        <div className="text-center mt-8">
          <button className="text-[11px] font-bold text-gray-300 hover:text-gray-500 uppercase tracking-widest transition-colors">
            Skip setup (Demo only)
          </button>
        </div>
      </motion.div>
    </div>
  );
}
