from app.retrieval.place import PlaceRetriever
from app.utils.config import PLACES_COLLECTION
from qdrant_client.models import Filter, FieldCondition, MatchValue

retriever = PlaceRetriever.get_instance()
client = retriever.client

points, _ = client.scroll(
    collection_name=PLACES_COLLECTION,
    scroll_filter=Filter(
        must=[FieldCondition(key="contenttypeid", match=MatchValue(value="관광지"))]
    ),
    limit=5,
    with_payload=True,
    with_vectors=False
)

for p in points:
    print(f"ID: {p.id}, Payload Keys: {p.payload.keys()}")
    # Print some interesting fields if they exist
    for key in ['cat1', 'cat2', 'cat3', 'contenttypeid', 'title']:
        if key in p.payload:
            print(f"  {key}: {p.payload[key]}")
