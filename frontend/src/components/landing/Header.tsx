"use client";

import { motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { useState } from "react";
import { Logo } from "@/components/Logo";
import { useRouter } from "next/navigation";

export function Header() {
    const [isOpen, setIsOpen] = useState(false);
    const router = useRouter();

    const handleNavigation = () => {
        const token = localStorage.getItem("access_token");
        if (token) {
            router.push("/explore");
        } else {
            router.push("/login");
        }
    };

    return (
        <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
            <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
                <Logo />

                <nav className="hidden md:flex items-center gap-8">
                    {["Features", "Destinations", "Reviews"].map((item) => (
                        <a
                            key={item}
                            href={`#${item.toLowerCase()}`}
                            className="text-sm font-medium text-gray-500 hover:text-black transition-colors"
                        >
                            {item}
                        </a>
                    ))}
                </nav>

                <div className="hidden md:flex items-center gap-4">
                    <button
                        onClick={handleNavigation}
                        className="bg-black text-white text-sm font-medium px-4 py-2 rounded-full hover:bg-gray-800 transition-colors"
                    >
                        Get Started
                    </button>
                </div>

                <button className="md:hidden p-2 text-black" onClick={() => setIsOpen(!isOpen)}>
                    {isOpen ? <X size={24} /> : <Menu size={24} />}
                </button>
            </div>

            {isOpen && (
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className="md:hidden absolute top-16 left-0 right-0 bg-white border-b border-gray-100 p-6 shadow-lg"
                >
                    <nav className="flex flex-col gap-4">
                        {["Features", "Destinations", "Reviews"].map((item) => (
                            <a
                                key={item}
                                href={`#${item.toLowerCase()}`}
                                className="text-base font-medium text-gray-500 hover:text-black"
                                onClick={() => setIsOpen(false)}
                            >
                                {item}
                            </a>
                        ))}
                        <hr className="my-2 border-gray-100" />
                        <button
                            onClick={() => { setIsOpen(false); handleNavigation(); }}
                            className="bg-black text-white text-base font-medium px-4 py-2 rounded-full"
                        >
                            Get Started
                        </button>
                    </nav>
                </motion.div>
            )}
        </header>
    );
}
