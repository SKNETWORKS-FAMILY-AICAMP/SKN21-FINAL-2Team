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
except ImportError:  # pragma: no cover
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        return False


LOCAL_SEARCH_ENDPOINT = "https://openapi.naver.com/v1/search/local.json"
GEOCODE_ENDPOINT = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
DEFAULT_TIMEOUT = 10


TITLE_REPLACEMENT_THRESHOLD = 2.65
ADDRESS_REPLACEMENT_THRESHOLD = 2.15
OPEN_THRESHOLD = 2.6
REVIEW_THRESHOLD = 1.65
CLOSED_DISTANCE_M = 180


COMMON_WORD_TRANSLITERATIONS: dict[str, str] = {
    "and": "앤",
    "bar": "바",
    "bbq": "바비큐",
    "beef": "비프",
    "bistro": "비스트로",
    "burger": "버거",
    "cafe": "카페",
    "campus": "캠퍼스",
    "club": "클럽",
    "coffee": "커피",
    "deli": "델리",
    "dream": "드림",
    "gallery": "갤러리",
    "garden": "가든",
    "guest": "게스트",
    "guesthouse": "게스트하우스",
    "grill": "그릴",
    "hall": "홀",
    "hanok": "한옥",
    "home": "홈",
    "hostel": "호스텔",
    "hotel": "호텔",
    "house": "하우스",
    "kstar": "케이스타",
    "k-star": "케이스타",
    "korea": "코리아",
    "lounge": "라운지",
    "motel": "모텔",
    "museum": "뮤지엄",
    "noodle": "누들",
    "place": "플레이스",
    "pub": "펍",
    "restaurant": "레스토랑",
    "road": "로드",
    "room": "룸",
    "shop": "샵",
    "stay": "스테이",
    "steak": "스테이크",
    "studio": "스튜디오",
    "suite": "스위트",
    "sweet": "스위",
    "tea": "티",
    "terrace": "테라스",
    "tour": "투어",
    "villa": "빌라",
    "view": "뷰",
    "wine": "와인",
}

LETTER_TO_HANGUL: dict[str, str] = {
    "a": "아",
    "b": "브",
    "c": "크",
    "d": "드",
    "e": "이",
    "f": "프",
    "g": "그",
    "h": "하",
    "i": "이",
    "j": "제",
    "k": "케",
    "l": "엘",
    "m": "엠",
    "n": "엔",
    "o": "오",
    "p": "피",
    "q": "큐",
    "r": "르",
    "s": "스",
    "t": "트",
    "u": "유",
    "v": "브",
    "w": "우",
    "x": "엑스",
    "y": "와이",
    "z": "즈",
}


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
    backend_dir = this.parents[2]
    project_root = this.parents[3]
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
    return [token for token in re.findall(r"[0-9A-Za-z가-힣]+", normalize_space(value)) if token]


def tokenize_address(value: str) -> list[str]:
    return [token for token in re.findall(r"[0-9A-Za-z가-힣-]+", clean_address(value)) if token]


def contains_hangul(value: str) -> bool:
    return bool(re.search(r"[가-힣]", value or ""))


def contains_roman_letters(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]", value or ""))


def extract_parenthetical_candidates(title: str) -> list[str]:
    found = [normalize_space(part) for part in re.findall(r"\(([^)]*)\)", title or "") if normalize_space(part)]
    return dedupe_strings(found)


def split_alpha_numeric(token: str) -> list[str]:
    return [part for part in re.findall(r"[A-Za-z]+|\d+", token or "") if part]


def transliterate_token_to_korean(token: str) -> str:
    token = token.strip().lower()
    if not token:
        return ""
    if token in COMMON_WORD_TRANSLITERATIONS:
        return COMMON_WORD_TRANSLITERATIONS[token]

    if token.endswith("house") and len(token) > 5:
        head = token[:-5]
        head_ko = transliterate_token_to_korean(head)
        return f"{head_ko}하우스" if head_ko else "하우스"

    if token.endswith("hotel") and len(token) > 5:
        head = token[:-5]
        head_ko = transliterate_token_to_korean(head)
        return f"{head_ko}호텔" if head_ko else "호텔"

    if token.endswith("stay") and len(token) > 4:
        head = token[:-4]
        head_ko = transliterate_token_to_korean(head)
        return f"{head_ko}스테이" if head_ko else "스테이"

    parts = split_alpha_numeric(token)
    if len(parts) > 1:
        merged = "".join(transliterate_token_to_korean(part) for part in parts)
        if merged:
            return merged

    token = token.replace("ph", "f").replace("oo", "u").replace("ee", "i")
    token = token.replace("ck", "k").replace("qu", "kw")
    syllables = re.findall(r"[^aeiouy]*[aeiouy]+(?:[^aeiouy](?![aeiouy]))?", token) or [token]

    converted: list[str] = []
    for syllable in syllables:
        if syllable in COMMON_WORD_TRANSLITERATIONS:
            converted.append(COMMON_WORD_TRANSLITERATIONS[syllable])
            continue
        piece = "".join(LETTER_TO_HANGUL.get(char, "") for char in syllable if char.isalpha())
        if piece:
            piece = piece.replace("으아", "와").replace("으오", "워").replace("하우스트", "하우스")
            converted.append(piece)

    merged = "".join(converted)
    if not merged:
        merged = "".join(LETTER_TO_HANGUL.get(char, "") for char in token if char.isalpha())
    return merged


def transliterate_title_variants(title: str) -> list[str]:
    if not contains_roman_letters(title):
        return []

    base = strip_parentheses(title)
    tokens = tokenize_title(base)
    alpha_tokens = [token for token in tokens if contains_roman_letters(token)]
    if not alpha_tokens:
        return []

    transliterated_tokens = [transliterate_token_to_korean(token) for token in alpha_tokens]
    transliterated_tokens = [token for token in transliterated_tokens if token]
    variants = [
        "".join(transliterated_tokens),
        " ".join(transliterated_tokens),
    ]
    return dedupe_strings([variant for variant in variants if variant])


def dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        normalized = normalize_space(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def area_hint_from_address(addr: str) -> str:
    tokens = tokenize_address(addr)
    if len(tokens) >= 2:
        return " ".join(tokens[:2])
    if tokens:
        return tokens[0]
    return ""


def road_hint_from_address(addr: str) -> str:
    tokens = tokenize_address(addr)
    road_tokens = [token for token in tokens if token.endswith(("로", "길")) or re.search(r"\d+-?\d*$", token)]
    return " ".join(road_tokens[:2])


def build_query_variants(item: dict[str, Any]) -> list[str]:
    title = normalize_space(str(item.get("title", "")))
    addr = clean_address(str(item.get("addr", "")))
    area_hint = area_hint_from_address(addr)
    road_hint = road_hint_from_address(addr)

    title_parts = [title, strip_parentheses(title), *extract_parenthetical_candidates(title)]
    korean_title_parts = [part for part in title_parts if contains_hangul(part)]
    english_to_korean = transliterate_title_variants(title)

    queries: list[str] = []

    for part in title_parts + english_to_korean:
        if not part:
            continue
        queries.append(part)
        if area_hint:
            queries.append(f"{part} {area_hint}")
        if road_hint:
            queries.append(f"{part} {road_hint}")

    if addr:
        queries.append(addr)
        if korean_title_parts:
            for part in korean_title_parts[:2]:
                queries.append(f"{addr} {part}")
        if road_hint:
            queries.append(f"{area_hint} {road_hint}".strip())

    return dedupe_strings(queries)


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    intersection = left & right
    union = left | right
    if not union:
        return 0.0
    return len(intersection) / len(union)


def to_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def distance_meters(lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    lat_factor = 111_320
    lon_factor = 88_000
    dy = (lat1 - lat2) * lat_factor
    dx = (lon1 - lon2) * lon_factor
    return (dx * dx + dy * dy) ** 0.5


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
        if not self.mapy:
            return None
        if "." in self.mapy:
            return to_float(self.mapy)
        try:
            return int(self.mapy) / 10_000_000
        except ValueError:
            return None

    @property
    def lon(self) -> float | None:
        if not self.mapx:
            return None
        if "." in self.mapx:
            return to_float(self.mapx)
        try:
            return int(self.mapx) / 10_000_000
        except ValueError:
            return None


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


class NaverPlaceChecker:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT, sleep_ms: int = 120) -> None:
        self.timeout = timeout
        self.sleep_ms = sleep_ms
        self.search_client_id = (
            os.getenv("NAVER_SEARCH_CLIENT_ID")
            or os.getenv("NAVER_CLIENT_ID")
            or ""
        ).strip()
        self.search_client_secret = (
            os.getenv("NAVER_SEARCH_CLIENT_SECRET")
            or os.getenv("NAVER_CLIENT_SECRET")
            or ""
        ).strip()
        self.map_client_id = (os.getenv("NAVER_CLIENT_ID") or "").strip()
        self.map_client_secret = (os.getenv("NAVER_CLIENT_SECRET") or "").strip()
        self._geocode_cache: dict[str, dict[str, Any] | None] = {}

    def ensure_credentials(self) -> None:
        if not self.search_client_id or not self.search_client_secret:
            raise RuntimeError(
                "NAVER_SEARCH_CLIENT_ID / NAVER_SEARCH_CLIENT_SECRET 또는 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 이 필요합니다."
            )

    def local_search(self, query: str, display: int = 5) -> list[LocalSearchCandidate]:
        headers = {
            "X-Naver-Client-Id": self.search_client_id,
            "X-Naver-Client-Secret": self.search_client_secret,
        }
        params = {"query": query, "display": max(1, min(display, 5)), "sort": "comment"}
        response = requests.get(
            LOCAL_SEARCH_ENDPOINT,
            headers=headers,
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        items = response.json().get("items") or []
        results: list[LocalSearchCandidate] = []
        for item in items:
            results.append(
                LocalSearchCandidate(
                    query=query,
                    title=strip_html(item.get("title") or ""),
                    road_address=normalize_space(item.get("roadAddress") or ""),
                    jibun_address=normalize_space(item.get("address") or ""),
                    telephone=normalize_space(item.get("telephone") or ""),
                    category=normalize_space(item.get("category") or ""),
                    link=normalize_space(item.get("link") or ""),
                    mapx=str(item.get("mapx") or "").strip(),
                    mapy=str(item.get("mapy") or "").strip(),
                )
            )
        return results

    def geocode(self, query: str) -> dict[str, Any] | None:
        normalized_query = normalize_space(query)
        if not normalized_query:
            return None
        if normalized_query in self._geocode_cache:
            return self._geocode_cache[normalized_query]

        if not self.map_client_id or not self.map_client_secret:
            self._geocode_cache[normalized_query] = None
            return None

        headers = {
            "X-NCP-APIGW-API-KEY-ID": self.map_client_id,
            "X-NCP-APIGW-API-KEY": self.map_client_secret,
        }
        params = {"query": normalized_query}

        try:
            response = requests.get(GEOCODE_ENDPOINT, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            addresses = payload.get("addresses") or []
            if not addresses:
                self._geocode_cache[normalized_query] = None
                return None
            target = addresses[0]
            result = {
                "lat": to_float(target.get("y")),
                "lon": to_float(target.get("x")),
                "road_address": normalize_space(target.get("roadAddress") or ""),
                "jibun_address": normalize_space(target.get("jibunAddress") or ""),
            }
            self._geocode_cache[normalized_query] = result
            return result
        except requests.RequestException:
            self._geocode_cache[normalized_query] = None
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

            for candidate in candidates:
                key = (normalize_key(candidate.title), clean_address(candidate.best_address))
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(candidate)

            if self.sleep_ms > 0:
                time.sleep(self.sleep_ms / 1000)

        return queries, deduped

    def evaluate_match(self, item: dict[str, Any], queries: list[str], candidates: list[LocalSearchCandidate]) -> MatchResult:
        if not candidates:
            return MatchResult(
                status="no_match",
                score=0.0,
                decision_reason="네이버 검색 결과 없음",
                candidate=None,
                searched_queries=queries,
            )

        item_title = normalize_space(str(item.get("title", "")))
        item_title_key = normalize_key(item_title)
        item_title_ko_variants = transliterate_title_variants(item_title)
        item_addr = clean_address(str(item.get("addr", "")))
        item_addr_tokens = set(tokenize_address(item_addr))
        input_lat = to_float(item.get("mapy"))
        input_lon = to_float(item.get("mapx"))
        tel_digits = only_digits(item.get("tel"))

        best_candidate: LocalSearchCandidate | None = None
        best_score = -1.0
        best_reason = "후보 점수 계산"
        best_name_similarity = 0.0
        best_address_similarity = 0.0
        best_distance: float | None = None

        for candidate in candidates:
            candidate_title_key = normalize_key(candidate.title)
            candidate_addr = clean_address(candidate.best_address)
            candidate_addr_tokens = set(tokenize_address(candidate_addr))

            name_similarity = 0.0
            if item_title_key and candidate_title_key:
                if item_title_key == candidate_title_key:
                    name_similarity = 1.0
                elif item_title_key in candidate_title_key or candidate_title_key in item_title_key:
                    name_similarity = 0.86
                else:
                    name_similarity = jaccard_similarity(
                        set(tokenize_title(item_title_key)),
                        set(tokenize_title(candidate_title_key)),
                    )

            translit_similarity = 0.0
            for variant in item_title_ko_variants:
                variant_key = normalize_key(variant)
                if not variant_key:
                    continue
                if variant_key == candidate_title_key:
                    translit_similarity = max(translit_similarity, 0.95)
                elif variant_key and (variant_key in candidate_title_key or candidate_title_key in variant_key):
                    translit_similarity = max(translit_similarity, 0.72)

            address_similarity = jaccard_similarity(item_addr_tokens, candidate_addr_tokens)
            if item_addr and candidate_addr and item_addr == candidate_addr:
                address_similarity = 1.0

            tel_similarity = 1.0 if tel_digits and tel_digits == only_digits(candidate.telephone) else 0.0

            candidate_lat = candidate.lat
            candidate_lon = candidate.lon
            if (candidate_lat is None or candidate_lon is None) and candidate.best_address:
                geocoded = self.geocode(candidate.best_address)
                if geocoded:
                    candidate_lat = geocoded.get("lat")
                    candidate_lon = geocoded.get("lon")

            candidate_distance = distance_meters(input_lat, input_lon, candidate_lat, candidate_lon)
            distance_score = 0.0
            if candidate_distance is not None:
                if candidate_distance <= 80:
                    distance_score = 1.0
                elif candidate_distance <= 180:
                    distance_score = 0.72
                elif candidate_distance <= 350:
                    distance_score = 0.35
                else:
                    distance_score = -0.3

            score = (
                max(name_similarity, translit_similarity) * 1.9
                + address_similarity * 1.65
                + tel_similarity * 0.8
                + distance_score * 0.9
            )

            if candidate.query and candidate.query == candidate.title:
                score += 0.12

            if score > best_score:
                best_candidate = candidate
                best_score = score
                best_name_similarity = max(name_similarity, translit_similarity)
                best_address_similarity = address_similarity
                best_distance = candidate_distance
                best_reason = (
                    f"name={best_name_similarity:.2f}, addr={best_address_similarity:.2f}, "
                    f"dist={candidate_distance if candidate_distance is not None else 'n/a'}"
                )

        if best_candidate is None:
            return MatchResult(
                status="no_match",
                score=0.0,
                decision_reason="후보 선택 실패",
                candidate=None,
                searched_queries=queries,
            )

        if best_score >= OPEN_THRESHOLD:
            return MatchResult(
                status="open",
                score=best_score,
                decision_reason=best_reason,
                candidate=best_candidate,
                searched_queries=queries,
                name_similarity=best_name_similarity,
                address_similarity=best_address_similarity,
                distance_m=best_distance,
            )

        if best_score >= REVIEW_THRESHOLD:
            return MatchResult(
                status="review_needed",
                score=best_score,
                decision_reason=f"부분 일치: {best_reason}",
                candidate=best_candidate,
                searched_queries=queries,
                name_similarity=best_name_similarity,
                address_similarity=best_address_similarity,
                distance_m=best_distance,
            )

        if best_distance is not None and best_distance <= CLOSED_DISTANCE_M:
            status = "review_needed"
            reason = f"주소는 가깝지만 상호 불일치: {best_reason}"
        else:
            status = "closed_suspected"
            reason = f"강한 일치 후보 없음: {best_reason}"

        return MatchResult(
            status=status,
            score=best_score,
            decision_reason=reason,
            candidate=best_candidate,
            searched_queries=queries,
            name_similarity=best_name_similarity,
            address_similarity=best_address_similarity,
            distance_m=best_distance,
        )

    def check_item(self, item: dict[str, Any]) -> MatchResult:
        queries, candidates = self.search_candidates(item)
        return self.evaluate_match(item, queries, candidates)


def apply_match_result(
    item: dict[str, Any],
    result: MatchResult,
    preserve_original: bool = False,
    include_review: bool = False,
) -> dict[str, Any]:
    updated = dict(item)
    candidate = result.candidate

    if include_review:
        audit: dict[str, Any] = {
            "status": result.status,
            "score": round(result.score, 4),
            "decision_reason": result.decision_reason,
            "searched_queries": result.searched_queries,
            "name_similarity": round(result.name_similarity, 4),
            "address_similarity": round(result.address_similarity, 4),
            "distance_m": round(result.distance_m, 2) if result.distance_m is not None else None,
        }
        if candidate is not None:
            audit["matched_candidate"] = asdict(candidate)
        updated["naver_place_review"] = audit

    if candidate is None:
        return updated

    if preserve_original:
        originals = updated.setdefault("naver_original", {})
        for key in ("title", "addr", "tel", "mapx", "mapy"):
            originals.setdefault(key, updated.get(key))

    best_address = candidate.best_address
    should_update_title = result.status == "open" and result.score >= TITLE_REPLACEMENT_THRESHOLD
    should_update_address = result.status in {"open", "review_needed"} and result.score >= ADDRESS_REPLACEMENT_THRESHOLD

    if should_update_title and candidate.title:
        updated["title"] = candidate.title
    if should_update_address and best_address:
        updated["addr"] = best_address
    if candidate.telephone:
        updated["tel"] = candidate.telephone
    if candidate.lon is not None:
        updated["mapx"] = f"{candidate.lon:.7f}"
    if candidate.lat is not None:
        updated["mapy"] = f"{candidate.lat:.7f}"

    return updated


def process_file(
    checker: NaverPlaceChecker,
    input_path: Path,
    output_path: Path,
    preserve_original: bool = False,
    include_review: bool = False,
) -> dict[str, int]:
    stats = {
        "total": 0,
        "open": 0,
        "review_needed": 0,
        "closed_suspected": 0,
        "no_match": 0,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        for line_no, raw_line in enumerate(src, start=1):
            line = raw_line.strip()
            if not line:
                continue
            stats["total"] += 1
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{input_path}:{line_no} JSON 파싱 실패: {exc}") from exc

            result = checker.check_item(item)
            stats[result.status] += 1
            updated = apply_match_result(
                item,
                result,
                preserve_original=preserve_original,
                include_review=include_review,
            )
            dst.write(json.dumps(updated, ensure_ascii=False) + "\n")

    return stats


def build_output_path(input_path: Path, output_dir: Path | None) -> Path:
    if output_dir is None:
        return input_path.with_name(f"{input_path.stem}_naver_checked{input_path.suffix}")
    return output_dir / f"{input_path.stem}_naver_checked{input_path.suffix}"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="네이버 지역검색 API로 장소 상태를 점검하고 JSONL을 갱신합니다.")
    parser.add_argument("inputs", nargs="+", help="입력 JSONL 파일 경로")
    parser.add_argument("--output-dir", help="출력 디렉터리. 생략하면 입력 파일 옆에 생성")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout 초")
    parser.add_argument("--sleep-ms", type=int, default=120, help="요청 간 대기 시간(ms)")
    parser.add_argument(
        "--preserve-original",
        action="store_true",
        help="수정 전 title/addr/tel/mapx/mapy를 naver_original 필드에 백업",
    )
    parser.add_argument(
        "--include-review",
        action="store_true",
        help="검토 메타데이터를 naver_place_review 필드에 포함",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    load_env_candidates()

    checker = NaverPlaceChecker(timeout=args.timeout, sleep_ms=args.sleep_ms)
    checker.ensure_credentials()

    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    for raw_input in args.inputs:
        input_path = Path(raw_input).resolve()
        output_path = build_output_path(input_path, output_dir)
        stats = process_file(
            checker,
            input_path=input_path,
            output_path=output_path,
            preserve_original=args.preserve_original,
            include_review=args.include_review,
        )
        print(
            f"[DONE] {input_path.name} -> {output_path} "
            f"(total={stats['total']}, open={stats['open']}, review={stats['review_needed']}, "
            f"closed_suspected={stats['closed_suspected']}, no_match={stats['no_match']})"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
