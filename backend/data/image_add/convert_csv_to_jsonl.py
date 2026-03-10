import csv
import json
import os
import sys

def convert_csv_to_jsonl(csv_path, jsonl_path):
    print(f"Starting conversion: {csv_path} -> {jsonl_path}")
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return

    encodings = ['utf-8-sig', 'cp949', 'utf-8', 'euc-kr']
    
    data = []
    success = False
    
    for enc in encodings:
        try:
            with open(csv_path, 'r', encoding=enc) as f:
                content = f.read(1024)
                if not content:
                    continue
                f.seek(0)
                reader = csv.DictReader(f)
                data = list(reader)
                if data:
                    print(f"Successfully read CSV with encoding: {enc}")
                    success = True
                    break
        except Exception as e:
            print(f"Failed with {enc}: {e}")
            continue
            
    if not success or not data:
        print(f"Failed to read CSV data from: {csv_path}")
        return

    try:
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for entry in data:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print(f"Successfully converted {len(data)} rows to JSONL: {jsonl_path}")
    except Exception as e:
        print(f"Failed to write JSONL file: {e}")

if __name__ == "__main__":
    csv_file = r'c:\Users\Playdata\Documents\SKN21\SKN21-FINAL-2Team\backend\data\image_add\공중화장실정보_서울특별시.csv'
    jsonl_file = r'c:\Users\Playdata\Documents\SKN21\SKN21-FINAL-2Team\backend\data\image_add\공중화장실정보_서울특별시.jsonl'
    
    convert_csv_to_jsonl(csv_file, jsonl_file)
