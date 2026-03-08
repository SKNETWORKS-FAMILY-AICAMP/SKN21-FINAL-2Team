"use client";

import { motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { useState, useEffect } from "react";
import { Logo } from "@/components/Logo";
import { useRouter } from "next/navigation";
import { fetchCurrentUser, type UserProfile } from "@/services/api";
import { IncompleteSignupModal } from "@/components/landing/IncompleteSignupModal";

export function Header() {
    const [isOpen, setIsOpen] = useState(false);
    const router = useRouter();
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null); // To store full user info for navigation guard
    const [profilePicture, setProfilePicture] = useState<string | null>(null);
    const [userInitial, setUserInitial] = useState<string>("?");
    const [imgError, setImgError] = useState(false);

    const [isWarningModalOpen, setIsWarningModalOpen] = useState(false);
    const [warningStep, setWarningStep] = useState<"profile" | "survey" | null>(null);

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

                <nav className="hidden md:flex items-center gap-8 absolute left-1/2 -translate-x-1/2">
                    {["Features", "Destinations", "Reviews"].map((item) => (
                        <a
                            key={item}
                            href={`#${item.toLowerCase()}`}
                            className="text-sm font-medium text-gray-500 hover:text-black transition-colors"
                        >
                            {item}
                        </a>
                    ))}
                </nav>

                <div className="hidden md:flex items-center gap-4">
                    {/* 로그인 상태 & 가입 완료(is_join, is_prefer): 프로필 사진 | 비로그인 or 가입 미완료: Get Started 버튼 */}
                    {profilePicture && !imgError && userProfile?.is_join && userProfile?.is_prefer ? (
                        <button
                            onClick={handleNavigation}
                            className="w-9 h-9 rounded-full overflow-hidden border-2 border-gray-200 shadow-sm transition-transform hover:scale-105"
                            title="내 프로필로 이동"
                        >
                            <img
                                src={profilePicture}
                                alt="프로필"
                                className="w-full h-full object-cover"
                                onError={() => setImgError(true)}
                            />
                        </button>
                    ) : profilePicture && imgError && userProfile?.is_join && userProfile?.is_prefer ? (
                        // 이미지 로드 실패 시 이니셜 폴백
                        <button
                            onClick={handleNavigation}
                            className="w-9 h-9 rounded-full bg-indigo-500 text-white text-sm font-bold border-2 border-gray-200 shadow-sm transition-transform hover:scale-105"
                            title="내 프로필로 이동"
                        >
                            {userInitial}
                        </button>
                    ) : (
                        <button
                            onClick={handleNavigation}
                            className="bg-black text-white text-sm font-medium px-4 py-2 rounded-full hover:bg-gray-800 transition-colors"
                        >
                            Get Started
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
                        {["Features", "Destinations", "Reviews"].map((item) => (
                            <a
                                key={item}
                                href={`#${item.toLowerCase()}`}
                                className="text-base font-medium text-gray-500 hover:text-black"
                                onClick={() => setIsOpen(false)}
                            >
                                {item}
                            </a>
                        ))}
                        <hr className="my-2 border-gray-100" />
                        {/* 모바일 메뉴: 로그인 상태에서도 동일하게 프로필 처리 */}
                        {profilePicture && !imgError && userProfile?.is_join && userProfile?.is_prefer ? (
                            <button
                                onClick={() => { setIsOpen(false); handleNavigation(); }}
                                className="flex items-center gap-3 w-full"
                                title="내 프로필로 이동"
                            >
                                <img
                                    src={profilePicture}
                                    alt="프로필"
                                    className="w-9 h-9 rounded-full object-cover border-2 border-gray-200"
                                    onError={() => setImgError(true)}
                                />
                                <span className="text-base font-medium text-gray-700">내 프로필로 이동</span>
                            </button>
                        ) : profilePicture && imgError && userProfile?.is_join && userProfile?.is_prefer ? (
                            <button
                                onClick={() => { setIsOpen(false); handleNavigation(); }}
                                className="flex items-center gap-3 w-full"
                            >
                                <span className="w-9 h-9 rounded-full bg-indigo-500 text-white text-sm font-bold flex items-center justify-center border-2 border-gray-200">
                                    {userInitial}
                                </span>
                                <span className="text-base font-medium text-gray-700">내 프로필로 이동</span>
                            </button>
                        ) : (
                            <button
                                onClick={() => { setIsOpen(false); handleNavigation(); }}
                                className="bg-black text-white text-base font-medium px-4 py-2 rounded-full"
                            >
                                Get Started
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
