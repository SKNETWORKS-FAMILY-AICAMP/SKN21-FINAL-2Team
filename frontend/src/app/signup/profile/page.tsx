"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { updateCurrentUser } from "@/services/api";
import { useEffect } from "react";

const genders = [
  { value: "female", label: "여성" },
  { value: "male", label: "남성" },
  { value: "other", label: "기타" },
];

export default function SignUpProfilePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [gender, setGender] = useState<string>("female");
  const [agree, setAgree] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("access_token");
    if (token) {
      router.replace("/chatbot");
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    try {
      await updateCurrentUser({
        name,
        gender,
        is_join: true,
      });
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
          <Link href="/" className="text-lg font-semibold text-slate-800">
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
            <p className="text-sm text-slate-600">이름과 성별을 알려주세요. 이후 선호도 조사를 진행합니다.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-800">이름</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                placeholder="홍길동"
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
              disabled={!name || !agree || loading}
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
