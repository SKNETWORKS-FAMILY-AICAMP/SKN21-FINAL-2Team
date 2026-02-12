"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Heart, Trophy, Sparkles } from "lucide-react";
import { fetchCurrentUser, fetchPrefers, logoutApi, PreferItem, updateCurrentUser } from "@/services/api";
import Link from "next/link";

type DbPreferType = "actor" | "movie" | "drama" | "celeb" | "variety";
type StaticType = "travel" | "dog" | "vegan";
type Category = DbPreferType | StaticType;

const dbTypes: DbPreferType[] = ["actor", "movie", "drama", "celeb", "variety"];
const defaultCategories: Category[] = ["actor", "movie", "drama", "celeb", "variety", "travel", "dog", "vegan"];

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

const staticOptions: Record<StaticType, { key: string; label: string }[]> = {
  travel: [
    { key: "a", label: "자연/트레킹" },
    { key: "b", label: "도시/미식" },
  ],
  dog: [
    { key: "a", label: "반려견 동행 필수" },
    { key: "b", label: "반려견 미동반" },
  ],
  vegan: [
    { key: "a", label: "비건 선호" },
    { key: "b", label: "상관없음" },
  ],
};

const randomInt = (min: number, max: number) => Math.floor(Math.random() * (max - min + 1)) + min;

const samplePreferOptions = (items: PreferItem[], selectedId?: number | null): PreferItem[] => {
  if (items.length <= 4) return items;

  const pool = [...items];
  for (let i = pool.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }

  const size = randomInt(2, 4);
  const picked = pool.slice(0, size);

  if (selectedId && !picked.some((v) => v.id === selectedId)) {
    const selected = items.find((v) => v.id === selectedId);
    if (selected) picked[0] = selected;
  }
  return picked;
};

export default function PreferenceSurveyPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [categories, setCategories] = useState<Category[]>(defaultCategories);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [preferOptions, setPreferOptions] = useState<Record<DbPreferType, PreferItem[]>>({
    actor: [],
    movie: [],
    drama: [],
    celeb: [],
    variety: [],
  });
  const [selectedPreferIds, setSelectedPreferIds] = useState<Record<DbPreferType, number | null>>({
    actor: null,
    movie: null,
    drama: null,
    celeb: null,
    variety: null,
  });
  const [staticAnswers, setStaticAnswers] = useState<Record<StaticType, string>>({
    travel: "",
    dog: "",
    vegan: "",
  });

  const current = categories[step];
  const total = categories.length;

  const logoutAndGoHome = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("chat_room_id");
    }
    logoutApi();
    router.replace("/");
  };

  useEffect(() => {
    const load = async () => {
      try {
        const [user, ...preferLists] = await Promise.all([
          fetchCurrentUser(),
          ...dbTypes.map((t) => fetchPrefers(t)),
        ]);

        const selectedFromUser: Record<DbPreferType, number | null> = {
          actor: user.actor_prefer_id ?? null,
          movie: user.movie_prefer_id ?? null,
          drama: user.drama_prefer_id ?? null,
          celeb: user.celeb_prefer_id ?? null,
          variety: user.variety_prefer_id ?? null,
        };
        setSelectedPreferIds(selectedFromUser);

        const optionsByType = dbTypes.reduce((acc, type, idx) => {
          acc[type] = samplePreferOptions(preferLists[idx], selectedFromUser[type]);
          return acc;
        }, {} as Record<DbPreferType, PreferItem[]>);
        setPreferOptions(optionsByType);
        const availableDbTypes = dbTypes.filter((type) => optionsByType[type].length > 0);
        setCategories([...availableDbTypes, "travel", "dog", "vegan"]);

        setStaticAnswers({
          travel: user.with_yn === null || user.with_yn === undefined ? "" : user.with_yn ? staticOptions.travel[0].label : staticOptions.travel[1].label,
          dog: user.dog_yn === null || user.dog_yn === undefined ? "" : user.dog_yn ? staticOptions.dog[0].label : staticOptions.dog[1].label,
          vegan: user.vegan_yn === null || user.vegan_yn === undefined ? "" : user.vegan_yn ? staticOptions.vegan[0].label : staticOptions.vegan[1].label,
        });
      } catch (error) {
        console.error("선호도 데이터를 불러오지 못했습니다:", error);
        logoutAndGoHome();
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const currentOptions = useMemo(() => {
    if (dbTypes.includes(current as DbPreferType)) {
      return (preferOptions[current as DbPreferType] || []).map((item, idx) => ({
        key: `db-${item.id}`,
        label: item.value || "-",
        preferId: item.id,
        badge: String.fromCharCode(65 + idx),
      }));
    }

    return staticOptions[current as StaticType].map((item, idx) => ({
      key: item.key,
      label: item.label,
      badge: String.fromCharCode(65 + idx),
    }));
  }, [current, preferOptions]);

  const selectedLabel = useMemo(() => {
    if (dbTypes.includes(current as DbPreferType)) {
      const selectedId = selectedPreferIds[current as DbPreferType];
      const selected = preferOptions[current as DbPreferType].find((v) => v.id === selectedId);
      return selected?.value || "";
    }
    return staticAnswers[current as StaticType] || "";
  }, [current, preferOptions, selectedPreferIds, staticAnswers]);

  const isCategoryAnswered = (category: Category) => {
    if (dbTypes.includes(category as DbPreferType)) {
      return selectedPreferIds[category as DbPreferType] !== null;
    }
    return !!staticAnswers[category as StaticType];
  };

  const isComplete = categories.every((category) => isCategoryAnswered(category));
  const isLast = step === total - 1;

  const handlePick = (label: string, preferId?: number) => {
    if (dbTypes.includes(current as DbPreferType)) {
      const dbType = current as DbPreferType;
      if (preferId !== undefined) {
        setSelectedPreferIds((prev) => ({ ...prev, [dbType]: preferId }));
      }
    } else {
      const staticType = current as StaticType;
      setStaticAnswers((prev) => ({ ...prev, [staticType]: label }));
    }

    if (step < total - 1) {
      setStep((s) => s + 1);
    }
  };

  const handleBack = () => setStep((s) => Math.max(0, s - 1));

  const handleFinish = async () => {
    setSaveError(null);
    if (!isComplete) {
      setSaveError("모든 항목을 선택한 뒤 완료할 수 있습니다.");
      return;
    }

    const payload = {
      actor_prefer_id: selectedPreferIds.actor,
      movie_prefer_id: selectedPreferIds.movie,
      drama_prefer_id: selectedPreferIds.drama,
      celeb_prefer_id: selectedPreferIds.celeb,
      variety_prefer_id: selectedPreferIds.variety,
      with_yn: staticAnswers.travel === staticOptions.travel[0].label,
      dog_yn: staticAnswers.dog === staticOptions.dog[0].label,
      vegan_yn: staticAnswers.vegan === staticOptions.vegan[0].label,
      is_prefer: true,
    };

    try {
      setSaving(true);
      await updateCurrentUser(payload);
      router.push("/chatbot");
    } catch (error) {
      console.error("선호도 저장 실패:", error);
      setSaveError("선호도 저장에 실패했습니다. 다시 시도해 주세요.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50 via-white to-slate-100">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-6 py-12">
        <header className="mb-6 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-lg font-semibold text-slate-800 hover:text-indigo-600">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            Polaris
          </Link>
        </header>
        {loading && <p className="mb-4 text-sm text-slate-500">기존 선호도를 불러오는 중...</p>}
        {saveError && <p className="mb-4 text-sm text-rose-600">{saveError}</p>}
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
              <h1 className="mt-2 text-3xl font-bold text-slate-900">더 끌리는 항목을 선택하세요</h1>
              <p className="mt-2 text-sm text-slate-600">선택할 때마다 챗봇이 더 똑똑해집니다.</p>

              <div className="mt-8 grid gap-4 md:grid-cols-2">
                {currentOptions.map((option) => {
                  const isSelected = option.label === selectedLabel;
                  return (
                    <button
                      key={option.key}
                      onClick={() => handlePick(option.label, option.preferId)}
                      className={`group relative overflow-hidden rounded-2xl border p-6 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-lg ${
                        isSelected ? "border-indigo-400 bg-indigo-50/80" : "border-slate-200 bg-gradient-to-br from-white to-slate-50"
                      }`}
                    >
                      {isSelected && (
                        <span className="absolute right-3 top-3 rounded-full bg-indigo-600 px-2 py-1 text-[10px] font-semibold text-white">
                          선택됨
                        </span>
                      )}
                      <div className="absolute inset-0 opacity-0 group-hover:opacity-100">
                        <div className="h-full w-full bg-gradient-to-br from-indigo-50 via-white to-sky-50" />
                      </div>
                      <div className="relative flex items-start gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 text-indigo-600">{option.badge}</div>
                        <div className="min-w-0 flex-1">
                          <p className="text-lg font-semibold text-slate-900 break-words">{option.label}</p>
                          <p className="mt-1 text-xs text-slate-500">선택하면 바로 다음 단계로 이동합니다.</p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>

              <div className="mt-10 flex items-center gap-3 text-sm text-slate-500">
                <div className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-slate-700">
                  <Heart className="h-4 w-4 text-rose-500" />
                  <span className="whitespace-nowrap overflow-hidden text-ellipsis">이미 선택한 항목: {selectedLabel || "없음"}</span>
                </div>
              </div>
            </div>

            <div className="flex flex-col justify-between border-t border-slate-100 bg-slate-50/80 p-6 md:border-l md:border-t-0">
              <div className="space-y-4">
                <p className="text-sm font-semibold text-slate-700">진행 상황</p>
                <div className="flex flex-wrap gap-2">
                  {categories.map((category, idx) => (
                    <button
                      key={category}
                      type="button"
                      onClick={() => setStep(idx)}
                      className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                        idx === step
                          ? "bg-indigo-600 text-white"
                          : isCategoryAnswered(category)
                            ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
                            : "bg-slate-200 text-slate-600 hover:bg-slate-300"
                      }`}
                    >
                      {categoryLabels[category]}
                    </button>
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
                    disabled={saving || loading || !isComplete}
                    className="flex items-center gap-2 rounded-full bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-md shadow-indigo-200 hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    {saving ? "저장 중..." : "완료하고 챗봇으로"} <ChevronRight className="h-4 w-4" />
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
