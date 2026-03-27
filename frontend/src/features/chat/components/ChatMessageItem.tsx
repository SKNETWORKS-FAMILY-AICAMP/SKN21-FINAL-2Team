import { memo } from "react";
import { Sparkles, Bookmark, Map as MapIcon, MapPin } from "lucide-react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChatMessage, ChatPlaceItem } from "@/services/api";
import { PipelineSteps, PipelineProgress } from "./PipelineProgress";
import { cn } from "@/lib/utils";
import { resolveImageUrl, PLACE_PLACEHOLDER } from "@/lib/imageUrl";
import { useTranslation } from "@/i18n/useTranslation";
const hasVisiblePipelineSteps = (steps?: PipelineSteps) => {
    if (!steps) return false;
    return Object.values(steps).some((status) => status === "running" || status === "done");
};

interface ChatMessageItemProps {
    msg: ChatMessage;
    isStreaming?: boolean;
    streamingMsgId?: number | null;
    showPipeline?: boolean;
    pipelineSteps?: PipelineSteps;
    streamBufferingReason?: string | null;
    selectedMapPlaceId: string | null;
    toMapId: (place: ChatPlaceItem) => string;
    handleSelectMapPlace: (mapId: string, messageId?: number) => void;
    handleTogglePlaceBookmark: (messageId: number, placeId: number, currentStatus: boolean) => void;
    placeCardRefs: React.MutableRefObject<Record<string, HTMLDivElement | null>>;
    compactPlaces?: boolean;
}

export const ChatMessageItem = memo(({
    msg,
    streamingMsgId,
    showPipeline,
    pipelineSteps,
    streamBufferingReason,
    selectedMapPlaceId,
    toMapId,
    handleSelectMapPlace,
    handleTogglePlaceBookmark,
    placeCardRefs,
    compactPlaces = false,
}: ChatMessageItemProps) => {
    const { t } = useTranslation();
    const isStreamingCurrentMessage = Boolean(msg.id === streamingMsgId);

    // 유저 메시지 처리
    if (msg.role === "human") {
        return (
            <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 10, transformOrigin: 'bottom right' }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="flex justify-end w-full px-1 sm:px-2 lg:px-4 mb-2"
            >
                <div className="bg-black text-white px-4 py-2.5 rounded-[16px] rounded-br-[4px] max-w-[90%] md:max-w-[66%] shadow-[0_4px_14px_rgba(0,0,0,0.08)]">
                    {!!msg.image_path && (
                        <div className="mb-2.5 overflow-hidden rounded-xl border border-white/15">
                            <img
                                src={resolveImageUrl(msg.image_path)}
                                alt="Attached"
                                className="w-full max-h-[220px] object-cover"
                            />
                        </div>
                    )}
                    {!!(msg.latitude && msg.longitude) && (
                        <div className="mb-2 flex items-center gap-1.5 rounded-lg bg-white/15 px-2.5 py-1.5 w-fit max-w-full">
                            <MapPin size={12} className="text-white/80 flex-shrink-0" />
                            <span className="text-[12px] font-medium text-white/90 truncate">
                                {msg.location ?? t("chat.currentLocation")}
                            </span>
                        </div>
                    )}
                    {!!msg.message && (
                        <p className="text-[14px] leading-[1.5] whitespace-pre-wrap font-medium">{msg.message}</p>
                    )}
                    <div className="text-[9px] mt-1.5 font-medium text-slate-300 text-right uppercase tracking-wider">
                        {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </div>
                </div>
            </motion.div>
        );
    }

    // AI 메시지 처리
    const shouldRenderPipeline = Boolean(
        isStreamingCurrentMessage &&
        showPipeline &&
        hasVisiblePipelineSteps(pipelineSteps)
    );
    const shouldRenderWaitingBubble = Boolean(
        isStreamingCurrentMessage &&
        !msg.message &&
        !shouldRenderPipeline
    );
    const shouldRenderAiBubble = Boolean(
        shouldRenderPipeline ||
        shouldRenderWaitingBubble ||
        msg.message
    );
    const shouldHideEmptyAiMessage = Boolean(
        !isStreamingCurrentMessage &&
        !(msg.message || "").trim() &&
        (!msg.places || msg.places.length === 0) &&
        !shouldRenderPipeline &&
        !shouldRenderWaitingBubble
    );

    if (shouldHideEmptyAiMessage) {
        return null;
    }

    return (
        <div className="flex flex-col gap-3 mb-2 w-full px-1 sm:px-3 lg:px-4">
            <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                className="flex items-start gap-3 w-full"
            >
                {/* AI 아이콘 */}
                <div className="w-8 h-8 rounded-full bg-black flex items-center justify-center flex-shrink-0 shadow-md shadow-black/10 mt-1 ring-2 ring-white">
                    <Sparkles size={14} className="text-white" />
                </div>

                <div className="flex-1 min-w-0 w-full overflow-hidden md:max-w-[70%]">
                    {shouldRenderAiBubble && (
                        <div
                            data-testid={`ai-bubble-${msg.id}`}
                            className="bg-white border border-slate-100/80 rounded-[20px] rounded-tl-[4px] px-4 sm:px-5 py-3 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.04)] inline-block w-full mb-2 backdrop-blur-xl"
                        >
                            {shouldRenderPipeline && (
                                <div className={msg.message ? "mb-3" : ""}>
                                    <PipelineProgress steps={pipelineSteps || {}} visible={true} />
                                </div>
                            )}

                            {shouldRenderWaitingBubble && (
                                <div className="inline-flex items-center gap-2 text-slate-400">
                                    <span className="inline-flex gap-1">
                                        <span className="h-1.5 w-1.5 rounded-full bg-slate-300 animate-pulse" />
                                        <span className="h-1.5 w-1.5 rounded-full bg-slate-300 animate-pulse [animation-delay:120ms]" />
                                        <span className="h-1.5 w-1.5 rounded-full bg-slate-300 animate-pulse [animation-delay:240ms]" />
                                    </span>
                                    <span className="text-[12px] font-medium tracking-wide">{t("chat.preparingResponse")}</span>
                                </div>
                            )}

                            {!!msg.message && (
                                <div className="prose prose-sm max-w-none text-slate-700 prose-p:my-2 prose-p:leading-[1.6] prose-p:text-[14px] prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline prose-pre:bg-slate-50 prose-pre:text-slate-800 prose-pre:rounded-xl overflow-x-auto">
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            a: (props) => (
                                                <a
                                                    {...props}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                />
                                            ),
                                        }}
                                    >
                                        {msg.message}
                                    </ReactMarkdown>
                                </div>
                            )}
                        </div>
                    )}

                    {isStreamingCurrentMessage && streamBufferingReason === "link" && (
                        <div className="mb-2 ml-1 text-[11px] font-medium tracking-wide text-slate-400">
                            링크 정리 중...
                        </div>
                    )}

                    {/* 추천 장소 (Place Cards Carousel) */}
                    {msg.places && msg.places.length > 0 && (
                        <div className="mt-2 w-full">
                            <h5 className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest mb-3 ml-2 flex items-center gap-1.5">
                                <MapIcon size={12} />
                                Recommended Places
                            </h5>
                            {/* pt-5 pb-9: 카드 hover shadow(0_8px_30px_-4px)가 scroll container overflow에 잘리지 않도록
                                 위쪽 18px + 여유 2px = pt-5(20px), 아래쪽 34px + 여유 2px = pb-9(36px) */}
                            <div className={cn(
                                "flex overflow-x-auto pt-5 pb-9 snap-x custom-scrollbar",
                                compactPlaces
                                    ? "gap-2 px-0"
                                    : "gap-3 sm:gap-4 -mx-1 px-1 sm:-mx-2 sm:px-2"
                            )}>
                                {msg.places.map((place) => {
                                    const mapId = toMapId(place);
                                    const isMapSelected = selectedMapPlaceId === mapId;
                                    return (
                                        <div
                                            key={place.id}
                                            ref={(element) => {
                                                placeCardRefs.current[mapId] = element;
                                            }}
                                            onMouseEnter={() => handleSelectMapPlace(mapId)}
                                            onClick={() => handleSelectMapPlace(mapId, msg.id)}
                                            className={cn(
                                                /* hover:-translate-y-1 제거: 카드가 위로 4px 이동하면 overflow-x-auto 컨테이너 밖으로
                                                   나가 box-shadow가 잘림. 대신 shadow만 강화하여 hover 효과 유지. */
                                                "snap-start flex-shrink-0 relative bg-white rounded-[20px] overflow-hidden border shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] group cursor-pointer transition-[box-shadow,border-color] duration-300 hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.13)]",
                                                compactPlaces ? "w-[148px] sm:w-[158px] xl:w-[168px]" : "w-[168px] sm:w-[180px]",
                                                isMapSelected ? "border-black ring-2 ring-black/10" : "border-slate-100 hover:border-slate-300"
                                            )}
                                            style={compactPlaces ? { width: "min(15rem, calc((100% - 1rem) / 3))", minWidth: "8.75rem" } : undefined}
                                        >
                                            <div className={cn(
                                                /* overflow-hidden: group-hover:scale-110 시 이미지가 고정 높이(120px) 밖으로
                                                   번져 텍스트 영역, 그라디언트와 겹치는 현상 방지 */
                                                "relative bg-slate-100 overflow-hidden",
                                                compactPlaces ? "h-[104px] sm:h-[112px]" : "h-[120px]"
                                            )}>
                                                <img
                                                    src={resolveImageUrl(place.image_path) || PLACE_PLACEHOLDER}
                                                    alt={place.name || "Place image"}
                                                    loading="lazy"
                                                    decoding="async"
                                                    style={{ opacity: 0, transition: 'opacity 0.2s ease' }}
                                                    onLoad={(e) => { e.currentTarget.style.opacity = '1'; }}
                                                    onError={(e) => {
                                                        e.currentTarget.src = PLACE_PLACEHOLDER;
                                                        e.currentTarget.style.opacity = '1';
                                                    }}
                                                    className="absolute inset-0 m-0 w-full h-full object-cover object-center transition-transform duration-500 ease-out group-hover:scale-110"
                                                />
                                                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none" />
                                                <button
                                                    onClick={(event) => {
                                                        event.stopPropagation();
                                                        handleTogglePlaceBookmark(msg.id, place.id, !!place.bookmark_yn);
                                                    }}
                                                    className={`absolute top-2.5 right-2.5 p-1.5 rounded-full transition-colors shadow-sm ${place.bookmark_yn ? "text-yellow-400 bg-black/50 hover:bg-black/70" : "text-white/90 bg-black/30 hover:text-yellow-400 hover:bg-black/50"}`}
                                                >
                                                    <Bookmark size={14} fill={place.bookmark_yn ? "currentColor" : "none"} />
                                                </button>
                                            </div>
                                            <div className={cn("bg-white", compactPlaces ? "p-3" : "p-3.5")}>
                                                <h4 className={cn(
                                                    "font-semibold text-slate-800 leading-tight line-clamp-1 group-hover:text-black transition-colors",
                                                    compactPlaces ? "text-[12px]" : "text-[13px]"
                                                )}>
                                                    {place.name}
                                                </h4>
                                                <p className={cn(
                                                    "text-slate-500 mt-1.5 line-clamp-1 font-medium",
                                                    compactPlaces ? "text-[10px]" : "text-[11px]"
                                                )}>{place.adress}</p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* 타임스탬프
                        카드 캐러셀 컨테이너에 pb-9(36px) shadow 공간이 있어
                        카드 시각적 하단과 타임스탬프 사이에 큰 공백이 생김.
                        카드가 있을 때만 -mt-8(-32px)로 당겨 일반 버블과 동일한 간격으로 맞춤. */}
                    <div className={cn(
                        "text-[10px] mb-2 font-medium text-slate-400 ml-1 uppercase tracking-wider",
                        msg.places && msg.places.length > 0 ? "-mt-6" : "mt-1"
                    )}>
                        {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </div>
                </div>
            </motion.div>
        </div>
    );
});

ChatMessageItem.displayName = "ChatMessageItem";
