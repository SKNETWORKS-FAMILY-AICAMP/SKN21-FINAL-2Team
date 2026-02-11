"use client";

import { useState } from "react";
import Link from "next/link";

export default function MyPage() {
  const [name, setName] = useState("홍길동");
  const [gender, setGender] = useState("female");
  const [preferencesUpdated, setPreferencesUpdated] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setPreferencesUpdated(true);
    setTimeout(() => setPreferencesUpdated(false), 2000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-100">
      <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-12">
        <header className="mb-10 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-indigo-600">마이페이지</p>
            <h1 className="text-3xl font-bold text-slate-900">내 정보 관리</h1>
          </div>
          <Link href="/chatbot" className="text-sm text-indigo-600 hover:underline">챗봇으로 돌아가기</Link>
        </header>

        <div className="grid gap-8 md:grid-cols-[1.1fr_0.9fr]">
          <form onSubmit={handleSave} className="rounded-3xl border border-slate-200 bg-white p-8 shadow-lg shadow-indigo-50 space-y-6">
            <div>
              <label className="text-sm font-semibold text-slate-800">이름</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-800 focus:border-indigo-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-sm font-semibold text-slate-800">성별</label>
              <div className="mt-3 flex gap-3">
                {[
                  { value: "female", label: "여성" },
                  { value: "male", label: "남성" },
                  { value: "other", label: "기타" },
                ].map((g) => (
                  <button
                    key={g.value}
                    type="button"
                    onClick={() => setGender(g.value)}
                    className={`rounded-full border px-4 py-2 text-sm font-medium transition ${gender === g.value ? "border-indigo-400 bg-indigo-50 text-indigo-700" : "border-slate-200 text-slate-600 hover:border-indigo-200"}`}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>
            <button
              type="submit"
              className="w-full rounded-2xl bg-indigo-600 px-4 py-3 text-white font-semibold shadow-lg shadow-indigo-200 hover:bg-indigo-700"
            >
              정보 저장
            </button>
            {preferencesUpdated && <p className="text-sm text-emerald-600">저장되었습니다.</p>}
          </form>

          <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-lg shadow-indigo-50 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-800">선호도 조사</p>
                <p className="text-xs text-slate-500">처음 로그인 시 진행한 월드컵 결과</p>
              </div>
              <Link href="/survey" className="text-sm font-semibold text-indigo-600 hover:underline">다시 하기</Link>
            </div>
            <ul className="grid gap-3 sm:grid-cols-2">
              {[
                "배우: 송강",
                "영화: 라라랜드",
                "드라마: 더 글로리",
                "셀럽: 아이유",
                "예능: 나혼산",
                "여행: 자연/트레킹",
                "반려견: 동반 필수",
                "비건: 상관없음",
              ].map((item) => (
                <li key={item} className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

