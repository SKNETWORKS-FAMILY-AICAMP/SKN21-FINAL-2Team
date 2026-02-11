"use client";

import GoogleLoginBtn from "@/components/GoogleLoginBtn";
import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("access_token");
    if (token) {
      router.replace("/chatbot");
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
        <div className="mb-10 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-lg font-semibold text-slate-800 hover:text-indigo-600">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            Polaris
          </Link>
          <Link href="/signup" className="text-sm text-indigo-600 hover:underline">계정이 없으신가요?</Link>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-10 shadow-xl shadow-indigo-50">
          <h1 className="text-3xl font-bold text-slate-900">로그인</h1>
          <p className="mt-2 text-sm text-slate-600">Google 계정으로 빠르게 시작하세요.</p>

          <div className="mt-8 space-y-4">
            <GoogleLoginBtn />
            <p className="text-center text-xs text-slate-500">로그인 시 선호도 저장을 위해 동의가 필요합니다.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
