"use client";

import { useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
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
                        aria-label="Close"
                        className="absolute inset-0 bg-black/40"
                        onClick={onClose}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                    />

                    <motion.div
                        className="relative z-10 w-full max-w-xl rounded-xl bg-white border border-gray-200 shadow-lg overflow-hidden flex flex-col"
                        initial={{ opacity: 0, y: 10, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.98 }}
                        transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    >
                        <div className="p-6 pb-4">
                            <h2 className="text-3xl font-bold text-gray-900 text-center">Journey Detail</h2>
                        </div>

                        <div className="px-6 pb-4">
                            <div className="relative rounded-xl border border-gray-200 bg-white p-5 max-h-[55vh] overflow-y-auto">
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ duration: 0.2 }}
                                    className="space-y-2"
                                >
                                    {transcript.length === 0 && (
                                        <div className="text-xs text-gray-500 text-center py-6">No chat history in this room.</div>
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
                                Menu
                            </button>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
