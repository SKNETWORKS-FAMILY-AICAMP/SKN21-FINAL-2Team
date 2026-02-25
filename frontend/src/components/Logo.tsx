"use client";

import { cn } from "../../utils";
import { useRouter } from "next/navigation";

interface LogoProps {
    className?: string;
}

export function Logo({ className }: LogoProps) {
    const router = useRouter();

    return (
        <div
            className={cn("flex items-center gap-3 cursor-pointer group", className)}
            onClick={() => router.push("/")}
        >
            <div className="w-8 h-8 bg-black flex items-center justify-center">
                <span className="text-white font-serif font-bold text-xl leading-none italic">T</span>
            </div>
            <span className="font-serif font-bold text-xl tracking-tighter text-gray-900 group-hover:opacity-80 transition-opacity">
                Triver.
            </span>
        </div>
    );
}
