"use client";

import GoogleLoginBtn from "@/components/GoogleLoginBtn";
import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { fetchCurrentUser, getPostLoginPath } from "@/services/api";

export default function SignUpEntryPage() {
  const router = useRouter();

  useEffect(() => {
    const routeIfLoggedIn = async () => {
      if (typeof window === "undefined") return;
      const token = localStorage.getItem("access_token");
      if (!token) return;
      try {
        const user = await fetchCurrentUser();
        router.replace(getPostLoginPath(user));
      } catch {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      }
    };
    routeIfLoggedIn();
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
        <div className="mb-10 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-lg font-semibold text-slate-800 hover:text-indigo-600">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            Polaris
          </Link>
          <Link href="/login" className="text-sm text-indigo-600 hover:underline">
            이미 계정이 있으신가요?
          </Link>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-10 shadow-xl shadow-indigo-50">
          <p className="text-sm font-medium text-indigo-600">1단계 · 구글 로그인</p>
          <h1 className="mt-2 text-3xl font-bold text-slate-900">회원가입 시작</h1>
          <p className="mt-2 text-sm text-slate-600">
            구글로 로그인하면 자동으로 계정이 생성됩니다. 이후 기본 정보와 선호도를 입력해 주세요.
          </p>

          <div className="mt-8 space-y-4">
            <GoogleLoginBtn label="Google로 시작하기" />
            <p className="text-center text-xs text-slate-500">
              로그인 완료 후 아직 회원정보가 없다면 회원정보 입력 화면으로 이동합니다.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
