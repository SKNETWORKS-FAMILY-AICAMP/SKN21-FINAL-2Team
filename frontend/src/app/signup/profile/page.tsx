"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchCurrentUser, getPostLoginPath, updateCurrentUser } from "@/services/api";
import { useEffect } from "react";
import { Sparkles } from "lucide-react";

const genders = [
  { value: "female", label: "여성" },
  { value: "male", label: "남성" },
  { value: "other", label: "기타" },
];

export default function SignUpProfilePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [nickname, setNickname] = useState("");
  const [birthday, setBirthday] = useState("");
  const [gender, setGender] = useState<string>("female");
  const [agree, setAgree] = useState(false);
  const [loading, setLoading] = useState(false);
  const [profileLoading, setProfileLoading] = useState(true);
  const trimmedNickname = nickname.trim();
  const canProceed =
    trimmedNickname.length >= 2 &&
    !!birthday &&
    !!gender &&
    agree &&
    !loading &&
    !profileLoading;

  useEffect(() => {
    const guardByUserStatus = async () => {
      if (typeof window === "undefined") return;
      const token = localStorage.getItem("access_token");
      if (!token) {
        setProfileLoading(false);
        return;
      }
      try {
        const user = await fetchCurrentUser();
        setName(user.name ?? "");
        setEmail(user.email ?? "");
        setNickname(user.nickname ?? "");
        setBirthday(user.birthday ? user.birthday.slice(0, 10) : "");
        if (user.gender) {
          setGender(user.gender);
        }
        if (!user.is_join) return;
        router.replace(getPostLoginPath(user));
      } catch {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      } finally {
        setProfileLoading(false);
      }
    };
    guardByUserStatus();
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    if (!trimmedNickname) {
      alert("닉네임을 입력해주세요.");
      return;
    }
    if (trimmedNickname.length < 2) {
      alert("닉네임은 2자 이상 입력해주세요.");
      return;
    }
    if (!birthday) {
      alert("생년월일을 입력해주세요.");
      return;
    }
    setLoading(true);
    try {
      const payload: {
        name?: string;
        nickname: string;
        birthday: string;
        gender: string;
        is_join: boolean;
      } = {
        nickname: trimmedNickname,
        birthday: `${birthday}T00:00:00`,
        gender,
        is_join: true,
      };
      if (name.trim()) {
        payload.name = name.trim();
      }
      await updateCurrentUser(payload);
      router.push("/survey");
    } catch (error) {
      alert("회원정보 저장에 실패했습니다.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
        <div className="mb-8 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-lg font-semibold text-slate-800 hover:text-indigo-600">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            Polaris
          </Link>
          <Link href="/login" className="text-sm text-indigo-600 hover:underline">
            이미 계정이 있으신가요?
          </Link>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-10 shadow-xl shadow-slate-100">
          <div className="mb-6 space-y-2">
            <p className="text-sm font-medium text-indigo-600">2단계 · 기본 정보</p>
            <h1 className="text-3xl font-bold text-slate-900">회원정보 입력</h1>
            <p className="text-sm text-slate-600">구글 계정 이름/이메일을 확인하고 닉네임, 생년월일, 성별을 입력해 주세요.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-800">이름</label>
              <input
                type="text"
                value={name}
                readOnly
                placeholder={profileLoading ? "불러오는 중..." : "구글 이름 정보 없음"}
                className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-700 shadow-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-800">이메일</label>
              <input
                type="email"
                value={email}
                readOnly
                placeholder={profileLoading ? "불러오는 중..." : "구글 이메일 정보 없음"}
                className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-700 shadow-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-800">닉네임</label>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                maxLength={50}
                required
                placeholder="닉네임을 입력하세요"
                className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-800 shadow-sm focus:border-indigo-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-800">생년월일</label>
              <input
                type="date"
                value={birthday}
                onChange={(e) => setBirthday(e.target.value)}
                required
                className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-800 shadow-sm focus:border-indigo-400 focus:outline-none"
              />
            </div>

            <div>
              <p className="block text-sm font-semibold text-slate-800">성별</p>
              <div className="mt-3 grid grid-cols-3 gap-3">
                {genders.map((g) => (
                  <button
                    key={g.value}
                    type="button"
                    onClick={() => setGender(g.value)}
                    className={`rounded-2xl border px-4 py-3 text-sm font-medium transition-all ${gender === g.value ? "border-indigo-400 bg-indigo-50 text-indigo-700 shadow" : "border-slate-200 bg-white text-slate-600 hover:border-indigo-200"}`}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>

            <label className="flex items-start gap-3 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={agree}
                onChange={(e) => setAgree(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              서비스 이용약관 및 개인정보 처리방침에 동의합니다.
            </label>

            <button
              type="submit"
              disabled={!canProceed}
              className="w-full rounded-2xl bg-indigo-600 px-4 py-3 text-white font-semibold shadow-lg shadow-indigo-200 transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {loading ? "저장 중..." : "다음: 선호도 조사"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
