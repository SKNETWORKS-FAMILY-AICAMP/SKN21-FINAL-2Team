import { ChatRoom } from "@/services/api";
import { Sparkles, Bookmark, Map as MapIcon } from "lucide-react";
import { useTranslation } from "@/i18n/useTranslation";

interface ChatHeaderProps {
    currentRoom: ChatRoom | null | undefined;
    currentRoomId: number | null;
    mapPlacesLength: number;
    isMapPanelOpen: boolean;
    handleToggleRoomBookmark: () => void;
    setIsMapPanelOpen: (open: boolean) => void;
}

export function ChatHeader({
    currentRoom,
    currentRoomId,
    mapPlacesLength,
    isMapPanelOpen,
    handleToggleRoomBookmark,
    setIsMapPanelOpen,
}: ChatHeaderProps) {
    const { t } = useTranslation();
    return (
        <header className="h-14 flex items-center justify-between pl-16 pr-3 sm:px-4 lg:px-6 bg-white/70 backdrop-blur-md z-10 sticky top-0 border-b border-white/50">
            <div className="flex items-center gap-2 min-w-0">
                <Sparkles size={16} className="text-slate-900 flex-none" />
                <span className="font-semibold text-[17px] tracking-tight text-slate-900 truncate">
                    {currentRoom?.title || t("chat.travelAssistant")}
                </span>
                <button
                    type="button"
                    onClick={handleToggleRoomBookmark}
                    className={`inline-flex items-center justify-center rounded-full p-1 transition-colors ${currentRoom?.bookmark_yn ? "text-yellow-500 bg-yellow-50" : "text-gray-300 hover:text-yellow-500 hover:bg-gray-100"
                        }`}
                    title={t("chat.bookmarkToggle")}
                    disabled={!currentRoomId}
                >
                    <Bookmark size={16} fill={currentRoom?.bookmark_yn ? "currentColor" : "none"} className="opacity-80" />
                </button>
            </div>

            <div className="flex items-center gap-2">
                {/* Desktop Map Toggle */}
                {mapPlacesLength > 0 && (
                    <button
                        onClick={() => setIsMapPanelOpen(!isMapPanelOpen)}
                        className={`hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold tracking-wide transition-all border ${isMapPanelOpen ? 'bg-black text-white border-black' : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                            }`}
                        title={isMapPanelOpen ? t("chat.mapClose") : t("chat.mapOpen")}
                    >
                        <MapIcon size={14} className={isMapPanelOpen ? "text-white" : "text-slate-500"} />
                        {isMapPanelOpen ? t("chat.mapOn") : t("chat.mapOff")}
                    </button>
                )}
            </div>
        </header>
    );
}
