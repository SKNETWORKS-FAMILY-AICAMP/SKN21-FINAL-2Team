"use client";

import React, { createContext, useContext, useEffect, useRef } from "react";

// ── Context ──────────────────────────────────────────────
interface DialogContextValue {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}
const DialogContext = createContext<DialogContextValue>({
    open: false,
    onOpenChange: () => { },
});

// ── Dialog ───────────────────────────────────────────────
interface DialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    children: React.ReactNode;
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
    return (
        <DialogContext.Provider value={{ open, onOpenChange }}>
            {children}
        </DialogContext.Provider>
    );
}

// ── DialogTrigger ─────────────────────────────────────────
interface DialogTriggerProps {
    asChild?: boolean;
    children: React.ReactNode;
}

export function DialogTrigger({ asChild, children }: DialogTriggerProps) {
    const { onOpenChange } = useContext(DialogContext);

    if (asChild && React.isValidElement(children)) {
        return React.cloneElement(children as React.ReactElement<React.HTMLAttributes<HTMLElement>>, {
            onClick: (e: React.MouseEvent<HTMLElement>) => {
                const original = (children as React.ReactElement<React.HTMLAttributes<HTMLElement>>).props.onClick;
                if (original) original(e);
                onOpenChange(true);
            },
        });
    }

    return (
        <button type="button" onClick={() => onOpenChange(true)}>
            {children}
        </button>
    );
}

// ── DialogContent ─────────────────────────────────────────
interface DialogContentProps {
    className?: string;
    children: React.ReactNode;
}

export function DialogContent({ className = "", children }: DialogContentProps) {
    const { open, onOpenChange } = useContext(DialogContext);
    const overlayRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") onOpenChange(false);
        };
        if (open) document.addEventListener("keydown", handleKey);
        return () => document.removeEventListener("keydown", handleKey);
    }, [open, onOpenChange]);

    if (!open) return null;

    return (
        <div
            ref={overlayRef}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
            onClick={(e) => { if (e.target === overlayRef.current) onOpenChange(false); }}
        >
            <div
                className={`relative bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6 ${className}`}
                onClick={(e) => e.stopPropagation()}
            >
                {children}
            </div>
        </div>
    );
}

// ── DialogHeader / Title / Description / Footer ───────────
export function DialogHeader({ children }: { children: React.ReactNode }) {
    return <div className="mb-4">{children}</div>;
}

export function DialogTitle({ className = "", children }: { className?: string; children: React.ReactNode }) {
    return <h2 className={`text-lg font-semibold text-gray-900 ${className}`}>{children}</h2>;
}

export function DialogDescription({ children }: { children: React.ReactNode }) {
    return <p className="text-sm text-gray-500 mt-1">{children}</p>;
}

export function DialogFooter({ children }: { children: React.ReactNode }) {
    return <div className="flex justify-end gap-2 mt-4">{children}</div>;
}
