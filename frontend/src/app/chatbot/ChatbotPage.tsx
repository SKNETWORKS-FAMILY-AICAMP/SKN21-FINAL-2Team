"use client";

import { Suspense } from "react";
import { Sidebar } from "@/components/navigation/Sidebar";
import { ChatHome } from "@/features/chat/components/ChatHome";
import { Loader2 } from "lucide-react";

export function ChatbotPage() {
  return (
    <div className="flex w-full h-dvh flex-col bg-gray-100 p-3 sm:p-4 gap-3 overflow-hidden lg:flex-row lg:gap-4">
      <Suspense
        fallback={
          <div className="flex-none h-full w-[280px] rounded-lg bg-white border border-gray-200 animate-pulse" />
        }
      >
        <div className="flex-none lg:h-full">
          <Sidebar />
        </div>
      </Suspense>
      <main className="flex-1 min-h-0 relative min-w-0 rounded-[24px] bg-white border border-gray-200 overflow-hidden lg:rounded-lg shadow-sm">
        <Suspense
          fallback={
            <div className="flex w-full h-full items-center justify-center">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          }
        >
          <ChatHome />
        </Suspense>
      </main>
    </div>
  );
}
