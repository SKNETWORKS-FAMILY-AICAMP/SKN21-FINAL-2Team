"use client";

import { cn } from "../../utils";
import { useRouter } from "next/navigation";

interface LogoProps {
    className?: string;
    variant?: "icon" | "lockup";
    tone?: "dark" | "light";
    size?: number;
    clickable?: boolean;
}

interface BrandMarkProps {
    className?: string;
    tone?: "dark" | "light";
    size?: number;
}

function resolveIconSrc(tone: "dark" | "light") {
    return tone === "light" ? "/brand/logo-icon-light.svg" : "/brand/logo-icon-dark.svg";
}

function resolveWordmarkSrc(tone: "dark" | "light") {
    return tone === "light" ? "/brand/logo-wordmark-light.svg" : "/brand/logo-wordmark-dark.svg";
}

export function BrandMark({ className, tone = "dark", size = 32 }: BrandMarkProps) {
    return (
        <img
            src={resolveIconSrc(tone)}
            alt="Triver logo"
            className={cn("inline-block object-contain", className)}
            style={{ width: size, height: size }}
        />
    );
}

export function Logo({
    className,
    variant = "lockup",
    tone = "dark",
    size = 32,
    clickable = true,
}: LogoProps) {
    const router = useRouter();
    const iconContainerClass = tone === "light" ? "bg-white" : "bg-black";
    const iconTone = tone === "light" ? "dark" : "light";

    return (
        <div
            className={cn("inline-flex items-center", clickable && "cursor-pointer", className)}
            onClick={() => {
                if (clickable) router.push("/");
            }}
        >
            {variant === "icon" ? (
                <div className={cn("inline-flex items-center justify-center rounded-[8px]", iconContainerClass)} style={{ width: size, height: size }}>
                    <BrandMark tone={iconTone} size={Math.round(size * 0.72)} />
                </div>
            ) : (
                <div className="inline-flex items-center gap-2.5">
                    <div className={cn("inline-flex items-center justify-center rounded-[8px]", iconContainerClass)} style={{ width: size, height: size }}>
                        <BrandMark tone={iconTone} size={Math.round(size * 0.68)} />
                    </div>
                    <img
                        src={resolveWordmarkSrc(tone)}
                        alt="Triver"
                        className="inline-block object-contain"
                        style={{ height: Math.round(size * 0.64), width: "auto" }}
                    />
                </div>
            )}
        </div>
    );
}
