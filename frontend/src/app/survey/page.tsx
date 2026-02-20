"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { fetchPrefers, PreferItem, updateCurrentUser } from "@/services/api";

type QuestionType = {
    id: string; // 'plan', 'member' ...
    title: string;
    description: string;
    options: PreferItem[];
};

const QUESTION_METADATA: Record<string, { title: string; description: string }> = {
    plan: { title: "Travel Style", description: "How do you plan your trips?" },
    member: { title: "Companions", description: "Who are you traveling with?" },
    transport: { title: "Transportation", description: "Preferred way to move around?" },
    age: { title: "Age Group", description: "Who is in your group?" },
    vibe: { title: "Vibe", description: "What kind of atmosphere do you prefer?" },
    movie: { title: "Movies", description: "Favorite movie genre?" },
    drama: { title: "Dramas", description: "Favorite drama genre?" },
    variety: { title: "Variety Shows", description: "Favorite variety show type?" },
};

// Order of questions
const QUESTION_ORDER = ["plan", "member", "transport", "age", "vibe", "movie", "drama", "variety"];

export default function PersonaSurveyPage() {
    const router = useRouter();
    const [questions, setQuestions] = useState<QuestionType[]>([]);
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [direction, setDirection] = useState(0);
    const [answers, setAnswers] = useState<Record<string, number>>({});

    useEffect(() => {
        fetchPrefers().then((items) => {
            // Group by type
            const grouped: Record<string, PreferItem[]> = {};
            items.forEach((item) => {
                if (item.type) {
                    if (!grouped[item.type]) grouped[item.type] = [];
                    grouped[item.type].push(item);
                }
            });

            // Construct questions based on order
            const loadedQuestions: QuestionType[] = [];
            QUESTION_ORDER.forEach((type) => {
                if (grouped[type]) {
                    loadedQuestions.push({
                        id: type,
                        title: QUESTION_METADATA[type]?.title || type,
                        description: QUESTION_METADATA[type]?.description || "",
                        options: grouped[type],
                    });
                }
            });
            setQuestions(loadedQuestions);
        }).catch(err => console.error("Failed to fetch prefers:", err));
    }, []);

    const handleSelect = async (optionId: number) => {
        const currentQ = questions[currentQuestionIndex];
        const newAnswers = { ...answers, [currentQ.id]: optionId };
        setAnswers(newAnswers);

        if (currentQuestionIndex < questions.length - 1) {
            setDirection(1);
            setCurrentQuestionIndex((prev) => prev + 1);
        } else {
            // Submit all answers
            try {
                // Map answers to API payload keys (e.g., plan -> plan_prefer_id)
                const payload: any = { is_prefer: true };
                Object.entries(newAnswers).forEach(([type, id]) => {
                    payload[`${type}_prefer_id`] = id;
                });

                await updateCurrentUser(payload);
                router.push("/chatbot");
            } catch (e) {
                console.error("Failed to submit survey:", e);
                alert("Failed to save preferences.");
            }
        }
    };

    if (questions.length === 0) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;

    const currentQuestion = questions[currentQuestionIndex];

    return (
        <div className="min-h-screen w-full bg-white flex flex-col items-center justify-center p-6 relative overflow-hidden">
            {/* Progress Bar */}
            <div className="absolute top-10 left-0 w-full px-8 md:px-20 lg:px-40 flex gap-2 z-20">
                {questions.map((_, idx) => (
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
                            Question {currentQuestionIndex + 1} of {questions.length}
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
                                onClick={() => handleSelect(option.id)}
                                className="group relative h-[400px] rounded-2xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-4"
                            >
                                <div className="absolute inset-0 bg-gray-200">
                                    <img
                                        src={option.image_path || ""}
                                        alt={option.value || ""}
                                        className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105 filter grayscale-[10%] group-hover:grayscale-0"
                                    />
                                </div>
                                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-60 group-hover:opacity-80 transition-opacity duration-500" />
                                <div className="absolute bottom-0 left-0 w-full p-8 flex items-end justify-between">
                                    <div className="text-left">
                                        <h3 className="text-2xl font-bold text-white mb-1 drop-shadow-md">{option.value}</h3>
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

