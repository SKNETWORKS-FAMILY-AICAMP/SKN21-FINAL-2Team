import os
from qdrant_client import QdrantClient

def check_qdrant():
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", 6333))
    client = QdrantClient(host=host, port=port)
    
    print(f"--- Qdrant Status on {host}:{port} ---")
    try:
        collections = client.get_collections().collections
        print(f"Collections: {[c.name for c in collections]}")
        
        for c in collections:
            info = client.get_collection(c.name)
            print(f"\nCollection: {c.name}")
            print(f"  Status: {info.status}")
            print(f"  Points count: {info.points_count}")
            # Named vectors check
            if info.config.params.vectors:
                print(f"  Vectors Config: {info.config.params.vectors}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_qdrant()
