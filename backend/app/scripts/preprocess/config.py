"""전처리 파이프라인 공통 설정"""

import asyncio
import logging
import re
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_ENV_PATH)

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
RAW_DIR = DATA_DIR / "raw"
PREPROCESSED_DIR = DATA_DIR / "preprocessed"
PREPROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# TourAPI contenttypeid → 카테고리명
TOURAPI_TYPE_MAP = {
    "12": "관광지",
    "14": "문화시설",
    "28": "레포츠",
    "32": "숙박",
    "39": "음식점",
}

# VisitSeoul cate_depth → contenttypeid 매핑
VISITSEOUL_TYPE_MAP = {
    "문화관광": "관광지",
    "역사관광": "관광지",
    "자연관광": "관광지",
    "체험관광": "관광지",
    "쇼핑": "투어",
    "음식": "음식점",
    "숙박": "숙박",
}

# VisitSeoul 수집/전처리 제외 카테고리
VISITSEOUL_EXCLUDE = {"축제/공연/행사"}

# HTML/CSS 제거 패턴
_CSS_BLOCK_RE = re.compile(r"\.[\w\-. >:*+~]+\{[^}]*\}")  # .class{...} 블록
_STYLE_TAG_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL)
_HTML_RE = re.compile(r"<[^>]+>")
_HTML_ENTITY_RE = re.compile(r"&\w+;|&#\d+;")
_WHITESPACE_RE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    """HTML 태그, CSS 블록, HTML 엔티티 제거 및 공백 정리."""
    if not text:
        return ""
    text = _STYLE_TAG_RE.sub(" ", text)
    text = _CSS_BLOCK_RE.sub(" ", text)
    text = _HTML_RE.sub(" ", text)
    text = _HTML_ENTITY_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def first_sentence(text: str) -> str:
    """첫 문장 추출 (summary용)."""
    if not text:
        return ""
    clean = strip_html(text)
    for sep in [".", "。", "\n"]:
        idx = clean.find(sep)
        if idx > 0:
            return clean[: idx + 1].strip()
    return clean[:200].strip()


_BRACKET_RE = re.compile(r"\[([^\]]*)\]")


def clean_title(title: str) -> str:
    """title에서 [내용] 통째로 제거."""
    if not title:
        return ""
    return _BRACKET_RE.sub("", title).strip()


def clean_value(val):
    """빈값 정리. 빈 문자열, None, '없음' 등은 None 반환."""
    if val is None:
        return None
    if isinstance(val, str):
        val = val.strip()
        if not val or val in ("없음", "null", "None", "-"):
            return None
    return val


# ── geo / addr_tokens 공통 함수 ──

_log = logging.getLogger(__name__)

# 이벤트 루프를 하나 유지해서 async 함수를 sync에서 호출
_loop: asyncio.AbstractEventLoop | None = None


def _run_async(coro):
    """async 함수를 sync에서 실행. 이벤트 루프를 재사용."""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop.run_until_complete(coro)

ADDR_TOKEN_SUFFIXES = ("시", "군", "구", "동", "읍", "면", "리", "로", "길")
ADDR_TOKEN_STOPWORDS = {"", "대한민국", "한국"}
ADDR_TOKEN_MAX = 24


def _safe_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        parsed = float(value)
        if parsed != parsed:
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def build_addr_tokens(addr: str) -> list[str]:
    """주소 문자열에서 검색용 토큰 리스트 생성."""
    if not addr:
        return []
    text = addr.lower().replace("(", " ").replace(")", " ")
    text = re.sub(r"(?<!\d)-|-(?!\d)", " ", text)
    text = re.sub(r"[,/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    raw_tokens = re.findall(r"\d+-\d+|[가-힣a-z0-9]+", text)
    tokens: list[str] = []
    for token in raw_tokens:
        if token in ADDR_TOKEN_STOPWORDS:
            continue
        if len(token) == 1 and not token.isdigit():
            continue
        tokens.append(token)
        if len(token) > 1 and token.endswith(ADDR_TOKEN_SUFFIXES):
            stem = token[:-1].strip()
            if stem and stem not in ADDR_TOKEN_STOPWORDS and (len(stem) > 1 or stem.isdigit()):
                tokens.append(stem)

    deduped: list[str] = []
    for token in tokens:
        if token not in deduped:
            deduped.append(token)
        if len(deduped) >= ADDR_TOKEN_MAX:
            break
    return deduped


def enrich_geo(item: dict) -> dict:
    """mapx/mapy로 geo 필드 생성. 없으면 addr로 지오코딩. 이후 mapx/mapy 제거."""
    lat = _safe_float(item.get("mapy"))
    lon = _safe_float(item.get("mapx"))

    # mapx/mapy 없으면 주소 기반 지오코딩
    if (lat is None or lon is None) and item.get("addr"):
        from app.utils.geocoder import GeoCoder
        try:
            result = _run_async(GeoCoder.get_instance().geocoder(item["addr"]))
            if result:
                lat = result.get("lat")
                lon = result.get("lon")
                _log.info("  지오코딩: %s → (%s, %s)", item.get("addr", "")[:30], lat, lon)
        except Exception as e:
            _log.warning("  지오코딩 실패: %s → %s", item.get("addr", "")[:30], e)

    # geo 생성
    if (
        lat is not None
        and lon is not None
        and -90.0 <= lat <= 90.0
        and -180.0 <= lon <= 180.0
        and not (abs(lat) < 1e-9 and abs(lon) < 1e-9)
    ):
        item["geo"] = {"lat": lat, "lon": lon}

    # mapx/mapy 제거
    item.pop("mapx", None)
    item.pop("mapy", None)

    # addr_tokens 생성
    addr = item.get("addr", "")
    if addr:
        item["addr_tokens"] = build_addr_tokens(addr)

    return item
