import os
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Connect to Qdrant
client = QdrantClient(host="localhost", port=6333)

collection_name = "compliance_openai"
vector_size = 3072

print(f"Testing search on '{collection_name}'...")

try:
    # Create a dummy vector of zeros
    dummy_vector = [0.0] * vector_size
    
    # Search
    results = client.search(
        collection_name=collection_name,
        query_vector=dummy_vector,
        limit=5
    )
    
    print(f"✅ Search successful! Found {len(results)} results.")
    for res in results:
        print(f" - Score: {res.score}, ID: {res.id}")
        
except Exception as e:
    print(f"❌ Search failed: {e}")
