from app.utils.place_id import get_candidate_point_id, get_place_id, get_place_id_from_point


class _Point:
    def __init__(self, pid, payload):
        self.id = pid
        self.payload = payload


def test_get_place_id_prefers_payload_contentid():
    candidate = {"id": "photo-uuid", "payload": {"contentid": "1234"}}
    assert get_place_id(candidate) == "1234"


def test_get_place_id_falls_back_to_candidate_id_when_missing_contentid():
    candidate = {"id": "5678", "payload": {"title": "테스트"}}
    assert get_place_id(candidate) == "5678"


def test_get_candidate_point_id_returns_raw_candidate_id():
    candidate = {"id": "photo-uuid", "payload": {"contentid": "1234"}}
    assert get_candidate_point_id(candidate) == "photo-uuid"


def test_get_place_id_from_point_prefers_payload():
    point = _Point("photo-uuid", {"contentid": "1234"})
    assert get_place_id_from_point(point, prefer_payload=True, fallback_to_point_id=True) == "1234"
