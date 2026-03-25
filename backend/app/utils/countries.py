from dataclasses import dataclass, field


@dataclass
class Country:
    """ISO 3166-1 alpha-2 기반 국가 정보 모델"""
    code: str          # ISO 국가 코드 (예: "KR", "JP")
    name: str          # 국가 영문명
    style: str = field(default="")  # 여행 스타일 선호 경향
    food: str = field(default="")   # 음식 선호 경향

    def prefer_hint(self) -> str | None:
        """여행 스타일 + 음식 선호를 합쳐서 반환. 둘 다 없으면 None."""
        parts = []
        if self.style:
            parts.append(self.style)
        if self.food:
            parts.append(f"음식: {self.food}")
        return " / ".join(parts) or None


# 새로운 국가 추가 시 이 리스트에만 항목을 추가하면 됩니다.
COUNTRIES: list[Country] = [
    Country("KR", "South Korea"),
    Country(
        "CN", "China",
        style="K-콘텐츠 체험·쇼핑(올리브영·다이소)·SNS 인증샷 중심, 효율적 동선 선호",
        food="길거리 음식(떡볶이·붕어빵), 매콤·짭짤한 한식(삼겹살·부대찌개) 선호",
    ),
    Country(
        "JP", "Japan",
        style="감성 카페 투어·K-Beauty·디자이너 브랜드 쇼핑, 슬로우 여행",
        food="정갈한 음식(비빔밥·불고기·삼계탕)·디저트 선호, 매운 음식 못 먹음",
    ),
    Country(
        "US", "United States",
        style="숨은 명소 탐방·자연(등산)·역사 문화 체험, 여유로운 일정",
        food="전통 한식(된장찌개·김밥·생선구이) 선호, 매운 음식 못 먹음",
    ),
    Country("TW", "Taiwan"),
    Country("TH", "Thailand"),
    Country("VN", "Vietnam"),
    Country("PH", "Philippines"),
    Country("SG", "Singapore"),
    Country("MY", "Malaysia"),
    Country("ID", "Indonesia"),
    Country("IN", "India"),
    Country("GB", "United Kingdom"),
    Country("DE", "Germany"),
    Country("FR", "France"),
    Country("IT", "Italy"),
    Country("ES", "Spain"),
    Country("AU", "Australia"),
    Country("CA", "Canada"),
    Country("BR", "Brazil"),
]

# 코드 기반 빠른 조회용 맵 (내부 사용)
_COUNTRY_MAP: dict[str, Country] = {c.code: c for c in COUNTRIES}

# 기존 호환용 (NATIONALITY_HINTS 형태가 필요한 경우)
NATIONALITY_HINTS: dict[str, str] = {
    c.code: hint for c in COUNTRIES if (hint := c.prefer_hint())
}


def get_country(code: str) -> Country | None:
    """국가 코드로 Country 객체 조회"""
    return _COUNTRY_MAP.get(code)


def get_nationality_hint(code: str) -> str | None:
    """국가 코드로 여행 선호 경향 힌트 반환. 없으면 None."""
    country = _COUNTRY_MAP.get(code)
    return country.prefer_hint() if country else None
