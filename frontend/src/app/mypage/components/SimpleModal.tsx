// [Feature] 팝업 애니메이션 통일 — TripContextModal과 동일한 framer-motion 적용
"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

export function SimpleModal({
    open,
    title,
    onClose,
    children,
    zIndex,
    maxWidth,
}: {
    open: boolean;
    title: string;
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
                        transition={{ duration: 0.2 }}
                        className="fixed inset-0 bg-black/45 backdrop-blur-[2px]"
                        style={{ zIndex: z }}
                        onClick={onClose}
                    />

                    {/* Modal content — scale + slide up */}
                    <motion.div
                        key="simple-modal-content"
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        transition={{ duration: 0.25, ease: "easeOut" }}
                        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
                        style={{ zIndex: z + 1 }}
                    >
                        <div
                            className={`relative w-full ${widthClass} rounded-3xl bg-white border border-gray-200 shadow-2xl overflow-hidden pointer-events-auto`}
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
                                <h3 className="text-[11px] font-bold text-gray-900 uppercase tracking-widest">
                                    {title}
                                </h3>
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className="w-8 h-8 rounded-full border border-gray-200 bg-white text-gray-600 flex items-center justify-center hover:bg-gray-50 transition-colors"
                                >
                                    <X size={14} />
                                </button>
                            </div>
                            <div className="p-6">{children}</div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
