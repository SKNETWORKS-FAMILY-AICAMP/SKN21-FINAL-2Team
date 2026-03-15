"""
OCR 서비스 — Google Cloud Vision API (REST 방식, API Key 인증)

날짜(필수)와 시간(선택)을 이미지에서 추출합니다.
"""

import os
import re
import base64
import httpx
from datetime import datetime
from typing import Optional


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


async def extract_datetime_from_image(image_bytes: bytes) -> dict:
    """
    Google Cloud Vision API(REST)로 이미지 텍스트 추출 후
    날짜(필수)·시간(선택) 파싱하여 반환.

    반환 형태:
        {
            "date": "2024-12-25" | None,
            "time": "14:30" | None,
            "raw_text": "...(OCR 전체 텍스트)...",
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

    return {
        "date": date_str,
        "time": time_str,
        "raw_text": raw_text,
        "error": None if date_str else "날짜를 찾지 못했습니다.",
    }
