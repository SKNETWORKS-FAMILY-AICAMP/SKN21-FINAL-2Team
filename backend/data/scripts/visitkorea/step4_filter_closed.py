"""
Step 4: 네이버 지도 API로 폐업 장소 필터링
==========================================
네이버 지역검색 API로 장소 상태를 점검하고 JSONL을 갱신한다.
- 영업 중(open) / 검토 필요(review_needed) / 폐업 의심(closed_suspected) 분류
- 상호명 한글↔영어 음차 변환으로 검색 정확도 향상
- 부가: detailIntro2 null 항목을 네이버 검색으로 보완

사용법:
  cd backend
  # 폐업 필터링
  PYTHONPATH=. python -u data/scripts/visitkorea/step4_filter_closed.py INPUT.jsonl
  PYTHONPATH=. python -u data/scripts/visitkorea/step4_filter_closed.py INPUT.jsonl --include-review

  # detailIntro2 null 보완
  PYTHONPATH=. python -u data/scripts/visitkorea/step4_filter_closed.py --supplement-intro
"""

# 이 파일은 기존 check_places_with_naver.py를 그대로 유지하면서
# supplement_intro_with_naver.py 기능을 추가한 통합 스크립트이다.
# check_places_with_naver.py의 핵심 로직(NaverPlaceChecker 등)은
# 그대로 보존되어 있다.

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        return False


# ══════════════════════════════════════════════════════════════
# 상수
# ══════════════════════════════════════════════════════════════

LOCAL_SEARCH_ENDPOINT = "https://openapi.naver.com/v1/search/local.json"
GEOCODE_ENDPOINT = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
DEFAULT_TIMEOUT = 10

TITLE_REPLACEMENT_THRESHOLD = 2.65
ADDRESS_REPLACEMENT_THRESHOLD = 2.15
OPEN_THRESHOLD = 2.6
REVIEW_THRESHOLD = 1.65
CLOSED_DISTANCE_M = 180

DATA_DIR = Path(__file__).resolve().parents[2] / "add(image,info)" / "visitkorea_only"
PREPROCESSED_DIR = Path(__file__).resolve().parents[2] / "preprocessed"


# ══════════════════════════════════════════════════════════════
# 영→한 음차 변환
# ══════════════════════════════════════════════════════════════

COMMON_WORD_TRANSLITERATIONS: dict[str, str] = {
    "and": "앤", "bar": "바", "bbq": "바비큐", "beef": "비프",
    "bistro": "비스트로", "burger": "버거", "cafe": "카페",
    "campus": "캠퍼스", "club": "클럽", "coffee": "커피",
    "deli": "델리", "dream": "드림", "gallery": "갤러리",
    "garden": "가든", "guest": "게스트", "guesthouse": "게스트하우스",
    "grill": "그릴", "hall": "홀", "hanok": "한옥", "home": "홈",
    "hostel": "호스텔", "hotel": "호텔", "house": "하우스",
    "kstar": "케이스타", "k-star": "케이스타", "korea": "코리아",
    "lounge": "라운지", "motel": "모텔", "museum": "뮤지엄",
    "noodle": "누들", "place": "플레이스", "pub": "펍",
    "restaurant": "레스토랑", "road": "로드", "room": "룸",
    "shop": "샵", "stay": "스테이", "steak": "스테이크",
    "studio": "스튜디오", "suite": "스위트", "sweet": "스위",
    "tea": "티", "terrace": "테라스", "tour": "투어",
    "villa": "빌라", "view": "뷰", "wine": "와인",
}

LETTER_TO_HANGUL: dict[str, str] = {
    "a": "아", "b": "브", "c": "크", "d": "드", "e": "이",
    "f": "프", "g": "그", "h": "하", "i": "이", "j": "제",
    "k": "케", "l": "엘", "m": "엠", "n": "엔", "o": "오",
    "p": "피", "q": "큐", "r": "르", "s": "스", "t": "트",
    "u": "유", "v": "브", "w": "우", "x": "엑스", "y": "와이", "z": "즈",
}


# ══════════════════════════════════════════════════════════════
# 유틸 함수
# ══════════════════════════════════════════════════════════════

def _load_env_file_fallback(path: Path) -> None:
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except Exception:
        return


def load_env_candidates() -> None:
    this = Path(__file__).resolve()
    backend_dir = this.parents[3]
    project_root = this.parents[4]
    for candidate in (project_root / ".env", backend_dir / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)
            _load_env_file_fallback(candidate)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


def strip_parentheses(value: str) -> str:
    return normalize_space(re.sub(r"\([^)]*\)", " ", value or ""))


def clean_address(value: str) -> str:
    cleaned = strip_parentheses(value)
    cleaned = cleaned.replace("특별시", "").replace("광역시", "")
    return normalize_space(cleaned)


def normalize_key(value: str) -> str:
    value = strip_html(value)
    value = normalize_space(value).lower()
    return re.sub(r"[^0-9a-z가-힣]+", "", value)


def only_digits(value: str) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def tokenize_title(value: str) -> list[str]:
    return [t for t in re.findall(r"[0-9A-Za-z가-힣]+", normalize_space(value)) if t]


def tokenize_address(value: str) -> list[str]:
    return [t for t in re.findall(r"[0-9A-Za-z가-힣-]+", clean_address(value)) if t]


def contains_hangul(value: str) -> bool:
    return bool(re.search(r"[가-힣]", value or ""))


def contains_roman_letters(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]", value or ""))


def extract_parenthetical_candidates(title: str) -> list[str]:
    found = [normalize_space(p) for p in re.findall(r"\(([^)]*)\)", title or "") if normalize_space(p)]
    return dedupe_strings(found)


def split_alpha_numeric(token: str) -> list[str]:
    return [p for p in re.findall(r"[A-Za-z]+|\d+", token or "") if p]


def dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        n = normalize_space(v)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def transliterate_token_to_korean(token: str) -> str:
    token = token.strip().lower()
    if not token:
        return ""
    if token in COMMON_WORD_TRANSLITERATIONS:
        return COMMON_WORD_TRANSLITERATIONS[token]
    for suffix, ko in [("house", "하우스"), ("hotel", "호텔"), ("stay", "스테이")]:
        if token.endswith(suffix) and len(token) > len(suffix):
            head_ko = transliterate_token_to_korean(token[:-len(suffix)])
            return f"{head_ko}{ko}" if head_ko else ko
    parts = split_alpha_numeric(token)
    if len(parts) > 1:
        merged = "".join(transliterate_token_to_korean(p) for p in parts)
        if merged:
            return merged
    token = token.replace("ph", "f").replace("oo", "u").replace("ee", "i")
    token = token.replace("ck", "k").replace("qu", "kw")
    syllables = re.findall(r"[^aeiouy]*[aeiouy]+(?:[^aeiouy](?![aeiouy]))?", token) or [token]
    converted: list[str] = []
    for syl in syllables:
        if syl in COMMON_WORD_TRANSLITERATIONS:
            converted.append(COMMON_WORD_TRANSLITERATIONS[syl])
            continue
        piece = "".join(LETTER_TO_HANGUL.get(c, "") for c in syl if c.isalpha())
        if piece:
            piece = piece.replace("으아", "와").replace("으오", "워").replace("하우스트", "하우스")
            converted.append(piece)
    merged = "".join(converted)
    if not merged:
        merged = "".join(LETTER_TO_HANGUL.get(c, "") for c in token if c.isalpha())
    return merged


def transliterate_title_variants(title: str) -> list[str]:
    if not contains_roman_letters(title):
        return []
    base = strip_parentheses(title)
    tokens = tokenize_title(base)
    alpha_tokens = [t for t in tokens if contains_roman_letters(t)]
    if not alpha_tokens:
        return []
    transliterated = [transliterate_token_to_korean(t) for t in alpha_tokens]
    transliterated = [t for t in transliterated if t]
    variants = ["".join(transliterated), " ".join(transliterated)]
    return dedupe_strings([v for v in variants if v])


def area_hint_from_address(addr: str) -> str:
    tokens = tokenize_address(addr)
    return " ".join(tokens[:2]) if len(tokens) >= 2 else (tokens[0] if tokens else "")


def road_hint_from_address(addr: str) -> str:
    tokens = tokenize_address(addr)
    road_tokens = [t for t in tokens if t.endswith(("로", "길")) or re.search(r"\d+-?\d*$", t)]
    return " ".join(road_tokens[:2])


def build_query_variants(item: dict[str, Any]) -> list[str]:
    title = normalize_space(str(item.get("title", "")))
    addr = clean_address(str(item.get("addr", "")))
    area_hint = area_hint_from_address(addr)
    road_hint = road_hint_from_address(addr)
    title_parts = [title, strip_parentheses(title), *extract_parenthetical_candidates(title)]
    korean_title_parts = [p for p in title_parts if contains_hangul(p)]
    english_to_korean = transliterate_title_variants(title)
    queries: list[str] = []
    for part in title_parts + english_to_korean:
        if not part:
            continue
        queries.append(part)
        if area_hint: queries.append(f"{part} {area_hint}")
        if road_hint: queries.append(f"{part} {road_hint}")
    if addr:
        queries.append(addr)
        if korean_title_parts:
            for part in korean_title_parts[:2]:
                queries.append(f"{addr} {part}")
        if road_hint: queries.append(f"{area_hint} {road_hint}".strip())
    return dedupe_strings(queries)


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def to_float(value: Any) -> float | None:
    try:
        if value in ("", None): return None
        return float(value)
    except (TypeError, ValueError):
        return None


def distance_meters(lat1, lon1, lat2, lon2) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    dy = (lat1 - lat2) * 111_320
    dx = (lon1 - lon2) * 88_000
    return (dx * dx + dy * dy) ** 0.5


# ══════════════════════════════════════════════════════════════
# 데이터 클래스
# ══════════════════════════════════════════════════════════════

@dataclass
class LocalSearchCandidate:
    query: str
    title: str
    road_address: str
    jibun_address: str
    telephone: str
    category: str
    link: str
    mapx: str
    mapy: str

    @property
    def best_address(self) -> str:
        return self.road_address or self.jibun_address

    @property
    def lat(self) -> float | None:
        if not self.mapy: return None
        if "." in self.mapy: return to_float(self.mapy)
        try: return int(self.mapy) / 10_000_000
        except ValueError: return None

    @property
    def long(self) -> float | None:
        if not self.mapx: return None
        if "." in self.mapx: return to_float(self.mapx)
        try: return int(self.mapx) / 10_000_000
        except ValueError: return None


@dataclass
class MatchResult:
    status: str
    score: float
    decision_reason: str
    candidate: LocalSearchCandidate | None
    searched_queries: list[str]
    name_similarity: float = 0.0
    address_similarity: float = 0.0
    distance_m: float | None = None


# ══════════════════════════════════════════════════════════════
# NaverPlaceChecker
# ══════════════════════════════════════════════════════════════

class NaverPlaceChecker:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT, sleep_ms: int = 120) -> None:
        self.timeout = timeout
        self.sleep_ms = sleep_ms
        self.search_client_id = (os.getenv("NAVER_SEARCH_CLIENT_ID") or os.getenv("NAVER_CLIENT_ID") or "").strip()
        self.search_client_secret = (os.getenv("NAVER_SEARCH_CLIENT_SECRET") or os.getenv("NAVER_CLIENT_SECRET") or "").strip()
        self.map_client_id = (os.getenv("NAVER_CLIENT_ID") or "").strip()
        self.map_client_secret = (os.getenv("NAVER_CLIENT_SECRET") or "").strip()
        self._geocode_cache: dict[str, dict[str, Any] | None] = {}

    def ensure_credentials(self) -> None:
        if not self.search_client_id or not self.search_client_secret:
            raise RuntimeError("NAVER_SEARCH_CLIENT_ID / NAVER_SEARCH_CLIENT_SECRET 또는 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 이 필요합니다.")

    def local_search(self, query: str, display: int = 5) -> list[LocalSearchCandidate]:
        headers = {"X-Naver-Client-Id": self.search_client_id, "X-Naver-Client-Secret": self.search_client_secret}
        params = {"query": query, "display": max(1, min(display, 5)), "sort": "comment"}
        response = requests.get(LOCAL_SEARCH_ENDPOINT, headers=headers, params=params, timeout=self.timeout)
        response.raise_for_status()
        results: list[LocalSearchCandidate] = []
        for item in response.json().get("items") or []:
            results.append(LocalSearchCandidate(
                query=query,
                title=strip_html(item.get("title") or ""),
                road_address=normalize_space(item.get("roadAddress") or ""),
                jibun_address=normalize_space(item.get("address") or ""),
                telephone=normalize_space(item.get("telephone") or ""),
                category=normalize_space(item.get("category") or ""),
                link=normalize_space(item.get("link") or ""),
                mapx=str(item.get("mapx") or "").strip(),
                mapy=str(item.get("mapy") or "").strip(),
            ))
        return results

    def geocode(self, query: str) -> dict[str, Any] | None:
        nq = normalize_space(query)
        if not nq: return None
        if nq in self._geocode_cache: return self._geocode_cache[nq]
        if not self.map_client_id or not self.map_client_secret:
            self._geocode_cache[nq] = None
            return None
        headers = {"X-NCP-APIGW-API-KEY-ID": self.map_client_id, "X-NCP-APIGW-API-KEY": self.map_client_secret}
        try:
            resp = requests.get(GEOCODE_ENDPOINT, headers=headers, params={"query": nq}, timeout=self.timeout)
            resp.raise_for_status()
            addresses = resp.json().get("addresses") or []
            if not addresses:
                self._geocode_cache[nq] = None
                return None
            target = addresses[0]
            result = {"lat": to_float(target.get("y")), "long": to_float(target.get("x")),
                       "road_address": normalize_space(target.get("roadAddress") or ""),
                       "jibun_address": normalize_space(target.get("jibunAddress") or "")}
            self._geocode_cache[nq] = result
            return result
        except requests.RequestException:
            self._geocode_cache[nq] = None
            return None

    def search_candidates(self, item: dict[str, Any]) -> tuple[list[str], list[LocalSearchCandidate]]:
        queries = build_query_variants(item)
        deduped: list[LocalSearchCandidate] = []
        seen: set[tuple[str, str]] = set()
        for query in queries:
            try:
                candidates = self.local_search(query)
            except requests.RequestException as exc:
                raise RuntimeError(f"네이버 지역검색 API 호출 실패: {exc}") from exc
            for c in candidates:
                key = (normalize_key(c.title), clean_address(c.best_address))
                if key not in seen:
                    seen.add(key)
                    deduped.append(c)
            if self.sleep_ms > 0:
                time.sleep(self.sleep_ms / 1000)
        return queries, deduped

    def evaluate_match(self, item: dict[str, Any], queries: list[str], candidates: list[LocalSearchCandidate]) -> MatchResult:
        if not candidates:
            return MatchResult(status="no_match", score=0.0, decision_reason="네이버 검색 결과 없음",
                               candidate=None, searched_queries=queries)

        item_title = normalize_space(str(item.get("title", "")))
        item_title_key = normalize_key(item_title)
        item_title_ko_variants = transliterate_title_variants(item_title)
        item_addr = clean_address(str(item.get("addr", "")))
        item_addr_tokens = set(tokenize_address(item_addr))
        input_lat = to_float(item.get("mapy"))
        input_lon = to_float(item.get("mapx"))
        tel_digits = only_digits(item.get("tel"))

        best_candidate = None
        best_score = -1.0
        best_reason = ""
        best_name_sim = best_addr_sim = 0.0
        best_distance: float | None = None

        for c in candidates:
            c_title_key = normalize_key(c.title)
            c_addr_tokens = set(tokenize_address(clean_address(c.best_address)))

            name_sim = 0.0
            if item_title_key and c_title_key:
                if item_title_key == c_title_key: name_sim = 1.0
                elif item_title_key in c_title_key or c_title_key in item_title_key: name_sim = 0.86
                else: name_sim = jaccard_similarity(set(tokenize_title(item_title_key)), set(tokenize_title(c_title_key)))

            translit_sim = 0.0
            for variant in item_title_ko_variants:
                vk = normalize_key(variant)
                if not vk: continue
                if vk == c_title_key: translit_sim = max(translit_sim, 0.95)
                elif vk in c_title_key or c_title_key in vk: translit_sim = max(translit_sim, 0.72)

            addr_sim = jaccard_similarity(item_addr_tokens, c_addr_tokens)
            if item_addr and clean_address(c.best_address) == item_addr: addr_sim = 1.0
            tel_sim = 1.0 if tel_digits and tel_digits == only_digits(c.telephone) else 0.0

            c_lat, c_long = c.lat, c.long
            if (c_lat is None or c_long is None) and c.best_address:
                geo = self.geocode(c.best_address)
                if geo: c_lat, c_long = geo.get("lat"), geo.get("long")

            c_dist = distance_meters(input_lat, input_lon, c_lat, c_long)
            dist_score = 0.0
            if c_dist is not None:
                if c_dist <= 80: dist_score = 1.0
                elif c_dist <= 180: dist_score = 0.72
                elif c_dist <= 350: dist_score = 0.35
                else: dist_score = -0.3

            score = (max(name_sim, translit_sim) * 1.9 + addr_sim * 1.65 + tel_sim * 0.8 + dist_score * 0.9)
            if c.query and c.query == c.title: score += 0.12

            if score > best_score:
                best_candidate = c
                best_score = score
                best_name_sim = max(name_sim, translit_sim)
                best_addr_sim = addr_sim
                best_distance = c_dist
                best_reason = f"name={best_name_sim:.2f}, addr={best_addr_sim:.2f}, dist={c_dist if c_dist is not None else 'n/a'}"

        if best_candidate is None:
            return MatchResult(status="no_match", score=0.0, decision_reason="후보 선택 실패",
                               candidate=None, searched_queries=queries)
        if best_score >= OPEN_THRESHOLD:
            return MatchResult(status="open", score=best_score, decision_reason=best_reason,
                               candidate=best_candidate, searched_queries=queries,
                               name_similarity=best_name_sim, address_similarity=best_addr_sim, distance_m=best_distance)
        if best_score >= REVIEW_THRESHOLD:
            return MatchResult(status="review_needed", score=best_score, decision_reason=f"부분 일치: {best_reason}",
                               candidate=best_candidate, searched_queries=queries,
                               name_similarity=best_name_sim, address_similarity=best_addr_sim, distance_m=best_distance)
        if best_distance is not None and best_distance <= CLOSED_DISTANCE_M:
            status, reason = "review_needed", f"주소는 가깝지만 상호 불일치: {best_reason}"
        else:
            status, reason = "closed_suspected", f"강한 일치 후보 없음: {best_reason}"
        return MatchResult(status=status, score=best_score, decision_reason=reason,
                           candidate=best_candidate, searched_queries=queries,
                           name_similarity=best_name_sim, address_similarity=best_addr_sim, distance_m=best_distance)

    def check_item(self, item: dict[str, Any]) -> MatchResult:
        queries, candidates = self.search_candidates(item)
        return self.evaluate_match(item, queries, candidates)


# ══════════════════════════════════════════════════════════════
# 결과 적용
# ══════════════════════════════════════════════════════════════

def apply_match_result(item: dict[str, Any], result: MatchResult,
                       preserve_original: bool = False, include_review: bool = False) -> dict[str, Any]:
    updated = dict(item)
    candidate = result.candidate
    if include_review:
        audit = {"status": result.status, "score": round(result.score, 4),
                 "decision_reason": result.decision_reason, "searched_queries": result.searched_queries,
                 "name_similarity": round(result.name_similarity, 4),
                 "address_similarity": round(result.address_similarity, 4),
                 "distance_m": round(result.distance_m, 2) if result.distance_m is not None else None}
        if candidate is not None: audit["matched_candidate"] = asdict(candidate)
        updated["naver_place_review"] = audit
    if candidate is None: return updated
    if preserve_original:
        originals = updated.setdefault("naver_original", {})
        for key in ("title", "addr", "tel", "mapx", "mapy"):
            originals.setdefault(key, updated.get(key))
    should_update_title = result.status == "open" and result.score >= TITLE_REPLACEMENT_THRESHOLD
    should_update_address = result.status in {"open", "review_needed"} and result.score >= ADDRESS_REPLACEMENT_THRESHOLD
    if should_update_title and candidate.title: updated["title"] = candidate.title
    if should_update_address and candidate.best_address: updated["addr"] = candidate.best_address
    if candidate.telephone: updated["tel"] = candidate.telephone
    if candidate.long is not None: updated["mapx"] = f"{candidate.long:.7f}"
    if candidate.lat is not None: updated["mapy"] = f"{candidate.lat:.7f}"
    return updated


# ══════════════════════════════════════════════════════════════
# 파일 처리 (폐업 필터링)
# ══════════════════════════════════════════════════════════════

def process_file(checker: NaverPlaceChecker, input_path: Path, output_path: Path,
                 preserve_original: bool = False, include_review: bool = False) -> dict[str, int]:
    stats = {"total": 0, "open": 0, "review_needed": 0, "closed_suspected": 0, "no_match": 0}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        for line_no, raw_line in enumerate(src, start=1):
            line = raw_line.strip()
            if not line: continue
            stats["total"] += 1
            item = json.loads(line)
            result = checker.check_item(item)
            stats[result.status] += 1
            updated = apply_match_result(item, result, preserve_original=preserve_original, include_review=include_review)
            dst.write(json.dumps(updated, ensure_ascii=False) + "\n")
    return stats


def build_output_path(input_path: Path, output_dir: Path | None) -> Path:
    if output_dir is None:
        return input_path.with_name(f"{input_path.stem}_naver_checked{input_path.suffix}")
    return output_dir / f"{input_path.stem}_naver_checked{input_path.suffix}"


# ══════════════════════════════════════════════════════════════
# detailIntro2 null 보완 (supplement)
# ══════════════════════════════════════════════════════════════

def _naver_to_detail_intro(candidate: LocalSearchCandidate, content_id: str) -> dict:
    intro = {
        "contentid": content_id, "contenttypeid": "39",
        "seat": "", "kidsfacility": "", "firstmenu": "", "treatmenu": "",
        "smoking": "", "packing": "", "infocenterfood": candidate.telephone or "",
        "scalefood": "", "parkingfood": "", "opendatefood": "",
        "opentimefood": "", "restdatefood": "", "discountinfofood": "",
        "chkcreditcardfood": "", "reservationfood": "", "lcnsno": "",
        "_source": "naver_local_search",
        "_naver_title": candidate.title,
        "_naver_category": candidate.category,
        "_naver_address": candidate.best_address,
    }
    if candidate.category:
        cat_parts = [p.strip() for p in candidate.category.split(">")]
        if len(cat_parts) >= 2:
            intro["firstmenu"] = cat_parts[-1]
    return intro


def supplement_intro(cat_name: str = "음식점"):
    """detailIntro2가 null인 항목을 네이버 검색으로 보완"""
    intro_file = DATA_DIR / f"visitkorea_only_{cat_name}_intro_raw.jsonl"
    enriched_file = DATA_DIR / f"visitkorea_only_{cat_name}_enriched.json"

    if not intro_file.exists() or not enriched_file.exists():
        print(f"[SKIP] 필요 파일 없음", flush=True)
        return

    checker = NaverPlaceChecker(timeout=10, sleep_ms=150)
    checker.ensure_credentials()

    # null intro 항목 추출
    null_items = []
    with open(intro_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip(): continue
            try:
                item = json.loads(line)
                if item.get("detail_intro") is None:
                    null_items.append(item)
            except json.JSONDecodeError:
                continue

    # enriched 매핑
    with open(enriched_file, encoding="utf-8") as f:
        enriched = json.load(f)
    enriched_map = {str(e["contentid"]): e for e in enriched}

    print(f"detail_intro null 항목: {len(null_items)}건", flush=True)

    # 기존 성공건 유지
    keep_lines = []
    null_cids = set()
    with open(intro_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip(): continue
            try:
                item = json.loads(line)
                if item.get("detail_intro") is not None:
                    keep_lines.append(line.rstrip("\n"))
                else:
                    null_cids.add(str(item["contentid"]))
            except json.JSONDecodeError:
                continue

    # 네이버 검색으로 보완
    success = fail = 0
    new_lines = []
    for i, null_item in enumerate(null_items):
        cid = str(null_item["contentid"])
        title = null_item.get("title", "")
        enriched_item = enriched_map.get(cid, {})
        search_item = {
            "title": title,
            "addr": enriched_item.get("addr", ""),
            "tel": enriched_item.get("tel", ""),
            "mapx": enriched_item.get("mapx", ""),
            "mapy": enriched_item.get("mapy", ""),
        }
        print(f"[{i+1}/{len(null_items)}] {title} (cid={cid})", flush=True)
        try:
            result = checker.check_item(search_item)
        except Exception as e:
            print(f"  [ERROR] 네이버 검색 실패: {e}", flush=True)
            fail += 1
            new_lines.append(json.dumps({"contentid": cid, "title": title, "detail_intro": None}, ensure_ascii=False))
            continue

        if result.candidate and result.status in ("open", "review_needed"):
            intro = _naver_to_detail_intro(result.candidate, cid)
            record = {"contentid": cid, "title": title, "detail_intro": intro}
            print(f"  → 네이버 매칭 성공 ({result.status}, score={result.score:.2f})", flush=True)
            success += 1
        else:
            record = {"contentid": cid, "title": title, "detail_intro": None}
            print(f"  → 매칭 실패 ({result.status}, score={result.score:.2f})", flush=True)
            fail += 1
        new_lines.append(json.dumps(record, ensure_ascii=False))

    # 파일 재작성
    with open(intro_file, "w", encoding="utf-8") as f:
        for line in keep_lines:
            f.write(line + "\n")
        for line in new_lines:
            f.write(line + "\n")

    print(f"\n완료: 네이버 매칭 성공 {success}건 / 실패 {fail}건", flush=True)


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="네이버 지역검색 API로 장소 상태 점검 + intro 보완")
    parser.add_argument("inputs", nargs="*", help="입력 JSONL 파일 경로 (폐업 필터링)")
    parser.add_argument("--output-dir", help="출력 디렉터리")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--sleep-ms", type=int, default=120)
    parser.add_argument("--preserve-original", action="store_true")
    parser.add_argument("--include-review", action="store_true")
    parser.add_argument("--supplement-intro", action="store_true",
                        help="detailIntro2 null 항목 네이버 검색으로 보완")
    parser.add_argument("--supplement-category", default="음식점",
                        help="보완 대상 카테고리 (기본: 음식점)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    load_env_candidates()

    if args.supplement_intro:
        supplement_intro(args.supplement_category)
        return 0

    if not args.inputs:
        print("사용법: step4_filter_closed.py INPUT.jsonl [INPUT2.jsonl ...]")
        print("        step4_filter_closed.py --supplement-intro")
        return 1

    checker = NaverPlaceChecker(timeout=args.timeout, sleep_ms=args.sleep_ms)
    checker.ensure_credentials()

    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    for raw_input in args.inputs:
        input_path = Path(raw_input).resolve()
        output_path = build_output_path(input_path, output_dir)
        stats = process_file(checker, input_path=input_path, output_path=output_path,
                             preserve_original=args.preserve_original, include_review=args.include_review)
        print(f"[DONE] {input_path.name} -> {output_path} "
              f"(total={stats['total']}, open={stats['open']}, review={stats['review_needed']}, "
              f"closed_suspected={stats['closed_suspected']}, no_match={stats['no_match']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
