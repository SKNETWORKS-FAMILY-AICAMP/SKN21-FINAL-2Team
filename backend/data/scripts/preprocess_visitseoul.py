"""
Visit Seoul 데이터 전처리 스크립트
=====================================
입력: data/visitseoul_{카테고리}.json
출력: data/preprocessed/visitseoul_{카테고리}.json

처리 내용:
    1. 불필요한 필드 제거 (parking, source, multi_lang_list, contenttypeid_code)
    2. null 필드 제거
    3. 텍스트 정규화 (공백/개행 정리, HTML 제거)
    4. tags 정제 (개행 제거, 빈 태그 제거)
    5. mapy/mapx float 보장
    6. category_depth 공백 정규화
"""

import ast
import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = DATA_DIR / "preprocessed"
OUT_DIR.mkdir(exist_ok=True)

CATEGORIES = ["관광지", "음식점", "숙박", "투어"]

# 제거할 필드
DROP_FIELDS = {"parking", "source", "multi_lang_list", "contenttypeid_code", "updated_at"}


# ── 텍스트 정규화 ──────────────────────────────────────────
def strip_html(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    # CSS 블록 패턴 제거 (태그 없이 텍스트로 삽입된 경우)
    # {…} 포함 블록 제거
    text = re.sub(r"[^{}]+\{[^}]*\}", "", text)
    # 남은 CSS 선택자 잔여물 제거 (한글 등장 전까지)
    text = re.sub(r"^[^가-힣\w\"\']+", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return text


def normalize(text: str) -> str:
    """공백·개행 정규화"""
    text = strip_html(text)
    text = re.sub(r"\r\n|\r", "\n", text)       # CR 통일
    text = re.sub(r"[ \t]+", " ", text)          # 수평 공백 압축
    text = re.sub(r"\n{3,}", "\n\n", text)       # 3개 이상 개행 → 2개
    return text.strip()


def normalize_category_depth(text: str) -> str:
    """'문화관광  > 랜드마크관광' → '문화관광 > 랜드마크관광'"""
    parts = [p.strip() for p in text.split(">")]
    return " > ".join(p for p in parts if p)


def clean_tags(tags) -> list:
    if not isinstance(tags, list):
        return []
    result = []
    for tag in tags:
        tag = re.sub(r"\s+", "", str(tag))   # 공백·개행 모두 제거
        if tag:
            result.append(tag)
    return result


def to_float(val):
    try:
        f = float(val)
        return f if f != 0.0 else None
    except (ValueError, TypeError):
        return None


# 음식점 코드 필드: "{'code_id': 'FOOD_1_2', 'code_nm': '한식'}" → "한식"
CODE_FIELDS = {"cuisine_kind", "restaurant_type", "halal", "salam", "dietary"}

# "None" 문자열을 실제 None으로 처리할 필드
NONE_STRING_FIELDS = {"menu", "price_range"}

# halal 필드: 논-할랄 값 (llm_text에 불필요)
HALAL_NON_HALAL = {"살람서울(기타/논-할랄)"}

# salam → dietary로 매핑할 값 (나머지는 halal과 중복이므로 제거)
SALAM_TO_DIETARY = {
    "살람 - 비건": "채식",
    "살람 - 해산물": "해산물",
}

def parse_code_field(val) -> str | None:
    """문자열로 저장된 코드 딕셔너리에서 code_nm 추출"""
    if not val or val == "None":
        return None
    try:
        if isinstance(val, str):
            parsed = ast.literal_eval(val)
        else:
            parsed = val
        nm = parsed.get("code_nm", "") if isinstance(parsed, dict) else ""
        return nm.strip() or None
    except Exception:
        return None


def merge_halal_dietary(result: dict) -> dict:
    """halal/salam/dietary 필드 정리
    - halal: 논-할랄 값 제거
    - salam: 비건/해산물만 dietary로 이관, 필드 자체 제거
    - dietary: 할랄(halal과 중복) 제거, salam에서 넘어온 값 추가
    """
    halal = result.pop("halal", None)
    salam = result.pop("salam", None)
    dietary = result.pop("dietary", None)

    # halal: 논-할랄이면 None 처리
    if halal in HALAL_NON_HALAL:
        halal = None

    # salam → dietary 이관
    salam_dietary = SALAM_TO_DIETARY.get(salam)  # 매핑 없으면 None (할랄/논할랄은 버림)

    # dietary: "할랄"은 halal 필드와 중복 → 제거, salam 유래 값 추가
    dietary_vals = set()
    if dietary and dietary != "할랄":
        dietary_vals.add(dietary)
    if salam_dietary:
        dietary_vals.add(salam_dietary)
    dietary_final = ", ".join(sorted(dietary_vals)) or None

    if halal:
        result["halal"] = halal
    if dietary_final:
        result["dietary"] = dietary_final

    return result


# ── 숙박 전용 전처리 ──────────────────────────────────────

def normalize_checkin_time(text: str) -> str:
    """usetime 텍스트 정규화
    - 입실/퇴실 → 체크인/체크아웃
    - PM/AM/오전/오후 → 24시간제
    - 구분자(콤마, 개행) → ' / '
    """
    text = re.sub(r"입실", "체크인", text)
    text = re.sub(r"퇴실", "체크아웃", text)

    def to24(m):
        ampm = m.group(1).upper()
        h = int(m.group(2))
        mn = m.group(3) or "00"
        if ampm in ("PM", "오후") and h < 12:
            h += 12
        elif ampm in ("AM", "오전") and h == 12:
            h = 0
        return f"{h:02d}:{mn}"

    text = re.sub(r"(PM|AM|오후|오전)\s*(\d{1,2}):?(\d{2})?", to24, text, flags=re.IGNORECASE)
    # "15시" 형태 → "15:00"
    text = re.sub(r"(\d{1,2})시", lambda m: f"{int(m.group(1)):02d}:00", text)
    # 구분자 통일: 콤마 또는 개행 → ' / '
    text = re.sub(r"\s*[,\r\n]+\s*", " / ", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text


def merge_accommodation_fields(result: dict) -> dict:
    """숙박 전용 필드 정리
    - checkin_time + checkout_time → usetime (기존 usetime 없을 때)
    - usetime 텍스트 정규화 (입실/퇴실 통일, 시간 포맷)
    - room_type: 요금 포함 라인 → 객실명만 남기고 요금은 fee로 이동
    """
    # 1. checkin_time / checkout_time → usetime 합성
    checkin = result.pop("checkin_time", None)
    checkout = result.pop("checkout_time", None)
    if checkin or checkout:
        if not result.get("usetime"):
            ci_h = int(checkin) if checkin else None
            co_h = int(checkout) if checkout else None
            parts = []
            if ci_h is not None:
                parts.append(f"체크인 {ci_h + 12 if ci_h < 12 else ci_h:02d}:00")
            if co_h is not None:
                parts.append(f"체크아웃 {co_h:02d}:00")
            result["usetime"] = " / ".join(parts)

    # 2. usetime 텍스트 정규화
    if result.get("usetime"):
        result["usetime"] = normalize_checkin_time(result["usetime"])

    # 3. room_type: 요금 포함 라인 분리
    room_type = result.get("room_type")
    if room_type and isinstance(room_type, str):
        lines = re.split(r"[\r\n]+", room_type)
        room_names = []
        fee_parts = []
        price_pattern = re.compile(r"(\d[\d,\s]*만?\s*원|\d[\d,]*\s*KRW)", re.IGNORECASE)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if price_pattern.search(line):
                # 요금 포함 라인: "객실명 : 가격 (설명)" 패턴에서 객실명 추출
                name_part = re.split(r"\s*:\s*", line)[0].strip()
                # 이름 부분에 숫자+원 패턴이 없을 때만 객실명으로 인정
                if name_part and not price_pattern.search(name_part):
                    room_names.append(name_part)
                fee_parts.append(line)
            else:
                room_names.append(line)

        result["room_type"] = ", ".join(room_names) if room_names else None
        if fee_parts:
            existing_fee = result.get("fee") or ""
            extra = " / ".join(fee_parts)
            result["fee"] = (existing_fee + " / " + extra).strip(" /") if existing_fee else extra

    return result


# ── 항목 변환 ─────────────────────────────────────────────
def transform(item: dict) -> dict:
    result = {}

    for key, val in item.items():
        # 제거 필드 스킵
        if key in DROP_FIELDS:
            continue

        # 타입별 처리
        if key in CODE_FIELDS:
            result[key] = parse_code_field(val)
        elif key in NONE_STRING_FIELDS:
            result[key] = None if (not val or val == "None") else val
        elif key in ("mapy", "mapx"):
            result[key] = to_float(val)
        elif key == "tags":
            result[key] = clean_tags(val)
        elif key == "category_depth" and isinstance(val, str):
            result[key] = normalize_category_depth(val) or None
        elif key in ("description", "summary"):
            result[key] = normalize(val) if val else None
        elif key in ("usetime", "restdate", "fee", "addr", "tel", "subway_info", "website", "title"):
            result[key] = normalize(val) if val else None
        else:
            result[key] = val

    # halal/salam/dietary 통합 정리 (음식점 전용)
    if any(k in result for k in ("halal", "salam", "dietary")):
        result = merge_halal_dietary(result)

    # 숙박 전용 필드 정리
    if any(k in result for k in ("checkin_time", "checkout_time", "room_type")):
        result = merge_accommodation_fields(result)

    # null 필드 제거
    result = {k: v for k, v in result.items() if v is not None and v != [] and v != ""}

    return result


# ── 메인 ──────────────────────────────────────────────────
def process(category: str):
    in_path = DATA_DIR / f"visitseoul_{category}.json"
    if not in_path.exists():
        print(f"  파일 없음: {in_path.name}")
        return

    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)

    results = [transform(item) for item in data]

    out_path = OUT_DIR / f"visitseoul_{category}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"  {category}: {len(results)}건 → {out_path.relative_to(DATA_DIR.parent)}")


def main():
    print("=" * 50)
    print("Visit Seoul 전처리")
    print("=" * 50)
    for cat in CATEGORIES:
        process(cat)
    print("완료")
    print("=" * 50)


if __name__ == "__main__":
    main()
