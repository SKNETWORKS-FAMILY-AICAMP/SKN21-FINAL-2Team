from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from app.database.connection import SessionLocal
from app.models.prefer import Prefer

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

        for record in _iter_prefer_records():
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


if __name__ == "__main__":
    result = insert_prefer()
    print(f"prefers insert done: inserted={result['inserted']}, skipped={result['skipped']}")

    
