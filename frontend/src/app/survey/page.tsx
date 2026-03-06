"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Check, ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { fetchPrefers, PreferItem, submitSurvey } from "@/services/api";

type QuestionType = {
    id: string; // 'plan', 'member' ...
    title: string;
    description: string;
    options: PreferItem[];
};

const QUESTION_METADATA: Record<string, { title: string; description: string }> = {
    plan_prefer: { title: "Travel Schedule", description: "How do you like to plan your trip?" },
    vibe_prefer: { title: "Travel Vibe", description: "What kind of destination do you prefer?" },
    places_prefer: { title: "Interests", description: "What are you most excited to explore?" },
};

// Order of questions
const QUESTION_ORDER = ["plan_prefer", "vibe_prefer", "places_prefer"];

// 선택지 value → 이미지 경로 매핑
const IMAGE_MAP: Record<string, string> = {
    "빽빽한 일정": "/image/planning.jpg",
    "느슨한 일정": "/image/noplan.png",
    "붐비는 도시": "/image/crowded.jpg",
    "한적한 자연": "/image/lonely.jpg",
    "맛집": "/image/kfood.jpg",
    "역사적 명소": "/image/khistorical.jpg",
    "K-culture": "/image/kculture.png",
};

export default function PersonaSurveyPage() {
    const router = useRouter();
    const [questions, setQuestions] = useState<QuestionType[]>([]);
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [direction, setDirection] = useState(0);
    const [answers, setAnswers] = useState<Record<string, string>>({})

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
        }).catch(err => {
            console.error("Failed to fetch prefers:", err);
            if (err.message === 'Unauthorized' || err.message === 'Session expired') {
                alert("로그인이 필요하거나 세션이 만료되었습니다. 다시 로그인해주세요.");
                router.push("/signup"); // 로그인 페이지로 이동
            }
        });
    }, [router]);

    const handleSelect = async (optionValue: string, optionType: string) => {
        const newAnswers = { ...answers, [optionType]: optionValue };
        setAnswers(newAnswers);

        if (currentQuestionIndex < questions.length - 1) {
            setDirection(1);
            setCurrentQuestionIndex((prev) => prev + 1);
        } else {
            try {
                await submitSurvey(newAnswers);

                // 주의: Destinations에서 챗봇 플로우를 위해 선택된 장소가 있다면 그곳으로 넘깁니다.
                const pending = localStorage.getItem("pendingDestination");
                if (pending) {
                    router.push("/chatbot?fromDestination=1");
                } else {
                    router.push("/explore");
                }
            } catch (e) {
                console.error("Failed to submit survey:", e);
                alert("Failed to save preferences.");
            }
        }
    };

    const handlePrevious = () => {
        if (currentQuestionIndex > 0) {
            setDirection(-1);
            setCurrentQuestionIndex((prev) => prev - 1);
        }
    };


    if (questions.length === 0) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;

    const currentQuestion = questions[currentQuestionIndex];

    return (
        <div className="min-h-screen w-full bg-white flex flex-col items-center justify-center p-6 relative overflow-hidden">
            {/* Back Button */}
            {currentQuestionIndex > 0 && (
                <button
                    onClick={handlePrevious}
                    // 주의: 절대 위치(absolute)를 사용해 프로그레스 바 영역과 겹치지 않게 왼쪽 상단에 배치합니다.
                    className="absolute top-8 left-2 md:top-8 md:left-6 lg:left-12 z-30 p-2 text-gray-400 hover:text-black hover:bg-gray-100 rounded-full transition-all"
                    aria-label="이전 문항으로 돌아가기"
                >
                    <ArrowLeft size={24} />
                </button>
            )}

            {/* Progress Bar */}
            <div className="absolute top-10 left-0 w-full px-14 md:px-24 lg:px-40 flex gap-2 z-20">
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
                        <h2 className="text-3xl md:text-4xl font-semibold text-gray-900 mb-3">
                            {currentQuestion.title}
                        </h2>
                        <p className="text-gray-500 font-normal">{currentQuestion.description}</p>
                    </div>

                    <div className={`grid gap-6 w-full ${currentQuestion.options.length === 3 ? 'grid-cols-3' : 'grid-cols-2'}`}>
                        {currentQuestion.options.map((option) => (
                            <button
                                key={option.value}
                                onClick={() => handleSelect(option.value, questions[currentQuestionIndex].id)}
                                className="group relative h-[400px] rounded-2xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-4"
                            >
                                <div className="absolute inset-0">
                                    <img
                                        src={IMAGE_MAP[option.value] ?? "/image/noplan.png"}
                                        alt={option.value}
                                        className="w-full h-full object-cover"
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

