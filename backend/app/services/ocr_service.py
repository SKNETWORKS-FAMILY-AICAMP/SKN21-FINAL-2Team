"""
OCR 서비스 — Google Cloud Vision API (REST 방식, API Key 인증)
+ LLM (HuggingFace Inference API: Qwen2.5-3B-Instruct / OpenAI 선택) 기반 상세 필드 추출

날짜(필수)와 시간(선택)을 이미지에서 추출합니다.
챗봇과 독립적으로 LLM을 선택할 수 있습니다.
"""

import json
import os
import re
import base64
import httpx
from datetime import datetime
from typing import Optional, Any
from app.core.llm_factory import LLMFactory
from app.utils.config import OCR_LLM_MODEL, OCR_LLM_TYPE, OCR_HF_MODEL_ID


# 지원하는 날짜 패턴 목록 (다양한 국가/포맷 티켓 대응)
DATE_PATTERNS = [
    # YYYY-MM-DD / YYYY/MM/DD / YYYY.MM.DD
    (r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", "%Y-%m-%d"),
    # DD-MM-YYYY / DD/MM/YYYY / DD.MM.YYYY
    (r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", "%d-%m-%Y"),
    # MM/DD/YYYY (미국식)
    (r"(\d{1,2})/(\d{1,2})/(\d{4})", "%m/%d/%Y"),
    # 한국어: YYYY년 M월 D일
    (r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", "%Y년 %m월 %d일"),
    # 한국어: MM월 DD일
    (r"(\d{1,2})월\s*(\d{1,2})일", None),  # 연도 없는 경우 별도 처리
    # 영문: DD Mon YYYY (예: 25 Dec 2024)
    (r"(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})", "%d %B %Y"),
]

# 시간 패턴
TIME_PATTERNS = [
    r"(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s*([AP]M))?",  # HH:MM[:SS] [AM/PM]
    r"(\d{1,2})시\s*(\d{2})분",                          # 한국어: HH시 MM분
]

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
    "일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6,
    "칠": 7, "팔": 8, "구": 9, "십": 10, "십일": 11, "십이": 12,
}


def _parse_date(text: str) -> Optional[str]:
    """텍스트에서 날짜 문자열 파싱 → 'YYYY-MM-DD' 반환"""

    # YYYY-MM-DD / YYYY/MM/DD / YYYY.MM.DD
    m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if m:
        try:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{mo:02d}-{d:02d}"
        except ValueError:
            pass

    # 한국어: YYYY년 M월 D일
    m = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", text)
    if m:
        try:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return f"{y:04d}-{mo:02d}-{d:02d}"
        except ValueError:
            pass

    # 영문: 25 Dec 2024 / December 25 2024
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})", text)
    if m:
        mon_str = m.group(2).lower()
        if mon_str in MONTH_MAP:
            try:
                d, mo, y = int(m.group(1)), MONTH_MAP[mon_str], int(m.group(3))
                return f"{y:04d}-{mo:02d}-{d:02d}"
            except ValueError:
                pass

    # DD/MM/YYYY (유럽식)
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{mo:02d}-{d:02d}"
        except ValueError:
            pass

    return None


def _parse_time(text: str) -> Optional[str]:
    """텍스트에서 시간 문자열 파싱 → 'HH:MM' 반환 (없으면 None)"""

    # HH:MM 또는 HH:MM:SS [AM/PM]
    m = re.search(r"(\d{1,2}):(\d{2})(?::\d{2})?(\s*[AP]M)?", text, re.IGNORECASE)
    if m:
        try:
            h, mi = int(m.group(1)), int(m.group(2))
            suffix = (m.group(3) or "").strip().upper()
            if suffix == "PM" and h != 12:
                h += 12
            elif suffix == "AM" and h == 12:
                h = 0
            if 0 <= h <= 23 and 0 <= mi <= 59:
                return f"{h:02d}:{mi:02d}"
        except ValueError:
            pass

    # 한국어: HH시 MM분
    m = re.search(r"(\d{1,2})시\s*(\d{2})분", text)
    if m:
        try:
            h, mi = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mi <= 59:
                return f"{h:02d}:{mi:02d}"
        except ValueError:
            pass

    return None


def _normalize_llm_output(data: dict[str, Any], category: str) -> dict[str, Any]:
    """
    LLM 출력 정규화 (Qwen2.5:3b 등 로컬 모델의 출력 편차 보정)
    
    주요 정규화:
    - 필드명 표준화 (e.g., "차량번호" → "차량 번호")
    - 시간 범위 처리 (e.g., "14:30~16:30" → "14:30")
    - 공백/정리
    - 예상치 못한 추가정보 제거
    """
    if not data:
        return {}
    
    normalized = {}
    
    # 카테고리별 필드명 매핑
    field_mappings = {
        "transportation": {
            "차량번호": "차량 번호",
            "vehicle_number": "차량 번호",
        },
        "hotel": {},
        "activity": {},
        "restaurant": {},
        "etc": {}
    }
    
    mapping = field_mappings.get(category, {})
    
    for key, value in data.items():
        # 필드명 정규화
        normalized_key = mapping.get(key, key)
        
        if not value:
            normalized[normalized_key] = ""
            continue
        
        if isinstance(value, str):
            value = value.strip()
            
            # 시간 필드 범위 처리: 활동/공연 '시간'만 범위 처리, 도착/체크아웃 시간은 제외
            # (도착시간, 체크아웃시간은 정확한 시간 1개이므로 범위 처리 X)
            if normalized_key == "시간" and ("~" in value or "-" in value):
                # 공연/활동 시간처럼 범위인 경우만 첫 번째 시간 추출
                first_time = re.split(r"[~\-~]", value)[0].strip()
                if re.match(r"\d{2}:\d{2}", first_time):
                    value = first_time
            
            # 값에서 불필요한 접미사 제거 (Qwen 특성)
            # e.g., "KONJIAM RESORT 레스토랑" → "KONJIAM RESORT"
            if "식당이름" in normalized_key or normalized_key == "식당이름":
                value = re.sub(r"\s*(레스토랑|카페|식당|음식점)$", "", value)
            
            # 객실 정보에서 타입 정보 정리
            if "방 호실" in normalized_key or normalized_key == "방 호실":
                # e.g., "Superior Twin 싱글2" 그대로 유지하되, 중복 제거
                value = re.sub(r"\s+", " ", value)
        
        normalized[normalized_key] = value
    
    # 좌석 번호 패턴 검증 (교통 티켓)
    if category == "transportation" and "좌석 번호" in normalized:
        seat_value = normalized["좌석 번호"]
        # 좌석 번호는 보통 숫자+알파벳 조합 (예: 13D, 7A)
        if not re.match(r"^\d{1,2}[A-Z]$", seat_value):
            normalized["좌석 번호"] = ""
    return normalized


async def extract_datetime_from_image(image_bytes: bytes, category: Optional[str] = None) -> dict:
    """
    Google Cloud Vision API(REST)로 이미지 텍스트 추출 후
    날짜(필수)·시간(선택) 파싱하여 반환.
    
    LLM을 통한 상세 필드 추출 지원:
    - OpenAI: gpt-4o-mini (권장, 고정확도)
    - HuggingFace: Qwen/Qwen2.5-3B-Instruct (HF Inference API, HF_TOKEN 필요)

    반환 형태:
        {
            "date": "2024-12-25" | None,
            "time": "14:30" | None,
            "raw_text": "...(OCR 전체 텍스트)...",
            "details": {...} | None,
            "error": None | "에러 메시지"
        }
    """
    api_key = os.getenv("GOOGLE_VISION_API_KEY")
    if not api_key:
        return {"date": None, "time": None, "raw_text": "", "error": "GOOGLE_VISION_API_KEY가 설정되지 않았습니다."}

    # 이미지를 base64로 인코딩
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # Vision API 요청 본문
    payload = {
        "requests": [
            {
                "image": {"content": image_b64},
                "features": [{"type": "TEXT_DETECTION"}],
            }
        ]
    }

    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        return {"date": None, "time": None, "raw_text": "", "error": f"Vision API 오류: {e.response.status_code}"}
    except Exception as e:
        return {"date": None, "time": None, "raw_text": "", "error": str(e)}

    # OCR 결과에서 전체 텍스트 추출
    try:
        annotations = data["responses"][0].get("textAnnotations", [])
        if not annotations:
            return {"date": None, "time": None, "raw_text": "", "error": "이미지에서 텍스트를 찾을 수 없습니다."}
        raw_text = annotations[0].get("description", "")
    except (KeyError, IndexError):
        return {"date": None, "time": None, "raw_text": "", "error": "OCR 결과 파싱 오류"}

    date_str = _parse_date(raw_text)
    time_str = _parse_time(raw_text)

    details = None
    if category and raw_text:
        # OCR 전용 LLM 사용 (챗봇과 독립적)
        llm = LLMFactory.get_llm(
            model=OCR_LLM_MODEL,
            temperature=0,
            llm_type=OCR_LLM_TYPE,
            base_url=OCR_HF_MODEL_ID  # HuggingFace 일 때는 미사용 (하위 호환)
        )
        
        # Category-specific prompt mapping (좌석 번호 정의/예시 추가)
        category_prompts = {
            "transportation": (
                "교통 티켓입니다. '날짜', '출발지', '출발시간', '도착지', '도착시간', '승차홈', '차량 번호', '좌석 번호'를 추출해주세요.\n"
                "좌석 번호는 실제로 앉는 좌석을 의미하며, 예시로 '13D', '7A' 등 숫자+알파벳 조합입니다.\n"
                "호차 번호(예: '2호차')나 승차권 번호(예: '83125-1101-10000-00')와 구분하세요.\n"
                "좌석 번호는 '좌석번호' 또는 '좌석'이라는 단어 근처에 위치한 값을 추출하세요."
            ),
            "hotel": (
                "호텔 예약증입니다. '숙소 이름', '체크인 날짜', '체크인 시간', '체크아웃 날짜', '체크아웃 시간', '방 호실'을 추출해주세요.\n"
                "체크인 정보는 '체크인' 또는 'Check-in' 라벨 근처에 있으며, 보통 'YYYY.MM.DD HH:MM' 또는 'YYYY.MM.DD() HH:MM' 형식입니다.\n"
                "체크아웃 정보는 '체크아웃' 또는 'Check-out' 라벨 근처에 있으며, 같은 형식입니다.\n"
                "날짜와 시간이 함께 표시되어 있으면, 날짜 부분(' YYYY.MM.DD')과 시간 부분('HH:MM')을 분리해서 추출하세요.\n"
                "예시: '2018.12.03() 15:00'에서 체크인 날짜='2018-12-03', 체크인 시간='15:00'"
            ),
            "activity": "공연/활동 티켓입니다. '날짜', '이름', '시간', '장소', '좌석 번호'를 추출해주세요.",
            "restaurant": "식당 예약증입니다. '날짜', '식당이름', '예약시간', '예약자명', '예약 인원'을 추출해주세요.",
            "etc": "기타 예약증/영수증입니다. '예약내역', '시간', '예약자명'을 추출해주세요.",
        }
        prompt_instruction = category_prompts.get(category, category_prompts["etc"])
        
        system_prompt = (
            f"당신은 OCR 텍스트에서 예약 정보를 추출하는 어시스턴트입니다.\n"
            f"다음 텍스트에서 {prompt_instruction}\n\n"
            f"추출 규칙 (반드시 따를 것):\n"
            f"1. 날짜 항목은 반드시 'YYYY-MM-DD' 형식만 사용하세요 (예: 2026-03-25)\n"
            f"2. 시간 항목은 반드시 '24시간 표기법 HH:MM'만 사용하세요 (예: 16:30)\n"
            f"   - 출발시간, 도착시간, 체크인 시간, 체크아웃 시간, 예약시간 등은 정확한 시간 1개만 추출하세요 (범위 아님)\n"
            f"   - 공연/활동 시간처럼 범위가 명확한 경우에만 시작 시간을 추출하세요 (예: '14:30~16:30' → '14:30')\n"
            f"3. Key 이름은 위에서 요청한 한글 명칭을 정확히 사용하세요 (오타나 변형 금지)\n"
            f"4. 결과는 JSON 형식만 반환하세요 (설명 텍스트 없음)\n"
            f"5. 찾을 수 없는 항목은 빈 문자열 \"\" 을 사용하세요 (null 금지)\n"
            f"6. 값에는 추가정보를 붙이지 마세요. 원문 그대로만 추출하세요\n"
            f"   (예: 식당명이 'KONJIAM RESORT'면 '레스토랑'을 붙이지 말 것)\n"
            f"7. 예상치 못한 추가 필드는 추가하지 마세요"
        )
        
        try:
            # invoke LLM
            response = await llm.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text}
            ])
            response_content = response.content.strip()
            # Clean up potential markdown formatting block
            if response_content.startswith("```json"):
                response_content = response_content[7:]
            if response_content.startswith("```"):
                response_content = response_content[3:]
            if response_content.endswith("```"):
                response_content = response_content[:-3]
                
            details = json.loads(response_content.strip())
            
            # 후처리: LLM 출력 정규화 (특히 Qwen 모델)
            details = _normalize_llm_output(details, category)
            
        except Exception as e:
            print(f"LLM details extraction failed: {e}")
            details = None

    return {
        "date": date_str,
        "time": time_str,
        "raw_text": raw_text,
        "details": details,
        "error": None if date_str else "날짜를 찾지 못했습니다.",
    }
