"""
성수/명동 올리브영 매장 데이터 추가 스크립트
"""
import asyncio
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from app.utils.geocoder import GeoCoder

NEW_STORES = [
    # 성수
    {
        "contentid": "OY_SS_001", "title": "올리브영 성수역점", "contenttypeid": "투어",
        "image": "https://image.oliveyoung.co.kr/cfimages/oystore/D405_1.jpg",
        "usetime": "08:30 ~ 22:30", "restdate": "연중무휴", "fee": None,
        "addr": "서울특별시 성동구 아차산로 91", "mapy": None, "mapx": None, "tel": None,
        "category_depth": "쇼핑 > 뷰티",
        "summary": "성수역 인근에 위치한 올리브영으로, 성수동 카페거리 관광과 함께 이용하기 좋습니다.",
        "description": "올리브영 성수역점은 지하철 2호선 성수역 인근에 위치한 매장입니다. 성수동 카페거리, 대림창고 등 핫플레이스 관광과 함께 K-뷰티 쇼핑을 즐길 수 있습니다. 아침 8시 30분부터 운영합니다.",
        "subway_info": "지하철 2호선 성수역",
        "website": "https://www.oliveyoung.co.kr",
        "tags": ["올리브영", "K뷰티", "화장품", "쇼핑", "성수동", "성수역"]
    },
    {
        "contentid": "OY_SS_002", "title": "올리브영N 성수", "contenttypeid": "투어",
        "image": "https://image.oliveyoung.co.kr/cfimages/oystore/DE25_1.jpg",
        "usetime": "10:00 ~ 22:00", "restdate": "연중무휴", "fee": None,
        "addr": "서울특별시 성동구 연무장7길 13 팩토리얼 성수", "mapy": None, "mapx": None, "tel": None,
        "category_depth": "쇼핑 > 뷰티",
        "summary": "성수동 팩토리얼 성수에 위치한 올리브영 특화 매장 '올리브영N'입니다.",
        "description": "올리브영N 성수는 성수동 핫플레이스 팩토리얼 성수 내에 위치한 특화 매장입니다. 일반 올리브영과 차별화된 체험형 콘텐츠와 큐레이션을 제공하며, 성수동 특유의 트렌디한 분위기에서 K-뷰티를 경험할 수 있습니다.",
        "subway_info": "지하철 2호선 성수역",
        "website": "https://www.oliveyoung.co.kr",
        "tags": ["올리브영", "올리브영N", "K뷰티", "체험", "쇼핑", "성수동"]
    },
    {
        "contentid": "OY_SS_003", "title": "올리브영 성수연방점", "contenttypeid": "투어",
        "image": "https://image.oliveyoung.co.kr/cfimages/oystore/DE80_1.jpg",
        "usetime": "10:00 ~ 21:30", "restdate": "연중무휴", "fee": None,
        "addr": "서울특별시 성동구 성수이로14길 14", "mapy": None, "mapx": None, "tel": None,
        "category_depth": "쇼핑 > 뷰티",
        "summary": "성수 연방 건물에 위치한 올리브영으로, 성수동 카페거리 중심에 있습니다.",
        "description": "올리브영 성수연방점은 성수동 카페거리의 랜드마크인 성수연방 건물에 위치한 매장입니다. 주변에 인기 카페와 맛집이 밀집해 있어 성수동 관광과 K-뷰티 쇼핑을 함께 즐기기에 최적입니다.",
        "subway_info": "지하철 2호선 성수역",
        "website": "https://www.oliveyoung.co.kr",
        "tags": ["올리브영", "K뷰티", "화장품", "쇼핑", "성수동", "성수연방"]
    },
    # 명동
    {
        "contentid": "OY_MD_001", "title": "올리브영 명동 타운", "contenttypeid": "투어",
        "image": "https://image.oliveyoung.co.kr/cfimages/oystore/D176_1.jpg",
        "usetime": "10:00 ~ 22:30", "restdate": "연중무휴", "fee": None,
        "addr": "서울특별시 중구 명동길 53 1~2층", "mapy": None, "mapx": None, "tel": None,
        "category_depth": "쇼핑 > 뷰티",
        "summary": "명동 중심에 위치한 올리브영 대형 플래그십 매장으로, 외국인 관광객에게 가장 인기 있는 K-뷰티 매장입니다.",
        "description": "올리브영 명동 타운은 명동 메인 거리에 위치한 1~2층 규모의 대형 플래그십 매장입니다. 외국인 관광객들에게 가장 유명한 K-뷰티 쇼핑 명소로, 다양한 한국 뷰티 브랜드를 체험하고 구매할 수 있습니다. 면세 서비스도 제공합니다.",
        "subway_info": "지하철 4호선 명동역",
        "website": "https://www.oliveyoung.co.kr",
        "tags": ["올리브영", "K뷰티", "화장품", "쇼핑", "명동", "플래그십", "면세"]
    },
    {
        "contentid": "OY_MD_002", "title": "올리브영 명동점", "contenttypeid": "투어",
        "image": "https://image.oliveyoung.co.kr/cfimages/oystore/DDEC_1.jpg",
        "usetime": "10:00 ~ 22:30", "restdate": "연중무휴", "fee": None,
        "addr": "서울특별시 중구 명동8길 14", "mapy": None, "mapx": None, "tel": None,
        "category_depth": "쇼핑 > 뷰티",
        "summary": "명동8길에 위치한 올리브영으로, 명동 쇼핑 거리 중심에 있습니다.",
        "description": "올리브영 명동점은 명동 핵심 쇼핑 거리인 명동8길에 위치한 매장입니다. 주변에 다양한 뷰티 브랜드 매장과 음식점이 밀집해 있어 명동 관광의 중심에서 K-뷰티 쇼핑을 즐길 수 있습니다.",
        "subway_info": "지하철 4호선 명동역",
        "website": "https://www.oliveyoung.co.kr",
        "tags": ["올리브영", "K뷰티", "화장품", "쇼핑", "명동", "명동역"]
    },
    {
        "contentid": "OY_MD_003", "title": "올리브영 명동타임워크점", "contenttypeid": "투어",
        "image": "https://image.oliveyoung.co.kr/cfimages/oystore/DD6F_1.jpg",
        "usetime": "09:30 ~ 22:30", "restdate": "연중무휴", "fee": None,
        "addr": "서울특별시 중구 남대문로 78 타임워크명동 108호, 109호", "mapy": None, "mapx": None, "tel": None,
        "category_depth": "쇼핑 > 뷰티",
        "summary": "명동 타임워크 빌딩 내 올리브영으로, 아침 9시 30분부터 운영합니다.",
        "description": "올리브영 명동타임워크점은 남대문로 타임워크명동 빌딩 내에 위치한 매장입니다. 아침 9시 30분부터 영업하여 이른 시간 쇼핑이 가능하며, 남대문시장과 명동을 연결하는 동선에 있어 관광에 편리합니다.",
        "subway_info": "지하철 4호선 명동역, 2호선 을지로입구역",
        "website": "https://www.oliveyoung.co.kr",
        "tags": ["올리브영", "K뷰티", "화장품", "쇼핑", "명동", "남대문"]
    },
    {
        "contentid": "OY_MD_004", "title": "올리브영 명동중앙점", "contenttypeid": "투어",
        "image": "https://image.oliveyoung.co.kr/cfimages/oystore/DCC1_1.jpg",
        "usetime": "10:00 ~ 22:30", "restdate": "연중무휴", "fee": None,
        "addr": "서울특별시 중구 명동8나길 18 인송빌딩 1층", "mapy": None, "mapx": None, "tel": None,
        "category_depth": "쇼핑 > 뷰티",
        "summary": "명동 중앙에 위치한 올리브영으로, 명동성당 근처입니다.",
        "description": "올리브영 명동중앙점은 명동 중심부 명동8나길에 위치한 매장으로, 명동성당과 가깝습니다. K-뷰티 인기 제품을 다양하게 갖추고 있어 외국인 관광객들이 많이 찾는 매장입니다.",
        "subway_info": "지하철 4호선 명동역",
        "website": "https://www.oliveyoung.co.kr",
        "tags": ["올리브영", "K뷰티", "화장품", "쇼핑", "명동", "명동성당"]
    },
    {
        "contentid": "OY_MD_005", "title": "올리브영 명동역점", "contenttypeid": "투어",
        "image": "https://image.oliveyoung.co.kr/cfimages/oystore/DE93_1.jpg",
        "usetime": "10:30 ~ 22:30", "restdate": "연중무휴", "fee": None,
        "addr": "서울특별시 중구 퇴계로 115 밀리오레 1층", "mapy": None, "mapx": None, "tel": None,
        "category_depth": "쇼핑 > 뷰티",
        "summary": "명동역 밀리오레 1층에 위치한 올리브영입니다.",
        "description": "올리브영 명동역점은 명동역 바로 앞 밀리오레 건물 1층에 위치한 매장으로, 지하철에서 나오자마자 바로 접근할 수 있어 편리합니다. 명동 쇼핑의 시작점으로 좋은 위치입니다.",
        "subway_info": "지하철 4호선 명동역",
        "website": "https://www.oliveyoung.co.kr",
        "tags": ["올리브영", "K뷰티", "화장품", "쇼핑", "명동", "명동역", "밀리오레"]
    },
    {
        "contentid": "OY_MD_006", "title": "올리브영 명동2가점", "contenttypeid": "투어",
        "image": "https://image.oliveyoung.co.kr/cfimages/oystore/DF23_1.jpg",
        "usetime": "10:00 ~ 22:30", "restdate": "연중무휴", "fee": None,
        "addr": "서울특별시 중구 남대문로 68-1", "mapy": None, "mapx": None, "tel": None,
        "category_depth": "쇼핑 > 뷰티",
        "summary": "명동2가 남대문로변에 위치한 올리브영입니다.",
        "description": "올리브영 명동2가점은 남대문로변에 위치하여 명동과 남대문시장을 연결하는 동선에 있습니다. 관광과 쇼핑을 함께 즐기기에 좋은 위치입니다.",
        "subway_info": "지하철 4호선 명동역, 4호선 회현역",
        "website": "https://www.oliveyoung.co.kr",
        "tags": ["올리브영", "K뷰티", "화장품", "쇼핑", "명동", "남대문"]
    },
    {
        "contentid": "OY_MD_007", "title": "올리브영 명동거리점", "contenttypeid": "투어",
        "image": "https://image.oliveyoung.co.kr/cfimages/oystore/DE0B_1.jpg",
        "usetime": "10:00 ~ 22:30", "restdate": "연중무휴", "fee": None,
        "addr": "서울특별시 중구 명동8나길 9", "mapy": None, "mapx": None, "tel": None,
        "category_depth": "쇼핑 > 뷰티",
        "summary": "명동 거리 중심에 위치한 올리브영입니다.",
        "description": "올리브영 명동거리점은 명동 보행자 거리 중심에 위치한 매장으로, 명동 거리를 걸으며 자연스럽게 방문할 수 있습니다. 외국인 관광객들로 항상 붐비는 인기 매장입니다.",
        "subway_info": "지하철 4호선 명동역",
        "website": "https://www.oliveyoung.co.kr",
        "tags": ["올리브영", "K뷰티", "화장품", "쇼핑", "명동"]
    },
    {
        "contentid": "OY_MD_008", "title": "올리브영 명동대로점", "contenttypeid": "투어",
        "image": "https://image.oliveyoung.co.kr/cfimages/oystore/DF91_1.jpg",
        "usetime": "10:00 ~ 22:30", "restdate": "연중무휴", "fee": None,
        "addr": "서울특별시 중구 퇴계로 120 1층", "mapy": None, "mapx": None, "tel": None,
        "category_depth": "쇼핑 > 뷰티",
        "summary": "명동 대로변에 위치한 올리브영으로, 접근성이 뛰어납니다.",
        "description": "올리브영 명동대로점은 퇴계로 대로변에 위치하여 찾기 쉬운 매장입니다. 명동역에서 충무로역 방향 동선에 있어 명동 관광 중 편리하게 이용할 수 있습니다.",
        "subway_info": "지하철 4호선 명동역, 3호선 충무로역",
        "website": "https://www.oliveyoung.co.kr",
        "tags": ["올리브영", "K뷰티", "화장품", "쇼핑", "명동", "충무로"]
    },
    {
        "contentid": "OY_MD_009", "title": "올리브영 명동글로벌점", "contenttypeid": "투어",
        "image": "https://image.oliveyoung.co.kr/cfimages/oystore/DCC0_1.jpg",
        "usetime": "10:00 ~ 22:30", "restdate": "연중무휴", "fee": None,
        "addr": "서울특별시 중구 명동길 27", "mapy": None, "mapx": None, "tel": None,
        "category_depth": "쇼핑 > 뷰티",
        "summary": "명동길에 위치한 올리브영 글로벌 매장으로, 외국인 관광객 특화 서비스를 제공합니다.",
        "description": "올리브영 명동글로벌점은 명동 메인 거리인 명동길에 위치한 글로벌 특화 매장입니다. 다국어 안내, 면세 서비스 등 외국인 관광객을 위한 서비스를 제공하며, K-뷰티 인기 제품을 폭넓게 갖추고 있습니다.",
        "subway_info": "지하철 4호선 명동역",
        "website": "https://www.oliveyoung.co.kr",
        "tags": ["올리브영", "K뷰티", "화장품", "쇼핑", "명동", "면세", "글로벌"]
    },
]


async def main():
    data_path = BACKEND_DIR / "data" / "oliveyoung_투어.json"

    with open(data_path, encoding="utf-8") as f:
        stores = json.load(f)

    # 기존 데이터에 추가
    stores.extend(NEW_STORES)

    # 좌표 채우기
    geo = GeoCoder()
    updated = 0
    for store in stores:
        if store.get("mapy") and store.get("mapx"):
            continue
        addr = store.get("addr")
        if not addr:
            continue
        result = await geo.geocoder(addr)
        if result:
            store["mapy"] = result["lat"]
            store["mapx"] = result["lon"]
            updated += 1
            print(f"  OK: {store['title']} → ({result['lat']}, {result['lon']})")
        else:
            print(f"  FAIL: {store['title']}")
        await asyncio.sleep(0.1)

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, indent=2)

    print(f"\n총 {len(stores)}개 매장, 좌표 신규 업데이트: {updated}건")


if __name__ == "__main__":
    asyncio.run(main())
