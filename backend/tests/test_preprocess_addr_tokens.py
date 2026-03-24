from app.scripts.preprocess.config import build_addr_tokens, enrich_geo
from app.scripts.qdrant_upsert import _build_sparse_text, _build_sparse_vector


def test_build_addr_tokens_generates_stem_and_keeps_lot_number():
    tokens = build_addr_tokens("서울특별시 용산구 한남대로20길 21-18 (한남동)")

    assert "용산구" in tokens
    assert "용산" in tokens
    assert "한남대로20길" in tokens
    assert "한남동" in tokens
    assert "21-18" in tokens
    assert len(tokens) <= 24


def test_enrich_geo_adds_geo_and_addr_tokens():
    payload = {
        "addr": "서울특별시 성북구 성북로 89",
        "mapy": "37.5912",
        "mapx": "127.0021",
    }

    enrich_geo(payload)

    assert payload["geo"]["lat"] == 37.5912
    assert payload["geo"]["lon"] == 127.0021
    assert "성북구" in payload["addr_tokens"]
    assert "성북" in payload["addr_tokens"]
    assert "mapy" not in payload
    assert "mapx" not in payload


def test_build_sparse_vector_returns_sorted_indices_and_values():
    indices, values = _build_sparse_vector("성북동 카페 성북동")
    assert indices
    assert len(indices) == len(values)
    assert indices == sorted(indices)


def test_build_sparse_text_uses_title_category_and_addr_tokens():
    payload = {
        "title": "손국수",
        "contenttypeid": "음식점",
        "addr_tokens": ["성북동", "성북", "89"],
        "addr": "서울특별시 성북구 성북로 89",
    }
    text = _build_sparse_text(payload)
    assert "손국수" in text
    assert "음식점" in text
    assert "성북동" in text
