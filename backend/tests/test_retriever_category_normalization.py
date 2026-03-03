from app.retrieval.place import PlaceRetriever


def test_normalize_category_maps_aliases_to_contenttypeid_values():
    assert PlaceRetriever.get_instance().normalize_category("숙소") == "숙박"
    assert PlaceRetriever.get_instance().normalize_category("카페") == "음식점"
    assert PlaceRetriever.get_instance().normalize_category("체험") == "레포츠"
    assert PlaceRetriever.get_instance().normalize_category("박물관") == "문화시설"


def test_normalize_category_returns_none_for_unknown_or_empty():
    assert PlaceRetriever.get_instance().normalize_category("쇼핑") is None
    assert PlaceRetriever.get_instance().normalize_category("") is None
    assert PlaceRetriever.get_instance().normalize_category(None) is None
