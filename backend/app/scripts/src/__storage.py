from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# __storage.py (수정)

def load_progress(path: Path) -> Dict[str, Any]:
    p = read_json(path, default={})
    if not isinstance(p, dict):
        p = {}

    done_ids = p.get("done_ids", [])
    if not isinstance(done_ids, list):
        done_ids = []
    done_ids = [str(x) for x in done_ids]

    processed = p.get("processed")
    if not isinstance(processed, int):
        processed = len(done_ids)

    return {
        "done_ids": done_ids,
        "processed": int(processed),
        "last_index": int(p.get("last_index") if p.get("last_index") is not None else (len(done_ids) - 1)),
        "total": int(p.get("total") or 0),
        "updated_at": str(p.get("updated_at") or ""),
    }


def save_progress(path: Path, pr: Dict[str, Any]) -> None:
    done_ids = [str(x) for x in (pr.get("done_ids") or [])]
    processed = pr.get("processed")
    if not isinstance(processed, int):
        processed = len(done_ids)

    last_index = pr.get("last_index")
    if not isinstance(last_index, int):
        last_index = len(done_ids) - 1

    out = {
        "done_ids": done_ids,
        "processed": int(processed),
        "last_index": int(last_index),
        "total": int(pr.get("total") or 0),
        "updated_at": now_iso(),
    }
    write_json(path, out)
