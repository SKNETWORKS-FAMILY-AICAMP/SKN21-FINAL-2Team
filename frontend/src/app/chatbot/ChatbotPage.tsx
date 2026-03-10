"use client";

import { Suspense } from "react";
import { Sidebar } from "@/components/navigation/Sidebar";
import { ChatHome } from "@/features/chat/components/ChatHome";
import { Loader2 } from "lucide-react";

export function ChatbotPage() {
  return (
    <div className="flex w-full min-h-screen flex-col bg-gray-100 p-3 sm:p-4 gap-3 lg:h-screen lg:flex-row lg:gap-4 lg:overflow-hidden">
      <Suspense
        fallback={
          <div className="flex-none h-full w-[280px] rounded-lg bg-white border border-gray-200 animate-pulse" />
        }
      >
        <div className="flex-none lg:h-full">
          <Sidebar />
        </div>
      </Suspense>
      <main className="flex-1 relative min-w-0 rounded-[24px] bg-white border-r border-gray-200 overflow-hidden min-h-[calc(100dvh-1.5rem)] lg:min-h-0 lg:h-full lg:rounded-lg">
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
