export const SURVEY_IMAGE_MAP: Record<string, string> = {
    "빽빽한 일정": "/image/planning.jpg",
    "느슨한 일정": "/image/noplan.png",
    "붐비는 도시": "/image/crowded.jpg",
    "한적한 자연": "/image/lonely.jpg",
    "맛집": "/image/kfood.jpg",
    "역사적 명소": "/image/khistorical.jpg",
    "K-culture": "/image/kculture.png",
};

/** 백엔드 데이터 값(한국어) → 번역 키 매핑. 화면 표시 시 t(SURVEY_LABEL_KEY_MAP[value]) 사용 */
export const SURVEY_LABEL_KEY_MAP: Record<string, string> = {
    "빽빽한 일정": "survey.busySchedule",
    "느슨한 일정": "survey.relaxedSchedule",
    "붐비는 도시": "survey.crowdedCity",
    "한적한 자연": "survey.quietNature",
    "맛집": "survey.restaurants",
    "역사적 명소": "survey.historicalSites",
    "K-culture": "survey.kCulture",
};

export const SURVEY_ITEM_LABELS: Record<"plan" | "vibe" | "places", string> = {
    plan: "Travel Schedule",
    vibe: "Travel Vibe",
    places: "Interests",
};

/** 백엔드 데이터 값(한국어) → 번역 키 매핑 */
export const EXTRA_PREFER_LABEL_KEY_MAP: Record<string, string> = {
    "할랄": "survey.halal",
    "코셔": "survey.kosher",
    "비건": "survey.vegan",
    "휠체어 이용 가능": "survey.wheelchair",
    "반려동물": "survey.pets",
};

export const SPECIAL_EXTRA_PREFER_OPTIONS = [
    "할랄",
    "코셔",
    "비건",
    "휠체어 이용 가능",
    "반려동물",
];

export const SNAPSHOT_OPTIONS: Record<"plan" | "vibe" | "places", string[]> = {
    plan: ["빽빽한 일정", "느슨한 일정"],
    vibe: ["붐비는 도시", "한적한 자연"],
    places: ["맛집", "역사적 명소", "K-culture"],
};

export const EXTRA_PREFER_OPTIONS = SPECIAL_EXTRA_PREFER_OPTIONS;
