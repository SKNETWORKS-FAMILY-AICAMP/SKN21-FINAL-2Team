from app.scripts.check_places_with_naver import (
    LocalSearchCandidate,
    NaverPlaceChecker,
    apply_match_result,
    build_query_variants,
    transliterate_title_variants,
)


def test_transliterate_title_variants_generates_korean_query_for_english_name():
    variants = transliterate_title_variants("Sweet Dream House")

    assert variants
    assert any("드림하우스" in variant for variant in variants)


def test_build_query_variants_includes_address_and_transliterated_title():
    item = {
        "title": "Sweet Dream House",
        "addr": "서울특별시 마포구 와우산로29길 48-14",
    }

    queries = build_query_variants(item)

    assert "서울 마포구 와우산로29길 48-14" in queries
    assert any("드림하우스" in query for query in queries)


def test_evaluate_match_can_recover_when_title_differs_but_address_matches():
    checker = NaverPlaceChecker(sleep_ms=0)
    item = {
        "title": "Sweet Dream House",
        "addr": "서울특별시 마포구 와우산로29길 48-14",
        "mapy": "37.5550000",
        "mapx": "126.9230000",
    }
    queries = ["Sweet Dream House", "서울 마포구 와우산로29길 48-14"]
    candidates = [
        LocalSearchCandidate(
            query=queries[1],
            title="스위드림하우스",
            road_address="서울 마포구 와우산로29길 48-14",
            jibun_address="",
            telephone="02-123-4567",
            category="숙박>게스트하우스",
            link="",
            mapx="126.9230000",
            mapy="37.5550000",
        )
    ]

    result = checker.evaluate_match(item, queries, candidates)

    assert result.status == "open"
    assert result.candidate is not None
    assert result.candidate.title == "스위드림하우스"


def test_apply_match_result_marks_review_and_updates_address_safely():
    item = {
        "title": "Old Name",
        "addr": "서울특별시 강남구 테헤란로 1",
        "tel": "",
        "mapx": "",
        "mapy": "",
    }
    candidate = LocalSearchCandidate(
        query="서울 강남구 테헤란로 1",
        title="완전히다른상호",
        road_address="서울 강남구 테헤란로 1 3층",
        jibun_address="",
        telephone="02-555-0000",
        category="음식점",
        link="",
        mapx="127.0276100",
        mapy="37.4979420",
    )

    result = type(
        "Result",
        (),
        {
            "status": "review_needed",
            "score": 2.3,
            "decision_reason": "주소는 맞지만 이름은 다름",
            "candidate": candidate,
            "searched_queries": ["Old Name", "서울 강남구 테헤란로 1"],
            "name_similarity": 0.1,
            "address_similarity": 0.9,
            "distance_m": 15.0,
        },
    )()

    updated = apply_match_result(item, result)

    assert updated["title"] == "Old Name"
    assert updated["addr"] == "서울 강남구 테헤란로 1 3층"
    assert updated["tel"] == "02-555-0000"
    assert "naver_place_review" not in updated


def test_apply_match_result_can_optionally_include_review_metadata():
    item = {
        "title": "Old Name",
        "addr": "서울특별시 강남구 테헤란로 1",
    }
    candidate = LocalSearchCandidate(
        query="서울 강남구 테헤란로 1",
        title="새상호",
        road_address="서울 강남구 테헤란로 1",
        jibun_address="",
        telephone="",
        category="음식점",
        link="",
        mapx="127.0276100",
        mapy="37.4979420",
    )
    result = type(
        "Result",
        (),
        {
            "status": "open",
            "score": 3.1,
            "decision_reason": "충분한 일치",
            "candidate": candidate,
            "searched_queries": ["Old Name"],
            "name_similarity": 0.9,
            "address_similarity": 1.0,
            "distance_m": 3.0,
        },
    )()

    updated = apply_match_result(item, result, include_review=True)

    assert updated["naver_place_review"]["status"] == "open"
