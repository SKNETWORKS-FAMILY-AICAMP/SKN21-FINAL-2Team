"""
auto_start_prompt._format_selected_places_block() 단위 테스트
- image_path, category, description 필드 렌더링 검증
"""
import pytest
from app.schemas.chat import AutoStarterPlaceSeed
from app.agents.prompts.auto_start_prompt import _format_selected_places_block


class TestFormatSelectedPlacesBlock:
    """_format_selected_places_block 함수 테스트"""

    def test_기본_name_address_출력(self):
        places = [AutoStarterPlaceSeed(name="광장시장", adress="서울 종로구", place_id=1)]
        result = _format_selected_places_block(places)
        assert "광장시장" in result
        assert "서울 종로구" in result
        assert "(ID: 1)" in result

    def test_category_포함시_출력됨(self):
        places = [AutoStarterPlaceSeed(name="광장시장", adress="서울 종로구", place_id=1, category="음식점")]
        result = _format_selected_places_block(places)
        assert "카테고리: 음식점" in result

    def test_category_없으면_카테고리_라인_없음(self):
        places = [AutoStarterPlaceSeed(name="광장시장", adress="서울 종로구", place_id=1)]
        result = _format_selected_places_block(places)
        assert "카테고리" not in result

    def test_description_포함시_출력됨(self):
        places = [AutoStarterPlaceSeed(name="광장시장", adress="서울 종로구", place_id=1, description="전통 시장")]
        result = _format_selected_places_block(places)
        assert "설명: 전통 시장" in result

    def test_image_path_프롬프트에_미포함(self):
        """image_path는 프롬프트가 아닌 pinned_places에만 저장 — 프롬프트 라인에 URL 노출 안 됨"""
        places = [AutoStarterPlaceSeed(
            name="광장시장", adress="서울 종로구", place_id=1,
            image_path="https://example.com/image.jpg"
        )]
        result = _format_selected_places_block(places)
        assert "https://example.com/image.jpg" not in result

    def test_category_description_image_모두_있을때_순서(self):
        places = [AutoStarterPlaceSeed(
            name="광장시장", adress="서울 종로구", place_id=1,
            category="음식점",
            description="전통 시장",
            image_path="https://example.com/image.jpg"
        )]
        result = _format_selected_places_block(places)
        # 순서: 이름/ID/주소 → 카테고리 → 설명 (이미지 URL은 없음)
        cat_idx = result.index("카테고리")
        desc_idx = result.index("설명")
        assert cat_idx < desc_idx

    def test_복수_장소_번호_매김(self):
        places = [
            AutoStarterPlaceSeed(name="광장시장", adress="서울 종로구", place_id=1),
            AutoStarterPlaceSeed(name="경복궁", adress="서울 종로구", place_id=2, category="관광지"),
        ]
        result = _format_selected_places_block(places)
        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert lines[0].startswith("1.")
        assert lines[1].startswith("2.")
        assert "카테고리: 관광지" in lines[1]

    def test_빈_리스트_기본값_출력(self):
        result = _format_selected_places_block([])
        assert "이름 없는 장소" in result

    def test_start_date_end_date가_description에_포함된_경우(self):
        """description 필드에 '기간: ...' 형태가 포함된 경우 프롬프트에 렌더됨"""
        places = [AutoStarterPlaceSeed(
            name="서울 팝업스토어",
            adress="서울 성수동",
            place_id=3,
            category="콘텐츠",
            description="기간: 2025-04-01 ~ 2025-04-30"
        )]
        result = _format_selected_places_block(places)
        assert "기간: 2025-04-01 ~ 2025-04-30" in result
