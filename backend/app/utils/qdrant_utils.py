import logging
import random
from typing import List

from app.utils.common import to_client_image_url

logger = logging.getLogger(__name__)


def scroll_random_places(client, content_type: str, limit: int = 3, collection_name: str = None) -> List[dict]:
    """Qdrant에서 contenttypeid 기준으로 장소를 랜덤 샘플링하여 반환.

    Args:
        client: Qdrant 클라이언트 인스턴스
        content_type: 검색할 contenttypeid 값 (예: "관광지", "음식점")
        limit: 반환할 최대 장소 수
        collection_name: 사용할 컬렉션 이름 (None이면 PLACES_COLLECTION 사용)

    Returns:
        contentid / name / address / image 키를 가진 딕셔너리 리스트
    """
    from qdrant_client.models import FieldCondition, Filter, MatchValue
    from app.utils.config import PLACES_COLLECTION

    if collection_name is None:
        collection_name = PLACES_COLLECTION

    try:
        points, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="contenttypeid", match=MatchValue(value=content_type))]
            ),
            limit=50,
            with_payload=True,
        )
        if not points:
            return []
        sampled = random.sample(points, min(limit, len(points)))
        return [
            {
                "contentid": str(p.id),
                "name": (p.payload or {}).get("title", "Unknown"),
                "address": (
                    (p.payload or {}).get("addr")
                    or (p.payload or {}).get("address")
                    or "주소 정보 없음"
                ),
                "image": to_client_image_url(
                    (p.payload or {}).get("image") or (p.payload or {}).get("firstimage", "")
                ),
            }
            for p in sampled
        ]
    except Exception as e:
        logger.error("Failed to fetch places (type=%s): %s", content_type, e)
        return []
