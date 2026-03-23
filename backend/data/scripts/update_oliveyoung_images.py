"""
올리브영 매장 이미지 URL 업데이트 스크립트
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent

# 수집한 이미지 데이터 (매장명 → 이미지 URL)
IMAGES = {
    # 종로
    "종각점": "https://image.oliveyoung.co.kr/cfimages/oystore/D092_1.jpg",
    "종로점": "https://image.oliveyoung.co.kr/cfimages/oystore/DE03_1.jpg",
    "종로YBM점": "https://image.oliveyoung.co.kr/cfimages/oystore/D138_2024113091329311.png",
    "종로1가점": "https://image.oliveyoung.co.kr/cfimages/oystore/D171_1.jpg",
    "스타필드애비뉴그랑서울점": "https://image.oliveyoung.co.kr/cfimages/oystore/DF9A_2025103011628381.jpg",
    "올리브베러 광화문점": "https://image.oliveyoung.co.kr/cfimages/oystore/DFCF_202601291134001.jpg",
    "세종로점": "https://image.oliveyoung.co.kr/cfimages/oystore/D094_1.jpg",
    "안국역점": "https://image.oliveyoung.co.kr/cfimages/oystore/DF89_202603771105561.jpg",
    "경복궁역점": "https://image.oliveyoung.co.kr/cfimages/oystore/DE02_2024102851909081.jpg",
    "대학로점": "https://image.oliveyoung.co.kr/cfimages/oystore/D193_1.jpg",
    # 홍대
    "홍대 타운": "https://image.oliveyoung.co.kr/cfimages/oystore/DE3C_202603620909041.jpg",
    "홍대입구역점": "https://image.oliveyoung.co.kr/cfimages/oystore/D203_2025041131601211.png",
    "홍대공항철도역점": "https://image.oliveyoung.co.kr/cfimages/oystore/DC57_1.jpg",
    "홍대정문점": "https://image.oliveyoung.co.kr/cfimages/oystore/D173_202502510921111.png",
    "홍대사거리점": "https://image.oliveyoung.co.kr/cfimages/oystore/DE18_1.jpg",
    "홍대놀이터점": "https://image.oliveyoung.co.kr/cfimages/oystore/DF31_2025061621351463.png",
    "트렌드팟 바이 올리브영홍대": "https://image.oliveyoung.co.kr/cfimages/oystore/DE90_202602592352091.jpg",
    "트렌드팟 바이 올리브영 홍대": "https://image.oliveyoung.co.kr/cfimages/oystore/DE90_202602592352091.jpg",
    # 강남
    "강남 타운": "https://image.oliveyoung.co.kr/cfimages/oystore/DAEA_1.jpg",
    "강남논현점": "https://image.oliveyoung.co.kr/cfimages/oystore/DE71_1.jpg",
    "신논현역점": "https://image.oliveyoung.co.kr/cfimages/oystore/DF42_1.jpg",
    "역삼역점": "https://image.oliveyoung.co.kr/cfimages/oystore/D122_1.jpg",
    "선릉중앙점": "https://image.oliveyoung.co.kr/cfimages/oystore/DE72_1.jpg",
    "삼성중앙역점": "https://image.oliveyoung.co.kr/cfimages/oystore/DDAE_1.jpg",
    "코엑스몰점": "https://image.oliveyoung.co.kr/cfimages/oystore/D321_1.jpg",
    "코엑스점": "https://image.oliveyoung.co.kr/cfimages/oystore/D321_1.jpg",
    "강남역점": "https://image.oliveyoung.co.kr/cfimages/oystore/DAEA_1.jpg",
    # 잠실
    "잠실학원사거리점": "https://image.oliveyoung.co.kr/cfimages/oystore/DB48_1.jpg",
    "롯데백화점잠실점": "https://image.oliveyoung.co.kr/cfimages/oystore/DD1F_1.jpg",
    "잠실역8호선점": "https://image.oliveyoung.co.kr/cfimages/oystore/BA3E_1.jpg",
    "잠실점": "https://image.oliveyoung.co.kr/cfimages/oystore/DF92_2025123371931221.jpg",
    "잠실장미상가점": "https://image.oliveyoung.co.kr/cfimages/oystore/DC70_1.jpg",
}


def match_image(title: str) -> str | None:
    """매장 title에서 이미지 URL 찾기"""
    # 정확한 매칭 먼저
    for key, url in IMAGES.items():
        if key in title:
            return url
    return None


def main():
    path = DATA_DIR / "oliveyoung_투어.json"
    with open(path, encoding="utf-8") as f:
        stores = json.load(f)

    updated = 0
    missing = []

    for store in stores:
        img = match_image(store["title"])
        if img:
            store["image"] = img
            updated += 1
        else:
            missing.append(store["title"])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, indent=2)

    print(f"이미지 업데이트: {updated}/{len(stores)}건")
    if missing:
        print(f"이미지 없는 매장 ({len(missing)}건): {missing}")


if __name__ == "__main__":
    main()
