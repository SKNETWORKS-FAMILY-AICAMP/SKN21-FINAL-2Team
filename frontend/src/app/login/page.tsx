"use client";

import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useGoogleLogin } from "@react-oauth/google";

export default function LoginPage() {
  const router = useRouter();

  const handleLogin = useGoogleLogin({
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
        const { access_token, refresh_token, is_join, profile_picture, name, email } = data;

        // 토큰 및 프로필 정보 저장
        localStorage.setItem("access_token", access_token);
        if (refresh_token) localStorage.setItem("refresh_token", refresh_token);
        if (profile_picture) localStorage.setItem("profile_picture", profile_picture);
        if (name) localStorage.setItem("user_name", name);
        if (email) localStorage.setItem("user_email", email);

        // is_join 기반 라우팅
        if (is_join) {
          router.push("/chatbot");          // 기존 사용자 → 채팅
        } else {
          router.push("/signup/profile");   // 신규 사용자 → 추가정보 입력
        }

      } catch (error) {
        console.error("Login Failed:", error);
        alert("Login failed. Please try again.");
      }
    },
    onError: () => {
      console.log("Login Failed");
      alert("Google Login Failed");
    },
    flow: "auth-code",
  });

  const handleBack = () => {
    router.push("/");
  };

  const handleSignUpClick = () => {
    router.push("/signup");
  };

  return (
    <div className="min-h-screen w-full flex bg-white">
      {/* Left Side - Image & Brand */}
      <div className="hidden lg:flex w-[45%] bg-black relative overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img
            src="https://images.unsplash.com/photo-1735491428084-853fb91c09e7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxTZW91bCUyMGNhZmUlMjBhZXN0aGV0aWMlMjBtaW5pbWFsaXN0fGVufDF8fHx8MTc3MTQ4MTgyNnww&ixlib=rb-4.1.0&q=80&w=1080"
            alt="Seoul Cafe Mood"
            className="w-full h-full object-cover opacity-80"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-black/30" />
        </div>

        <div className="relative z-10 p-12 flex flex-col justify-between h-full text-white w-full">
          <div
            className="flex items-center gap-3 cursor-pointer w-fit group"
            onClick={handleBack}
          >
            <div className="w-8 h-8 bg-white text-black flex items-center justify-center">
              <span className="font-serif font-bold text-xl leading-none italic">T</span>
            </div>
            <span className="font-serif font-bold text-xl tracking-tighter opacity-90 group-hover:opacity-100 transition-opacity">Triver.</span>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.8 }}
            className="max-w-sm"
          >
            <h2 className="text-3xl font-serif italic font-light leading-snug mb-4 text-white/90">
              &quot;The journey of a thousand miles begins with a single step.&quot;
            </h2>
            <div className="h-[1px] w-12 bg-white/30 my-6"></div>
            <p className="text-white/50 text-sm font-light leading-relaxed">
              Join a community of travelers planning their next adventure with AI-powered insights.
            </p>
          </motion.div>

          <div className="text-[10px] text-white/30 font-medium tracking-widest uppercase">
            © 2026 Triver Inc.
          </div>
        </div>
      </div>

      {/* Right Side - Login Content */}
      <div className="flex-1 flex flex-col items-center justify-center p-8 relative bg-white">
        <button
          onClick={handleBack}
          className="absolute top-8 left-8 lg:hidden flex items-center gap-2 text-[13px] font-medium text-gray-400 hover:text-black transition-colors"
        >
          <ArrowLeft size={16} /> Back
        </button>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-[320px] text-center"
        >
          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight text-gray-900 mb-2">
              Welcome back
            </h1>
            <p className="text-[13px] text-gray-500 font-light">
              Log in to continue your journey
            </p>
          </div>

          <div className="space-y-4">
            <Button
              onClick={() => handleLogin()}
              variant="outline"
              className="w-full h-12 border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900"
            >
              <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
              Continue with Google
            </Button>
          </div>
          <div className="mt-8 pt-8 border-t border-gray-100">
            <p className="text-[10px] text-gray-400 leading-relaxed">
              By clicking continue, you agree to our{" "}
              <a href="#" className="underline hover:text-black decoration-gray-300">Terms of Service</a>{" "}
              and{" "}
              <a href="#" className="underline hover:text-black decoration-gray-300">Privacy Policy</a>.
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
