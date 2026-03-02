declare global {
    interface SpeechRecognitionEvent extends Event {
        readonly resultIndex: number;
        readonly results: SpeechRecognitionResultList;
    }

    type SpeechRecognitionErrorType =
        | "aborted"
        | "audio-capture"
        | "bad-grammar"
        | "language-not-supported"
        | "network"
        | "no-speech"
        | "not-allowed"
        | "phrases-not-supported"
        | "service-not-allowed"
        | string;

    interface SpeechRecognitionErrorEvent extends Event {
        readonly error: SpeechRecognitionErrorType;
        readonly message: string;
    }

    interface SpeechRecognitionResult {
        readonly isFinal: boolean;
        readonly length: number;
        [index: number]: SpeechRecognitionAlternative;
    }

    interface SpeechRecognitionAlternative {
        readonly transcript: string;
        readonly confidence: number;
    }

    interface SpeechRecognitionResultList {
        readonly length: number;
        [index: number]: SpeechRecognitionResult;
    }

    interface SpeechRecognition extends EventTarget {
        lang: string;
        continuous: boolean;
        interimResults: boolean;
        maxAlternatives: number;
        onresult: ((event: SpeechRecognitionEvent) => void) | null;
        onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
        onend: (() => void) | null;
        onstart: (() => void) | null;
        start(): void;
        stop(): void;
        abort(): void;
    }

    interface SpeechRecognitionConstructor {
        new(): SpeechRecognition;
        prototype: SpeechRecognition;
    }

    interface Window {
        SpeechRecognition?: SpeechRecognitionConstructor;
        webkitSpeechRecognition?: SpeechRecognitionConstructor;
    }
}

export {};
