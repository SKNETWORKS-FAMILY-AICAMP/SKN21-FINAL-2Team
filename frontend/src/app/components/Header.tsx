"use client";

import { motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { useState, useEffect, useRef, useCallback } from "react";
import { Logo } from "@/components/common/Logo";
import { useRouter } from "next/navigation";
import { fetchCurrentUser, type UserProfile } from "@/services/api";
import { IncompleteSignupModal } from "@/app/components/IncompleteSignupModal";
import { useTranslation } from "@/i18n/useTranslation";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";

// [Fix] Header h-16 = 64px, 섹션 상단이 Header 바로 아래에 딱 맞도록 오프셋
const HEADER_HEIGHT = 64;

export function Header() {
    const { t } = useTranslation();
    const [isOpen, setIsOpen] = useState(false);
    const router = useRouter();
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const [profilePicture, setProfilePicture] = useState<string | null>(null);
    const [userInitial, setUserInitial] = useState<string>("?");
    const [imgError, setImgError] = useState(false);

    const [isWarningModalOpen, setIsWarningModalOpen] = useState(false);
    const [warningStep, setWarningStep] = useState<"profile" | "survey" | null>(null);

    // [Fix] 현재 네비로 이동한 섹션 ID 추적 (리사이즈 시 자동 재정렬용)
    const activeSectionRef = useRef<string | null>(null);

    // [Fix] 섹션 상단 기준 스크롤: 섹션이 뷰포트를 채우므로 상단만 맞추면 콘텐츠가 자동 중앙
    const scrollToSection = useCallback((sectionId: string, smooth = true) => {
        const section = document.getElementById(sectionId);
        if (!section) return;
        const top = section.getBoundingClientRect().top + window.scrollY - HEADER_HEIGHT;
        window.scrollTo({ top: Math.max(0, top), behavior: smooth ? "smooth" : "instant" });
        activeSectionRef.current = sectionId;
    }, []);

    // [Fix] 화면 크기 변경 시 현재 활성 섹션으로 자동 재정렬
    useEffect(() => {
        let resizeTimer: ReturnType<typeof setTimeout>;
        const handleResize = () => {
            clearTimeout(resizeTimer);
            // 리사이즈 끝난 후 150ms 뒤에 재정렬 (성능 보호)
            resizeTimer = setTimeout(() => {
                if (activeSectionRef.current) {
                    scrollToSection(activeSectionRef.current, false);
                }
            }, 150);
        };
        window.addEventListener("resize", handleResize);
        return () => {
            window.removeEventListener("resize", handleResize);
            clearTimeout(resizeTimer);
        };
    }, [scrollToSection]);

    // [Fix] 사용자가 수동으로 스크롤하면 활성 섹션 추적 해제 (자동 재정렬 방지)
    useEffect(() => {
        let scrollTimer: ReturnType<typeof setTimeout>;
        const handleScroll = () => {
            clearTimeout(scrollTimer);
            scrollTimer = setTimeout(() => {
                // 현재 뷰포트 중심에 가장 가까운 섹션 찾기
                const sections = ["features", "destinations", "reviews"];
                let closest: string | null = null;
                let minDist = Infinity;
                for (const id of sections) {
                    const el = document.getElementById(id);
                    if (!el) continue;
                    const rect = el.getBoundingClientRect();
                    const dist = Math.abs(rect.top - HEADER_HEIGHT);
                    if (dist < minDist) {
                        minDist = dist;
                        closest = id;
                    }
                }
                // 섹션과 멀리 떨어져 있으면(Hero/CTA/Footer 등) 추적 해제
                if (minDist > 300) {
                    activeSectionRef.current = null;
                } else {
                    activeSectionRef.current = closest;
                }
            }, 100);
        };
        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => {
            window.removeEventListener("scroll", handleScroll);
            clearTimeout(scrollTimer);
        };
    }, []);

    // 컴포넌트 마운트 시 토큰 확인 → 프로필 정보 가져오기
    useEffect(() => {
        const token = localStorage.getItem("access_token");
        if (!token) return;

        fetchCurrentUser()
            .then((user) => {
                setUserProfile(user);
                if (user.profile_picture) {
                    setProfilePicture(user.profile_picture);
                }
                // 이니셜: 닉네임 > 이름 > 이메일 첫 글자 순서로 우선순위
                const label = user.nickname || user.name || user.email || "?";
                setUserInitial(label.charAt(0).toUpperCase());
            })
            .catch(() => {
                // 주의: 토큰 만료 시 조용히 무시 (버튼은 Get Started로 유지)
                console.warn("Header: 프로필 정보 로드 실패 (토큰 만료 가능성)");
            });
    }, []);

    const handleNavigation = () => {
        const token = localStorage.getItem("access_token");
        if (token && userProfile) {
            // 주의: 가입 기입 내용이나 설문을 다 마치지 않았다면, explore 대신 경고 모달 표시
            if (!userProfile.is_join) {
                setWarningStep("profile");
                setIsWarningModalOpen(true);
                return;
            }
            if (!userProfile.is_prefer) {
                setWarningStep("survey");
                setIsWarningModalOpen(true);
                return;
            }
            router.push("/explore");
        } else {
            router.push("/signup");
        }
    };

    const confirmWarning = () => {
        setIsWarningModalOpen(false);
        if (warningStep === "profile") {
            router.push("/signup/profile");
        } else if (warningStep === "survey") {
            router.push("/survey");
        }
    };

    return (
        <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
            <div className="max-w-7xl mx-auto px-6 h-16 relative flex items-center justify-between">
                <Logo />

                {/* [Fix] 네비 클릭 시 h2 기준 스크롤 + 리사이즈 시 자동 재정렬 */}
                <nav className="hidden md:flex items-center gap-8 absolute left-1/2 -translate-x-1/2">
                    {[
                        { label: t("header.features"), id: "features" },
                        { label: t("header.destinations"), id: "destinations" },
                        { label: t("header.reviews"), id: "reviews" },
                    ].map((item) => (
                        <button
                            key={item.id}
                            onClick={() => scrollToSection(item.id)}
                            className="text-sm font-medium text-gray-500 hover:text-black transition-colors cursor-pointer"
                        >
                            {item.label}
                        </button>
                    ))}
                </nav>

                <div className="hidden md:flex items-center gap-4">
                    <LanguageSwitcher variant="dropdown" />
                    {/* 로그인 상태 & 가입 완료(is_join, is_prefer): 프로필 사진 | 비로그인 or 가입 미완료: Get Started 버튼 */}
                    {profilePicture && !imgError && userProfile?.is_join && userProfile?.is_prefer ? (
                        <button
                            onClick={handleNavigation}
                            className="w-9 h-9 rounded-full overflow-hidden border-2 border-gray-200 shadow-sm transition-transform hover:scale-105"
                            title={t("header.goToProfile")}
                        >
                            <img
                                src={profilePicture}
                                alt={t("header.profileAlt")}
                                className="w-full h-full object-cover"
                                onError={() => setImgError(true)}
                            />
                        </button>
                    ) : profilePicture && imgError && userProfile?.is_join && userProfile?.is_prefer ? (
                        // 이미지 로드 실패 시 이니셜 폴백
                        <button
                            onClick={handleNavigation}
                            className="w-9 h-9 rounded-full bg-indigo-500 text-white text-sm font-bold border-2 border-gray-200 shadow-sm transition-transform hover:scale-105"
                            title={t("header.goToProfile")}
                        >
                            {userInitial}
                        </button>
                    ) : (
                        <button
                            onClick={handleNavigation}
                            className="bg-black text-white text-sm font-medium px-4 py-2 rounded-full hover:bg-gray-800 transition-colors"
                        >
                            {t("header.getStarted")}
                        </button>
                    )}
                </div>

                <button className="md:hidden p-2 text-black" onClick={() => setIsOpen(!isOpen)}>
                    {isOpen ? <X size={24} /> : <Menu size={24} />}
                </button>
            </div>

            {isOpen && (
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className="md:hidden absolute top-16 left-0 right-0 bg-white border-b border-gray-100 p-6 shadow-lg"
                >
                    <nav className="flex flex-col gap-4">
                        {/* [Fix] 모바일 네비도 동일 스크롤 + 리사이즈 자동 재정렬 */}
                        {[
                            { label: t("header.features"), id: "features" },
                            { label: t("header.destinations"), id: "destinations" },
                            { label: t("header.reviews"), id: "reviews" },
                        ].map((item) => (
                            <button
                                key={item.id}
                                className="text-base font-medium text-gray-500 hover:text-black text-left"
                                onClick={() => {
                                    setIsOpen(false);
                                    setTimeout(() => scrollToSection(item.id), 100);
                                }}
                            >
                                {item.label}
                            </button>
                        ))}
                        <hr className="my-2 border-gray-100" />
                        <LanguageSwitcher variant="dropdown" />
                        {/* 모바일 메뉴: 로그인 상태에서도 동일하게 프로필 처리 */}
                        {profilePicture && !imgError && userProfile?.is_join && userProfile?.is_prefer ? (
                            <button
                                onClick={() => { setIsOpen(false); handleNavigation(); }}
                                className="flex items-center gap-3 w-full"
                                title={t("header.goToProfile")}
                            >
                                <img
                                    src={profilePicture}
                                    alt={t("header.profileAlt")}
                                    className="w-9 h-9 rounded-full object-cover border-2 border-gray-200"
                                    onError={() => setImgError(true)}
                                />
                                <span className="text-base font-medium text-gray-700">{t("header.goToProfile")}</span>
                            </button>
                        ) : profilePicture && imgError && userProfile?.is_join && userProfile?.is_prefer ? (
                            <button
                                onClick={() => { setIsOpen(false); handleNavigation(); }}
                                className="flex items-center gap-3 w-full"
                            >
                                <span className="w-9 h-9 rounded-full bg-indigo-500 text-white text-sm font-bold flex items-center justify-center border-2 border-gray-200">
                                    {userInitial}
                                </span>
                                <span className="text-base font-medium text-gray-700">{t("header.goToProfile")}</span>
                            </button>
                        ) : (
                            <button
                                onClick={() => { setIsOpen(false); handleNavigation(); }}
                                className="bg-black text-white text-base font-medium px-4 py-2 rounded-full"
                            >
                                {t("header.getStarted")}
                            </button>
                        )}
                    </nav>
                </motion.div>
            )}

            <IncompleteSignupModal
                isOpen={isWarningModalOpen}
                missingStep={warningStep}
                onClose={() => setIsWarningModalOpen(false)}
                onConfirm={confirmWarning}
            />
        </header>
    );
}
