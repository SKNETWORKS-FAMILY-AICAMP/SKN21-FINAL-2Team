from app.retrieval.place import PlaceRetriever
from app.utils.config import PLACES_COLLECTION
from qdrant_client.models import Filter, HasIdCondition

def check_specific_points():
    retriever = PlaceRetriever.get_instance()
    client = retriever.client

    target_ids = ["126502", "126482", "126490"]
    # Qdrant IDs can be integers if they were ingested as such. 
    # Let's try to find them.
    
    for tid in target_ids:
        try:
             # Try numeric ID first as common in these scripts
            res = client.retrieve(
                collection_name=PLACES_COLLECTION,
                ids=[int(tid)],
                with_payload=True
            )
            if not res:
                # Try string ID
                res = client.retrieve(
                    collection_name=PLACES_COLLECTION,
                    ids=[tid],
                    with_payload=True
                )
            
            if res:
                p = res[0]
                print(f"\nID: {p.id}")
                print(f"Payload Keys: {list(p.payload.keys())}")
                if 'llm_text' in p.payload:
                    print(f"llm_text: {p.payload['llm_text'][:50]}...")
                else:
                    print("llm_text MISSING")
                # Check for alternatives
                for alt in ['overview', 'description', 'feature', 'content']:
                    if alt in p.payload:
                        print(f"Alternative '{alt}': {str(p.payload[alt])[:50]}...")
            else:
                print(f"\nID {tid} not found")
        except Exception as e:
            print(f"Error checking {tid}: {e}")

if __name__ == "__main__":
    check_specific_points()
