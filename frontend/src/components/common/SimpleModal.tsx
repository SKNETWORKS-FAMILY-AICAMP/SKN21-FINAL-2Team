// [Feature] 모달 디자인 시스템 통일 — TripContextModal 기반 테마 상수 추출
"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

/**
 * 모달 전체에서 공통으로 사용할 디자인 테마 상수입니다.
 * 다른 모달들은 이 스타일을 참조하여 일관성을 유지합니다.
 */
export const MODAL_STYLES = {
    overlay: "fixed inset-0 bg-black/30 backdrop-blur-md z-[9998]",
    container: "relative w-full rounded-[2.5rem] bg-white border border-gray-100 shadow-[0_32px_80px_-16px_rgba(0,0,0,0.08)] overflow-hidden pointer-events-auto",
    headerIconBox: "w-10 h-10 bg-black text-white rounded-xl flex items-center justify-center shadow-sm",
    headerLabel: "text-[14px] font-bold text-[#8b98a5] uppercase leading-none mb-0.5 px-0.5",
    headerTitle: "text-[15px] font-bold text-gray-900 leading-none",
    closeButton: "absolute top-6 right-6 p-2.5 text-gray-400 hover:text-gray-800 hover:bg-black/[0.03] rounded-full transition-all bg-transparent",
};

export function SimpleModal({
    open,
    title,
    icon,
    onClose,
    children,
    zIndex,
    maxWidth,
}: {
    open: boolean;
    title: string;
    icon?: React.ReactNode;
    onClose: () => void;
    children: React.ReactNode;
    zIndex?: number;
    maxWidth?: "sm" | "xl";
}) {
    const z = zIndex ?? 50;
    const widthClass = maxWidth === "sm" ? "max-w-sm" : "max-w-xl";

    return (
        <AnimatePresence>
            {open && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        key="simple-modal-backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.3, ease: "easeInOut" }}
                        className={MODAL_STYLES.overlay}
                        style={{ zIndex: z }}
                        onClick={onClose}
                    />

                    {/* Modal content */}
                    <motion.div
                        key="simple-modal-content"
                        initial={{ opacity: 0, scale: 0.9, y: 30 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        transition={{ duration: 0.2 }}
                        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
                        style={{ zIndex: z + 1 }}
                    >
                        <div
                            className={`${MODAL_STYLES.container} ${widthClass} p-8`}
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center gap-3 mb-6">
                                {icon && (
                                    <div className={MODAL_STYLES.headerIconBox}>
                                        {icon}
                                    </div>
                                )}
                                <div className="flex items-center gap-2 mt-0.5">
                                    <h2 className={MODAL_STYLES.headerLabel}>
                                        {title}
                                    </h2>
                                </div>
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className={MODAL_STYLES.closeButton}
                                >
                                    <X size={18} />
                                </button>
                            </div>
                            <div className="w-full">{children}</div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
