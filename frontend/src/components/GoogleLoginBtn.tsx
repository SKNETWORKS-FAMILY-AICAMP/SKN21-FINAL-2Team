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
                const res = await fetch("http://localhost:8000/api/auth/google/callback", {
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
                console.error("Login Error:", error);
                alert("Login Failed");
            }
        },
        onError: (errorResponse) => console.log(errorResponse),
    });

    return (
        <div className="flex justify-center">
            <button
                onClick={() => login()}
                className="px-4 py-2 border flex gap-2 border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-200 hover:border-slate-400 dark:hover:border-slate-500 hover:text-slate-900 dark:hover:text-slate-300 hover:shadow transition duration-150"
            >
                <img className="w-6 h-6" src="https://www.svgrepo.com/show/475656/google-color.svg" loading="lazy" alt="google logo" />
                <span>{label}</span>
            </button>
        </div>
    );
}
