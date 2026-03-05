export const SURVEY_IMAGE_MAP: Record<string, string> = {
    "빽빽한 일정": "/image/planning.jpg",
    "느슨한 일정": "/image/noplan.png",
    "붐비는 도시": "/image/crowded.jpg",
    "한적한 자연": "/image/lonely.jpg",
    "맛집": "/image/kfood.jpg",
    "역사적 명소": "/image/khistorical.jpg",
    "K-culture": "/image/kculture.png",
};

export const SURVEY_ITEM_LABELS: Record<"plan" | "vibe" | "places", string> = {
    plan: "Travel Schedule",
    vibe: "Travel Vibe",
    places: "Interests",
};

export const SPECIAL_EXTRA_PREFER_OPTIONS = [
    "Halal",
    "Kosher",
    "Vegan",
    "Wheelchair Accessible",
];

export const SNAPSHOT_OPTIONS: Record<"plan" | "vibe" | "places", string[]> = {
    plan: ["빽빽한 일정", "느슨한 일정"],
    vibe: ["붐비는 도시", "한적한 자연"],
    places: ["맛집", "역사적 명소", "K-culture"],
};

export const EXTRA_PREFER_OPTIONS = SPECIAL_EXTRA_PREFER_OPTIONS;
