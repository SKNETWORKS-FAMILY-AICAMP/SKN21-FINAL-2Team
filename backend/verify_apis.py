import requests

def test_apis():
    base_url = "http://localhost:8000/api"
    endpoints = ["/attractions", "/restaurants", "/hot-places"]
    
    for ep in endpoints:
        try:
            url = base_url + ep
            print(f"Testing {url}...")
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            data = r.json()
            print(f"  Status: {r.status_code}")
            print(f"  Type: {type(data)}")
            if isinstance(data, list):
                print(f"  Count: {len(data)}")
                if len(data) > 0:
                    print(f"  Keys in first item: {list(data[0].keys())}")
            else:
                print(f"  Data: {data}")
        except Exception as e:
            print(f"  Error testing {ep}: {e}")
        print("-" * 20)

if __name__ == "__main__":
    test_apis()
