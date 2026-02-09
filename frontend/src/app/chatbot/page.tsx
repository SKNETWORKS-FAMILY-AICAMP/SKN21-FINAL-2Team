// src/app/chatbot/page.tsx
'use client';

import { useState } from 'react';
import { sendChatMessage } from '@/services/api';

interface ChatMessage {
    role: 'user' | 'bot';
    text: string;
}

export default function ChatbotPage() {
    const [input, setInput] = useState('');
    const [chatLog, setChatLog] = useState<ChatMessage[]>([]);
    const [isTyping, setIsTyping] = useState(false);

    const handleSend = async () => {
        if (!input.trim()) return;
        const newUserMsg: ChatMessage = { role: 'user', text: input };
        setChatLog((prev) => [...prev, newUserMsg]);
        setInput('');
        setIsTyping(true);

        const botReply = await sendChatMessage(input);
        const newBotMsg: ChatMessage = { role: 'bot', text: botReply };
        setChatLog((prev) => [...prev, newBotMsg]);
        setIsTyping(false);
    };

    return (
        <div className="flex flex-col h-screen p-10 bg-zinc-50 dark:bg-black text-black dark:text-white">
            <h1 className="text-2xl font-bold mb-4">AI 챗봇과 대화하기</h1>
            <div className="flex-1 overflow-y-auto mb-4 p-4 bg-white dark:bg-zinc-900 rounded-lg shadow border border-zinc-200 dark:border-zinc-800">
                {chatLog.map((msg, i) => (
                    <div key={i} className={`mb-4 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                        <span className={`inline-block p-2 rounded-lg ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-zinc-200 dark:bg-zinc-800'}`}>
                            {msg.text}
                        </span>
                    </div>
                ))}
                {isTyping && <p className="text-zinc-400 text-sm">답변 생성 중...</p>}
            </div>
            <div className="flex gap-2">
                <input
                    className="flex-1 p-2 border rounded bg-white dark:bg-zinc-900 border-zinc-300 dark:border-zinc-700"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="메시지를 입력하세요..."
                />
                <button onClick={handleSend} className="px-6 py-2 bg-blue-600 text-white rounded-full font-medium hover:bg-blue-700 transition-colors">전송</button>
            </div>
        </div>
    );
}