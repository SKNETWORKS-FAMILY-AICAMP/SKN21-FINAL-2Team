"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Check, ArrowLeft, LogOut } from "lucide-react";
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
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const [isCompleted, setIsCompleted] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

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
            // 마지막 문항 선택 시 처리
            setIsSubmitting(true);
            try {
                await submitSurvey(newAnswers);
                // 주의: DB 저장이 완료되면 즉시 라우팅하지 않고 완료 화면을 띄웁니다.
                setIsCompleted(true);
                setDirection(1); // 애니메이션용 방향 설정
            } catch (e) {
                console.error("Failed to submit survey:", e);
                alert("Failed to save preferences.");
            } finally {
                setIsSubmitting(false);
            }
        }
    };

    const handleFinalizeSignup = () => {
        // 완료 화면에서 'Signup' 버튼을 눌렀을 때의 동작
        const pending = localStorage.getItem("pendingDestination");
        if (pending) {
            router.push("/chatbot?fromDestination=1");
        } else {
            router.push("/explore");
        }
    };

    const handlePrevious = () => {
        if (currentQuestionIndex > 0) {
            setDirection(-1);
            setCurrentQuestionIndex((prev) => prev - 1);
        }
    };

    const handleProgressClick = (idx: number) => {
        if (idx === currentQuestionIndex) return;

        // 주의: 사용자가 풀지 않은 미래의 질문으로 건너뛰는 것을 방지합니다. 
        // 응답을 완료한 개수(Object.keys(answers).length)까지만 클릭 가능하게 막습니다.
        if (idx > Object.keys(answers).length) return;

        setDirection(idx > currentQuestionIndex ? 1 : -1);
        setCurrentQuestionIndex(idx);
    };

    const handleLogout = () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("profile_picture");
        localStorage.removeItem("user_name");
        localStorage.removeItem("user_email");
        router.replace("/signup");
    };

    if (questions.length === 0) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;

    const currentQuestion = questions[currentQuestionIndex];

    return (
        <div className="min-h-screen w-full bg-white flex flex-col items-center justify-center p-6 relative overflow-hidden">
            {/* Progress Bar */}
            <div className="absolute top-10 left-0 w-full px-14 md:px-24 lg:px-40 flex gap-2 z-20">
                {questions.map((_, idx) => {
                    // 아직 도달하지 못한(응답하지 않은) 항목은 비활성화 처리
                    const isClickable = idx <= Object.keys(answers).length;

                    return (
                        <button
                            key={idx}
                            onClick={() => handleProgressClick(idx)}
                            disabled={!isClickable}
                            // 주의: 사용자가 마우스로 쉽게 클릭할 수 있도록 기존 h-1에서 클릭 영역을 높이기 위해 h-2로 변경했습니다.
                            className={`h-2 flex-1 rounded-full overflow-hidden transition-all ${isClickable ? 'cursor-pointer hover:opacity-75' : 'cursor-not-allowed opacity-50'} bg-gray-200`}
                            aria-label={`${idx + 1}번째 질문으로 이동`}
                        >
                            <motion.div
                                className="h-full bg-black"
                                initial={{ width: "0%" }}
                                animate={{ width: idx <= currentQuestionIndex ? "100%" : "0%" }}
                                transition={{ duration: 0.5, ease: "easeInOut" }}
                            />
                        </button>
                    )
                })}
            </div>

            <AnimatePresence mode="wait" custom={direction}>
                {isCompleted ? (
                    // 설문 완료 후 렌더링될 '가입 완료' 화면
                    <motion.div
                        key="completed"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.5, ease: "easeOut" }}
                        className="w-full max-w-2xl flex flex-col items-center justify-center text-center py-20"
                    >
                        <div className="w-20 h-20 bg-black text-white rounded-full flex items-center justify-center mb-8 shadow-lg">
                            <Check size={40} />
                        </div>
                        <h2 className="text-3xl md:text-4xl font-semibold text-gray-900 mb-4">
                            You're all set!
                        </h2>
                        <p className="text-gray-500 font-normal mb-12 text-lg">
                            회원가입 및 취향 분석이 완료되었습니다. <br className="hidden md:block" />
                            이제 맞춤형 여행 추천을 시작해 보세요.
                        </p>

                        <button
                            onClick={handleFinalizeSignup}
                            // 주의: 사용자의 피드백에 맞춰 시각적으로 가입이 완료되는 느낌을 주기 위해 버튼명을 SignUp으로 설정했습니다.
                            className="w-full sm:w-auto px-12 py-4 bg-black text-white text-lg font-semibold rounded-full hover:bg-gray-800 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 flex items-center justify-center gap-2"
                        >
                            Sign Up <ArrowRight size={20} />
                        </button>
                    </motion.div>
                ) : (
                    // 기존 질문 화면
                    <motion.div
                        key={currentQuestion.id}
                        initial={{ opacity: 0, x: direction * 50 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: direction * -50 }}
                        transition={{ duration: 0.4, ease: "easeOut" }}
                        className="w-full max-w-5xl flex flex-col items-center"
                    >
                        <div className="w-full relative flex items-center justify-center mb-12 min-h-[100px]">
                            <div className="text-center">
                                <span className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 block">
                                    Question {currentQuestionIndex + 1} of {questions.length}
                                </span>
                                <h2 className="text-3xl md:text-4xl font-semibold text-gray-900 mb-3">
                                    {currentQuestion.title}
                                </h2>
                                <p className="text-gray-500 font-normal">{currentQuestion.description}</p>
                            </div>

                            {/* 텍스트 우측 '이전' 영역 */}
                            {currentQuestionIndex > 0 && (
                                <button
                                    onClick={handlePrevious}
                                    // 주의: 텍스트 블록의 정렬을 해치지 않으면서 우측 끝에 배치하기 위해 absolute right-0를 사용했습니다.
                                    className="absolute right-0 md:right-4 flex items-center gap-2 p-3 px-4 text-gray-600 bg-white border border-gray-200 shadow-sm hover:shadow-md hover:text-black hover:bg-gray-50 rounded-full transition-all"
                                    aria-label="이전 문항으로 돌아가기"
                                >
                                    <span className="text-sm font-semibold hidden sm:block">이전</span>
                                    <ArrowLeft size={20} />
                                </button>
                            )}
                        </div>

                        <div className={`grid gap-6 w-full ${currentQuestion.options.length === 3 ? 'grid-cols-3' : 'grid-cols-2'}`}>
                            {currentQuestion.options.map((option) => (
                                <button
                                    key={option.value}
                                    onClick={() => handleSelect(option.value, questions[currentQuestionIndex].id)}
                                    disabled={isSubmitting}
                                    className={`group relative h-[400px] rounded-2xl overflow-hidden border border-gray-100 shadow-sm transition-all duration-500 focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-4 ${isSubmitting ? 'opacity-70 cursor-wait' : 'hover:shadow-2xl transform hover:-translate-y-1'}`}
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
                                    </div>
                                    <div className="absolute top-6 right-6 w-8 h-8 rounded-full border-2 border-white/30 flex items-center justify-center group-hover:border-white group-hover:bg-white transition-all duration-300">
                                        <Check size={14} className="text-black opacity-0 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                </button>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* 하단 로그아웃 버튼 영역 */}
            {!isCompleted && (
                <div className="absolute w-full bottom-8 flex justify-center z-10">
                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-1.5 text-[12px] font-medium text-gray-400 hover:text-gray-600 transition-colors bg-white/50 px-4 py-2 rounded-full backdrop-blur-sm shadow-sm"
                    >
                        <LogOut size={14} />
                        다른 구글 계정으로 로그인하기
                    </button>
                </div>
            )}
        </div>
    );
}
