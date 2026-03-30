"use client";

import { LogOut, AlertCircle, ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslation } from "@/i18n/useTranslation";
import { SimpleModal } from "@/components/common/SimpleModal";

interface IncompleteSignupModalProps {
    isOpen: boolean;
    missingStep: "profile" | "survey" | null;
    onConfirm: () => void;
    onClose: () => void;
}

export function IncompleteSignupModal({ isOpen, missingStep, onConfirm, onClose }: IncompleteSignupModalProps) {
    const { t } = useTranslation();
    const title = missingStep === "profile" ? t("incomplete.profileTitle") : t("incomplete.surveyTitle");
    const description = missingStep === "profile"
        ? t("incomplete.profileDescription")
        : t("incomplete.surveyDescription");
    const buttonText = missingStep === "profile" ? t("incomplete.profileButton") : t("incomplete.surveyButton");
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
        <SimpleModal
            open={!!(isOpen && missingStep)}
            onClose={onClose}
            title={title}
            icon={<AlertCircle size={20} />}
            maxWidth="sm"
        >
            <div className="flex flex-col">
                <p className="text-sm text-gray-500 mb-8 leading-relaxed">
                    {description}
                </p>

                <div className="flex flex-col gap-3">
                    <button
                        onClick={onConfirm}
                        className="w-full py-4 bg-black text-white rounded-2xl text-sm font-semibold flex items-center justify-center gap-2 hover:bg-gray-800 transition-all shadow-md hover:shadow-lg active:scale-[0.98]"
                    >
                        {buttonText}
                        <ArrowRight size={16} />
                    </button>
                    <button
                        onClick={onClose}
                        className="w-full py-4 text-gray-500 rounded-2xl text-sm font-medium hover:bg-gray-50 transition-colors"
                    >
                        {t("incomplete.later")}
                    </button>
                </div>

                <div className="mt-8 pt-6 border-t border-gray-100">
                    <button
                        onClick={handleLogout}
                        className="w-full flex items-center justify-center gap-2 text-xs text-gray-400 hover:text-red-500 transition-colors py-2"
                    >
                        <LogOut size={14} />
                        {t("incomplete.switchAccount")}
                    </button>
                </div>
            </div>
        </SimpleModal>
    );
}
