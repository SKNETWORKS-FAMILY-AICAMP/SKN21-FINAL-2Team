"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { fetchCurrentUser, fetchPrefers, PreferItem, updateCurrentUser, UserProfile } from "@/services/api";
import { Sparkles } from "lucide-react";

const allowedGenders = ["male", "female", "other"] as const;
type Gender = (typeof allowedGenders)[number];

export default function MyPage() {
  const [name, setName] = useState("");
  const [nickname, setNickname] = useState("");
  const [birthday, setBirthday] = useState("");
  const [gender, setGender] = useState<Gender>("female");
  const [preferencesUpdated, setPreferencesUpdated] = useState(false);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [preferMap, setPreferMap] = useState<Record<number, string>>({});
  const [toast, setToast] = useState<{ type: "error"; message: string } | null>(null);
  const trimmedNickname = nickname.trim();
  const canSave =
    !!name.trim() &&
    trimmedNickname.length >= 2 &&
    !!birthday &&
    !!gender &&
    !loading &&
    !isSaving;

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 1800);
    return () => clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    const loadUser = async () => {
      try {
        const [me, preferList] = await Promise.all([fetchCurrentUser(), fetchPrefers()]);
        setUser(me);
        setPreferMap(
          preferList.reduce((acc, item: PreferItem) => {
            if (item.id && item.value) acc[item.id] = item.value;
            return acc;
          }, {} as Record<number, string>)
        );
        setName(me.name ?? "");
        setNickname(me.nickname ?? "");
        setBirthday(me.birthday ? me.birthday.slice(0, 10) : "");
        setGender(me.gender && allowedGenders.includes(me.gender as Gender) ? (me.gender as Gender) : "female");
      } catch (e) {
        console.error("마이페이지 사용자 정보 조회 실패:", e);
        setError("내 정보를 불러오지 못했습니다.");
      } finally {
        setLoading(false);
      }
    };
    loadUser();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setPreferencesUpdated(false);

    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("이름을 입력해주세요.");
      setToast({ type: "error", message: "저장 실패했습니다" });
      return;
    }
    if (trimmedName.length > 50) {
      setError("이름은 50자 이내로 입력해주세요.");
      setToast({ type: "error", message: "저장 실패했습니다" });
      return;
    }
    if (!allowedGenders.includes(gender)) {
      setError("성별 값이 올바르지 않습니다.");
      setToast({ type: "error", message: "저장 실패했습니다" });
      return;
    }
    if (!trimmedNickname) {
      setError("닉네임을 입력해주세요.");
      setToast({ type: "error", message: "저장 실패했습니다" });
      return;
    }
    if (trimmedNickname.length < 2) {
      setError("닉네임은 2자 이상 입력해주세요.");
      setToast({ type: "error", message: "저장 실패했습니다" });
      return;
    }
    if (!birthday) {
      setError("생년월일을 입력해주세요.");
      setToast({ type: "error", message: "저장 실패했습니다" });
      return;
    }

    setIsSaving(true);

    try {
      const updatedUser = await updateCurrentUser({
        name: trimmedName,
        nickname: trimmedNickname,
        birthday: `${birthday}T00:00:00`,
        gender,
      });
      setUser(updatedUser);
      setName(updatedUser.name ?? "");
      setNickname(updatedUser.nickname ?? "");
      setBirthday(updatedUser.birthday ? updatedUser.birthday.slice(0, 10) : "");
      setGender(updatedUser.gender && allowedGenders.includes(updatedUser.gender as Gender) ? (updatedUser.gender as Gender) : "female");
      setPreferencesUpdated(true);
      setTimeout(() => setPreferencesUpdated(false), 2000);
    } catch (e) {
      console.error("마이페이지 사용자 정보 저장 실패:", e);
      setError("정보 저장에 실패했습니다.");
      setToast({ type: "error", message: "저장 실패했습니다" });
    } finally {
      setIsSaving(false);
    }
  };

  const preferenceSummary = useMemo(
    () => [
      `배우 : ${user?.actor_prefer_id ? (preferMap[user.actor_prefer_id] ?? "-") : "-"}`,
      `영화 : ${user?.movie_prefer_id ? (preferMap[user.movie_prefer_id] ?? "-") : "-"}`,
      `드라마 : ${user?.drama_prefer_id ? (preferMap[user.drama_prefer_id] ?? "-") : "-"}`,
      `셀럽 : ${user?.celeb_prefer_id ? (preferMap[user.celeb_prefer_id] ?? "-") : "-"}`,
      `예능 : ${user?.variety_prefer_id ? (preferMap[user.variety_prefer_id] ?? "-") : "-"}`,
      `여행 스타일 : ${user?.with_yn === null || user?.with_yn === undefined ? "-" : user.with_yn ? "자연/트레킹" : "도시/미식"}`,
      `반려견 동행 : ${user?.dog_yn === null || user?.dog_yn === undefined ? "-" : user.dog_yn ? "예" : "아니오"}`,
      `비건 : ${user?.vegan_yn === null || user?.vegan_yn === undefined ? "-" : user.vegan_yn ? "예" : "아니오"}`,
    ],
    [preferMap, user]
  );

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-100 text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-6 py-12">
        <Link href="/home" className="mb-6 flex items-center gap-2 text-lg font-semibold hover:text-indigo-600">
          <Sparkles className="h-6 w-6 text-indigo-600" />
          <span>Polaris</span>
        </Link>

        <header className="mb-10 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-indigo-600">마이페이지</p>
            <h1 className="text-3xl font-bold text-slate-900">내 정보 관리</h1>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/chatbot" className="text-sm text-indigo-600 hover:underline">챗봇으로 돌아가기</Link>
          </div>
        </header>

        <div className="grid gap-8 md:grid-cols-[1.1fr_0.9fr]">
          <form onSubmit={handleSave} className="rounded-3xl border border-slate-200 bg-white p-8 shadow-lg shadow-indigo-50 space-y-6">
            {loading && <p className="text-sm text-slate-500">내 정보를 불러오는 중...</p>}
            {error && <p className="text-sm text-rose-600">{error}</p>}
            <div>
              <label className="text-sm font-semibold text-slate-800">이름</label>
              <input
                value={name}
                readOnly
                className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-700"
              />
            </div>
            <div>
              <label className="text-sm font-semibold text-slate-800">닉네임</label>
              <input
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                maxLength={50}
                className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-800 focus:border-indigo-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-sm font-semibold text-slate-800">생년월일</label>
              <input
                type="date"
                value={birthday}
                onChange={(e) => setBirthday(e.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-800 focus:border-indigo-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-sm font-semibold text-slate-800">성별</label>
              <div className="mt-3 flex gap-3">
                {[
                  { value: "female", label: "여성" },
                  { value: "male", label: "남성" },
                  { value: "other", label: "기타" },
                ].map((g) => (
                  <button
                    key={g.value}
                    type="button"
                    onClick={() => setGender(g.value)}
                    className={`rounded-full border px-4 py-2 text-sm font-medium transition ${gender === g.value ? "border-indigo-400 bg-indigo-50 text-indigo-700" : "border-slate-200 text-slate-600 hover:border-indigo-200"}`}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-semibold text-slate-800">이메일</label>
              <p className="mt-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-700">
                {user?.email ?? "-"}
              </p>
            </div>
            <button
              type="submit"
              disabled={!canSave}
              className="w-full rounded-2xl px-4 py-3 font-semibold text-white shadow-lg shadow-indigo-200 transition disabled:cursor-not-allowed disabled:bg-slate-300 enabled:bg-indigo-600 enabled:hover:bg-indigo-700"
            >
              {isSaving ? "저장 중..." : "정보 저장"}
            </button>
            {preferencesUpdated && <p className="text-sm text-emerald-600">저장되었습니다.</p>}
            {error && <p className="text-sm text-rose-600">저장 실패했습니다.</p>}
          </form>

          <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-lg shadow-indigo-50 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-800">선호도 조사</p>
                <p className="text-xs text-slate-500">처음 로그인 시 진행한 월드컵 결과</p>
              </div>
              <Link href="/survey" className="text-sm font-semibold text-indigo-600 hover:underline">다시 하기</Link>
            </div>
            <ul className="grid gap-3 sm:grid-cols-2">
              {preferenceSummary.map((item) => (
                <li key={item} className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-700 whitespace-nowrap overflow-hidden text-ellipsis">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
