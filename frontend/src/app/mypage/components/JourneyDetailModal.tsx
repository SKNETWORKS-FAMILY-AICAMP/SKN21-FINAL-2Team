"use client";

import { useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useTranslation } from "@/i18n/useTranslation";
import type { TripSummary, ChatTranscriptMessage } from "../types";

export function JourneyDetailModal({
    open,
    trip,
    onClose,
}: {
    open: boolean;
    trip: TripSummary | null;
    onClose: () => void;
}) {
    const { t } = useTranslation();
    const transcript = useMemo(() => {
        if (!trip) return [] as ChatTranscriptMessage[];
        return trip.messages;
    }, [trip]);

    return (
        <AnimatePresence>
            {open && trip && (
                <motion.div
                    className="fixed inset-0 z-50 flex items-center justify-center p-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                >
                    <motion.button
                        type="button"

                        className="absolute inset-0 bg-black/40"
                        onClick={onClose}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                    />

                    <motion.div
                        className="relative z-10 w-[95%] sm:w-full max-w-xl rounded-[28px] bg-white/95 backdrop-blur-3xl border border-white shadow-2xl overflow-hidden flex flex-col"
                        initial={{ opacity: 0, y: 10, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.98 }}
                        transition={{ type: "spring", stiffness: 300, damping: 25 }}
                    >
                        <div className="flex flex-none items-center justify-between border-b border-gray-100/50 px-6 py-4">
                            <div className="flex items-center gap-3">
                                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#f1f3f5] text-gray-700">
                                    <span className="text-[10px] font-black">AI</span>
                                </div>
                                <h2 className="text-[11px] font-extrabold uppercase tracking-widest text-[#8b98a5]">
                                    {t("mypage.journeyDetail")}
                                </h2>
                            </div>
                        </div>

                        <div className="px-6 pb-4 pt-4">
                            <div className="relative rounded-[20px] border border-gray-100 bg-black/[0.02] p-5 max-h-[55vh] overflow-y-auto">
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ duration: 0.2 }}
                                    className="space-y-2"
                                >
                                    {transcript.length === 0 && (
                                        <div className="text-xs text-gray-500 text-center py-6">{t("mypage.noChatHistory")}</div>
                                    )}
                                    {transcript.map((m, idx) => {
                                        const isUser = m.role === "user";
                                        return (
                                            <motion.div
                                                key={`${m.role}-${idx}-${m.text.slice(0, 12)}`}
                                                initial={{ opacity: 0, y: 8, scale: 0.98 }}
                                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                                transition={{ duration: 0.25, delay: idx * 0.08 }}
                                                className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                                            >
                                                <div
                                                    className={
                                                        isUser
                                                            ? "max-w-[85%] rounded-2xl rounded-br-md bg-black text-white px-4 py-3 text-xs leading-relaxed shadow-sm"
                                                            : "max-w-[85%] rounded-2xl rounded-bl-md bg-gray-100 text-gray-900 px-4 py-3 text-xs leading-relaxed shadow-sm"
                                                    }
                                                >
                                                    <div className="whitespace-pre-wrap">{m.text}</div>
                                                </div>
                                            </motion.div>
                                        );
                                    })}
                                </motion.div>
                            </div>
                        </div>

                        <div className="px-6 pb-6">
                            <button
                                type="button"
                                onClick={onClose}
                                className="w-full bg-black text-white py-3 rounded-lg text-sm font-semibold"
                            >
                                {t("mypage.menu")}
                            </button>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
