'use client';

import Link from "next/link";
import { ArrowRight, Sparkles, Star, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { logoutApi } from "@/services/api";

export default function Home() {
  const router = useRouter();
  const [hasToken, setHasToken] = useState(() =>
    typeof window !== "undefined" ? !!localStorage.getItem("access_token") : false
  );

  const handleLogout = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("chat_room_id");
    }
    logoutApi();
    setHasToken(false);
    router.push("/");
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-100 text-slate-900">
      {/* Top nav */}
      <header className="sticky top-0 z-20 backdrop-blur border-b border-slate-200 bg-white/85">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2 font-semibold text-lg">
            <Sparkles className="h-6 w-6 text-indigo-600" />
            <span>Polaris</span>
          </div>
          <div className="flex items-center gap-3 text-sm font-medium">
            {hasToken ? (
              <>
                <Link
                  href="/mypage"
                  className="rounded-full px-4 py-2 text-slate-700 hover:text-indigo-600 transition-colors"
                >
                  마이페이지
                </Link>
                <button
                  onClick={handleLogout}
                  className="rounded-full bg-indigo-600 px-4 py-2 text-white shadow-sm hover:bg-indigo-700 transition-colors"
                >
                  로그아웃
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="rounded-full px-4 py-2 text-slate-700 hover:text-indigo-600 transition-colors"
                >
                  로그인
                </Link>
                <Link
                  href="/signup"
                  className="rounded-full bg-indigo-600 px-4 py-2 text-white shadow-sm hover:bg-indigo-700 transition-colors"
                >
                  회원가입
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <main className="mx-auto flex max-w-6xl flex-col gap-16 px-6 pb-24 pt-14">
        <section className="grid items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700">
              <Star className="h-4 w-4" /> AI 취향 맞춤형 챗 경험
            </div>
            <div className="space-y-4">
              <h1 className="text-4xl font-bold leading-tight md:text-5xl">
                당신의 취향을 배우는 <span className="text-indigo-600">개인화 챗봇</span>
              </h1>
              <p className="text-lg text-slate-600">
                영화, 배우, 여행 스타일까지 한 번에 알려주면 챗봇이 더 나은 답변을 준비합니다.
                첫 로그인 후 선호도 월드컵으로 나만의 프로필을 완성하세요.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                href={hasToken ? "/chatbot" : "/signup"}
                className="inline-flex items-center gap-2 rounded-full bg-indigo-600 px-5 py-3 text-white shadow-lg shadow-indigo-200 hover:bg-indigo-700 transition-transform hover:-translate-y-0.5"
              >
                {hasToken ? "챗봇 바로가기" : "지금 시작하기"} <ArrowRight className="h-4 w-4" />
              </Link>
              {!hasToken && (
                <Link
                  href="/chatbot_demo"
                  className="inline-flex items-center gap-2 rounded-full border border-slate-300 px-5 py-3 text-slate-800 hover:border-indigo-300 hover:text-indigo-700"
                >
                  데모 챗봇 보기
                </Link>
              )}
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              {["취향 기반 답변", "구글 로그인", "선호도 재설정"].map((item) => (
                <div key={item} className="rounded-2xl border border-slate-200 bg-white/60 p-4 shadow-sm">
                  <p className="text-sm font-semibold text-slate-700">{item}</p>
                  <p className="mt-1 text-xs text-slate-500">간편하게 설정하고 계속 업데이트하세요.</p>
                </div>
              ))}
            </div>
          </div>
          <div className="relative">
            <div className="absolute -inset-6 rounded-3xl bg-gradient-to-br from-indigo-200/60 via-white to-sky-200/60 blur-2xl" />
            <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full bg-emerald-500" />
                  <p className="text-sm font-semibold text-slate-800">오늘의 추천 스팟</p>
                </div>
                <ShieldCheck className="h-4 w-4 text-slate-400" />
              </div>
              <div className="space-y-4 px-5 py-6">
                <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                  ✨ 여행 선호도가 &quot;자연 &amp; 반려견 동행&quot;으로 설정되어 있어요.
                  주말엔 근교 애견 동반 트레킹 코스 어때요?
                </div>
                <div className="rounded-2xl border border-slate-200 p-4 text-sm text-slate-800">
                  <p className="font-semibold">추천 일정</p>
                  <ul className="mt-2 space-y-1 text-slate-600">
                    <li>· 남한산성 반려견 동반 산책</li>
                    <li>· 근처 비건 카페 브런치</li>
                    <li>· 전망 좋은 포토 스폿</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Feature grid */}
        <section className="grid gap-6 md:grid-cols-3">
          {[
            {
              title: "구글 로그인",
              desc: "한 번 클릭으로 안전하게 시작하고, 접근 토큰을 로컬에 저장합니다.",
            },
            {
              title: "선호도 월드컵",
              desc: "배우·영화·여행 스타일 등 8개 카테고리로 취향을 빠르게 수집합니다.",
            },
            {
              title: "마이페이지 관리",
              desc: "회원 정보와 선호도를 언제든 다시 수정하고 챗봇에 반영하세요.",
            },
          ].map(({ title, desc }) => (
            <div key={title} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-base font-semibold text-slate-800">{title}</p>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">{desc}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}
