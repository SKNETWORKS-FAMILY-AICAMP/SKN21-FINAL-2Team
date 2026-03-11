import os
import json
import time
import requests

# Hardcoded Naver API credentials from .env for robustness in this script
CLIENT_ID = "7fgqgnf5k0"
CLIENT_SECRET = "vdvYOUkpssoXZOgVhBHAJInwI09C1qTBZy8aQDtw"

def get_geocode(query):
    endpoint = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": CLIENT_ID,
        "X-NCP-APIGW-API-KEY": CLIENT_SECRET,
    }
    params = {"query": query}
    try:
        resp = requests.get(endpoint, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "OK" and data.get("addresses"):
            target = data["addresses"][0]
            return {
                "lat": target["y"],
                "lng": target["x"],
                "road": target.get("roadAddress"),
                "jibun": target.get("jibunAddress")
            }
    except Exception as e:
        print(f"Error for {query}: {e}")
    return None

def main():
    input_file = r"c:\Users\Playdata\Documents\SKN21\SKN21-FINAL-2Team\backend\data\image_add\12_관광지_enriched.jsonl"
    output_file = r"c:\Users\Playdata\Documents\SKN21\SKN21-FINAL-2Team\backend\data\image_add\12_관광지_updated.jsonl"
    
    if not os.path.exists(input_file):
        print("Input file not found.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    results = []
    total = len(lines)
    print(f"Starting update of {total} items...")

    for i, line in enumerate(lines):
        item = json.loads(line.strip())
        title = item.get("title", "")
        
        # Search by title
        geo = get_geocode(title)
        
        # If title fails, try existing address
        if not geo:
            addr = item.get("addr", "")
            if addr:
                geo = get_geocode(addr)
        
        if geo:
            item["addr"] = geo["road"] or geo["jibun"] or item.get("addr")
            item["mapx"] = geo["lng"]
            item["mapy"] = geo["lat"]
            print(f"[{i+1}/{total}] {title} -> {item['addr']}")
        else:
            print(f"[{i+1}/{total}] {title} -> FAILED")
            
        results.append(item)
        time.sleep(0.05)

    with open(output_file, 'w', encoding='utf-8') as f:
        for res in results:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
    
    print("Done.")

if __name__ == "__main__":
    main()
