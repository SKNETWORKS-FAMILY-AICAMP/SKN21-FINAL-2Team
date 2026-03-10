export type AppLanguage = "en" | "ko" | "ja";

export type TripSummary = {
    id: string;
    title: string;
    createdAt?: string;
    messages: { role: "user" | "assistant"; text: string }[];
};

export type ReservationItem = {
    id: string;
    reservationId: number;
    category: "transportation" | "hotel" | "restaurant" | "activity" | "etc";
    title: string;
    subtitle: string;
    dateLabel: string;
    reservationImageUrl?: string;
    identifierLabel?: string;
    identifierValue?: string;
    destinationLabel?: string;
    durationLabel?: string;
    details: { label: string; value: string }[];
};

export type ChatTranscriptMessage = {
    role: "user" | "assistant";
    text: string;
};
