import random
import requests
import json
import sys

# Configuration
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
BASE_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

COLLECTIONS = [
    {"name": "compliance_openai", "size": 3072},
    {"name": "qa_compliance_openai", "size": 3072},
    {"name": "compliance_gemini", "size": 768},
    {"name": "qa_compliance_gemini", "size": 768}
]

def test_search(collection_name, vector_size):
    print(f"\n🔍 Testing collection: {collection_name} ({vector_size}d)")
    
    # Generate random vector
    vector = [random.random() for _ in range(vector_size)]
    
    payload = {
        "vector": vector,
        "limit": 5,
        "with_payload": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/collections/{collection_name}/points/search",
            json=payload,
            timeout=5
        )
        
        if response.status_code == 200:
            results = response.json().get("result", [])
            print(f"✅ Success! Found {len(results)} items.")
            return True
        else:
            print(f"❌ Failed! Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print(f"🚀 Starting Qdrant Debugger (Target: {BASE_URL})")
    
    # Check Qdrant Health
    try:
        r = requests.get(f"{BASE_URL}/healthz")
        if r.status_code != 200:
            print("❌ Qdrant is not healthy!")
            sys.exit(1)
        print("✅ Qdrant is healthy.")
    except Exception as e:
        print(f"❌ Could not connect to Qdrant: {e}")
        sys.exit(1)

    # Test Collections
    failures = 0
    for col in COLLECTIONS:
        if not test_search(col["name"], col["size"]):
            failures += 1
            
    if failures == 0:
        print("\n🎉 All collections are working correctly!")
        sys.exit(0)
    else:
        print(f"\n⚠️ {failures} collections failed tests.")
        sys.exit(1)

if __name__ == "__main__":
    main()
