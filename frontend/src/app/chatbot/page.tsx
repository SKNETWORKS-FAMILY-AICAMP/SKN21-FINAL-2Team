"use client";

import { Suspense } from "react";
import { Sidebar } from "@/components/Sidebar";
import { ChatHome } from "@/components/chat/ChatHome";
import { Loader2 } from "lucide-react";

export default function ChatbotPage() {
  return (
    <div className="flex w-full h-screen bg-gray-100 p-4 gap-4 overflow-hidden">
      <div className="flex-none h-full">
        <Sidebar />
      </div>
      <main className="flex-1 h-full relative min-w-0 bg-white border-r border-gray-200 rounded-lg">
        <Suspense fallback={
          <div className="flex w-full h-full items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
          </div>
        }>
          <ChatHome />
        </Suspense>
      </main>
    </div>
  );
}
