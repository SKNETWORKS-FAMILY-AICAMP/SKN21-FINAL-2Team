"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, AlertCircle, ArrowRight, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

interface IncompleteSignupModalProps {
    isOpen: boolean;
    missingStep: "profile" | "survey" | null;
    onConfirm: () => void;
    onClose: () => void;
}

export function IncompleteSignupModal({ isOpen, missingStep, onConfirm, onClose }: IncompleteSignupModalProps) {
    const title = missingStep === "profile" ? "회원 정보 입력이 필요해요" : "취향 분석 설문이 필요해요";
    const description = missingStep === "profile"
        ? "Triver의 맞춤형 추천을 위해 기본 프로필 정보를 먼저 입력해주세요."
        : "더 완벽한 여행 추천을 위해 3가지 짧은 설문을 완료해주세요.";
    const buttonText = missingStep === "profile" ? "프로필 입력하러 가기" : "설문하러 가기";
    const router = useRouter();

    const handleLogout = () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("profile_picture");
        localStorage.removeItem("user_name");
        localStorage.removeItem("user_email");
        onClose();
        router.push("/signup");
    };

    return (
        <AnimatePresence>
            {isOpen && missingStep && (
                <>
                    <motion.div
                        key="backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[9999]"
                        onClick={onClose}
                    />

                    <motion.div
                        key="modal"
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        transition={{ duration: 0.25, ease: "easeOut" }}
                        className="fixed inset-0 w-screen h-screen flex items-center justify-center z-[9999] p-4 pointer-events-none"
                    >
                        <div
                            className="bg-white rounded-3xl shadow-2xl w-full max-w-sm p-8 relative pointer-events-auto"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <button
                                onClick={onClose}
                                className="absolute top-5 right-5 p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
                            >
                                <X size={18} />
                            </button>

                            <div className="w-12 h-12 bg-red-50 rounded-full flex items-center justify-center mb-6">
                                <AlertCircle size={24} className="text-red-500" />
                            </div>

                            <h2 className="text-xl font-bold text-gray-900 mb-3">
                                {title}
                            </h2>
                            <p className="text-sm text-gray-500 mb-8 leading-relaxed">
                                {description}
                            </p>

                            <div className="flex flex-col gap-3">
                                <button
                                    onClick={onConfirm}
                                    className="w-full py-3.5 bg-black text-white rounded-2xl text-sm font-semibold flex items-center justify-center gap-2 hover:bg-gray-800 transition-colors shadow-md hover:shadow-lg"
                                >
                                    {buttonText}
                                    <ArrowRight size={16} />
                                </button>
                                <button
                                    onClick={onClose}
                                    className="w-full py-3.5 text-gray-500 rounded-2xl text-sm font-medium hover:bg-gray-50 transition-colors"
                                >
                                    다음에 할게요
                                </button>
                            </div>

                            <button
                                onClick={handleLogout}
                                className="mt-6 w-full flex items-center justify-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
                            >
                                <LogOut size={12} />
                                다른 구글 계정으로 로그인하기
                            </button>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
