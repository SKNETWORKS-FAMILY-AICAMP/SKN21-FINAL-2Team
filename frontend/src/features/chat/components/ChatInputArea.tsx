import { useRef, useEffect, useState } from "react";
import { Send, Mic, MicOff, Square, Map as MapIcon, Plus, ImagePlus, MapPin } from "lucide-react";
import { motion } from "framer-motion";
import { useTranslation } from "@/i18n/useTranslation";

interface ChatInputAreaProps {
    inputText: string;
    setInputText: (text: string) => void;
    handleSendMessage: () => void;
    handleStopMessage: () => void;
    isStreaming: boolean;
    isListening: boolean;
    isLocating?: boolean;
    sttPermission: "unknown" | "granted" | "denied" | "unsupported" | "prompt";
    handleToggleListening: () => void;
    setIsMapSheetOpen: (open: boolean) => void;
    attachedImageDataUrl: string | null;
    attachedFileName: string;
    attachedLocationLabel: string;
    handleAttachLocation: () => void;
    handleAttachFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    setAttachedImageDataUrl: (url: string | null) => void;
    setAttachedFileName: (name: string) => void;
    clearAttachedLocation: () => void;
}

export function ChatInputArea({
    inputText,
    setInputText,
    handleSendMessage,
    handleStopMessage,
    isStreaming,
    isListening,
    isLocating = false,
    sttPermission,
    handleToggleListening,
    setIsMapSheetOpen,
    attachedImageDataUrl,
    attachedFileName,
    attachedLocationLabel,
    handleAttachLocation,
    handleAttachFileChange,
    setAttachedImageDataUrl,
    setAttachedFileName,
    clearAttachedLocation,
}: ChatInputAreaProps) {
    const { t } = useTranslation();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const inputTextareaRef = useRef<HTMLTextAreaElement>(null);
    const attachMenuRef = useRef<HTMLDivElement>(null);
    const [isAttachMenuOpen, setIsAttachMenuOpen] = useState(false);

    useEffect(() => {
        if (inputTextareaRef.current) {
            inputTextareaRef.current.style.height = "auto";
            inputTextareaRef.current.style.height = `${inputTextareaRef.current.scrollHeight}px`;
        }
    }, [inputText]);

    useEffect(() => {
        const handlePointerDown = (event: MouseEvent) => {
            if (!attachMenuRef.current?.contains(event.target as Node)) {
                setIsAttachMenuOpen(false);
            }
        };

        if (isAttachMenuOpen) {
            document.addEventListener("mousedown", handlePointerDown);
        }

        return () => {
            document.removeEventListener("mousedown", handlePointerDown);
        };
    }, [isAttachMenuOpen]);

    const handleKeyPress = (e: React.KeyboardEvent) => {
        const nativeEvent = e.nativeEvent as unknown as { isComposing?: boolean; keyCode?: number };
        if (nativeEvent.isComposing || nativeEvent.keyCode === 229) return;
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const handleAttachClick = () => {
        fileInputRef.current?.click();
    };

    const micButtonClass = isListening
        ? "text-white bg-blue-500 hover:bg-blue-600 shadow-[0_0_15px_rgba(59,130,246,0.5)]"
        : sttPermission === "denied"
            ? "text-red-600 bg-red-50 border border-red-200 hover:bg-red-100"
            : sttPermission === "unsupported"
                ? "text-gray-300 bg-gray-100 cursor-not-allowed"
                : "text-gray-400 hover:text-black hover:bg-gray-100";

    const micButtonTitle = isListening
        ? t("chatInput.voiceStop")
        : sttPermission === "denied"
            ? t("chatInput.voiceDenied")
            : sttPermission === "unsupported"
                ? t("chatInput.voiceUnsupported")
                : t("chatInput.voiceStart");

    return (
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white to-white/0 pt-8 pb-[max(1rem,env(safe-area-inset-bottom))] px-3 sm:px-4 z-20 pointer-events-none">
            <div className="w-full mx-auto relative pointer-events-auto max-w-4xl" ref={attachMenuRef}>
                {isAttachMenuOpen && (
                    <div className="absolute left-0 bottom-[calc(100%+0.75rem)] z-30 min-w-[148px] rounded-2xl border border-slate-200 bg-white/95 backdrop-blur-xl shadow-lg p-1.5">
                        <button
                            type="button"
                            onClick={() => {
                                setIsAttachMenuOpen(false);
                                handleAttachClick();
                            }}
                            className="w-full flex items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
                        >
                            <ImagePlus size={16} />
                            {t("chatInput.attachPhoto")}
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                setIsAttachMenuOpen(false);
                                void handleAttachLocation();
                            }}
                            className="w-full flex items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
                        >
                            <MapPin size={16} />
                            {isLocating ? t("chatInput.locating") : t("chatInput.attachLocation")}
                        </button>
                    </div>
                )}
                <div className="bg-white/60 backdrop-blur-xl border border-slate-200/60 rounded-[28px] p-1.5 pr-1.5 shadow-[0_8px_30px_-4px_rgba(0,0,0,0.08)] focus-within:ring-4 focus-within:ring-slate-900/5 focus-within:border-slate-300 focus-within:bg-white/90 transition-all duration-300">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={handleAttachFileChange}
                    />

                    {(attachedFileName || attachedLocationLabel) && (
                        <div className="px-3 pt-2 pb-1 flex flex-wrap gap-2">
                            {attachedFileName && (
                            <div className="inline-flex items-center gap-2 rounded-full bg-slate-900 text-white text-xs pl-1.5 pr-2 py-1.5 max-w-[340px]">
                                {attachedImageDataUrl && (
                                    <img
                                        src={attachedImageDataUrl}
                                        alt={t("chatInput.attachedImage")}
                                        className="w-6 h-6 rounded-full object-cover border border-white/20"
                                    />
                                )}
                                <span className="truncate">{attachedFileName}</span>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setAttachedImageDataUrl(null);
                                        setAttachedFileName("");
                                    }}
                                    className="text-white/80 hover:text-white transition-colors"
                                    aria-label={t("chatInput.removeAttachment")}
                                >
                                    ×
                                </button>
                            </div>
                            )}
                            {attachedLocationLabel && (
                                <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 text-slate-700 text-xs pl-2.5 pr-2 py-1.5 max-w-[240px] border border-slate-200">
                                    <MapPin size={12} className="text-slate-500" />
                                    <span className="truncate">{attachedLocationLabel}</span>
                                    <button
                                        type="button"
                                        onClick={clearAttachedLocation}
                                        className="text-slate-500 hover:text-slate-800 transition-colors"
                                        aria-label={t("chatInput.removeLocation")}
                                    >
                                        ×
                                    </button>
                                </div>
                            )}
                        </div>
                    )}

                    <div className="flex items-end gap-1.5 sm:gap-2 mb-0.5">
                        <div className="relative ml-0.5">
                            <button
                                type="button"
                                onClick={() => setIsAttachMenuOpen((prev) => !prev)}
                                className="p-2.5 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors"
                                title={t("chatInput.attach")}
                            >
                                <Plus size={18} />
                            </button>
                        </div>

                        <textarea
                            ref={inputTextareaRef}
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            onKeyDown={handleKeyPress}
                            placeholder={t("chatInput.placeholder")}
                            className="flex-1 bg-transparent border-none outline-none resize-none text-[15px] leading-[1.5] font-medium text-slate-800 placeholder:text-slate-400 custom-scrollbar py-2"
                            rows={1}
                            style={{ minHeight: "40px", maxHeight: "130px" }}
                        />

                        <div className="flex items-center gap-1.5 sm:gap-2 pl-1 sm:pl-2 pr-0.5 sm:pr-1">
                            <button
                                type="button"
                                onClick={() => setIsMapSheetOpen(true)}
                                className="p-2.5 rounded-full transition-all duration-300 text-slate-500 hover:text-black hover:bg-slate-100 lg:hidden"
                                title={t("chatInput.viewMap")}
                            >
                                <MapIcon size={18} />
                            </button>

                            <button
                                onClick={handleToggleListening}
                                className={`p-2.5 rounded-full transition-all duration-300 relative ${micButtonClass}`}
                                title={micButtonTitle}
                                disabled={sttPermission === "unsupported"}
                            >
                                {isListening ? (
                                    <>
                                        <Square size={16} fill="currentColor" strokeWidth={0} />
                                        <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-blue-500 rounded-full border-2 border-white animate-pulse shadow-sm shadow-blue-500/50" />
                                    </>
                                ) : sttPermission === "denied" ? (
                                    <MicOff size={18} strokeWidth={1.5} />
                                ) : (
                                    <Mic size={18} strokeWidth={1.5} />
                                )}
                            </button>

                            {isStreaming ? (
                                <motion.button
                                    initial={false}
                                    animate={{ scale: 1, opacity: 1 }}
                                    onClick={handleStopMessage}
                                    className="p-2.5 rounded-full transition-all duration-300 shadow-md bg-slate-800 text-white shadow-slate-800/20 hover:shadow-slate-800/40 hover:-translate-y-0.5"
                                    title={t("chatInput.stopResponse")}
                                >
                                    <Square size={16} fill="currentColor" strokeWidth={0} />
                                </motion.button>
                            ) : (
                                <motion.button
                                    initial={false}
                                    animate={{ scale: (inputText.trim() || attachedImageDataUrl || attachedLocationLabel) ? 1 : 0.9, opacity: (inputText.trim() || attachedImageDataUrl || attachedLocationLabel) ? 1 : 0.7 }}
                                    onClick={handleSendMessage}
                                    disabled={!inputText.trim() && !attachedImageDataUrl && !attachedLocationLabel}
                                    className={`p-2.5 rounded-full transition-all duration-300 shadow-md ${(inputText.trim() || attachedImageDataUrl || attachedLocationLabel) ? "bg-black text-white shadow-black/20 hover:shadow-black/40 hover:-translate-y-0.5" : "bg-slate-100 text-slate-300 cursor-not-allowed shadow-none"}`}
                                    title={t("chatInput.send")}
                                >
                                    <Send size={18} />
                                </motion.button>
                            )}
                        </div>
                    </div>
                </div>

                <p className="text-[10px] sm:text-[11px] text-center text-slate-400 mt-3 font-medium tracking-wide px-2">
                    {t("chatInput.disclaimer")}
                </p>
            </div>
        </div>
    );
}
