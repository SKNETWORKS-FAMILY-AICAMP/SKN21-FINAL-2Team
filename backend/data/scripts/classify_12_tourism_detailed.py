import json
import re
from collections import Counter
from pathlib import Path

BASE = Path('backend/data/image_add/12_관광지_image_add.jsonl')
OUT = Path('backend/data/image_add/12_관광지_image_add_detailed_categories.jsonl')
SUMMARY = Path('backend/data/image_add/12_관광지_image_add_detailed_category_summary.json')

RULES = [
    ('둘레길/트레킹코스', [r'서울둘레길', r'둘레길', r'트레킹', r'산책로', r'숲길', r'탐방로', r'올레']),
    ('궁궐/왕릉/역사유산', [r'궁$', r'궁\b', r'왕릉', r'릉$', r'종묘', r'사직단', r'고궁', r'유적', r'고택', r'한옥', r'문화유산', r'민속문화재', r'사적']),
    ('사찰/종교성지', [r'사찰', r'암\(', r'암$', r'사\(', r'사$', r'성당', r'교회', r'성지', r'순례길', r'절']),
    ('기념물/동상/탑', [r'동상', r'기념', r'기념비', r'기념관', r'기념탑', r'탑$', r'비$', r'동상$']),
    ('전시/문화공간', [r'박물관', r'미술관', r'전시', r'갤러리', r'아트', r'문화관', r'문화센터', r'체험관', r'홍보관', r'전통문화', r'콘텐츠문화']),
    ('광장/공공공간', [r'광장', r'플라자', r'광장$']),
    ('시장/상권/관광특구', [r'시장', r'특구', r'상점가', r'상가', r'쇼핑', r'명품거리']),
    ('거리/골목/테마거리', [r'거리', r'길$', r'길\(', r'골목', r'로데오', r'먹자골목', r'벽화길']),
    ('공원/도시휴식공간', [r'공원', r'유수지', r'어린이공원', r'근린공원', r'수변공원', r'광장공원']),
    ('산/봉우리/자연경관', [r'산$', r'산\(', r'봉수대', r'봉우리', r'폭포', r'계곡', r'바위', r'전망대', r'전망명소', r'호수', r'습지', r'생태', r'천$', r'천변', r'나루터']),
    ('랜드마크/복합명소', [r'타워', r'SPA', r'스파', r'전망', r'센터', r'돔', r'아레나']),
]


def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def classify(title: str, llm_text: str):
    text = normalize(f'{title} {llm_text}')
    for category, patterns in RULES:
        for pattern in patterns:
            if re.search(pattern, text):
                return category, pattern
    return '기타관광지', 'fallback'

rows = []
with BASE.open(encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        category, reason = classify(row.get('title', ''), row.get('llm_text', ''))
        out = dict(row)
        out['detailed_category'] = category
        out['detailed_category_reason'] = reason
        rows.append(out)

rows.sort(key=lambda r: (r['detailed_category'], r['title']))
with OUT.open('w', encoding='utf-8') as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')

counts = Counter(r['detailed_category'] for r in rows)
summary = {
    'source_file': str(BASE),
    'output_file': str(OUT),
    'total_rows': len(rows),
    'category_counts': dict(sorted(counts.items(), key=lambda x: (-x[1], x[0]))),
}
with SUMMARY.open('w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(json.dumps(summary, ensure_ascii=False, indent=2))
