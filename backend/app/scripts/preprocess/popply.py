"""Popply 팝업스토어 원본 데이터 전처리

raw/popply.jsonl → preprocessed/popply_팝업스토어.json

- 서울 외 지역 제외
- 종료일이 수집일 이전인 건 제외
- 이모지 제거
- place는 전처리에서 만들지 않음 (llm_text 생성 시 LLM이 추출)
"""

import json
import logging
import re
from datetime import date

from .config import PREPROCESSED_DIR, RAW_DIR, clean_title, clean_value, enrich_geo, strip_html

log = logging.getLogger(__name__)

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U0001D400-\U0001D7FF"
    "\U00002600-\U000026FF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "\U00002B50"
    "\U0000203C-\U00002BFF"
    "]+",
    flags=re.UNICODE,
)


# 라벨 역할 이모지 → 한글 치환
_LABEL_EMOJI_MAP = [
    (r"📍\s*(?:장소\s*[:：]\s*)?", "장소: "),
    (r"📅\s*(?:일정\s*[:：]\s*)?", "일정: "),
    (r"⏰\s*(?:시간\s*[:：]\s*)?", "시간: "),
    (r"📞\s*(?:전화\s*[:：]\s*)?", "전화: "),
    (r"🎁\s*", ""),
    (r"✅\s*", "- "),
]


def _clean_description(text: str) -> str:
    """팝업스토어 description 텍스트 정리."""
    if not text:
        return ""
    # 1. HTML 태그 제거
    text = re.sub(r"<[^>]+>", " ", text)
    # 2. 라벨 이모지 → 한글 치환 (제거 전에 먼저 처리)
    for pattern, replacement in _LABEL_EMOJI_MAP:
        text = re.sub(pattern, replacement, text)
    # 3. 나머지 이모지 제거
    text = _EMOJI_RE.sub("", text)
    # 4. 동그라미 숫자 제거
    text = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", "", text)
    # 5. 장식 괄호 제거
    text = re.sub(r"[⟪⟫〈〉《》「」『』【】〔〕]", "", text)
    # 6. HTML 엔티티 제거
    text = re.sub(r"&\w+;|&#\d+;", " ", text)
    # 7. 연속 줄바꿈 최대 2개
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 8. 연속 공백 정리 (줄바꿈 유지)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _extract_id(url: str) -> str:
    m = re.search(r"/popup/(\d+)", url or "")
    return m.group(1) if m else url or ""


def _process_one(raw: dict) -> dict:
    """원본 1건을 통일 스키마로 변환."""
    desc_raw = raw.get("description", "")
    description = clean_value(_clean_description(desc_raw))

    result = {
        "contentid": _extract_id(raw.get("url", "")),
        "title": clean_title(clean_value(raw.get("name")) or ""),
        "contenttypeid": "콘텐츠",
        "image": (raw.get("images") or [None])[0] if isinstance(raw.get("images"), list) else clean_value(raw.get("images")),
        "addr": clean_value(raw.get("location")),
        "usetime": clean_value(raw.get("hours")),
        "fee": clean_value(raw.get("fee")),
        "parking": clean_value(raw.get("parking")),
        "description": description,
        "website": clean_value(raw.get("url")),
        "category_depth": "팝업스토어",
        # 고유 필드
        "startDate": (clean_value(raw.get("startDate")) or "")[:10] or None,
        "endDate": (clean_value(raw.get("endDate")) or "")[:10] or None,
    }

    # amenity 고유 필드
    for field in ["kids", "pet", "wifi", "photo", "food_ban", "adult_only", "reservation"]:
        val = clean_value(raw.get(field))
        if val:
            result[field] = val

    # None 값 제거
    result = {k: v for k, v in result.items() if v is not None}
    return enrich_geo(result)


def preprocess():
    """Popply 전처리."""
    input_path = RAW_DIR / "popply.jsonl"
    if not input_path.exists():
        log.warning("[popply] 원본 파일 없음: %s", input_path)
        return

    today = date.today().isoformat()
    results = []
    skipped_region = 0
    skipped_expired = 0

    with open(input_path, encoding="utf-8") as f:
        for line in f:
            try:
                raw = json.loads(line)

                # 서울 외 지역 제외
                location = raw.get("location", "")
                if location and "서울" not in location:
                    skipped_region += 1
                    continue

                # 종료일이 수집일 이전이면 제외
                end_date = (raw.get("endDate") or "")[:10]
                if end_date and end_date < today:
                    skipped_expired += 1
                    continue

                results.append(_process_one(raw))
            except (json.JSONDecodeError, KeyError) as e:
                log.warning("[popply] 파싱 실패: %s", e)

    output_path = PREPROCESSED_DIR / "popply_팝업스토어.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    log.info("[popply] %d건 → %s (지역제외 %d건, 만료제외 %d건)",
             len(results), output_path.name, skipped_region, skipped_expired)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    preprocess()
