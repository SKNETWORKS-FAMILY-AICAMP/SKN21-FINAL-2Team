import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('QDRANT_HOST', "localhost")
port = int(os.getenv('QDRANT_PORT', 6333))
client = QdrantClient(host=host, port=port)

try:
    collections = client.get_collections().collections
    print(f"Total collections: {len(collections)}")
    for col in collections:
        count = client.get_collection(col.name).points_count
        print(f"Collection: {col.name}, Points: {count}")
except Exception as e:
    print(f"Error: {e}")
