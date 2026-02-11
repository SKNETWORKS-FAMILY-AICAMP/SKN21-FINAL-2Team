"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Heart, Trophy, Sparkles } from "lucide-react";
import { fetchCurrentUser, updateCurrentUser, logoutApi } from "@/services/api";
import Link from "next/link";

type Category = "actor" | "movie" | "drama" | "celeb" | "variety" | "travel" | "dog" | "vegan";

const categoryLabels: Record<Category, string> = {
  actor: "배우",
  movie: "영화",
  drama: "드라마",
  celeb: "셀럽",
  variety: "예능",
  travel: "여행 스타일",
  dog: "반려견 동행",
  vegan: "비건 음식",
};

const mockOptions: Record<Category, { a: string; b: string }> = {
  actor: { a: "마동석", b: "송강" },
  movie: { a: "어벤져스", b: "라라랜드" },
  drama: { a: "더 글로리", b: "응답하라" },
  celeb: { a: "아이유", b: "정해인" },
  variety: { a: "나혼산", b: "런닝맨" },
  travel: { a: "자연/트레킹", b: "도시/미식" },
  dog: { a: "반려견 동행 필수", b: "반려견 미동반" },
  vegan: { a: "비건 선호", b: "상관없음" },
};

export default function PreferenceSurveyPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<Category, string>>({
    actor: "",
    movie: "",
    drama: "",
    celeb: "",
    variety: "",
    travel: "",
    dog: "",
    vegan: "",
  });
  const [loading, setLoading] = useState(true);
  const [lastPicked, setLastPicked] = useState("");
  const logoutAndGoHome = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("chat_room_id");
    }
    logoutApi();
    router.replace("/");
  };

  const categories = useMemo(() => Object.keys(categoryLabels) as Category[], []);
  const current = categories[step];
  const total = categories.length;
  const { a, b } = mockOptions[current];

  // Load existing user prefer flags
  useEffect(() => {
    const load = async () => {
      try {
        const user = await fetchCurrentUser();
        setAnswers((prev) => {
          const next = {
            ...prev,
            dog: user.dog_yn ? mockOptions.dog.a : user.dog_yn === false ? mockOptions.dog.b : prev.dog,
            vegan: user.vegan_yn ? mockOptions.vegan.a : user.vegan_yn === false ? mockOptions.vegan.b : prev.vegan,
          };
          return next;
        });
        setLastPicked((prev) => {
          const candidate = user.dog_yn !== null && user.dog_yn !== undefined
            ? (user.dog_yn ? mockOptions.dog.a : mockOptions.dog.b)
            : prev;
          return candidate || prev;
        });
      } catch (error) {
        console.error("사용자 정보를 불러오지 못했습니다:", error);
        logoutAndGoHome();
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handlePick = (choice: string) => {
    setAnswers((prev) => ({ ...prev, [current]: choice }));
    setLastPicked(choice);
    if (step < total - 1) {
      setStep((s) => s + 1);
    }
  };

  const handleBack = () => setStep((s) => Math.max(0, s - 1));

  const handleFinish = async () => {
    const dog_yn = answers.dog === mockOptions.dog.a; // 반려견 동행 필수
    const vegan_yn = answers.vegan === mockOptions.vegan.a; // 비건 선호

    // TODO: actor/movie/etc.는 추후 prefer_id로 매핑 필요
    const payload = {
      dog_yn,
      vegan_yn,
      is_prefer: true,
    };

    try {
      await updateCurrentUser(payload);
    } catch (error) {
      console.error("선호도 저장 실패:", error);
      logoutAndGoHome();
    } finally {
      router.push("/chatbot");
    }
  };

  const isLast = step === total - 1;

  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50 via-white to-slate-100">
      <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-12">
        <header className="mb-6 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-lg font-semibold text-slate-800 hover:text-indigo-600">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            Polaris
          </Link>
          <Link href="/" className="text-sm text-slate-500 hover:text-indigo-600">홈으로</Link>
        </header>
        {loading && <p className="text-sm text-slate-500 mb-4">기존 선호도를 불러오는 중...</p>}
        <header className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-indigo-700">
            <Trophy className="h-5 w-5" /> 취향 월드컵
          </div>
          <p className="text-sm text-slate-500">
            {step + 1} / {total}
          </p>
        </header>

        <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-indigo-50">
          <div className="grid gap-0 md:grid-cols-[1.2fr_0.8fr]">
            <div className="p-8 md:p-12">
              <p className="text-sm font-medium text-indigo-600">{categoryLabels[current]}</p>
              <h1 className="mt-2 text-3xl font-bold text-slate-900">더 끌리는 쪽을 선택하세요</h1>
              <p className="mt-2 text-sm text-slate-600">선택할 때마다 챗봇이 더 똑똑해집니다.</p>

              <div className="mt-8 grid gap-4 md:grid-cols-2">
                {[{ key: "a", label: a }, { key: "b", label: b }].map(({ key, label }) => (
                  <button
                    key={key}
                    onClick={() => handlePick(label)}
                    className={`group relative overflow-hidden rounded-2xl border p-6 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-lg ${
                      answers[current] === label
                        ? "border-indigo-400 bg-indigo-50/80"
                        : "border-slate-200 bg-gradient-to-br from-white to-slate-50"
                    }`}
                  >
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100">
                      <div className="h-full w-full bg-gradient-to-br from-indigo-50 via-white to-sky-50" />
                    </div>
                    <div className="relative flex items-start gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 text-indigo-600">{key === "a" ? "A" : "B"}</div>
                      <div>
                        <p className="text-lg font-semibold text-slate-900">{label}</p>
                        <p className="mt-1 text-xs text-slate-500">선택하면 바로 다음 매치로 이동합니다.</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              <div className="mt-10 flex items-center gap-3 text-sm text-slate-500">
                <div className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-slate-700">
                  <Heart className="h-4 w-4 text-rose-500" />
                  이미 선택한 항목: {answers[current] || lastPicked || "없음"}
                </div>
              </div>
            </div>

            <div className="flex flex-col justify-between border-t border-slate-100 bg-slate-50/80 p-6 md:border-l md:border-t-0">
              <div className="space-y-4">
                <p className="text-sm font-semibold text-slate-700">진행 상황</p>
                <div className="flex flex-wrap gap-2">
                  {categories.map((c, idx) => (
                    <span
                      key={c}
                      className={`rounded-full px-3 py-1 text-xs font-semibold transition ${idx === step
                        ? "bg-indigo-600 text-white"
                        : answers[c]
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-slate-200 text-slate-600"}`}
                    >
                      {categoryLabels[c]}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between gap-3">
                <button
                  onClick={handleBack}
                  disabled={step === 0}
                  className="flex items-center gap-1 rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <ChevronLeft className="h-4 w-4" /> 이전
                </button>
                {isLast ? (
                  <button
                    onClick={handleFinish}
                    className="flex items-center gap-2 rounded-full bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-md shadow-indigo-200 hover:bg-indigo-700"
                  >
                    완료하고 챗봇으로 <ChevronRight className="h-4 w-4" />
                  </button>
                ) : (
                  <button
                    onClick={() => setStep((s) => Math.min(total - 1, s + 1))}
                    className="flex items-center gap-2 rounded-full bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-md shadow-indigo-200 hover:bg-indigo-700"
                  >
                    다음 <ChevronRight className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
