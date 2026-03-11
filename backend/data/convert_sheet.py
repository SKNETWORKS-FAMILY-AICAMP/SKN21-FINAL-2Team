import csv
import json
import urllib.request
import io

url = "https://docs.google.com/spreadsheets/d/1zTUYKO0TDQ6iLYhTblUfE95aem1D_Zc3SqogaQLObi0/export?format=csv"

try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        content = response.read().decode('utf-8')

    reader = csv.DictReader(io.StringIO(content))
    output_path = r"c:\project\final\SKN21-FINAL-2Team\backend\data\tour.jsonl"

    count = 0
    with open(output_path, 'w', encoding='utf-8') as f:
        for row in reader:
            clean_row = {k: (v if v is not None else "") for k, v in row.items()}
            f.write(json.dumps(clean_row, ensure_ascii=False) + '\n')
            count += 1
    print(f"Success! {count} rows written to {output_path}")
except Exception as e:
    print(f"Error: {e}")
