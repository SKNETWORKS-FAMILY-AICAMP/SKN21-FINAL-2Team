"use client";

import { useGoogleLogin } from "@react-oauth/google";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import i18n from "@/i18n/config";
import { fetchCurrentUser, getPostLoginPath, updateCurrentUser } from "@/services/api";

type Props = {
    label?: string;
};
const GOOGLE_POPUP_REDIRECT_URI = "postmessage";

export default function GoogleLoginBtn({ label }: Props) {
    const router = useRouter();
    const { t } = useTranslation();

    const displayLabel = label || t("login.googleStart");

    const login = useGoogleLogin({
        flow: "auth-code",
        ux_mode: "popup",
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
                        redirect_uri: GOOGLE_POPUP_REDIRECT_URI,
                    }),
                });

                if (!res.ok) {
                    throw new Error(t("login.failed"));
                }

                const data = await res.json();
                localStorage.setItem("access_token", data.access_token);
                if (data.refresh_token) {
                    localStorage.setItem("refresh_token", data.refresh_token);
                }

                const user = await fetchCurrentUser();

                // 클라이언트에서 선택한 언어를 DB에 동기화
                const clientLang = i18n.language;
                if (clientLang && ["en", "ko", "ja", "zh"].includes(clientLang) && clientLang !== user.language) {
                    updateCurrentUser({ language: clientLang }).catch(() => {});
                }

                const targetPath = getPostLoginPath(user);
                console.log("Login Success: User", user, "Redirecting to", targetPath);

                router.push(targetPath);
            } catch (error) {
                console.error("Login Error:", error instanceof Error ? error.message : error);
                alert(t("login.failed"));
            }
        },
        onError: (errorResponse) => console.log("Google OAuth error:", errorResponse.error, errorResponse.error_description),
    });

    return (
        <div className="flex justify-center">
            <button
                type="button"
                onClick={() => login()}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 font-medium text-slate-800 shadow-sm transition hover:border-slate-400 hover:bg-slate-50 hover:text-slate-900"
            >
                <img className="w-6 h-6" src="https://www.svgrepo.com/show/475656/google-color.svg" loading="lazy" alt="Google" />
                <span>{displayLabel}</span>
            </button>
        </div>
    );
}
