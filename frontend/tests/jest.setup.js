import '@testing-library/jest-dom'

// `jose` ships ESM-only entrypoints that Jest may not transform in this setup.
// For current tests we only need `decodeJwt`, so provide a minimal mock.
jest.mock('jose', () => ({
  decodeJwt: jest.fn(() => ({ exp: Math.floor(Date.now() / 1000) + 3600 })),
}))

jest.mock('@/i18n/useTranslation', () => ({
  useTranslation: () => ({
    t: (key, params) => {
      const labels = {
        "pipeline.imageAnalysis": "이미지 분석",
        "pipeline.intent": "의도 분석",
        "pipeline.planner": "여행 계획 수립",
        "pipeline.geocoder": "위치 좌표 확인",
        "pipeline.retriever": "장소 검색",
        "pipeline.retrieverRetry": "반경 확대 후 장소 검색",
        "pipeline.webSearch": "웹 검색",
        "pipeline.executor": "답변 생성",
        "pipeline.executorMissing": "추가 정보 확인",
        "pipeline.executorGeneral": "일반 답변 생성",
        "login.googleStart": "Google로 시작하기",
      };
      if (key === "pipeline.running") return `${params?.label} 중...`;
      if (key === "pipeline.done") return `${params?.label} 완료`;
      return labels[key] || key;
    },
    language: "ko",
    setLanguage: jest.fn(),
  }),
}));
