import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex min-h-screen w-full max-w-3xl flex-col items-center justify-between py-32 px-16 bg-white dark:bg-black sm:items-start">
        <div className="flex flex-col gap-4 text-base font-medium sm:flex-row">
          {/* 2. 챗봇 이동 버튼 추가 */}
          <Link
            href="/chatbot"
            className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-blue-600 px-8 text-white transition-colors hover:bg-blue-700 md:w-auto"
          >
            챗봇 시작하기 →
          </Link>
          <Link
            href="/login"
            className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-gray-200 px-8 text-black transition-colors hover:bg-gray-300 md:w-auto"
          >
            로그인
          </Link>
        </div>
      </main>
    </div>
  );
}
