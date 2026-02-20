"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";

export function Hero() {
    const router = useRouter();

    return (
        <section className="relative w-full h-screen min-h-[600px] flex items-center justify-center overflow-hidden">
            <div className="absolute inset-0 z-0">
                <img
                    src="https://images.unsplash.com/photo-1634028281608-d636a88abc09?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzZW91bCUyMGNpdHlzY2FwZSUyMHdpZGUlMjBtaW5pbWFsaXN0fGVufDF8fHx8MTc3MTQ0MTAzOHww&ixlib=rb-4.1.0&q=80&w=1080"
                    alt="Seoul Cityscape"
                    className="w-full h-full object-cover brightness-[0.7] saturate-110"
                />
                <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/60 z-10" />
            </div>

            <div className="relative z-20 max-w-6xl mx-auto px-6 text-center text-white">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                >
                    <span className="inline-block py-1 px-3 rounded-full bg-white/20 backdrop-blur-md border border-white/30 text-xs font-semibold tracking-widest uppercase mb-8">
                        Discover Seoul with AI
                    </span>
                    <h1 className="text-6xl md:text-8xl font-serif italic font-light tracking-tight leading-none mb-10 opacity-90">
                        Travel smarter,
                        <br />
                        not harder
                    </h1>
                    <p className="text-lg md:text-2xl text-white/90 max-w-4xl mx-auto font-light leading-normal mb-12 drop-shadow-md">
                        Experience hyper-personalized travel planning.
                        <br className="hidden md:block" />
                        Let our AI curate your perfect Seoul itinerary in seconds.
                    </p>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
                    className="max-w-md mx-auto relative group"
                >
                    <div className="relative flex items-center bg-white/10 backdrop-blur-xl border border-white/30 rounded-full p-2 pl-6 transition-colors hover:bg-white/20">
                        <input
                            type="text"
                            placeholder="Where is your next destination?"
                            className="w-full bg-transparent text-white placeholder-white/70 outline-none text-lg font-light"
                        />
                        <button
                            onClick={() => router.push("/login")}
                            className="ml-2 bg-white text-black hover:bg-gray-100 shadow-lg px-8 h-12 text-sm font-semibold rounded-full transition-colors"
                        >
                            Start
                        </button>
                    </div>
                </motion.div>
            </div>

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1, duration: 1 }}
                className="absolute bottom-10 left-1/2 -translate-x-1/2 text-white/70 text-sm flex flex-col items-center gap-2"
            >
                <span className="uppercase tracking-[0.3em] text-[10px]">Scroll</span>
                <div className="w-[1px] h-16 bg-white/50" />
            </motion.div>
        </section>
    );
}
