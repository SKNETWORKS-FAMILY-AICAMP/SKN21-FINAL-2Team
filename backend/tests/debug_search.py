import os
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

def debug_search():
    client = QdrantClient(host="localhost", port=6333)
    
    print("--- Checking Payload Sampling ---")
    scroll_result = client.scroll(
        collection_name="places",
        limit=5,
        with_payload=True
    )
    for point in scroll_result[0]:
        print(f"Point ID: {point.id}")
        print(f"Payload: {point.payload}")
        print("-" * 20)

    print("\n--- Testing '음식점' (39) Filter ---")
    filter_39 = Filter(
        must=[FieldCondition(key="category", match=MatchValue(value="39"))]
    )
    res_39 = client.count(collection_name="places", count_filter=filter_39)
    print(f"Count for category='39': {res_39.count}")

    print("\n--- Testing '음식점' (Literal) Filter ---")
    filter_lit = Filter(
        must=[FieldCondition(key="category", match=MatchValue(value="음식점"))]
    )
    res_lit = client.count(collection_name="places", count_filter=filter_lit)
    print(f"Count for category='음식점': {res_lit.count}")

if __name__ == "__main__":
    debug_search()
