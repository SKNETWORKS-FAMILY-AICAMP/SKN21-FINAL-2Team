from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    out.append(obj)
            except Exception:
                continue
    return out


def append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()


def write_jsonl(path: Path, rows: List[Dict[str, Any]], append: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()


def load_json(path: Path, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not path.exists():
        return {} if default is None else default
    try:
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else ({} if default is None else default)
    except Exception:
        return {} if default is None else default


def save_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush()


def _guess_ext_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"):
        if path.endswith(ext):
            return ext
    return ".jpg"


def download_image(url: str, save_path: Path, timeout: float = 15.0) -> bool:
    try:
        r = requests.get(url, timeout=timeout, stream=True)
        if r.status_code != 200:
            return False
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with save_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception:
        return False


def save_firstimage_for_row(
    row: Dict[str, Any],
    image_root: Path,
    category_label: str,
) -> Dict[str, Any]:
    url = str(row.get("firstimage", "")).strip()
    if not url:
        return row

    contentid = str(row.get("contentid", "")).strip()
    title = str(row.get("title", "")).strip() or "untitled"

    safe_title = safe_filename(title)
    ext = _guess_ext_from_url(url)
    fname = f"{contentid}_{safe_title}{ext}" if contentid else f"{safe_title}{ext}"

    folder = image_root / safe_filename(category_label)
    save_path = folder / fname

    ok = download_image(url, save_path)
    if ok:
        row["image_local_path"] = str(save_path.as_posix())

    return row
