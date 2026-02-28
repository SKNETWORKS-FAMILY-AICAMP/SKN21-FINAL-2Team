// src/app/chatbot_demo/page.tsx
'use client';

import { useRef, useState } from 'react';
import Link from "next/link";
import { Paperclip, Image as ImageIcon, MapPin, X, Menu, Plus, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMessage {
    role: 'human' | 'ai';
    text: string;
}

interface DemoRoom {
    id: string;
    title: string;
    messages: ChatMessage[];
}

interface AttachedLocation {
    lat: number;
    lng: number;
}

const INITIAL_DEMO_ROOMS: DemoRoom[] = [
    {
        id: "travel",
        title: "여행 추천",
        messages: [
            { role: "human", text: "주말에 서울 근교로 반려견과 갈만한 곳 추천해줘." },
            { role: "ai", text: "남한산성 산책 코스, **양평 두물머리**, *가평 애견 동반 카페*를 추천해요." },
            { role: "human", text: "가평 쪽으로 반나절 코스도 짜줘." },
            { role: "ai", text: "다음과 같은 **4~5시간 코스**를 추천합니다:\n\n1. **아침 카페**: 펫프렌들리 카페 방문\n2. **호수 산책**: 가평 호수 주변 산책\n3. **점심 식사**: 애견 동반 가능 식당\n\n즐거운 여행 되세요!" },
        ],
    },
    {
        id: "vegan",
        title: "비건 맛집",
        messages: [
            { role: "human", text: "강남역 근처 비건 식당 3곳만 알려줘." },
            { role: "ai", text: "샐러드 중심 1곳, 비건 버거 1곳, 한식 비건 1곳으로 구성해볼게요." },
        ],
    },
    {
        id: "pet",
        title: "반려견 숙소",
        messages: [
            { role: "human", text: "애견 동반 가능한 펜션 찾고 있어." },
            { role: "ai", text: "마당 유무, 소형견/대형견 허용 여부, 추가 요금을 먼저 확인하는 게 좋아요." },
        ],
    },
    {
        id: "actor",
        title: "배우 추천",
        messages: [
            { role: "human", text: "송강 느낌의 로맨스 드라마 추천해줘." },
            { role: "ai", text: "청춘 로맨스 톤의 작품 위주로 3개 추천해드릴게요." },
        ],
    },
];

export default function ChatbotDemoPage() {
    const [input, setInput] = useState('');
    const [rooms, setRooms] = useState<DemoRoom[]>(INITIAL_DEMO_ROOMS);
    const [currentRoomId, setCurrentRoomId] = useState<string>(INITIAL_DEMO_ROOMS[0].id);
    const [isTyping, setIsTyping] = useState(false);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

    // Attachments
    const [attachedImage, setAttachedImage] = useState<string | null>(null); // Base64
    const [attachedLocation, setAttachedLocation] = useState<AttachedLocation | null>(null);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const currentRoom = rooms.find((room) => room.id === currentRoomId) ?? rooms[0];
    const chatLog = currentRoom?.messages ?? [];

    const handleCreateRoom = () => {
        const roomNo = rooms.length + 1;
        const newRoom: DemoRoom = {
            id: `demo-${Date.now()}`,
            title: `새 데모 채팅 ${roomNo}`,
            messages: [
                { role: "ai", text: "데모 채팅이 시작되었습니다. 여행/맛집/취향 질문을 입력해보세요." },
            ],
        };
        setRooms((prev) => [newRoom, ...prev]);
        setCurrentRoomId(newRoom.id);
        setInput('');
        setAttachedImage(null);
        setAttachedLocation(null);
        setIsTyping(false);
    };

    const appendMessage = (roomId: string, message: ChatMessage) => {
        setRooms((prev) =>
            prev.map((room) =>
                room.id === roomId
                    ? { ...room, messages: [...room.messages, message] }
                    : room
            )
        );
    };

    const getDemoReply = (text: string) => {
        const normalized = text.toLowerCase();
        if (normalized.includes("비건")) {
            return "비건 기준으로 단백질/포만감/접근성을 함께 고려한 후보를 우선 추천할게요.";
        }
        if (normalized.includes("반려견") || normalized.includes("강아지")) {
            return "반려견 동반 여부, 실내 허용 범위, 주변 산책 동선을 기준으로 다시 정리해드릴게요.";
        }
        if (normalized.includes("여행")) {
            return "이동 시간 1시간 내외 기준으로 당일치기 코스를 우선 추천할게요.";
        }
        return "좋아요. 데모 응답입니다. 질문 의도에 맞춰 핵심만 요약해 안내해드릴게요.";
    };

    const handleSend = async () => {
        if (!input.trim() && !attachedImage && !attachedLocation) return;

        let userText = input;
        if (attachedLocation) {
            userText += `\n[Location Attached: ${attachedLocation.lat}, ${attachedLocation.lng}]`;
        }
        if (attachedImage) {
            userText += `\n[Image Attached]`;
        }

        const newUserMsg: ChatMessage = { role: 'human', text: userText };
        appendMessage(currentRoomId, newUserMsg);

        // Reset inputs immediately
        setInput('');
        setAttachedImage(null);
        setAttachedLocation(null);
        setIsTyping(true);

        await new Promise((resolve) => setTimeout(resolve, 450));
        const newBotMsg: ChatMessage = { role: 'ai', text: getDemoReply(userText) };
        appendMessage(currentRoomId, newBotMsg);
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
        <div
            className={
                isSidebarCollapsed
                    ? "grid min-h-screen grid-cols-1 bg-slate-50 text-slate-900 md:grid-cols-[72px_1fr]"
                    : "grid min-h-screen grid-cols-1 bg-slate-50 text-slate-900 md:grid-cols-[320px_1fr]"
            }
        >
            {/* Sidebar */}
            <aside className="flex h-full flex-col border-r border-slate-200 bg-white">
                {isSidebarCollapsed ? (
                    <div className="flex h-full flex-col items-center px-2 py-4">
                        <button
                            type="button"
                            onClick={() => setIsSidebarCollapsed(false)}
                            aria-label="사이드바 확장"
                            title="사이드바 확장"
                            className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:border-indigo-300 hover:text-indigo-600"
                        >
                            <Menu className="h-5 w-5" />
                        </button>
                        <button
                            type="button"
                            onClick={handleCreateRoom}
                            aria-label="새 채팅 만들기"
                            title="새 채팅 만들기"
                            className="mt-3 flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 text-white shadow hover:bg-indigo-700"
                        >
                            <Plus className="h-5 w-5" />
                        </button>
                    </div>
                ) : (
                    <>
                        <div className="flex items-center justify-between px-4 py-4">
                            <Link href="/home" className="flex items-center gap-2 text-lg font-semibold hover:text-indigo-600">
                                <Sparkles className="h-5 w-5 text-indigo-600" />
                                Triver
                            </Link>
                            <button
                                type="button"
                                onClick={() => setIsSidebarCollapsed(true)}
                                aria-label="사이드바 축소"
                                title="사이드바 축소"
                                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                            >
                                <Menu className="h-5 w-5" />
                            </button>
                        </div>

                        <div className="px-4 pb-4">
                            <button
                                onClick={handleCreateRoom}
                                className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow hover:bg-indigo-700"
                            >
                                <Plus className="h-4 w-4" /> 새 채팅 만들기
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto px-2 pb-4">
                            <p className="px-2 text-xs font-semibold uppercase text-slate-500">채팅 리스트</p>
                            <div className="mt-2 space-y-1">
                                {rooms.map((room) => (
                                    <button
                                        key={room.id}
                                        onClick={() => setCurrentRoomId(room.id)}
                                        className={`flex w-full items-center justify-between rounded-lg px-3 py-3 text-left text-sm transition ${currentRoomId === room.id ? "bg-indigo-50 text-indigo-700" : "hover:bg-slate-100"}`}
                                    >
                                        <span>{room.title}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </>
                )}

            </aside>

            {/* Chat area */}
            <div className="flex h-full flex-col">
                <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
                    <div>
                        <p className="text-xs font-semibold uppercase text-slate-500">채팅방</p>
                        <h1 className="text-xl font-bold">{currentRoom?.title ?? "데모 채팅"}</h1>
                    </div>
                    <div className="flex items-center gap-3 text-sm text-slate-500" />
                </header>

                <div className="flex-1 overflow-y-auto bg-gradient-to-b from-slate-50 to-white px-6 py-6">
                    <div className="mx-auto flex max-w-3xl flex-col gap-4">
                        {chatLog.map((msg, i) => (
                            <div key={i} className={`flex ${msg.role === 'human' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${msg.role === 'human' ? 'bg-indigo-600 text-white' : 'bg-white border border-slate-200 text-slate-800'}`}>
                                    {msg.role === 'ai' ? (
                                        <div className="prose prose-sm max-w-none prose-slate prose-p:leading-relaxed prose-pre:bg-slate-50 prose-pre:text-slate-900">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {msg.text}
                                            </ReactMarkdown>
                                        </div>
                                    ) : (
                                        msg.text
                                    )}
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
