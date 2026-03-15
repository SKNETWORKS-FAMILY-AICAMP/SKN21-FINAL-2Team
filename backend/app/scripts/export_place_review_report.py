from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


TARGET_STATUSES = ("review_needed", "closed_suspected", "no_match")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="네이버 점검 결과 JSONL에서 검토 대상만 별도 JSONL/CSV로 추출합니다."
    )
    parser.add_argument("input", help="입력 checked JSONL 파일")
    parser.add_argument(
        "--statuses",
        nargs="*",
        default=list(TARGET_STATUSES),
        help="추출할 status 목록",
    )
    parser.add_argument(
        "--output-prefix",
        help="출력 파일 prefix. 생략하면 입력 파일명 기준으로 생성",
    )
    return parser.parse_args(argv)


def build_output_paths(input_path: Path, output_prefix: str | None) -> tuple[Path, Path]:
    if output_prefix:
        prefix_path = Path(output_prefix)
    else:
        prefix_path = input_path.with_suffix("")
        prefix_path = prefix_path.with_name(f"{prefix_path.name}_review_report")
    return prefix_path.with_suffix(".jsonl"), prefix_path.with_suffix(".csv")


def serialize_candidate(candidate: dict[str, Any] | None) -> str:
    if not isinstance(candidate, dict):
        return ""
    title = candidate.get("title") or ""
    address = candidate.get("road_address") or candidate.get("jibun_address") or ""
    query = candidate.get("query") or ""
    return f"title={title} | addr={address} | query={query}"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    input_path = Path(args.input).resolve()
    statuses = set(args.statuses)
    jsonl_path, csv_path = build_output_paths(input_path, args.output_prefix)

    rows: list[dict[str, Any]] = []
    with input_path.open("r", encoding="utf-8") as src:
        for line_no, raw_line in enumerate(src, start=1):
            line = raw_line.strip()
            if not line:
                continue
            item = json.loads(line)
            review = item.get("naver_place_review") or {}
            status = review.get("status")
            if status not in statuses:
                continue

            row = {
                "contentid": item.get("contentid", ""),
                "title": item.get("title", ""),
                "addr": item.get("addr", ""),
                "tel": item.get("tel", ""),
                "status": status,
                "score": review.get("score", ""),
                "decision_reason": review.get("decision_reason", ""),
                "matched_candidate_title": ((review.get("matched_candidate") or {}).get("title") or ""),
                "matched_candidate_addr": (
                    ((review.get("matched_candidate") or {}).get("road_address"))
                    or ((review.get("matched_candidate") or {}).get("jibun_address"))
                    or ""
                ),
                "searched_queries": " | ".join(review.get("searched_queries") or []),
                "distance_m": review.get("distance_m", ""),
            }
            rows.append({"item": item, "flat": row, "line_no": line_no})

    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as dst:
        for row in rows:
            dst.write(json.dumps(row["item"], ensure_ascii=False) + "\n")

    fieldnames = [
        "contentid",
        "title",
        "addr",
        "tel",
        "status",
        "score",
        "decision_reason",
        "matched_candidate_title",
        "matched_candidate_addr",
        "searched_queries",
        "distance_m",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as dst:
        writer = csv.DictWriter(dst, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row["flat"])

    print(
        f"[DONE] extracted={len(rows)} jsonl={jsonl_path} csv={csv_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
