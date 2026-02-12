"use client";

import { useGoogleLogin } from "@react-oauth/google";
import { useRouter } from "next/navigation";
import { fetchCurrentUser, UserProfile } from "@/services/api";

type Props = {
    label?: string;
};

export default function GoogleLoginBtn({ label = "Google로 시작하기" }: Props) {
    const router = useRouter();

    const routeByStatus = (user: UserProfile) => {
        if (!user.is_join) {
            router.push("/signup/profile");
            return;
        }
        if (!user.is_prefer) {
            router.push("/survey");
            return;
        }
        router.push("/chatbot");
    };

    const login = useGoogleLogin({
        flow: "auth-code",
        scope: "https://www.googleapis.com/auth/calendar",
        onSuccess: async (codeResponse) => {
            try {
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/auth/google/callback`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    credentials: "include",
                    body: JSON.stringify({
                        code: codeResponse.code,
                    }),
                });

                if (!res.ok) {
                    throw new Error("Login failed");
                }

                const data = await res.json();
                localStorage.setItem("access_token", data.access_token);
                if (data.refresh_token) {
                    localStorage.setItem("refresh_token", data.refresh_token);
                }

                const user = await fetchCurrentUser();
                routeByStatus(user);
            } catch (error) {
                console.error("Login Error:", error['message']);
                alert("Login Failed");
            }
        },
        onError: (errorResponse) => console.log(errorResponse['message']),
    });

    return (
        <div className="flex justify-center">
            <button
                type="button"
                onClick={() => login()}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 font-medium text-slate-800 shadow-sm transition hover:border-slate-400 hover:bg-slate-50 hover:text-slate-900"
            >
                <img className="w-6 h-6" src="https://www.svgrepo.com/show/475656/google-color.svg" loading="lazy" alt="google logo" />
                <span>{label}</span>
            </button>
        </div>
    );
}
