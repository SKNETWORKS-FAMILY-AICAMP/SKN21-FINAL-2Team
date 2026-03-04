from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def build_evaluation_summary(
    stage: str,
    sample_count: int,
    executed: bool,
    metrics: dict[str, Any],
    skipped_reason: str | None = None,
) -> dict[str, Any]:
    summary = {
        "stage": stage,
        "sample_count": sample_count,
        "executed": executed,
    }
    if skipped_reason:
        summary["skipped_reason"] = skipped_reason
    summary.update(metrics)
    return summary


def write_evaluation_outputs(
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    output_prefix: str,
    output_dir: str | Path,
) -> tuple[Path, Path, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report_path = out_dir / f"{output_prefix}_report.csv"
    summary_json_path = out_dir / f"{output_prefix}_summary.json"
    summary_txt_path = out_dir / f"{output_prefix}_summary.txt"

    if rows:
        fieldnames = list(rows[0].keys())
        with report_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                record = {}
                for key, value in row.items():
                    if isinstance(value, (list, dict)):
                        record[key] = json.dumps(value, ensure_ascii=False)
                    else:
                        record[key] = value
                writer.writerow(record)
    else:
        with report_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["message"])
            writer.writerow(["no rows"])

    with summary_json_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    lines = ["--- Evaluation Summary ---"]
    for key, value in summary.items():
        lines.append(f"{key}: {value}")
    with summary_txt_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return report_path, summary_json_path, summary_txt_path
