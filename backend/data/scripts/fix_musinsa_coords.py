"""
무신사 투어 JSON 좌표/데이터 보정 스크립트
========================================
- 주소 기반 좌표 하드코딩 (Kakao/Naver 지도 기준)
- 매장운영 종료/비정상 매장 제거
- 이미지 없는 매장 보완
- 텍스트 정리
"""

import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "musinsa_투어.json"

# 주소 기반 좌표 (카카오맵/네이버지도에서 확인한 실제 좌표)
COORDS = {
    "서울 마포구 양화로 144": (37.5561, 126.9236),       # 스탠다드 홍대점
    "서울 성동구 아차산로 78": (37.5425, 127.0570),       # 슬랙스 랩 성수
    "서울 서초구 서초대로77길 54": (37.4963, 127.0280),    # 스탠다드 강남점
    "서울 마포구 양화로 164": (37.5569, 126.9226),         # 스토어 홍대
    "서울 성동구 연무장길 83": (37.5440, 127.0562),        # 스탠다드 성수점
    "서울 중구 남대문로 90": (37.5630, 126.9831),          # 스탠다드 명동점
    "서울 성동구 연무장길 81": (37.5438, 127.0560),        # 뷰티 스페이스 1 / 스퀘어 성수
    "서울 성동구 성수동2가 275-89": (37.5445, 127.0555),   # 스페이스 성수 3
    "서울 송파구 올림픽로 300": (37.5136, 127.1028),       # 롯데월드몰 잠실
    "서울 강남구 신사동 640-2": (37.5274, 127.0283),       # 엠프티 압구정
    "서울 서초구 강남대로 441": (37.5045, 127.0250),       # 스토어 강남
    "서울 마포구 서교동 354-2": (37.5565, 126.9245),       # 킥스 홍대
    "서울 송파구 올림픽로 240": (37.5113, 127.0980),       # 롯데백화점 잠실
    "서울 중구 명동길 13": (37.5636, 126.9847),            # 스토어 명동
}

# 제거 대상
REMOVE_TITLES = [
    "매장운영 종료",   # 폐점 매장
    "무신사 부티크",   # 영업시간 비정상 (01:05~08:12)
]

# 이미지 보완 (이미지 없는 매장)
FALLBACK_IMAGES = {
    "무신사스탠다드 슬랙스 랩 성수": "https://image.msscdn.net/display/images/common/2024/08/26/148dbac74bbe4d3f878068005b163027.jpg",
    "무신사 뷰티 스페이스 1": "https://image.msscdn.net/display/images/common/2024/08/27/c02a6bcd738a404ab8033b71cbf262b9.jpg",
}


def match_coords(addr: str) -> tuple[float, float]:
    """주소에서 좌표 찾기"""
    for key, (lat, lon) in COORDS.items():
        if key in addr:
            return lat, lon
    return 0.0, 0.0


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        stores = json.load(f)

    print(f"▶ 원본: {len(stores)}개 매장")

    # 1. 제거 대상 필터링
    filtered = []
    for store in stores:
        title = store["title"]
        if any(rm in title for rm in REMOVE_TITLES):
            print(f"  ✗ 제거: {title}")
            continue
        filtered.append(store)

    # 2. 좌표 보정 + 텍스트 정리
    for store in filtered:
        # 좌표
        lat, lon = match_coords(store["addr"])
        if lat != 0.0:
            store["mapy"] = lat
            store["mapx"] = lon
            print(f"  ✓ 좌표: {store['title']} → ({lat}, {lon})")
        else:
            print(f"  ✗ 좌표 없음: {store['title']} | {store['addr']}")

        # 이미지 보완
        if not store["image"] and store["title"] in FALLBACK_IMAGES:
            store["image"] = FALLBACK_IMAGES[store["title"]]
            print(f"  ✓ 이미지 보완: {store['title']}")

        # 제목 더블 스페이스 수정
        store["title"] = " ".join(store["title"].split())

        # summary/description 재생성 (조사 보정)
        name = store["title"]
        store["summary"] = f"{name}은 무신사의 오프라인 매장으로, 다양한 브랜드의 패션 아이템을 직접 체험하고 구매할 수 있는 공간입니다."
        store["description"] = f"{name}은 {store['addr']}에 위치한 무신사 오프라인 매장입니다. 무신사에서 인기 있는 다양한 브랜드의 의류, 신발, 액세서리 등을 직접 체험하고 구매할 수 있습니다."

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 완료! {len(filtered)}개 매장 저장")
    # 요약
    has_img = sum(1 for s in filtered if s["image"])
    has_coord = sum(1 for s in filtered if s["mapy"] != 0.0)
    print(f"   이미지: {has_img}/{len(filtered)}")
    print(f"   좌표: {has_coord}/{len(filtered)}")


if __name__ == "__main__":
    main()
