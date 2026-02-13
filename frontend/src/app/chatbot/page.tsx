// src/app/chatbot/page.tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import Link from "next/link";
import { sendChatMessage, fetchRooms, fetchRoom, createRoom, ChatMessage, ChatRoom, logoutApi } from '@/services/api';
import { Paperclip, Image as ImageIcon, MapPin, X, Menu, Plus, Sparkles, ChevronDown } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface AttachedLocation {
  lat: number;
  lng: number;
}

function renderInlineMarkdown(text: string) {
  const tokenRegex = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  const tokens = text.split(tokenRegex).filter(Boolean);

  return tokens.map((token, idx) => {
    if (token.startsWith("**") && token.endsWith("**")) {
      return <strong key={idx}>{token.slice(2, -2)}</strong>;
    }
    if (token.startsWith("`") && token.endsWith("`")) {
      return (
        <code key={idx} className="rounded bg-slate-100 px-1 py-0.5 text-[12px] text-slate-700">
          {token.slice(1, -1)}
        </code>
      );
    }
    if (token.startsWith("[") && token.includes("](") && token.endsWith(")")) {
      const splitIndex = token.indexOf("](");
      const label = token.slice(1, splitIndex);
      const href = token.slice(splitIndex + 2, -1);
      return (
        <a
          key={idx}
          href={href}
          target="_blank"
          rel="noreferrer"
          className="text-indigo-600 underline decoration-indigo-300 underline-offset-2 hover:text-indigo-700"
        >
          {label}
        </a>
      );
    }
    return <span key={idx}>{token}</span>;
  });
}

function MarkdownMessage({ text }: { text: string }) {
  const lines = text.split("\n");
  const nodes: JSX.Element[] = [];
  let listItems: string[] = [];
  let listType: "ul" | "ol" | null = null;

  const flushList = () => {
    if (!listItems.length || !listType) return;
    const items = listItems.map((item, idx) => <li key={idx}>{renderInlineMarkdown(item)}</li>);
    nodes.push(
      listType === "ul" ? (
        <ul key={`ul-${nodes.length}`} className="my-2 ml-5 list-disc space-y-1">
          {items}
        </ul>
      ) : (
        <ol key={`ol-${nodes.length}`} className="my-2 ml-5 list-decimal space-y-1">
          {items}
        </ol>
      )
    );
    listItems = [];
    listType = null;
  };

  lines.forEach((rawLine, idx) => {
    const line = rawLine.trim();
    if (!line) {
      flushList();
      return;
    }

    const orderedMatch = line.match(/^\d+\.\s+(.+)$/);
    if (line.startsWith("- ")) {
      if (listType !== "ul") flushList();
      listType = "ul";
      listItems.push(line.slice(2).trim());
      return;
    }
    if (orderedMatch) {
      if (listType !== "ol") flushList();
      listType = "ol";
      listItems.push(orderedMatch[1].trim());
      return;
    }

    flushList();

    if (line.startsWith("### ")) {
      nodes.push(
        <h3 key={`h3-${idx}`} className="mt-2 mb-1 text-sm font-bold">
          {renderInlineMarkdown(line.slice(4))}
        </h3>
      );
      return;
    }
    if (line.startsWith("## ")) {
      nodes.push(
        <h2 key={`h2-${idx}`} className="mt-2 mb-1 text-base font-bold">
          {renderInlineMarkdown(line.slice(3))}
        </h2>
      );
      return;
    }
    if (line.startsWith("# ")) {
      nodes.push(
        <h1 key={`h1-${idx}`} className="mt-2 mb-1 text-lg font-bold">
          {renderInlineMarkdown(line.slice(2))}
        </h1>
      );
      return;
    }

    nodes.push(
      <p key={`p-${idx}`} className="my-1">
        {renderInlineMarkdown(line)}
      </p>
    );
  });

  flushList();
  return <div className="prose prose-sm max-w-none prose-p:my-1">{nodes}</div>;
}

export default function ChatbotPage() {
  const router = useRouter();
  const [input, setInput] = useState('');
  const [chatLog, setChatLog] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [rooms, setRooms] = useState<ChatRoom[]>([]);
  const [currentRoomId, setCurrentRoomId] = useState<number | null>(null);
  const [loadingRoom, setLoadingRoom] = useState(false);
  const [roomsLoaded, setRoomsLoaded] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const [hasUnseenNewMessages, setHasUnseenNewMessages] = useState(false);

  // Attachments
  const [attachedImages, setAttachedImages] = useState<string[]>([]); // Base64 list
  const [attachedLocation, setAttachedLocation] = useState<AttachedLocation | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const messageListRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollOnNextMessageRef = useRef(false);
  const prevChatLogLengthRef = useRef(0);
  const isInitializingRoomRef = useRef(false);
  const isRoomLoadingRef = useRef(false);

  const logoutAndGoHome = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("chat_room_id");
    }
    logoutApi();
    router.replace("/");
  };

  // Redirect unauthenticated users
  useEffect(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("access_token");
    if (!token) {
      logoutAndGoHome();
    }
  }, [router]);

  // Load rooms on mount
  useEffect(() => {
    refreshRooms();
  }, []);

  const refreshRooms = async (stayOnRoomId?: number | null) => {
    try {
      const list = await fetchRooms();
      // 최신 생성/업데이트 순으로 정렬 (created_at 최신 순, fallback: id desc)
      list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime() || b.id - a.id);
      setRooms(list);
      if (stayOnRoomId && list.some(r => r.id === stayOnRoomId)) {
        setCurrentRoomId(stayOnRoomId);
      } else if (list[0] && !stayOnRoomId) {
        setCurrentRoomId(list[0].id);
      }
    } catch (error) {
      console.error("Failed to load rooms:", error);
      logoutAndGoHome();
    } finally {
      setRoomsLoaded(true);
    }
  };

  // Load selected room history
  useEffect(() => {
    if (!currentRoomId) return;
    isInitializingRoomRef.current = true;
    isRoomLoadingRef.current = true;
    setHasUnseenNewMessages(false);
    shouldAutoScrollOnNextMessageRef.current = false;

    const loadRoomHistory = async (roomId: number) => {
      setLoadingRoom(true);
      try {
        const room = await fetchRoom(roomId);
        const messages = room.messages || [];
        setChatLog(messages);
        prevChatLogLengthRef.current = messages.length;
      } catch (error) {
        console.error("Failed to load room history:", error);
        setChatLog([]);
        prevChatLogLengthRef.current = 0;
        logoutAndGoHome();
      } finally {
        isRoomLoadingRef.current = false;
        setLoadingRoom(false);
      }
    };
    loadRoomHistory(currentRoomId);
  }, [currentRoomId]);

  const handleSend = async () => {
    if (!input.trim() && attachedImages.length === 0 && !attachedLocation) return;
    if (!currentRoomId) {
      alert("채팅방이 없습니다. 새 채팅을 시작해주세요.");
      return;
    }

    const currentInput = input;
    const currentImage = attachedImages.length > 0 ? attachedImages[attachedImages.length - 1] : null;
    const currentLocation = attachedLocation ? `${attachedLocation.lat},${attachedLocation.lng}` : null;

    // Reset inputs immediately
    setInput('');
    setAttachedImages([]);
    setAttachedLocation(null);
    setIsTyping(true);

    // Optimistic user message
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      room_id: currentRoomId,
      role: 'human',
      message: currentInput,
      created_at: new Date().toISOString(),
      latitude: attachedLocation?.lat ?? null,
      longitude: attachedLocation?.lng ?? null,
      image_path: currentImage ?? null,
      bookmark_yn: false,
    };
    shouldAutoScrollOnNextMessageRef.current = isNearBottom();
    setChatLog((prev) => [...prev, tempUserMsg]);

    try {
      const botReply = await sendChatMessage(currentRoomId, currentInput, currentImage, currentLocation);
      // 최신 메시지·제목을 서버에서 다시 가져와 동기화
      const updatedRoom = await fetchRoom(currentRoomId);
      shouldAutoScrollOnNextMessageRef.current = isNearBottom();
      setChatLog(updatedRoom.messages || []);
      // 최신 순서 반영을 위해 방 목록 다시 정렬 후 현재 방 유지
      await refreshRooms(currentRoomId);
    } catch (error) {
      console.error("Error sending chat:", error);
      logoutAndGoHome();
    } finally {
      setIsTyping(false);
    }
  };

  const handleCreateRoom = async () => {
    try {
      const newRoom = await createRoom("New Chat");
      setRooms((prev) => [newRoom, ...prev]);
      setCurrentRoomId(newRoom.id);
    } catch (error) {
      console.error("Failed to create room:", error);
      alert("채팅방 생성에 실패했습니다.");
    }
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    files.forEach((file) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setAttachedImages((prev) => [...prev, reader.result as string]);
      };
      reader.readAsDataURL(file);
    });

    e.target.value = '';
    setIsMenuOpen(false);
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

  const isNearBottom = () => {
    const container = messageListRef.current;
    if (!container) return true;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    return distanceFromBottom <= 80;
  };

  const updateScrollButtonVisibility = () => {
    const container = messageListRef.current;
    if (!container) return;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    if (distanceFromBottom <= 80) {
      setHasUnseenNewMessages(false);
    }
    setShowScrollToBottom(distanceFromBottom > 80);
  };

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    const container = messageListRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior });
    setHasUnseenNewMessages(false);
  };

  useEffect(() => {
    updateScrollButtonVisibility();
  }, [loadingRoom, currentRoomId, isTyping]);

  useEffect(() => {
    if (!currentRoomId || loadingRoom) return;
    const rafId = requestAnimationFrame(() => {
      updateScrollButtonVisibility();
    });
    return () => cancelAnimationFrame(rafId);
  }, [currentRoomId, loadingRoom, chatLog.length]);

  useEffect(() => {
    if (loadingRoom || !currentRoomId || isInitializingRoomRef.current) {
      prevChatLogLengthRef.current = chatLog.length;
      return;
    }

    const hasNewMessage = chatLog.length > prevChatLogLengthRef.current;
    if (hasNewMessage) {
      if (shouldAutoScrollOnNextMessageRef.current) {
        requestAnimationFrame(() => scrollToBottom('smooth'));
      } else {
        setHasUnseenNewMessages(true);
      }
    }

    shouldAutoScrollOnNextMessageRef.current = false;
    prevChatLogLengthRef.current = chatLog.length;
  }, [chatLog.length, loadingRoom, currentRoomId]);

  useEffect(() => {
    if (!currentRoomId) return;
    if (loadingRoom || isRoomLoadingRef.current) return;
    if (!isInitializingRoomRef.current) return;

    const rafId = requestAnimationFrame(() => {
      scrollToBottom('auto');
      updateScrollButtonVisibility();
      setHasUnseenNewMessages(false);
      isInitializingRoomRef.current = false;
    });

    return () => cancelAnimationFrame(rafId);
  }, [currentRoomId, loadingRoom, chatLog.length]);

  return (
    <div
      className={
        isSidebarCollapsed
          ? "grid h-screen grid-cols-1 overflow-hidden bg-slate-50 text-slate-900 md:grid-cols-[72px_1fr]"
          : "grid h-screen grid-cols-1 overflow-hidden bg-slate-50 text-slate-900 md:grid-cols-[320px_1fr]"
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
              <Link href="/" className="flex items-center gap-2 text-lg font-semibold hover:text-indigo-600">
                <Sparkles className="h-5 w-5 text-indigo-600" />
                Polaris
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
              <button onClick={handleCreateRoom} className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow hover:bg-indigo-700">
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
                    <span>{room.title || "제목 없음"}</span>
                    <span className="text-[10px] text-slate-400">{new Date(room.created_at).toLocaleTimeString()}</span>
                  </button>
                ))}
                {rooms.length === 0 && (
                  <p className="px-3 py-3 text-xs text-slate-500">채팅방이 없습니다.</p>
                )}
              </div>
            </div>
          </>
        )}

      </aside>

      {/* Chat area */}
      <div className="flex min-h-0 h-full flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">채팅방</p>
            <h1 className="text-xl font-bold">{rooms.find(r => r.id === currentRoomId)?.title || "채팅"}</h1>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-500">
            <Link href="/mypage" className="font-semibold text-indigo-600 hover:underline">마이페이지</Link>
            <span className="h-6 w-px bg-slate-200" />
            <button onClick={logoutAndGoHome} className="hover:text-slate-700">로그아웃</button>
          </div>
        </header>

        <div className="relative min-h-0 flex-1">
          <div
            ref={messageListRef}
            onScroll={updateScrollButtonVisibility}
            className="h-full overflow-y-auto bg-gradient-to-b from-slate-50 to-white px-6 py-6"
          >
            {!roomsLoaded ? (
              <div className="mx-auto h-full max-w-3xl" />
            ) : rooms.length === 0 ? (
              <div className="mx-auto flex h-full max-w-3xl flex-col items-center justify-center gap-4 text-center text-slate-600">
                <p className="text-lg font-semibold text-slate-800">아직 채팅방이 없어요</p>
                <p className="text-sm text-slate-500">새 채팅을 시작해 첫 메시지를 보내보세요.</p>
                <button
                  onClick={handleCreateRoom}
                  className="rounded-full bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-md shadow-indigo-200 hover:bg-indigo-700"
                >
                  채팅 시작하기
                </button>
              </div>
            ) : (
              <div className="mx-auto flex max-w-3xl flex-col gap-4">
                {loadingRoom && <p className="text-xs text-slate-400">대화 내역을 불러오는 중...</p>}
                {chatLog.map((msg) => (
                  <div key={msg.id} className={`flex ${msg.role === 'human' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${msg.role === 'human' ? 'bg-indigo-600 text-white' : 'bg-white border border-slate-200 text-slate-800'}`}>
                      {(msg.latitude !== null && msg.latitude !== undefined && msg.longitude !== null && msg.longitude !== undefined) && (
                        <div className={`mb-3 inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs ${msg.role === 'human' ? 'bg-indigo-500/70 text-indigo-50' : 'bg-slate-100 text-slate-600'}`}>
                          <MapPin className="h-3 w-3" />
                          위치 첨부
                        </div>
                      )}
                      {msg.image_path && (
                        <div className="mb-2">
                          <img
                            src={msg.image_path}
                            alt="Attached"
                            className="max-h-60 rounded-2xl object-cover"
                          />
                        </div>
                      )}
                      {!!msg.message && (
                        <div className={`${(msg.latitude !== null && msg.latitude !== undefined && msg.longitude !== null && msg.longitude !== undefined) || !!msg.image_path ? 'mt-1' : ''}`}>
                          {msg.role === 'ai' ? (
                            <MarkdownMessage text={msg.message} />
                          ) : (
                            <p>{msg.message}</p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {isTyping && <p className="text-xs text-slate-400">답변 생성 중...</p>}
              </div>
            )}
          </div>
          {showScrollToBottom && (
            <button
              type="button"
              onClick={() => scrollToBottom()}
              aria-label="맨 아래로 이동"
              title="맨 아래로 이동"
              className={`absolute right-6 bottom-4 z-20 rounded-full border bg-white p-2 shadow-md hover:text-indigo-600 ${
                hasUnseenNewMessages
                  ? 'border-indigo-300 text-indigo-600 shadow-indigo-300'
                  : 'border-slate-200 text-slate-600'
              }`}
            >
              <ChevronDown className="h-4 w-4" />
            </button>
          )}
        </div>

        {rooms.length > 0 && (
          <div className="border-t border-slate-200 bg-white px-6 py-4">
            {(attachedImages.length > 0 || attachedLocation) && (
              <div className="mx-auto mb-3 flex w-full max-w-3xl flex-wrap gap-2">
                {attachedImages.map((image, index) => (
                  <div key={`${index}-${image.slice(0, 24)}`} className="relative">
                    <img src={image} alt={`Preview ${index + 1}`} className="h-16 w-16 rounded-xl border border-slate-200 object-cover" />
                    <button
                      onClick={() => setAttachedImages((prev) => prev.filter((_, i) => i !== index))}
                      className="absolute -top-2 -right-2 rounded-full bg-rose-500 p-1 text-white"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
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
                  multiple
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
        )}
      </div>
    </div>
  );
}
