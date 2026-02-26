"use client";

import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";

export default function MyPageSettingsPage() {
  const router = useRouter();

  return (
    <div className="flex w-full h-screen bg-gray-100 p-4 gap-4 overflow-hidden">
      <div className="flex-none h-full">
        <Sidebar />
      </div>

      <main className="flex-1 h-full min-w-0 bg-white rounded-lg border border-gray-200 overflow-y-auto">
        <header className="p-6 border-b border-gray-100 flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-serif italic font-medium text-gray-900 mb-1">Settings</h1>
            <p className="text-xs text-gray-500 font-medium tracking-wide uppercase">Coming Soon</p>
          </div>
          <button
            type="button"
            onClick={() => router.push("/mypage")}
            className="bg-black text-white px-4 py-2.5 rounded-lg text-[10px] font-bold hover:opacity-90 transition-all uppercase tracking-wide"
          >
            Back to MyPage
          </button>
        </header>

        <div className="p-6">
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="text-sm font-bold text-gray-900 mb-2 uppercase tracking-widest">Prototype</h2>
            <p className="text-xs text-gray-600 leading-relaxed">
              이 페이지는 Settings 화면 자리만 먼저 만들어 둔 프로토타입입니다.
              <br />
              이후에 프로필/언어/연동(예: Google) 같은 설정 기능이 여기에 들어갈 예정입니다.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
