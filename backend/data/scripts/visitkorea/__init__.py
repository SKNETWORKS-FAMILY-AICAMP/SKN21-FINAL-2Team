"""
visitkorea (TourAPI) 데이터 파이프라인
======================================
Step 1: detailCommon2로 카테고리별 장소 수집
Step 2: detailIntro2로 장소별 상세 정보 수집
Step 3: 스키마 평탄화 + 텍스트 전처리 + 중복 제거 + tags/llm_text 생성
Step 4: 네이버 지도 API로 폐업 장소 필터링
Step 5: OpenAI 기반 llm_text 보강 (선택)
"""
