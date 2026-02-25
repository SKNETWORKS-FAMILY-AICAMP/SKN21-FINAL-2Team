import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app.retrieval.place import PlaceRetriever

def verify():
    retriever = PlaceRetriever.get_instance()
    
    # 1. Scenario 2: Text -> Text (Semantic)
    print("\n--- [Scenario 2] Text -> Text (Semantic) ---")
    results_t_t = retriever.search_text("경복궁 근처 맛집", limit=2)
    for i, r in enumerate(results_t_t):
        payload = r.payload
        print(f"{i+1}. {payload.get('title')} (score: {r.score:.4f})")

    # 2. Scenario 1: Text -> Image (Cross-modal)
    print("\n--- [Scenario 1] Text -> Image (Cross-modal) ---")
    results_t_i = retriever.search_text_to_image("바다가 보이는 풍경", limit=2)
    for i, r in enumerate(results_t_i):
        payload = r.payload
        print(f"{i+1}. {payload.get('title')} (score: {r.score:.4f})")

    # 3. Scenario 4: Hybrid
    print("\n--- [Scenario 4] Hybrid (Text + Image Simulation) ---")
    # Simulation: Just text for now, but uses the hybrid fusion logic
    results_h = retriever.search_hybrid("제주도 돌담길", limit=2)
    for i, r in enumerate(results_h):
        payload = r.get('payload', {})
        print(f"{i+1}. {payload.get('title')} (score: {r.get('score'):.4f})")

if __name__ == "__main__":
    verify()
