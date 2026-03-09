import json
from pathlib import Path

from app.scripts.fill_missing_images_visitkorea import (
    extract_attraction_candidates,
    extract_representative_image_url,
    normalize_search_response,
    process_jsonl,
    select_best_candidate,
    similarity_score,
)


class _FakeVisitKoreaClient:
    def __init__(self, search_map=None, detail_map=None):
        self.search_map = search_map or {}
        self.detail_map = detail_map or {}
        self.search_calls = []
        self.detail_calls = []

    def open(self):
        return None

    def close(self):
        return None

    def search(self, query: str):
        self.search_calls.append(query)
        if query not in self.search_map:
            raise RuntimeError("query not mocked")
        value = self.search_map[query]
        if isinstance(value, Exception):
            raise value
        return value

    def fetch_detail_html(self, cotid: str) -> str:
        self.detail_calls.append(cotid)
        if cotid not in self.detail_map:
            raise RuntimeError("cotid not mocked")
        value = self.detail_map[cotid]
        if isinstance(value, Exception):
            raise value
        return value


def test_normalize_search_response_handles_malformed_tail():
    malformed = '{"Data":[{"Result":[{"GroupResult":[]}]}]},,]}'
    parsed = normalize_search_response(malformed)
    assert "Data" in parsed
    assert isinstance(parsed["Data"], list)


def test_extract_attraction_candidates_filters_type():
    payload = {
        "Data": [
            {
                "Result": [
                    {
                        "ContentTypeName": "recommend",
                        "GroupResult": [{"COT_ID": "r-1", "TITLE": "추천"}],
                    },
                    {
                        "ContentTypeName": "attraction",
                        "GroupResult": [{"COT_ID": "a-1", "TITLE": "여행지1"}],
                    },
                ]
            }
        ]
    }
    candidates = extract_attraction_candidates(payload)
    assert len(candidates) == 1
    assert candidates[0]["COT_ID"] == "a-1"


def test_similarity_score_and_best_candidate():
    candidates = [
        {"COT_ID": "1", "TITLE": "가문 유적지"},
        {"COT_ID": "2", "TITLE": "가문"},
    ]
    match = select_best_candidate("가문", candidates)
    assert match.candidate is not None
    assert match.candidate["COT_ID"] == "2"
    assert similarity_score("가문", "가문") > similarity_score("가문", "가문 유적지")


def test_extract_representative_image_url_prefers_og_image():
    html = """
    <html><head><meta property="og:image" content="https://cdn.visitkorea.or.kr/img/a.jpg"></head>
    <body><img src="/resources/images/fallback.jpg"></body></html>
    """
    image_url = extract_representative_image_url(
        html, "https://korean.visitkorea.or.kr/detail/detail_view.do?cotid=abc"
    )
    assert image_url == "https://cdn.visitkorea.or.kr/img/a.jpg"


def test_extract_representative_image_url_uses_fallback_img_selector():
    html = """
    <html><body>
      <div class="detail_top_wrap"><img src="/resources/images/top.jpg"></div>
    </body></html>
    """
    image_url = extract_representative_image_url(
        html, "https://korean.visitkorea.or.kr/detail/detail_view.do?cotid=abc"
    )
    assert image_url == "https://korean.visitkorea.or.kr/resources/images/top.jpg"


def test_process_jsonl_updates_missing_only_and_writes_report(tmp_path):
    input_path = tmp_path / "in.jsonl"
    output_path = tmp_path / "out.jsonl"
    report_path = tmp_path / "report.json"

    records = [
        {"contentid": "1", "title": "가문", "image": ""},
        {"contentid": "2", "title": "가담", "image": "https://existing.example.com/img.jpg"},
        {"contentid": "3", "title": "없는곳", "image": ""},
    ]
    with input_path.open("w", encoding="utf-8") as wf:
        for record in records:
            wf.write(json.dumps(record, ensure_ascii=False) + "\n")

    payload_for_gamun = {
        "Data": [
            {
                "Result": [
                    {
                        "ContentTypeName": "attraction",
                        "GroupResult": [
                            {"COT_ID": "cot-1", "TITLE": "가문", "IMAGE_URL": "dummy"}
                        ],
                    }
                ]
            }
        ]
    }
    payload_for_not_found = {"Data": [{"Result": []}]}

    detail_html = """
    <html><head><meta property="og:image" content="https://cdn.visitkorea.or.kr/img/final.jpg"></head></html>
    """
    fake_client = _FakeVisitKoreaClient(
        search_map={"가문": payload_for_gamun, "없는곳": payload_for_not_found},
        detail_map={"cot-1": detail_html},
    )

    stats = process_jsonl(
        input_path=input_path,
        output_path=output_path,
        report_path=report_path,
        limit=None,
        similarity_threshold=0.65,
        sleep_seconds=0,
        timeout=10,
        headless=True,
        client=fake_client,
    )

    assert stats.total == 3
    assert stats.target_missing == 2
    assert stats.filled == 1
    assert stats.skipped_existing == 1
    assert stats.no_attraction == 1

    with output_path.open("r", encoding="utf-8") as rf:
        out_records = [json.loads(line) for line in rf if line.strip()]

    assert len(out_records) == 3
    assert out_records[0]["image"] == "https://cdn.visitkorea.or.kr/img/final.jpg"
    assert out_records[1]["image"] == "https://existing.example.com/img.jpg"
    assert out_records[2]["image"] == ""

    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    assert report["summary"]["filled"] == 1
    assert len(report["failures"]) >= 1
