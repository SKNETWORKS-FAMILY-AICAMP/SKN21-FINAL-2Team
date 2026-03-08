import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "default" | "outline" | "ghost";
    size?: "sm" | "md" | "lg";
    className?: string;
}

export function Button({ children, className = "", variant = "default", ...props }: ButtonProps) {
    const base = "inline-flex items-center justify-center font-medium transition-colors focus:outline-none disabled:opacity-50 disabled:pointer-events-none px-4 py-2 text-sm rounded-lg";
    const variants = {
        default: "bg-black text-white hover:bg-gray-800",
        outline: "border border-gray-200 text-gray-700 hover:bg-gray-50",
        ghost: "text-gray-700 hover:bg-gray-100",
    };
    return (
        <button className={`${base} ${variants[variant]} ${className}`} {...props}>
            {children}
        </button>
    );
}
