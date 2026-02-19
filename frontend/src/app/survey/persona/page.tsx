"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Check } from "lucide-react";
import { useRouter } from "next/navigation";

const QUESTIONS = [
    {
        id: 1,
        title: "What's your travel vibe?",
        description: "Choose the atmosphere you want to immerse yourself in.",
        options: [
            { id: "tradition", label: "Timeless Tradition", image: "https://images.unsplash.com/photo-1652172176229-d527bb17af68?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxTZW91bCUyMEJ1a2Nob24lMjBIYW5vayUyMHZpbGxhZ2UlMjBtb2Rlcm4lMjBjb250cmFzdHxlbnwxfHx8fDE3NzE0ODE4Mjd8MA&ixlib=rb-4.1.0&q=80&w=1080" },
            { id: "modern", label: "Modern Energy", image: "https://images.unsplash.com/photo-1763141711469-32db51fa2e17?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxTZW91bCUyMERvbmdkYWVtdW4lMjBEZXNpZ24lMjBQbGF6YSUyMGZ1dHVyaXN0aWMlMjBhcmNoaXRlY3R1cmUlMjBkeW5hbWljfGVufDF8fHx8MTc3MTQ4MTM1N3ww&ixlib=rb-4.1.0&q=80&w=1080" },
        ],
    },
    {
        id: 2,
        title: "What are you craving?",
        description: "Pick your flavor of Seoul.",
        options: [
            { id: "food", label: "Street Food & Cafes", image: "https://images.unsplash.com/photo-1692103675608-6e635afa077b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxLb3JlYW4lMjBzdHJlZXQlMjBmb29kJTIwdHRlb2tib2traSUyMGFlc3RoZXRpY3xlbnwxfHx8fDE3NzE0ODE4MjZ8MA&ixlib=rb-4.1.0&q=80&w=1080" },
            { id: "kpop", label: "K-Pop & Culture", image: "https://images.unsplash.com/photo-1760539618919-5516b979bab4?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxLLXBvcCUyMHN0eWxlJTIwY29uY2VydCUyMGNyb3dkJTIwbGlnaHRzdGljayUyMGFlc3RoZXRpY3xlbnwxfHx8fDE3NzE0ODE4MjZ8MA&ixlib=rb-4.1.0&q=80&w=1080" },
        ],
    },
    {
        id: 3,
        title: "How do you want to relax?",
        description: "Find your perfect healing spot.",
        options: [
            { id: "nature", label: "Nature & Hiking", image: "https://images.unsplash.com/photo-1440190727617-48b9b2c7e24b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxTZW91bCUyMEJ1a2hhbnNhbiUyMG1vdW50YWluJTIwY2l0eSUyMHZpZXclMjBjb250cmFzdHxlbnwxfHx8fDE3NzE0ODEzNTd8MA&ixlib=rb-4.1.0&q=80&w=1080" },
            { id: "river", label: "Han River Picnic", image: "https://images.unsplash.com/photo-1612794794535-210c45928c5f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxTZW91bCUyMEhhbiUyMHJpdmVyJTIwcGljbmljJTIwc3Vuc2V0JTIwY2FsbXxlbnwxfHx8fDE3NzE0ODE4Mjd8MA&ixlib=rb-4.1.0&q=80&w=1080" },
        ],
    },
];

export default function PersonaSurveyPage() {
    const router = useRouter();
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [direction, setDirection] = useState(0);

    const handleSelect = () => {
        if (currentQuestionIndex < QUESTIONS.length - 1) {
            setDirection(1);
            setCurrentQuestionIndex((prev) => prev + 1);
        } else {
            router.push("/chatbot");
        }
    };

    const currentQuestion = QUESTIONS[currentQuestionIndex];

    return (
        <div className="min-h-screen w-full bg-white flex flex-col items-center justify-center p-6 relative overflow-hidden">
            {/* Progress Bar */}
            <div className="absolute top-10 left-0 w-full px-8 md:px-20 lg:px-40 flex gap-2 z-20">
                {QUESTIONS.map((_, idx) => (
                    <div key={idx} className="h-1 flex-1 bg-gray-100 rounded-full overflow-hidden">
                        <motion.div
                            className="h-full bg-black"
                            initial={{ width: "0%" }}
                            animate={{ width: idx <= currentQuestionIndex ? "100%" : "0%" }}
                            transition={{ duration: 0.5, ease: "easeInOut" }}
                        />
                    </div>
                ))}
            </div>

            <AnimatePresence mode="wait" custom={direction}>
                <motion.div
                    key={currentQuestion.id}
                    initial={{ opacity: 0, x: direction * 50 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: direction * -50 }}
                    transition={{ duration: 0.4, ease: "easeOut" }}
                    className="w-full max-w-5xl flex flex-col items-center"
                >
                    <div className="text-center mb-12">
                        <span className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 block">
                            Question {currentQuestion.id} of {QUESTIONS.length}
                        </span>
                        <h2 className="text-3xl md:text-4xl font-serif font-light text-gray-900 mb-3">
                            {currentQuestion.title}
                        </h2>
                        <p className="text-gray-500 font-light">{currentQuestion.description}</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                        {currentQuestion.options.map((option) => (
                            <button
                                key={option.id}
                                onClick={handleSelect}
                                className="group relative h-[400px] rounded-2xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-4"
                            >
                                <div className="absolute inset-0 bg-gray-200">
                                    <img
                                        src={option.image}
                                        alt={option.label}
                                        className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105 filter grayscale-[10%] group-hover:grayscale-0"
                                    />
                                </div>
                                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-60 group-hover:opacity-80 transition-opacity duration-500" />
                                <div className="absolute bottom-0 left-0 w-full p-8 flex items-end justify-between">
                                    <div className="text-left">
                                        <h3 className="text-2xl font-bold text-white mb-1 drop-shadow-md">{option.label}</h3>
                                        <div className="h-0.5 w-0 bg-white group-hover:w-full transition-all duration-500 ease-out" />
                                    </div>
                                    <div className="w-10 h-10 rounded-full bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                                        <ArrowRight className="text-white" size={18} />
                                    </div>
                                </div>
                                <div className="absolute top-6 right-6 w-8 h-8 rounded-full border-2 border-white/30 flex items-center justify-center group-hover:border-white group-hover:bg-white transition-all duration-300">
                                    <Check size={14} className="text-black opacity-0 group-hover:opacity-100 transition-opacity" />
                                </div>
                            </button>
                        ))}
                    </div>
                </motion.div>
            </AnimatePresence>
        </div>
    );
}
