import { useState, useRef, useCallback, useEffect } from "react";

export type SttPermissionState = "unknown" | "prompt" | "granted" | "denied" | "unsupported";

interface UseSpeechRecognitionProps {
    inputText: string;
    setInputText: (text: string) => void;
}

export const useSpeechRecognition = ({ inputText, setInputText }: UseSpeechRecognitionProps) => {
    const [isListening, setIsListening] = useState(false);
    const [sttPermission, setSttPermission] = useState<SttPermissionState>("unknown");

    const recognitionRef = useRef<SpeechRecognition | null>(null);
    const micPermissionStatusRef = useRef<PermissionStatus | null>(null);

    const getSpeechRecognitionAPI = () =>
        (window.SpeechRecognition || window.webkitSpeechRecognition) as SpeechRecognitionConstructor | undefined;

    const syncMicPermission = useCallback(async () => {
        const SpeechRecognitionAPI = getSpeechRecognitionAPI();
        if (!SpeechRecognitionAPI) {
            setSttPermission("unsupported");
            return;
        }

        if (!navigator.permissions?.query) {
            setSttPermission((prev) => (prev === "unknown" || prev === "unsupported" ? "prompt" : prev));
            return;
        }

        try {
            const status = await navigator.permissions.query({ name: "microphone" as PermissionName });
            if (status.state === "granted") setSttPermission("granted");
            else if (status.state === "denied") setSttPermission("denied");
            else setSttPermission("prompt");

            if (micPermissionStatusRef.current && micPermissionStatusRef.current !== status) {
                micPermissionStatusRef.current.onchange = null;
            }
            status.onchange = () => { void syncMicPermission(); };
            micPermissionStatusRef.current = status;
        } catch {
            setSttPermission((prev) => (prev === "unknown" || prev === "unsupported" ? "prompt" : prev));
        }
    }, []);

    const handleToggleListening = useCallback(async () => {
        if (isListening && recognitionRef.current) {
            recognitionRef.current.stop();
            setIsListening(false);
            return;
        }

        const SpeechRecognitionAPI = getSpeechRecognitionAPI();

        if (!SpeechRecognitionAPI) {
            setSttPermission("unsupported");
            alert("이 브라우저는 음성 인식을 지원하지 않습니다. Chrome 브라우저를 사용해주세요.");
            return;
        }

        if (sttPermission === "denied") {
            alert("마이크 권한이 차단되어 있습니다.\n마이크 권한을 '허용'으로 변경 후 다시 시도해 주세요.");
            return;
        }

        const baseText = inputText;

        const recognition = new SpeechRecognitionAPI();
        recognition.lang = "ko-KR";
        recognition.interimResults = true;
        recognition.continuous = true;
        recognition.maxAlternatives = 1;
        recognitionRef.current = recognition;

        let finalTranscript = "";

        recognition.onstart = () => {
            setIsListening(true);
            setSttPermission("granted");
        };

        recognition.onresult = (event: SpeechRecognitionEvent) => {
            let interim = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interim += transcript;
                }
            }
            const separator = baseText && !baseText.endsWith(" ") ? " " : "";
            setInputText(baseText + separator + finalTranscript + interim);
        };

        recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
            console.error("Speech recognition error:", event.error);
            if (event.error === "not-allowed" || event.error === "service-not-allowed") {
                setSttPermission("denied");
            }
            setIsListening(false);
        };

        recognition.onend = () => {
            setIsListening(false);
            recognitionRef.current = null;
            const separator = baseText && !baseText.endsWith(" ") ? " " : "";
            setInputText((baseText + separator + finalTranscript).trim());
        };

        try {
            recognition.start();
        } catch (error) {
            console.error("Speech recognition start failed:", error);
            setIsListening(false);
            await syncMicPermission();
        }
    }, [isListening, inputText, setInputText, syncMicPermission, sttPermission]);

    useEffect(() => {
        syncMicPermission();

        const onFocus = () => { void syncMicPermission(); };
        const onVisibilityChange = () => {
            if (document.visibilityState === "visible") {
                void syncMicPermission();
            }
        };

        window.addEventListener("focus", onFocus);
        document.addEventListener("visibilitychange", onVisibilityChange);

        return () => {
            if (recognitionRef.current) {
                // eslint-disable-next-line react-hooks/exhaustive-deps
                recognitionRef.current.stop();
            }
            const cleanupStatus = micPermissionStatusRef.current;
            if (cleanupStatus) {
                cleanupStatus.onchange = null;
            }
            window.removeEventListener("focus", onFocus);
            document.removeEventListener("visibilitychange", onVisibilityChange);
        };
    }, [syncMicPermission]);

    return {
        isListening,
        sttPermission,
        handleToggleListening,
    };
};
