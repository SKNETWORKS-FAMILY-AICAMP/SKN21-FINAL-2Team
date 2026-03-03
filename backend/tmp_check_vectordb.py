from app.retrieval.place import PlaceRetriever
from app.utils.config import PLACES_COLLECTION
from qdrant_client.models import Filter, FieldCondition, MatchValue

def check_vectordb():
    retriever = PlaceRetriever.get_instance()
    client = retriever.client

    print(f"--- Checking {PLACES_COLLECTION} collection ---")
    points, _ = client.scroll(
        collection_name=PLACES_COLLECTION,
        scroll_filter=Filter(
            must=[FieldCondition(key="contenttypeid", match=MatchValue(value="관광지"))]
        ),
        limit=3,
        with_payload=True,
        with_vectors=False
    )

    for p in points:
        print(f"\nID: {p.id}")
        payload = p.payload
        print(f"Title: {payload.get('title')}")
        print(f"Keys: {list(payload.keys())}")
        # Potential candidates for feature/tags
        print(f"LLM Text snippet: {str(payload.get('llm_text', ''))[:100]}...")
        print(f"Cat1/2/3: {payload.get('cat1')}, {payload.get('cat2')}, {payload.get('cat3')}")

if __name__ == "__main__":
    check_vectordb()
