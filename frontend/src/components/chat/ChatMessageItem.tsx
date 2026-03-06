import { memo } from "react";
import { Sparkles, Bookmark, Map as MapIcon } from "lucide-react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChatMessage, ChatPlaceItem } from "@/services/api";

const DEFAULT_PLACEHOLDER = "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200&q=80";

interface ChatMessageItemProps {
    msg: ChatMessage;
    isStreaming?: boolean;
    streamingMsgId?: number | null;
    showPipeline?: boolean;
    selectedMapPlaceId: string | null;
    toMapId: (place: ChatPlaceItem) => string;
    handleSelectMapPlace: (mapId: string) => void;
    handleTogglePlaceBookmark: (messageId: number, placeId: number, currentStatus: boolean) => void;
    placeCardRefs: React.MutableRefObject<Record<string, HTMLDivElement | null>>;
}

export const ChatMessageItem = memo(({
    msg,
    isStreaming,
    streamingMsgId,
    showPipeline,
    selectedMapPlaceId,
    toMapId,
    handleSelectMapPlace,
    handleTogglePlaceBookmark,
    placeCardRefs
}: ChatMessageItemProps) => {

    // 스트리밍 중이면서 메시지가 비어있고 파이프라인 진행 상태라면 렌더링하지 않음
    if (isStreaming && msg.id === streamingMsgId && !msg.message && showPipeline) {
        return null;
    }
    // 스트리밍 중이면서 메시지가 비어있어도 대기 상태라면 렌더링을 막음 (파이프라인 여부와 무관하게)
    if (isStreaming && msg.id === streamingMsgId && !msg.message) {
        return null;
    }

    // 유저 메시지 처리
    if (msg.role === "human") {
        return (
            <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 10, transformOrigin: 'bottom right' }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="flex justify-end w-full px-2 lg:px-4 mb-2"
            >
                <div className="bg-black text-white px-4 py-2.5 rounded-[16px] rounded-br-[4px] max-w-[85%] md:max-w-[66%] shadow-[0_4px_14px_rgba(0,0,0,0.08)]">
                    <p className="text-[14px] leading-[1.5] whitespace-pre-wrap font-medium">{msg.message}</p>
                    <div className="text-[9px] mt-1.5 font-medium text-slate-300 text-right uppercase tracking-wider">
                        {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </div>
                </div>
            </motion.div>
        );
    }

    // AI 메시지 처리
    return (
        <div className="flex flex-col gap-3 mb-2 w-full px-4">
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
                    {/* 메시지 내용 (Markdown 렌더링) */}
                    {!!msg.message && (
                        <div className="bg-white border border-slate-100/80 rounded-[20px] rounded-tl-[4px] px-5 py-3 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.04)] inline-block w-full mb-2 backdrop-blur-xl">
                            <div className="prose prose-sm max-w-none text-slate-700 prose-p:my-2 prose-p:leading-[1.6] prose-p:text-[14px] prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline prose-pre:bg-slate-50 prose-pre:text-slate-800 prose-pre:rounded-xl">
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
                        </div>
                    )}

                    {/* 추천 장소 (Place Cards Carousel) */}
                    {msg.places && msg.places.length > 0 && (
                        <div className="mt-2 w-full">
                            <h5 className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest mb-3 ml-2 flex items-center gap-1.5">
                                <MapIcon size={12} />
                                Recommended Places
                            </h5>
                            <div className="flex overflow-x-auto pb-4 pt-1 gap-4 snap-x custom-scrollbar -mx-2 px-2">
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
                                            onClick={() => handleSelectMapPlace(mapId)}
                                            className={`snap-start flex-shrink-0 relative w-[180px] bg-white rounded-[20px] overflow-hidden border shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] group cursor-pointer transition-all duration-300 hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.1)] hover:-translate-y-1 ${isMapSelected ? "border-black ring-2 ring-black/10" : "border-slate-100 hover:border-slate-300"
                                                }`}
                                        >
                                            <div className="relative h-[120px] bg-slate-100 overflow-hidden">
                                                <img
                                                    src={place.image_path || DEFAULT_PLACEHOLDER}
                                                    alt={place.name || "Place image"}
                                                    className="absolute inset-0 m-0 w-full h-full object-cover object-center transition-transform duration-700 ease-out group-hover:scale-110"
                                                />
                                                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none" />
                                                <button
                                                    onClick={(event) => {
                                                        event.stopPropagation(); // 카드 클릭 이벤트 막기
                                                        handleTogglePlaceBookmark(msg.id, place.id, !!place.bookmark_yn);
                                                    }}
                                                    className={`absolute top-2.5 right-2.5 p-1.5 rounded-full backdrop-blur-md transition-colors shadow-sm ${place.bookmark_yn ? "text-yellow-400 bg-black/40 hover:bg-black/60" : "text-white/90 bg-black/20 hover:text-yellow-400 hover:bg-black/40"}`}
                                                >
                                                    <Bookmark size={14} fill={place.bookmark_yn ? "currentColor" : "none"} />
                                                </button>
                                            </div>
                                            <div className="p-3.5 bg-white">
                                                <h4 className="font-semibold text-slate-800 leading-tight line-clamp-1 text-[13px] group-hover:text-black transition-colors">
                                                    {place.name}
                                                </h4>
                                                <p className="text-[11px] text-slate-500 mt-1.5 line-clamp-1 font-medium">{place.adress}</p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* 타임스탬프 */}
                    <div className="text-[10px] mt-1 mb-2 font-medium text-slate-400 ml-1 uppercase tracking-wider">
                        {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </div>
                </div>
            </motion.div>
        </div>
    );
});
