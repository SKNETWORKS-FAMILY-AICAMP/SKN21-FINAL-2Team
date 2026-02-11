// src/app/chatbot/page.tsx
'use client';

import { useState, useRef } from 'react';
import Link from "next/link";
import { sendChatMessage } from '@/services/api';
import { Paperclip, Image as ImageIcon, MapPin, X, Menu, Plus } from 'lucide-react';

interface ChatMessage {
    role: 'user' | 'bot';
    text: string;
}

interface AttachedLocation {
    lat: number;
    lng: number;
}

export default function ChatbotPage() {
    const [input, setInput] = useState('');
    const [chatLog, setChatLog] = useState<ChatMessage[]>([]);
    const [isTyping, setIsTyping] = useState(false);
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    // Attachments
    const [attachedImage, setAttachedImage] = useState<string | null>(null); // Base64
    const [attachedLocation, setAttachedLocation] = useState<AttachedLocation | null>(null);

    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleSend = async () => {
        if (!input.trim() && !attachedImage && !attachedLocation) return;

        let userText = input;
        if (attachedLocation) {
            userText += `\n[Location Attached: ${attachedLocation.lat}, ${attachedLocation.lng}]`;
        }
        if (attachedImage) {
            userText += `\n[Image Attached]`;
        }

        const newUserMsg: ChatMessage = { role: 'user', text: userText };
        setChatLog((prev) => [...prev, newUserMsg]);

        const currentInput = input;
        const currentImage = attachedImage;
        const currentLocation = attachedLocation ? JSON.stringify(attachedLocation) : null;

        // Reset inputs immediately
        setInput('');
        setAttachedImage(null);
        setAttachedLocation(null);
        setIsTyping(true);

        const botReply = await sendChatMessage(currentInput, currentImage, currentLocation);
        const newBotMsg: ChatMessage = { role: 'bot', text: botReply };
        setChatLog((prev) => [...prev, newBotMsg]);
        setIsTyping(false);
    };

    const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onloadend = () => {
            setAttachedImage(reader.result as string);
            setIsMenuOpen(false);
        };
        reader.readAsDataURL(file);
    };

    const handleLocationSelect = () => {
        if (!navigator.geolocation) {
            alert('위치 정보를 지원하지 않는 브라우저입니다.');
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (position) => {
                setAttachedLocation({
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                });
                setIsMenuOpen(false);
            },
            (error) => {
                console.error("Error getting location:", error);
                alert('위치 정보를 가져올 수 없습니다.');
            }
        );
    };

    return (
        <div className="grid min-h-screen grid-cols-1 bg-slate-50 text-slate-900 md:grid-cols-[320px_1fr]">
            {/* Sidebar */}
            <aside className="flex h-full flex-col border-r border-slate-200 bg-white">
                <div className="flex items-center justify-between px-4 py-4">
                    <Link href="/" className="text-lg font-semibold">Polaris</Link>
                    <Menu className="h-5 w-5 text-slate-400" />
                </div>

                <div className="px-4 pb-4">
                    <button className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow hover:bg-indigo-700">
                        <Plus className="h-4 w-4" /> 새 채팅 만들기
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto px-2 pb-4">
                    <p className="px-2 text-xs font-semibold uppercase text-slate-500">채팅 리스트</p>
                    <div className="mt-2 space-y-1">
                        {["여행 추천", "비건 맛집", "반려견 숙소", "배우 추천"].map((title, idx) => (
                            <button
                                key={title}
                                className={`flex w-full items-center justify-between rounded-lg px-3 py-3 text-left text-sm transition ${idx === 0 ? "bg-indigo-50 text-indigo-700" : "hover:bg-slate-100"}`}
                            >
                                <span>{title}</span>
                                <span className="text-[10px] text-slate-400">12:3{idx}</span>
                            </button>
                        ))}
                    </div>
                </div>

                <div className="border-t border-slate-200 px-4 py-4 text-sm text-slate-600">
                    <p className="font-semibold">내 정보</p>
                    <p className="text-xs text-slate-500">is_first_login = false</p>
                    <Link href="/mypage" className="mt-2 inline-flex text-xs font-semibold text-indigo-600 hover:underline">마이페이지</Link>
                </div>
            </aside>

            {/* Chat area */}
            <div className="flex h-full flex-col">
                <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
                    <div>
                        <p className="text-xs font-semibold uppercase text-slate-500">채팅방</p>
                        <h1 className="text-xl font-bold">여행 추천</h1>
                    </div>
                    <div className="flex items-center gap-3 text-sm text-slate-500">
                        <Link href="/survey" className="font-semibold text-indigo-600 hover:underline">선호도 재설정</Link>
                        <span className="h-6 w-px bg-slate-200" />
                        <Link href="/login" className="hover:text-slate-700">로그아웃</Link>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto bg-gradient-to-b from-slate-50 to-white px-6 py-6">
                    <div className="mx-auto flex max-w-3xl flex-col gap-4">
                        {chatLog.map((msg, i) => (
                            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${msg.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-white border border-slate-200 text-slate-800'}`}>
                                    {msg.text}
                                </div>
                            </div>
                        ))}
                        {isTyping && <p className="text-xs text-slate-400">답변 생성 중...</p>}
                    </div>
                </div>

                {(attachedImage || attachedLocation) && (
                    <div className="mx-auto flex w-full max-w-3xl gap-2 px-6 pb-3">
                        {attachedImage && (
                            <div className="relative">
                                {/* Using img intentionally for quick preview; optimization can be added later */}
                                <img src={attachedImage} alt="Preview" className="h-16 w-16 rounded-xl border border-slate-200 object-cover" />
                                <button
                                    onClick={() => setAttachedImage(null)}
                                    className="absolute -top-2 -right-2 rounded-full bg-rose-500 p-1 text-white"
                                >
                                    <X size={12} />
                                </button>
                            </div>
                        )}
                        {attachedLocation && (
                            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
                                <MapPin className="h-4 w-4 text-indigo-500" /> 위치 첨부됨
                                <button onClick={() => setAttachedLocation(null)} className="text-slate-400 hover:text-rose-500">
                                    <X size={14} />
                                </button>
                            </div>
                        )}
                    </div>
                )}

                <div className="border-t border-slate-200 bg-white px-6 py-4">
                    <div className="mx-auto flex max-w-3xl items-end gap-3">
                        <div className="relative">
                            <button
                                onClick={() => setIsMenuOpen(!isMenuOpen)}
                                className="flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 hover:border-indigo-300"
                            >
                                <Paperclip size={18} />
                            </button>
                            {isMenuOpen && (
                                <div className="absolute -top-28 left-0 z-10 w-40 rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
                                    <button
                                        onClick={() => fileInputRef.current?.click()}
                                        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100"
                                    >
                                        <ImageIcon size={16} /> 이미지 첨부
                                    </button>
                                    <button
                                        onClick={handleLocationSelect}
                                        className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100"
                                    >
                                        <MapPin size={16} /> 위치 첨부
                                    </button>
                                </div>
                            )}
                            <input
                                type="file"
                                accept="image/*"
                                ref={fileInputRef}
                                className="hidden"
                                onChange={handleImageSelect}
                            />
                        </div>

                        <input
                            className="flex-1 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 shadow-inner focus:border-indigo-400 focus:outline-none"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            placeholder="메시지를 입력하세요..."
                        />
                        <button
                            onClick={handleSend}
                            className="rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-md shadow-indigo-200 hover:bg-indigo-700"
                        >
                            전송
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
