// [Feature] 팝업 애니메이션 통일 — TripContextModal과 동일한 framer-motion 적용
"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

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
    // [Feature] maxWidth 옵션 — "sm"(400px) | 기본 "xl"(576px) 으로 팝업 크기 조절
    maxWidth?: "sm" | "xl";
}) {
    const z = zIndex ?? 50;
    const widthClass = maxWidth === "sm" ? "max-w-sm" : "max-w-xl";

    return (
        <AnimatePresence>
            {open && (
                <>
                    {/* Backdrop — fade in/out */}
                    <motion.div
                        key="simple-modal-backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.3, ease: "easeInOut" }}
                        className="fixed inset-0 bg-black/30 backdrop-blur-md z-[9998]"
                        style={{ zIndex: z }}
                        onClick={onClose}
                    />

                    {/* Modal content — scale + slide up */}
                    <motion.div
                        key="simple-modal-content"
                        initial={{ opacity: 0, scale: 0.9, y: 30 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        transition={{ type: "spring", damping: 25, stiffness: 300 }}
                        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
                        style={{ zIndex: z + 1 }}
                    >
                        <div
                            className={`relative w-full ${widthClass} rounded-[2rem] bg-white/90 backdrop-blur-3xl border border-white shadow-[0_16px_40px_-8px_rgba(0,0,0,0.15)] overflow-hidden pointer-events-auto p-8`}
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center gap-2 mb-5">
                                {icon && (
                                    <div className="w-8 h-8 bg-gray-100/80 backdrop-blur-sm rounded-xl flex items-center justify-center border border-white shadow-sm">
                                        {icon}
                                    </div>
                                )}
                                <h2 className="text-[11px] font-extrabold text-gray-400 uppercase tracking-widest">
                                    {title}
                                </h2>
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className="absolute top-6 right-6 p-2.5 text-gray-400 hover:text-gray-800 hover:bg-gray-100/70 rounded-full transition-all bg-transparent"
                                >
                                    <X size={16} />
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
