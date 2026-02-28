from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from app.database.connection import SessionLocal
from app.models.prefer import Prefer
from app.models.country import Country
from app.models.country import Country

PREFER_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "prefer"


def _pick_value(item: dict[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _pick_category(item: dict[str, Any]) -> str:
    direct = _pick_value(item, ("category", "job_type", "type"))
    if direct:
        return direct

    for key in ("genres_ko", "genres", "genres_en"):
        value = item.get(key)
        if isinstance(value, list) and value:
            text_values = [str(v).strip() for v in value if str(v).strip()]
            if text_values:
                return ", ".join(text_values)

    return "unknown"


def _pick_image_path(item: dict[str, Any], json_path: Path) -> str | None:
    raw = _pick_value(item, ("image_path", "profile_image_file", "poster_file"))
    if not raw:
        return None

    # "./001_xxx.jpg" -> "actor/001_xxx.jpg"
    if raw.startswith("./"):
        return f"{json_path.parent.name}/{raw[2:]}"
    return raw


def _iter_prefer_records() -> Iterable[dict[str, str | None]]:
    for json_path in sorted(PREFER_DATA_ROOT.rglob("*.json")):
        with json_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        items = payload.get("items")
        if not isinstance(items, list):
            continue

        prefer_type = json_path.parent.name  # actor, movie, drama, celeb ...
        for item in items:
            if not isinstance(item, dict):
                continue

            value = _pick_value(item, ("value", "name_ko", "title_ko", "name_en", "title_en", "name", "title"))
            if not value:
                continue

            yield {
                "type": prefer_type,
                "category": _pick_category(item),
                "value": value,
                "image_path": _pick_image_path(item, json_path),
            }

def _iter_demo_survey_records() -> Iterable[dict[str, str | None]]:
    """
    Survey 페이지용 데모 데이터 (Vibe, Craving, Relax)
    """
    demo_data = [
        # 1. 여행 계획 타입
        {"category": "style", "type": "plan", "value": "Planning (J)", "image_path": "http://localhost:8000/static/plan/plan_yesplan.png"},
        {"category": "style", "type": "plan", "value": "Spontaneous (P)", "image_path": "http://localhost:8000/static/plan/plan_nonplan.png"},

        # 2. 여행 인원
        {"category": "style", "type": "member", "value": "With Group", "image_path": "http://localhost:8000/static/member/member_together.png"},
        {"category": "style", "type": "member", "value": "Solo Trip", "image_path": "http://localhost:8000/static/member/member_alone.png"},

        # 3. 이동 수단
        {"category": "style", "type": "transport", "value": "Public Transport & Walk", "image_path": "http://localhost:8000/static/transport/transport_walk.png"},
        {"category": "style", "type": "transport", "value": "Car Rental", "image_path": "http://localhost:8000/static/transport/transport_car.png"},

        # 4. 여행자 연령대
        {"category": "style", "type": "age", "value": "Adults Only", "image_path": "http://localhost:8000/static/age/adult.png"},
        {"category": "style", "type": "age", "value": "With Children", "image_path": "http://localhost:8000/static/age/alone.png"},

        # 5. 여행 성향
        {"category": "style", "type": "vibe", "value": "Adventure", "image_path": "http://localhost:8000/static/vibe/vibe_adventure.png"},
        {"category": "style", "type": "vibe", "value": "Relaxation", "image_path": "http://localhost:8000/static/vibe/vibe_calm.png"},

        # 6. 영화 선호 (New)
        {"category": "content", "type": "movie", "value": "Romance", "image_path": "http://localhost:8000/static/movie/romance.png"},
        {"category": "content", "type": "movie", "value": "Action", "image_path": "http://localhost:8000/static/movie/action.png"},

        # 7. 드라마 선호 (New)
        {"category": "content", "type": "drama", "value": "K-Drama", "image_path": "http://localhost:8000/static/drama/kdrama.png"},
        {"category": "content", "type": "drama", "value": "American Series", "image_path": "http://localhost:8000/static/drama/us_series.png"},

        # 8. 예능 선호 (New)
        {"category": "content", "type": "variety", "value": "Talk Show", "image_path": "http://localhost:8000/static/variety/talk.png"},
        {"category": "content", "type": "variety", "value": "Reality Show", "image_path": "http://localhost:8000/static/variety/reality.png"},
    ]

    for item in demo_data:
        yield item


def insert_prefer() -> dict[str, int]:
    """
    backend/data/prefer 하위 JSON의 items 데이터를 prefers 테이블에 삽입한다.
    중복 기준: (type, value)
    """

    db = SessionLocal()
    inserted = 0
    skipped = 0

    try:
        existing = {
            (row.type, row.value)
            for row in db.query(Prefer.type, Prefer.value).all()
        }

        from itertools import chain
        for record in chain(_iter_prefer_records(), _iter_demo_survey_records()):
            key = (record["type"], record["value"])
            if key in existing:
                skipped += 1
                continue

            db.add(
                Prefer(
                    category=record["category"],
                    type=record["type"],
                    value=record["value"],
                    image_path=record["image_path"],
                )
            )
            existing.add(key)
            inserted += 1

        db.commit()
        return {"inserted": inserted, "skipped": skipped}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def insert_country() -> dict[str, int]:
    """
    기본 국가 데이터를 country 테이블에 삽입한다.
    """
    countries = [
        {"code": "kr", "name": "대한민국"},
        {"code": "us", "name": "미국"},
        {"code": "jp", "name": "일본"},
        {"code": "cn", "name": "중국"},
        {"code": "fr", "name": "프랑스"},
        {"code": "de", "name": "독일"},
        {"code": "es", "name": "스페인"},
        {"code": "it", "name": "이탈리아"},
        {"code": "pt", "name": "포르투갈"},
        {"code": "ru", "name": "러시아"},
        {"code": "other", "name": "기타"}
    ]

    db = SessionLocal()
    inserted = 0
    skipped = 0

    try:
        existing = {row.code for row in db.query(Country.code).all()}

        for item in countries:
            if item["code"] in existing:
                skipped += 1
                continue

            db.add(Country(code=item["code"], name=item["name"]))
            existing.add(item["code"])
            inserted += 1

        db.commit()
        return {"inserted": inserted, "skipped": skipped}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def insert_country() -> dict[str, int]:
    """
    기본 국가 데이터를 country 테이블에 삽입한다.
    """
    countries = [
        {"code": "ko", "name": "한국"},
        {"code": "jp", "name": "일본"},
        {"code": "it", "name": "이탈리아"},
        {"code": "us", "name": "미국"},
        {"code": "cn", "name": "중국"},
        {"code": "fr", "name": "프랑스"},
        {"code": "gb", "name": "영국"},
        {"code": "de", "name": "독일"},
        {"code": "es", "name": "스페인"},
        {"code": "th", "name": "태국"},
        {"code": "vn", "name": "베트남"},
        {"code": "sg", "name": "싱가포르"},
        {"code": "tw", "name": "대만"},
        {"code": "ph", "name": "필리핀"},
        {"code": "id", "name": "인도네시아"},
        {"code": "my", "name": "말레이시아"},
        {"code": "au", "name": "호주"},
        {"code": "nz", "name": "뉴질랜드"},
        {"code": "ca", "name": "캐나다"},
        {"code": "mx", "name": "멕시코"},
    ]

    db = SessionLocal()
    inserted = 0
    skipped = 0

    try:
        existing = {row.code for row in db.query(Country.code).all()}

        for item in countries:
            if item["code"] in existing:
                skipped += 1
                continue

            db.add(Country(code=item["code"], name=item["name"]))
            existing.add(item["code"])
            inserted += 1

        db.commit()
        return {"inserted": inserted, "skipped": skipped}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Prefer 데이터 삽입
    pref_res = insert_prefer()
    print(f"[INFO] prefers insert done: inserted={pref_res['inserted']}, skipped={pref_res['skipped']}")

    # Country 데이터 삽입
    cntry_res = insert_country()
    print(f"[INFO] country insert done: inserted={cntry_res['inserted']}, skipped={cntry_res['skipped']}")