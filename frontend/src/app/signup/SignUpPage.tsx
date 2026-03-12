"use client";

import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { useGoogleLogin } from "@react-oauth/google";
import { Logo } from "@/components/common/Logo";
import { Button } from "./components/SignUpButton";
import { useState, useEffect } from "react";
import { useTranslation } from "@/i18n/useTranslation";
import type { SupportedLanguage } from "@/i18n";

const BACKGROUND_IMAGES = [
  "https://images.unsplash.com/photo-1448523183439-d2ac62aca997?q=80&w=1170&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
  "https://images.unsplash.com/photo-1602479185195-32f5cd203559?q=80&w=764&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
  "https://images.unsplash.com/photo-1538485399081-7191377e8241?q=80&w=674&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
  "https://images.unsplash.com/photo-1546672136-49179bf19b4e?q=80&w=1170&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
];

export function SignUpPage() {
  const router = useRouter();
  const { t, setLanguage } = useTranslation();

  const [bgImage, setBgImage] = useState("");

  useEffect(() => {
    // 1. 배경 이미지 설정
    const randomIndex = Math.floor(Math.random() * BACKGROUND_IMAGES.length);
    setBgImage(BACKGROUND_IMAGES[randomIndex]);

    // 2. 세션 체크 및 자동 리다이렉트
    const checkSession = async () => {
      const { fetchCurrentUser, getPostLoginPath } = await import("@/services/api");
      const { clearAuth } = await import("@/services/errorHandler");

      const token = localStorage.getItem("access_token");
      if (!token) return; // 토큰이 없으면 가입 페이지 유지

      try {
        const user = await fetchCurrentUser();
        if (user) {
          // 서버에 저장된 언어 설정 복원
          if (user.language && ["en", "ko", "ja", "zh"].includes(user.language)) {
            setLanguage(user.language as SupportedLanguage);
          }
          const targetPath = getPostLoginPath(user);
          router.replace(targetPath);
        }
      } catch (err) {
        console.warn("Invalid session detected on signup page entry, clearing auth.");
        clearAuth();
      }
    };

    checkSession();
  }, [router, setLanguage]);

  const handleSignUp = useGoogleLogin({
    onSuccess: async (codeResponse) => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/auth/google/callback`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ code: codeResponse.code }),
        });

        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }

        const data = await res.json();
        const { access_token, refresh_token, profile_picture, name, email } = data;

        // 토큰 및 프로필 정보 저장
        localStorage.setItem("access_token", access_token);
        if (refresh_token) localStorage.setItem("refresh_token", refresh_token);
        if (profile_picture) localStorage.setItem("profile_picture", profile_picture);
        if (name) localStorage.setItem("user_name", name);
        if (email) localStorage.setItem("user_email", email);

        const { fetchCurrentUser, getPostLoginPath } = await import("@/services/api");

        let user;
        try {
          user = await fetchCurrentUser();
        } catch (fetchError) {
          console.error("Failed to fetch user after signup:", fetchError);
          const { clearAuth } = await import("@/services/errorHandler");
          clearAuth();
          return;
        }

        if (!user) {
          const { clearAuth } = await import("@/services/errorHandler");
          clearAuth();
          return;
        }

        // 서버에 저장된 언어 설정 복원
        if (user.language && ["en", "ko", "ja", "zh"].includes(user.language)) {
          setLanguage(user.language as SupportedLanguage);
        }

        const targetPath = getPostLoginPath(user);
        router.push(targetPath);

      } catch (error) {
        console.error("SignUp Failed:", error);
        const { clearAuth } = await import("@/services/errorHandler");
        clearAuth();
      }
    },
    onError: () => {
      console.log("SignUp Failed");
      alert(t("signup.signupFailed"));
    },
    flow: "auth-code",
  });

  const handleBack = () => {
    router.push("/");
  };

  return (
    <div className="min-h-screen w-full flex bg-white">
      {/* Left Side - Image & Brand */}
      <div className="hidden lg:flex w-[45%] bg-black relative overflow-hidden">
        <div className="absolute inset-0 z-0 bg-black">
          {bgImage && (
            <img
              src={bgImage}
              alt="Travel Background"
              className="w-full h-full object-cover opacity-70 transition-opacity duration-1000 ease-in-out"
            />
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-purple-900/10 to-black/30" />
        </div>

        <div className="relative z-10 p-12 flex flex-col justify-between h-full text-white w-full">
          <Logo tone="light" size={34} className="w-fit opacity-90 group-hover:opacity-100 transition-opacity" />

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.8 }}
            className="max-w-sm"
          >
            <h2 className="text-3xl font-semibold leading-snug mb-4 text-white/90">
              &quot;To travel is to live.&quot;
            </h2>
            <div className="h-[1px] w-12 bg-white/30 my-6"></div>
            <p className="text-white/50 text-sm font-normal leading-relaxed">
              Start your journey with Triver today. Curated experiences awaiting.
            </p>
          </motion.div>

          <div className="text-[10px] text-white/30 font-medium tracking-widest uppercase">
            © 2026 Triver Inc.
          </div>
        </div>
      </div>

      {/* Right Side - Sign Up Content */}
      <div className="flex-1 flex flex-col items-center justify-center p-8 relative bg-white">
        <button
          onClick={handleBack}
          className="absolute top-8 left-8 lg:hidden flex items-center gap-2 text-[13px] font-medium text-gray-400 hover:text-black transition-colors"
        >
          <ArrowLeft size={16} /> {t("common.back")}
        </button>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-[320px] text-center"
        >
          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight text-gray-900 mb-2">
              {t("signup.welcomeTitle")}
            </h1>
            <p className="text-[13px] text-gray-500 font-normal">
              {t("signup.welcomeSubtitle")}
            </p>
          </div>

          <div className="space-y-4">
            <Button
              onClick={() => handleSignUp()}
              variant="outline"
              className="w-full h-12 border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900"
            >
              <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
              {t("signup.continueGoogle")}
            </Button>
          </div>

          <div className="mt-8 pt-8 border-t border-gray-100">
            <p className="text-[10px] text-gray-400 leading-relaxed">
              {t("signup.termsPrefix")}{" "}
              <a href="#" className="underline hover:text-black decoration-gray-300">{t("signup.termsOfService")}</a>{" "}
              {t("signup.and")}{" "}
              <a href="#" className="underline hover:text-black decoration-gray-300">{t("signup.privacyPolicy")}</a>.
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
