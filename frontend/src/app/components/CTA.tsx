"use client";

import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { verifyAndRefreshToken, fetchCurrentUser } from "@/services/api";
// [Feature] 가입/설문 미완료 시 경고 팝업 — Hero/Destinations와 동일한 IncompleteSignupModal 재사용
import { IncompleteSignupModal } from "@/app/components/IncompleteSignupModal";

export function CTA() {
    const router = useRouter();

    // [Feature] Start for Free 버튼 클릭 시 가입 미완료 사용자에게 경고 모달 표시
    const [isNavigating, setIsNavigating] = useState(false);
    const [isWarningModalOpen, setIsWarningModalOpen] = useState(false);
    const [warningStep, setWarningStep] = useState<"profile" | "survey" | null>(null);

    const handleNavigation = async () => {
        if (isNavigating) return;

        const token = localStorage.getItem("access_token");
        if (!token) {
            router.push("/signup");
            return;
        }

        setIsNavigating(true);
        try {
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

            router.push("/explore");
        } catch {
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
        <section className="py-24 bg-black text-white text-center">
            <div className="max-w-4xl mx-auto px-6">
                <h2 className="text-4xl md:text-6xl font-light tracking-tight mb-8">
                    Your journey begins <span className="font-serif italic text-gray-400">here.</span>
                </h2>
                <p className="text-lg md:text-xl text-gray-500 max-w-2xl mx-auto mb-10 leading-relaxed font-light">
                    Start planning your dream trip to Seoul today with our AI-powered travel assistant. No hidden fees, just pure exploration.
                </p>
                <button
                    onClick={handleNavigation}
                    disabled={isNavigating}
                    className="bg-white text-black px-8 py-4 rounded-full text-lg font-semibold hover:bg-gray-200 transition-colors shadow-xl hover:shadow-2xl hover:-translate-y-1 transform duration-300 flex items-center justify-center gap-2 mx-auto disabled:opacity-60 disabled:cursor-not-allowed"
                >
                    {isNavigating ? "..." : "Start for Free"} <ArrowRight size={20} />
                </button>
            </div>
        </section>

        {/* [Feature] 가입/설문 미완료 경고 모달 — Start for Free 버튼에서 미완료 사용자 감지 시 표시 */}
        <IncompleteSignupModal
            isOpen={isWarningModalOpen}
            missingStep={warningStep}
            onClose={() => setIsWarningModalOpen(false)}
            onConfirm={confirmWarning}
        />
        </>
    );
}
