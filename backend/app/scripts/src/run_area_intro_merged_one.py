from pathlib import Path

from src.config import CONTENT_TYPES, load_env
from src.io_utils import read_jsonl
from backend.app.scripts.src.area_collector import collect_area_with_intro_merged_incremental


def run_one(
    target_ctid: int,
    target_label: str,
    throttle_s: float,
    batch_size: int,
    batch_sleep_s: float,
    reset_file: bool = False,
    retry_missing_intro: bool = True,
):
    base_url, service_key, mobile_os, mobile_app, resp_type = load_env()
    outdir = Path("tourapi_out")
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\n===== START {target_label} ({target_ctid}) =====")

    out_path = collect_area_with_intro_merged_incremental(
        base_url=base_url,
        service_key=service_key,
        mobile_os=mobile_os,
        mobile_app=mobile_app,
        resp_type=resp_type,
        outdir=outdir,
        content_type_id=target_ctid,
        label=target_label,
        num_rows=1000,
        throttle_s=throttle_s,
        reset_file=reset_file,
        retry_missing_intro=retry_missing_intro,
        batch_size=batch_size,
        batch_sleep_s=batch_sleep_s,
    )

    rows = read_jsonl(out_path)
    sample = rows[0] if rows else {}
    print(f"[{target_label}] save_file={out_path}")
    print(f"[{target_label}] rows_len={len(rows)}")
    if sample:
        print(f"[{target_label}] sample_title={sample.get('title')}")
        print(f"[{target_label}] sample_keys={list(sample.keys())[:25]}")


if __name__ == "__main__":
    # 단독 실행 테스트용 기본값
    run_one(
        target_ctid=25,
        target_label="여행코스",
        throttle_s=2.0,
        batch_size=20,
        batch_sleep_s=120.0,
        reset_file=False,
        retry_missing_intro=True,
    )
