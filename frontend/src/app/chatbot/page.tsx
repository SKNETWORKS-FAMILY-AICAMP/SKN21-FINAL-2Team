// src/app/chatbot/page.tsx
'use client';

import { useState, useRef } from 'react';
import { sendChatMessage } from '@/services/api';
import { Paperclip, Image as ImageIcon, MapPin, X } from 'lucide-react';

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
        <div className="flex flex-col h-screen p-10 bg-zinc-50 dark:bg-black text-black dark:text-white relative">
            <h1 className="text-2xl font-bold mb-4">AI 챗봇과 대화하기</h1>
            <div className="flex-1 overflow-y-auto mb-4 p-4 bg-white dark:bg-zinc-900 rounded-lg shadow border border-zinc-200 dark:border-zinc-800">
                {chatLog.map((msg, i) => (
                    <div key={i} className={`mb-4 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                        <div className={`inline-block p-2 rounded-lg whitespace-pre-wrap ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-zinc-200 dark:bg-zinc-800'}`}>
                            {msg.text}
                        </div>
                    </div>
                ))}
                {isTyping && <p className="text-zinc-400 text-sm">답변 생성 중...</p>}
            </div>

            {/* Attachment Preview */}
            {(attachedImage || attachedLocation) && (
                <div className="flex gap-2 mb-2">
                    {attachedImage && (
                        <div className="relative">
                            <img src={attachedImage} alt="Preview" className="h-20 w-20 object-cover rounded border border-zinc-300" />
                            <button
                                onClick={() => setAttachedImage(null)}
                                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-0.5 hover:bg-red-600"
                            >
                                <X size={12} />
                            </button>
                        </div>
                    )}
                    {attachedLocation && (
                        <div className="relative flex items-center gap-2 bg-blue-100 dark:bg-blue-900 p-2 rounded border border-blue-200 dark:border-blue-800">
                            <MapPin size={20} className="text-blue-600 dark:text-blue-400" />
                            <span className="text-sm">위치 정보 첨부됨</span>
                            <button
                                onClick={() => setAttachedLocation(null)}
                                className="ml-2 text-zinc-500 hover:text-red-500"
                            >
                                <X size={14} />
                            </button>
                        </div>
                    )}
                </div>
            )}

            <div className="flex gap-2 relative items-end">
                {/* Attachment Menu */}
                <div className="relative">
                    <button
                        onClick={() => setIsMenuOpen(!isMenuOpen)}
                        className="p-3 bg-zinc-200 dark:bg-zinc-800 rounded-full hover:bg-zinc-300 dark:hover:bg-zinc-700 transition-colors"
                    >
                        <Paperclip size={20} />
                    </button>

                    {isMenuOpen && (
                        <div className="absolute bottom-14 left-0 bg-white dark:bg-zinc-800 shadow-xl rounded-lg border border-zinc-200 dark:border-zinc-700 p-2 w-40 z-10 flex flex-col gap-1">
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                className="flex items-center gap-2 w-full p-2 text-left hover:bg-zinc-100 dark:hover:bg-zinc-700 rounded text-sm"
                            >
                                <ImageIcon size={16} /> 이미지 첨부
                            </button>
                            <button
                                onClick={handleLocationSelect}
                                className="flex items-center gap-2 w-full p-2 text-left hover:bg-zinc-100 dark:hover:bg-zinc-700 rounded text-sm"
                            >
                                <MapPin size={16} /> 장소 첨부
                            </button>
                        </div>
                    )}
                    <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        ref={fileInputRef}
                        onChange={handleImageSelect}
                    />
                </div>

                <input
                    className="flex-1 p-3 border rounded-lg bg-white dark:bg-zinc-900 border-zinc-300 dark:border-zinc-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="메시지를 입력하세요..."
                />
                <button onClick={handleSend} className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors">전송</button>
            </div>
        </div>
    );
}