export const QUESTION_METADATA: Record<string, { title: string; description: string }> = {
  plan_prefer: { title: "Travel Schedule", description: "How do you like to plan your trip?" },
  vibe_prefer: { title: "Travel Vibe", description: "What kind of destination do you prefer?" },
  places_prefer: { title: "Interests", description: "What are you most excited to explore?" },
};

export const QUESTION_ORDER = ["plan_prefer", "vibe_prefer", "places_prefer"];

export const IMAGE_MAP: Record<string, string> = {
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
