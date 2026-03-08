import { useState, useRef, useCallback } from "react";
import {
    ChatMessage,
    sendChatMessageStream,
    sendAutoStartChatRoomStream,
    updatePlaceBookmark
} from "@/services/api";
import {
    PipelineSteps,
    StepStatus,
    createInitialPipelineSteps
} from "@/features/chat/components/PipelineProgress";

export function useChatMessages({
    setMessages,
    updateRoomTitle,
    clearPendingAutoStartMeta
}: {
    setMessages: (messages: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void;
    updateRoomTitle: (roomId: number, roomTitle: string) => void;
    clearPendingAutoStartMeta: (roomId: number) => void;
}) {
    const [isTyping, setIsTyping] = useState(false);
    const [isStreaming, setIsStreaming] = useState(false);
    const [showPipeline, setShowPipeline] = useState(false);
    const [pipelineSteps, setPipelineSteps] = useState<PipelineSteps>(createInitialPipelineSteps());
    const [streamBufferingReason, setStreamBufferingReason] = useState<string | null>(null);
    const [streamingMsgId, setStreamingMsgId] = useState<number | null>(null);

    const isSendingRef = useRef(false);
    const isPipelineVisibleRef = useRef(false);
    const streamTokenBufferRef = useRef<Record<number, string>>({});
    const streamTokenFrameRef = useRef<Record<number, number>>({});
    const stopRequestedRef = useRef(false);
    const streamAbortControllerRef = useRef<AbortController | null>(null);
    const activeStreamRef = useRef<{ roomId: number; placeholderId: number } | null>(null);

    const hidePipeline = useCallback(() => {
        if (!isPipelineVisibleRef.current) return;
        isPipelineVisibleRef.current = false;
        setShowPipeline(false);
    }, []);

    const updatePipelineStep = useCallback((step: string, status: string) => {
        const mappedStatus: StepStatus = status === "start" ? "running" : status as StepStatus;
        setPipelineSteps((prev) => ({
            ...prev,
            [step]: mappedStatus,
        }));
    }, []);

    const flushBufferedToken = useCallback((streamingId: number, roomId: number) => {
        const buffered = streamTokenBufferRef.current[streamingId];
        if (!buffered) return;

        delete streamTokenBufferRef.current[streamingId];
        delete streamTokenFrameRef.current[streamingId];

        setMessages((prev) => {
            let found = false;
            const next = prev.map((m) => {
                if (m.id !== streamingId) return m;
                found = true;
                return { ...m, message: (m.message || "") + buffered };
            });

            if (!found) {
                next.push({
                    id: streamingId,
                    room_id: roomId,
                    message: buffered,
                    role: "ai",
                    created_at: new Date().toISOString(),
                });
            }

            return next;
        });
    }, [setMessages]);

    const queueStreamToken = useCallback((streamingId: number, roomId: number, token: string) => {
        streamTokenBufferRef.current[streamingId] = (streamTokenBufferRef.current[streamingId] || "") + token;
        if (streamTokenFrameRef.current[streamingId] != null) return;

        streamTokenFrameRef.current[streamingId] = window.setTimeout(() => {
            flushBufferedToken(streamingId, roomId);
        }, 16);
    }, [flushBufferedToken]);

    const clearStreamTokenBuffer = useCallback((streamingId: number, roomId: number) => {
        const frameId = streamTokenFrameRef.current[streamingId];
        if (frameId != null) {
            window.clearTimeout(frameId);
            delete streamTokenFrameRef.current[streamingId];
        }
        flushBufferedToken(streamingId, roomId);
    }, [flushBufferedToken]);

    const mergeHydratedMessages = useCallback((roomId: number, nextMessages: ChatMessage[]) => {
        setMessages((prev) => {
            const activeStream = activeStreamRef.current;
            if (!activeStream || activeStream.roomId !== roomId) {
                return nextMessages;
            }

            const placeholder = prev.find((message) => message.id === activeStream.placeholderId);
            if (!placeholder) {
                return nextMessages;
            }

            const alreadyHydrated = nextMessages.some((message) => message.id === placeholder.id);
            if (alreadyHydrated) {
                return nextMessages;
            }

            return [...nextMessages, placeholder];
        });
    }, [setMessages]);

    const streamMessageToRoom = useCallback(async ({
        roomId,
        message,
        saveUserMessage,
        optimisticUserText,
        imageDataUrl,
    }: {
        roomId: number;
        message: string;
        saveUserMessage: boolean;
        optimisticUserText?: string;
        imageDataUrl?: string | null;
    }) => {
        if (isSendingRef.current) return;
        isSendingRef.current = true;
        stopRequestedRef.current = false;
        const abortController = new AbortController();
        streamAbortControllerRef.current = abortController;

        if (optimisticUserText) {
            const optimisticUserMsg: ChatMessage = {
                id: Date.now(),
                room_id: roomId,
                message: optimisticUserText,
                role: "human",
                image_path: imageDataUrl ?? null,
                created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, optimisticUserMsg]);
        }

        setIsTyping(true);
        setIsStreaming(true);
        setStreamBufferingReason(null);
        isPipelineVisibleRef.current = true;
        setShowPipeline(true);
        setPipelineSteps(createInitialPipelineSteps());

        const streamingId = Date.now() + 1;
        setStreamingMsgId(streamingId);
        activeStreamRef.current = { roomId, placeholderId: streamingId };
        const placeholderAiMsg: ChatMessage = {
            id: streamingId,
            room_id: roomId,
            message: "",
            role: "ai",
            created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, placeholderAiMsg]);

        try {
            await sendChatMessageStream(roomId, message, {
                onToken: (token) => {
                    queueStreamToken(streamingId, roomId, token);
                },
                onStep: (step, status) => {
                    updatePipelineStep(step, status);
                },
                onBufferingChange: (reason) => {
                    setStreamBufferingReason(reason);
                },
                onDone: (fullMessage, messageId, createdAt, _roomTitle, places) => {
                    clearPendingAutoStartMeta(roomId);
                    hidePipeline();
                    setStreamBufferingReason(null);
                    clearStreamTokenBuffer(streamingId, roomId);
                    const finalMessage = (fullMessage || "").trim() || "추천 결과를 준비했어요.";
                    setMessages((prev) => {
                        let found = false;
                        const next = prev.map((m) => {
                            if (m.id !== streamingId) return m;
                            found = true;
                            return {
                                ...m,
                                id: messageId,
                                message: finalMessage,
                                created_at: createdAt || m.created_at,
                                places: places,
                            };
                        });

                        if (!found) {
                            next.push({
                                id: messageId,
                                room_id: roomId,
                                message: finalMessage,
                                role: "ai",
                                created_at: createdAt || new Date().toISOString(),
                                places: places,
                            });
                        }
                        return next;
                    });
                    if (activeStreamRef.current?.placeholderId === streamingId) {
                        activeStreamRef.current = null;
                    }
                    setStreamingMsgId(null);
                },
                onRoomTitle: (roomTitle) => {
                    updateRoomTitle(roomId, roomTitle);
                },
                onError: (err) => {
                    console.error("Stream error", err);
                    hidePipeline();
                    setStreamBufferingReason(null);
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === streamingId
                                ? { ...m, message: "죄송합니다. 오류가 발생했습니다." }
                                : m
                        )
                    );
                    if (activeStreamRef.current?.placeholderId === streamingId) {
                        activeStreamRef.current = null;
                    }
                    setStreamingMsgId(null);
                },
            }, imageDataUrl ?? null, null, { saveUserMessage, signal: abortController.signal });
        } catch (error) {
            const isAbort =
                stopRequestedRef.current ||
                ((error as { name?: string })?.name === "AbortError");
            if (!isAbort) {
                console.error("Failed to send streamed message", error);
                setStreamBufferingReason(null);
                if (activeStreamRef.current?.placeholderId === streamingId) {
                    activeStreamRef.current = null;
                }
            } else {
                setMessages((prev) =>
                    prev.filter((m) => !(m.id === streamingId && !(m.message || "").trim()))
                );
            }
        } finally {
            setIsTyping(false);
            setIsStreaming(false);
            setShowPipeline(false);
            setStreamingMsgId(null);
            isSendingRef.current = false;
        }
    }, [clearStreamTokenBuffer, hidePipeline, queueStreamToken, setMessages, updatePipelineStep, updateRoomTitle, clearPendingAutoStartMeta]);

    const runAutoStarterStream = useCallback(async ({
        roomId,
        payload,
    }: {
        roomId: number;
        payload: {
            mode: "trip_context" | "selected_places" | "combined" | "greeting";
            trip_context?: { travel_duration: string; adult_count: number; child_count: number };
            selected_places?: { name?: string | null; adress?: string | null; place_id?: number }[];
            save_user_message?: boolean;
        };
    }) => {
        if (isSendingRef.current) return;
        isSendingRef.current = true;
        setIsTyping(true);
        setIsStreaming(true);
        setStreamBufferingReason(null);
        isPipelineVisibleRef.current = true;
        setShowPipeline(true);
        setPipelineSteps(createInitialPipelineSteps());

        const streamingId = Date.now() + 1;
        setStreamingMsgId(streamingId);
        activeStreamRef.current = { roomId, placeholderId: streamingId };
        setMessages((prev) => [
            ...prev,
            {
                id: streamingId,
                room_id: roomId,
                message: "",
                role: "ai",
                created_at: new Date().toISOString(),
            },
        ]);

        try {
            await sendAutoStartChatRoomStream(roomId, payload, {
                onToken: (token) => {
                    queueStreamToken(streamingId, roomId, token);
                },
                onStep: (step, status) => {
                    updatePipelineStep(step, status);
                },
                onBufferingChange: (reason) => {
                    setStreamBufferingReason(reason);
                },
                onDone: (fullMessage, messageId, createdAt, _roomTitle, places) => {
                    hidePipeline();
                    setStreamBufferingReason(null);
                    clearStreamTokenBuffer(streamingId, roomId);
                    const finalMessage = (fullMessage || "").trim() || "추천 결과를 준비했어요.";
                    setMessages((prev) => {
                        let found = false;
                        const next = prev.map((m) => {
                            if (m.id !== streamingId) return m;
                            found = true;
                            return {
                                ...m,
                                id: messageId,
                                message: finalMessage,
                                created_at: createdAt || m.created_at,
                                places: places,
                            };
                        });
                        if (!found) {
                            next.push({
                                id: messageId,
                                room_id: roomId,
                                message: finalMessage,
                                role: "ai",
                                created_at: createdAt || new Date().toISOString(),
                                places: places,
                            });
                        }
                        return next;
                    });
                    if (activeStreamRef.current?.placeholderId === streamingId) {
                        activeStreamRef.current = null;
                    }
                    setStreamingMsgId(null);
                },
                onRoomTitle: (roomTitle) => updateRoomTitle(roomId, roomTitle),
                onError: (err) => {
                    console.error("Auto start stream error", err);
                    hidePipeline();
                    setStreamBufferingReason(null);
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === streamingId ? { ...m, message: "죄송합니다. 오류가 발생했습니다." } : m
                        )
                    );
                    if (activeStreamRef.current?.placeholderId === streamingId) {
                        activeStreamRef.current = null;
                    }
                    setStreamingMsgId(null);
                },
            });
        } catch (error) {
            console.error("Failed to run auto start stream", error);
            setStreamBufferingReason(null);
            if (activeStreamRef.current?.placeholderId === streamingId) {
                activeStreamRef.current = null;
            }
        } finally {
            setIsTyping(false);
            setIsStreaming(false);
            isSendingRef.current = false;
        }
    }, [clearStreamTokenBuffer, hidePipeline, queueStreamToken, setMessages, updatePipelineStep, updateRoomTitle]);

    const handleStopMessage = () => {
        if (!isStreaming) return;
        stopRequestedRef.current = true;
        streamAbortControllerRef.current?.abort();
    };

    const handleTogglePlaceBookmark = async (messageId: number, placeId: number, currentStatus: boolean) => {
        try {
            const updatedPlace = await updatePlaceBookmark(placeId, !currentStatus);
            setMessages(prev => prev.map(m => {
                if (m.id === messageId && m.places) {
                    return {
                        ...m,
                        places: m.places.map(p => p.id === placeId ? { ...p, bookmark_yn: updatedPlace.bookmark_yn } : p)
                    };
                }
                return m;
            }));
        } catch (error) {
            console.error("Failed to toggle bookmark", error);
        }
    };

    return {
        isTyping,
        isStreaming,
        showPipeline,
        pipelineSteps,
        streamBufferingReason,
        streamingMsgId,
        mergeHydratedMessages,
        streamMessageToRoom,
        runAutoStarterStream,
        handleStopMessage,
        handleTogglePlaceBookmark
    };
}
