"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { verifyAndRefreshToken, fetchCurrentUser } from "@/services/api";
// [Feature] 가입/설문 미완료 시 경고 팝업 — Destinations.tsx와 동일한 IncompleteSignupModal 재사용
import { IncompleteSignupModal } from "@/app/components/IncompleteSignupModal";
import { useTranslation } from "@/i18n/useTranslation";

export function Hero() {
    const { t } = useTranslation();
    const router = useRouter();
    const [isNavigating, setIsNavigating] = useState(false);

    // [Feature] Start 버튼 클릭 시 가입 미완료 사용자에게 경고 모달 표시
    const [isWarningModalOpen, setIsWarningModalOpen] = useState(false);
    const [warningStep, setWarningStep] = useState<"profile" | "survey" | null>(null);

    const handleNavigation = async () => {
        // 중복 클릭 방지
        if (isNavigating) return;

        // [Feature] 일반 버튼(Start)을 통한 진입이므로 Plan Trip 플로우 플래그 제거
        localStorage.removeItem("planTripFlow");

        const token = localStorage.getItem("access_token");

        // 토큰 자체가 없으면 바로 로그인 페이지로
        if (!token) {
            router.push("/signup");
            return;
        }

        setIsNavigating(true);
        try {
            // 주의: localStorage에 토큰이 있어도 만료되었을 수 있으므로 서버 검증 필수
            await verifyAndRefreshToken();

            // [Feature] 토큰 유효 → 가입/설문 완료 여부 확인 후 미완료 시 팝업 표시
            const user = await fetchCurrentUser();
            if (!user.is_join) {
                setWarningStep("profile");
                setIsWarningModalOpen(true);
                return;
            }
            if (!user.is_prefer) {
                setWarningStep("survey");
                setIsWarningModalOpen(true);
                return;
            }

            // 가입 + 설문 모두 완료된 사용자만 explore 이동
            router.push("/explore");
        } catch {
            // 토큰 만료 또는 유효하지 않은 경우 → 정리 후 로그인
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            router.push("/signup");
        } finally {
            setIsNavigating(false);
        }
    };

    // [Feature] 경고 모달에서 "확인" 클릭 시 미완료 단계로 이동
    const confirmWarning = () => {
        setIsWarningModalOpen(false);
        if (warningStep === "profile") {
            router.push("/signup/profile");
        } else if (warningStep === "survey") {
            router.push("/survey");
        }
    };

    return (
        <>
        <section className="relative w-full h-screen min-h-[600px] flex items-center justify-center overflow-hidden">
            <div className="absolute inset-0 z-0">
                <img
                    src="https://images.unsplash.com/photo-1634028281608-d636a88abc09?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzZW91bCUyMGNpdHlzY2FwZSUyMHdpZGUlMjBtaW5pbWFsaXN0fGVufDF8fHx8MTc3MTQ0MTAzOHww&ixlib=rb-4.1.0&q=80&w=1080"
                    alt="Seoul Cityscape"
                    className="w-full h-full object-cover brightness-[0.7] saturate-110"
                />
                <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/60 z-10" />
            </div>

            <div className="relative z-20 max-w-6xl mx-auto px-6 text-center text-white">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                >
                    <span className="inline-block py-1 px-3 rounded-full bg-white/20 backdrop-blur-md border border-white/30 text-xs font-semibold tracking-widest uppercase mb-8">
                        {t("hero.badge")}
                    </span>
                    <h1 className="text-6xl md:text-8xl font-serif italic font-light tracking-tight leading-none mb-10 opacity-90">
                        {t("hero.titleLine1")}
                        <br />
                        {t("hero.titleLine2")}
                    </h1>
                    <p className="text-lg md:text-2xl text-white/90 max-w-4xl mx-auto font-light leading-normal mb-12 drop-shadow-md">
                        {t("hero.descriptionLine1")}
                        <br className="hidden md:block" />
                        {t("hero.descriptionLine2")}
                    </p>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
                    className="max-w-md mx-auto relative group"
                >
                    <div className="relative flex items-center bg-white/10 backdrop-blur-xl border border-white/30 rounded-full p-2 pl-6 transition-colors hover:bg-white/20">
                        <input
                            type="text"
                            placeholder={t("hero.placeholder")}
                            className="w-full bg-transparent text-white placeholder-white/70 outline-none text-lg font-light cursor-default"
                            readOnly
                        />
                        <button
                            onClick={handleNavigation}
                            disabled={isNavigating}
                            className="ml-2 bg-white text-black hover:bg-gray-100 shadow-lg px-8 h-12 text-sm font-semibold rounded-full transition-colors disabled:opacity-60 disabled:cursor-not-allowed whitespace-nowrap shrink-0"
                        >
                            {isNavigating ? "..." : t("hero.start")}
                        </button>
                    </div>
                </motion.div>
            </div>

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1, duration: 1 }}
                className="absolute bottom-10 left-1/2 -translate-x-1/2 text-white/70 text-sm flex flex-col items-center gap-2"
            >
                <span className="uppercase tracking-[0.3em] text-[10px]">{t("hero.scroll")}</span>
                <div className="w-[1px] h-16 bg-white/50" />
            </motion.div>
        </section>

        {/* [Feature] 가입/설문 미완료 경고 모달 — Start 버튼에서 미완료 사용자 감지 시 표시 */}
        <IncompleteSignupModal
            isOpen={isWarningModalOpen}
            missingStep={warningStep}
            onClose={() => setIsWarningModalOpen(false)}
            onConfirm={confirmWarning}
        />
        </>
    );
}
