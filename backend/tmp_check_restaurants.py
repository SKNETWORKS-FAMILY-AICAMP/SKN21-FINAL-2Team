from app.retrieval.place import PlaceRetriever
from app.utils.config import PLACES_COLLECTION
from qdrant_client.models import Filter, FieldCondition, MatchValue

def check_restaurants():
    retriever = PlaceRetriever.get_instance()
    client = retriever.client

    print(f"--- Checking restaurants in {PLACES_COLLECTION} ---")
    points, _ = client.scroll(
        collection_name=PLACES_COLLECTION,
        scroll_filter=Filter(
            must=[FieldCondition(key="contenttypeid", match=MatchValue(value="음식점"))]
        ),
        limit=3,
        with_payload=True,
        with_vectors=False
    )

    for p in points:
        print(f"\nID: {p.id}")
        print(f"Payload: {p.payload}")

if __name__ == "__main__":
    check_restaurants()
