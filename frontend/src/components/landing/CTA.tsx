"use client";

import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";

export function CTA() {
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
        <section className="py-24 bg-black text-white text-center">
            <div className="max-w-4xl mx-auto px-6">
                <h2 className="text-4xl md:text-6xl font-light tracking-tight mb-8">
                    Your journey begins <span className="font-serif italic text-gray-400">here.</span>
                </h2>
                <p className="text-lg md:text-xl text-gray-500 max-w-2xl mx-auto mb-10 leading-relaxed font-light">
                    Start planning your dream trip to Seoul today with our AI-powered travel assistant. No hidden fees, just pure exploration.
                </p>
                <button
                    onClick={handleNavigation}
                    className="bg-white text-black px-8 py-4 rounded-full text-lg font-semibold hover:bg-gray-200 transition-colors shadow-xl hover:shadow-2xl hover:-translate-y-1 transform duration-300 flex items-center justify-center gap-2 mx-auto"
                >
                    Start for Free <ArrowRight size={20} />
                </button>
            </div>
        </section>
    );
}
