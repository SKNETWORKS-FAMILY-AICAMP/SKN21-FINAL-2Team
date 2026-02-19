from __future__ import annotations

from typing import Dict, List, Optional, Set

from datetime import datetime

from .__config import (
    Settings,
    places_jsonl_path,
    places_test_jsonl_path,
    checkpoint_path,
    legacy_progress_path,
)
from .__storage import read_jsonl, write_jsonl, load_progress, save_progress, now_iso
from .__collectors import collect_category_items


def _load_done_ids(settings: Settings, ct: int) -> Set[str]:
    p = checkpoint_path(settings, ct)
    pr = load_progress(p)
    return set(pr.get("done_ids") or [])



def _append_done_ids(
    settings: Settings,
    ct: int,
    ids: List[str],
    *,
    last_index: int | None = None,
    total: int | None = None,
) -> None:
    p = checkpoint_path(settings, ct)
    pr = load_progress(p)

    done = list(dict.fromkeys(pr.get("done_ids", []) + [str(x) for x in ids]))
    pr["done_ids"] = done
    pr["processed"] = len(done)
    pr["updated_at"] = now_iso()

    if last_index is not None:
        try:
            pr["last_index"] = max(int(pr.get("last_index", -1)), int(last_index))
        except Exception:
            pr["last_index"] = int(last_index)
    else:
        pr["last_index"] = max(int(pr.get("last_index") or -1), len(done) - 1)

    if total is not None:
        try:
            pr["total"] = int(total)
        except Exception:
            pr["total"] = 0

    save_progress(p, pr)




def run_pipeline(
    settings: Settings,
    content_types: List[int],
    area_code: int,
    resume: bool,
    fresh: bool,
    num_rows: int,
    throttle: float,
    verbose: bool,
    test_one: bool,
    test_pages: int,
    test_geocode_limit: int,
) -> Dict[int, Dict[str, int]]:
    summary: Dict[int, Dict[str, int]] = {}

    for ct in content_types:
        resume_done_ids: Optional[set] = _load_done_ids(settings, ct) if resume else None

        rows, meta = collect_category_items(
            settings=settings,
            ct=ct,
            area_code=area_code,
            resume_done_ids=resume_done_ids,
            fresh=fresh,
            num_rows=num_rows,
            throttle=throttle,
            verbose=verbose,
            test_one=test_one,
            pages_limit=test_pages,
            test_geocode_limit=test_geocode_limit,
        )

        out_path = places_test_jsonl_path(settings, ct) if test_one else places_jsonl_path(settings, ct)

        if test_one:
            write_jsonl(out_path, rows)
            if verbose:
                print(f"[WRITE] ct={ct} -> {out_path} rows={len(rows)}")
        else:
            prev = read_jsonl(out_path)
            prev_map = {str(r.get("contentid")): r for r in prev if r.get("contentid")}
            new_ids: List[str] = []

            for r in rows:
                cid = str(r.get("contentid") or "")
                if not cid:
                    continue
                prev_map[cid] = r
                new_ids.append(cid)

            merged = list(prev_map.values())
            write_jsonl(out_path, merged)

            _append_done_ids(
                settings,
                ct,
                new_ids,
                total=int(meta.get("total") or 0),
            )

            if verbose:
                print(f"[WRITE] ct={ct} -> {out_path} rows={len(merged)}")

        summary[ct] = {
            "fetched": int(meta.get("fetched") or 0),
            "wrote": int(meta.get("wrote") or 0),
            "skipped": int(meta.get("skipped") or 0),
            "errors": int(meta.get("errors") or 0),
            "geocode_calls": int(meta.get("geocode_calls") or 0),
        }

    return summary
