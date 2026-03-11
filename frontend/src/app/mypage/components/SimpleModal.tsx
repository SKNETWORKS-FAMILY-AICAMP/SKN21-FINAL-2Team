"use client";

import { X } from "lucide-react";

export function SimpleModal({
    open,
    title,
    onClose,
    children,
    zIndex,
}: {
    open: boolean;
    title: string;
    onClose: () => void;
    children: React.ReactNode;
    zIndex?: number;
}) {
    if (!open) return null;

    return (
        <div className="fixed inset-0 flex items-center justify-center p-4" style={{ zIndex: zIndex ?? 50 }}>
            <button
                type="button"
                aria-label="Close"
                className="absolute inset-0 bg-black/45 backdrop-blur-[2px]"
                onClick={onClose}
            />
            <div className="relative z-10 w-full max-w-xl rounded-3xl bg-white border border-gray-200 shadow-2xl overflow-hidden">
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
        </div>
    );
}
