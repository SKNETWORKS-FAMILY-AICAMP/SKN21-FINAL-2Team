"use client";

import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { Plus_Jakarta_Sans } from "next/font/google";

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

// 워드마크는 아이콘의 곡선형 실루엣과 충돌하지 않도록
// 대비가 강한 세리프 대신 단단한 산세리프로 맞춘다.
const wordmarkFont = Plus_Jakarta_Sans({
    subsets: ["latin"],
    weight: ["800"],
});

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
                <div className="inline-flex items-center gap-2">  {/* 아이콘과 워드마크 표시 */}
                    <BrandMark tone={tone} size={size} />
                    <span
                        className={cn(wordmarkFont.className, tone === "light" ? "text-white" : "text-black")}
                        style={{
                            fontSize: Math.round(size * 0.84),
                            fontWeight: 800,
                            lineHeight: 1,
                            letterSpacing: "-0.03em",
                            transform: "translateY(-1px)",
                        }}
                    >
                        Triver
                    </span>
                </div>
            )}
        </div>
    );
}
