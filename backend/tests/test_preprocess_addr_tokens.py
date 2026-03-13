from app.scripts.preprocess_data import (
    build_addr_tokens,
    enrich_payload_geo_and_addr_tokens,
    build_sparse_text,
    build_sparse_vector,
)


def test_build_addr_tokens_generates_stem_and_keeps_lot_number():
    payload = {
        "road_address": "서울특별시 용산구 한남대로20길 21-18 (한남동)",
    }

    tokens = build_addr_tokens(payload)

    assert "용산구" in tokens
    assert "용산" in tokens
    assert "한남대로20길" in tokens
    assert "한남동" in tokens
    assert "21-18" in tokens
    assert len(tokens) <= 24


def test_enrich_payload_geo_and_addr_tokens_adds_geo_and_addr_tokens():
    payload = {
        "addr": "서울특별시 성북구 성북로 89",
        "mapy": "37.5912",
        "mapx": "127.0021",
    }

    out = enrich_payload_geo_and_addr_tokens(payload)

    assert out["geo"]["lat"] == 37.5912
    assert out["geo"]["long"] == 127.0021
    assert "성북구" in out["addr_tokens"]
    assert "성북" in out["addr_tokens"]


def test_build_sparse_vector_returns_sorted_indices_and_values():
    indices, values = build_sparse_vector("성북동 카페 성북동")
    assert indices
    assert len(indices) == len(values)
    assert indices == sorted(indices)


def test_build_sparse_text_uses_title_category_and_addr_tokens():
    payload = {
        "title": "손국수",
        "contenttypeid": "음식점",
        "addr_tokens": ["성북동", "성북", "89"],
        "road_address": "서울특별시 성북구 성북로 89",
    }
    text = build_sparse_text(payload)
    assert "손국수" in text
    assert "음식점" in text
    assert "성북동" in text
