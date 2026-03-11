from __future__ import annotations

from typing import Any


def get_candidate_point_id(candidate: dict[str, Any] | None) -> str:
    if not isinstance(candidate, dict):
        return ""
    return str(candidate.get("id") or "").strip()


def get_place_id(candidate: dict[str, Any] | None, fallback_to_candidate_id: bool = True) -> str:
    if not isinstance(candidate, dict):
        return ""

    payload = candidate.get("payload") or {}
    if isinstance(payload, dict):
        cid = str(payload.get("contentid") or "").strip()
        if cid:
            return cid

    if fallback_to_candidate_id:
        return get_candidate_point_id(candidate)
    return ""


def get_place_id_from_point(
    point: Any,
    *,
    prefer_payload: bool = True,
    fallback_to_point_id: bool = True,
) -> str:
    payload = getattr(point, "payload", None) or {}
    point_id = str(getattr(point, "id", "") or "").strip()

    payload_cid = ""
    if isinstance(payload, dict):
        payload_cid = str(payload.get("contentid") or "").strip()

    if prefer_payload and payload_cid:
        return payload_cid
    if fallback_to_point_id and point_id:
        return point_id
    if payload_cid:
        return payload_cid
    return ""
