"use client";

import { cn } from "../../utils";
import { useRouter } from "next/navigation";

// 로고 컴포넌트 (타입 지정, 색상 모드 종류 지정)
interface LogoProps {
    className?: string;
    variant?: "icon" | "lockup";
    tone?: "dark" | "light";
    size?: number;
}

// icon 전용 속성 지정
interface BrandMarkProps {
    tone?: "dark" | "light";
    size?: number;
}

// icon 전용 함수
// 톤에 따라 파일 선택
export function BrandMark({ tone = "dark", size = 32 }: BrandMarkProps) {
    return (
        <img
            src={tone === "light" ? "/brand/logo-icon-light.svg?v=20260308-2" : "/brand/logo-icon-dark.svg?v=20260308-2"}
            alt="Triver logo"
            className="inline-block object-contain"
            style={{ width: size, height: size }}   // 크기 지정
        />
    );
}

// 로고 본체 정의, variant로 아이콘/워드마크 선택, tone으로 색상 선택, size로 크기 선택
export function Logo({
    className,
    variant = "lockup",
    tone = "dark",
    size = 24,
}: LogoProps) {
    const router = useRouter();

    return (
        <div
            className={cn("inline-flex items-center cursor-pointer", className)}
            onClick={() => router.push("/")}
        >   {/* 클릭 시 메인 페이지로 이동 */}
            {variant === "icon" ? (   // 아이콘만 표시
                <BrandMark tone={tone} size={size} />
            ) : (
                <div className="inline-flex items-center gap-2.5">  {/* 아이콘과 워드마크 표시 */}
                    <BrandMark tone={tone} size={size} />
                    <span
                        className={cn("font-brand-serif", tone === "light" ? "text-white" : "text-black")}
                        style={{
                            fontSize: Math.round(size * 0.8),
                            fontWeight: 700,
                            lineHeight: 1,
                            letterSpacing: "-0.01em",
                            transform: "translateY(1px)",
                        }}
                    >
                        Triver
                    </span>
                </div>
            )}
        </div>
    );
}
