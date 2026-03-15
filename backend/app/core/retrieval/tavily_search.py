import html
import re
import math
import concurrent.futures
from typing import Dict
from langchain_community.tools.tavily_search import TavilySearchResults

from app.utils.error_handler import AppException
from app.agents.models.output import TavilyExtractionOutput
from app.core.llm_factory import LLMFactory
from app.agents.models.place import PlaceInfo
from app.utils.common import build_naver_map_url
from app.utils.geocoder import GeoCoder

class TavilySearch:
    _TAVILY_TIMEOUT_SEC = 10
    _TAVILY_SCORE_THRESHOLD = 0.3
    
    def __init__(self, max_result=10):
        self._tavily = TavilySearchResults(max_results=max_result, include_images=True)

    def _clean_tavily_results(self, raw_results: list) -> list[dict]:
        """Tavily 결과 정제: score 필터 → 서울 키워드 필터 → URL 중복 제거 → 내용 정규화."""
        seen_urls: set[str] = set()
        cleaned = []

        for r in raw_results:
            if not isinstance(r, dict):
                continue

            # score 기준 미달 제거
            score = r.get("score") or 0.0
            if score < self._TAVILY_SCORE_THRESHOLD:
                continue

            # 서울 관련 결과만 허용
            if not self.is_seoul_result(r):
                continue

            # URL 중복 제거
            url = (r.get("url") or "").strip()
            if url and url in seen_urls:
                continue

            if url:
                seen_urls.add(url)
            
            # content 정제: HTML 엔티티 디코딩 + 공백 정규화
            raw_content = r.get("content") or ""
            raw_content = html.unescape(raw_content)
            raw_content = re.sub(r"<[^>]+>", "", raw_content)          # HTML 태그 제거
            raw_content = re.sub(r"\s+", " ", raw_content).strip()    # 공백 정규화
            
            if not raw_content:
                continue

            cleaned.append({
                "title": (r.get("title") or "").strip(),
                "url": url,
                "content": raw_content[:300],
                "score": score,
                "images": r.get("images") or [],
            })

        return cleaned


    def web_search(self, query: str) -> tuple[list[dict], str]:
        results = []

        # ThreadPoolExecutor + shutdown(wait=False) 로 진짜 타임아웃 보장
        # with 블록 방식은 shutdown(wait=True)가 되어 timeout 후에도 블로킹 발생
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._tavily.invoke, query)
        try:
            results = future.result(timeout=self._TAVILY_TIMEOUT_SEC)
        except concurrent.futures.TimeoutError:
            print(f"[TavilySearch] Tavily search timed out after {self._TAVILY_TIMEOUT_SEC:.1f}s")
            future.cancel()
        except Exception as e:
            print(f"[TavilySearch] Tavily search failed: {e}")
            future.cancel()
        finally:
            executor.shutdown(wait=False)

        if not results:
            return [], ""

        sorted_results = sorted(results, key=lambda x: x.get("score", 0.0), reverse=True)
        
        # ==== Tavily 결과 정제 ====
        cleaned = self._clean_tavily_results(sorted_results)
        print(f"[TavilySearch] Tavily raw={len(sorted_results)} → cleaned(Seoul)={cleaned}")

        web_lines = []
        if cleaned:
            for r in cleaned:
                web_lines.append(f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}")
        
        return cleaned, "\n\n".join(web_lines)
        

    async def extract_placeinfos(self, query: str, raw_text: str) -> list[PlaceInfo]:
        """
        Tavily 검색 결과에서 장소 정보[PlaceInfo]를 추출합니다.
        """
        llm = LLMFactory.get_llm(temperature=0.0).with_structured_output(TavilyExtractionOutput)
        extraction_result = await llm.ainvoke([
            ("system", """
            당신은 사용자의 질의와 Tavily 검색 결과를 바탕으로 가장 적합한 장소 정보를 추출하는 전문가입니다.
            스키마의 description을 바탕으로 장소 정보를 추출하세요.
            
            ## 추가 설명
            ### 이미지 URL (image_url):
            - 웹 검색 결과에 포함된 이미지 url들 중 가장 적합한 것을 사용하세요. (ex: https://example.com/image.jpg, https://example.com/image.png, https://example.com/image.gif, https://example.com/image.jpeg)
            - 이미지가 없는 경우, ""로 표시하세요.

            ### 유사도 점수 (score):
            - 사용자의 질의와 해당 장소의 관련성을 0.0에서 1.0 사이의 점수로 평가하세요.
            - 1.0은 매우 관련성이 높음, 0.0은 관련성이 없음.
            """),
            ("human", f"사용자 키워드 : {query}, \n\n Tavily 검색 결과 : {raw_text}")
        ])

        places = []
        for place in extraction_result.places:
            # 위도, 경도 추출
            lat, long = await GeoCoder.get_coordinates(place.address)

            place_info = PlaceInfo(
                place_id="",
                name=place.name,
                address=place.address,
                image_path=place.image_url,
                map_url=build_naver_map_url(place.name, lat, long),
                longitude=long,
                latitude=lat
            )
            places.append(place_info)

        print(f"[TavilySearch] Extracted Place Info: {places}")

        return places


    # =================================================
    # 
    # =================================================
    def in_seoul_bbox(self, lat: float, lng: float) -> bool:
        # 서울 행정 경계 bounding box
        _SEOUL_BBOX = {
            "lat_min": 37.413,
            "lat_max": 37.701,
            "lng_min": 126.734,
            "lng_max": 127.269,
        }
        return (
            _SEOUL_BBOX["lat_min"] <= lat <= _SEOUL_BBOX["lat_max"]
            and _SEOUL_BBOX["lng_min"] <= lng <= _SEOUL_BBOX["lng_max"]
        )


    def is_seoul_result(self, r: Dict) -> bool:
        """Tavily 결과 dict에 서울 관련 키워드가 포함되어 있는지 확인."""
        text = " ".join([
            r.get("content", ""),
            r.get("title", ""),
            r.get("url", ""),
        ])
        return "서울" in text or "Seoul".lower() in text.lower()

    @staticmethod
    def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """두 WGS84 좌표 간 거리(km)."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lng2 - lng1)
        a = (math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def tavily_search_for_places(query, input_geo: tuple[float, float] | None = None, slots_geo: tuple[float, float] | None = None) -> list[PlaceInfo]:
    """
    Tavily 검색을 수행하고 PlaceInfo 리스트를 반환합니다.
    """
    tavily = TavilySearch()

    web_results, web_context = tavily.web_search(query)
    places = await tavily.extract_placeinfos(query, web_context)

    # 서울 bbox 내 장소만 필터링
    places = [place for place in places if tavily.in_seoul_bbox(place.latitude, place.longitude)]

    # 1순위 slots 좌표, 2순위 입력 좌표 기준으로 정렬
    if slots_geo and input_geo:
        places.sort(key=lambda p: (
            tavily.haversine_km(slots_geo[0], slots_geo[1], p.latitude, p.longitude),
            tavily.haversine_km(input_geo[0], input_geo[1], p.latitude, p.longitude)
        ))
    elif slots_geo:
        places.sort(key=lambda p: tavily.haversine_km(slots_geo[0], slots_geo[1], p.latitude, p.longitude))
    elif input_geo:
        places.sort(key=lambda p: tavily.haversine_km(input_geo[0], input_geo[1], p.latitude, p.longitude))

    return places
