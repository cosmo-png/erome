"""Resumable, size-checked file downloads."""
from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse


def filename(index: int, url: str) -> str:
    base = re.sub(r"[^\w.\-]+", "_", os.path.basename(urlparse(url).path)) or "file"
    return f"{index:03d}_{base}"


def download_file(session, url: str, dest: Path, retries: int = 3, retry_delay: float = 1.5) -> str:
    """Returns 'ok', 'skipped' or 'failed'."""
    if dest.exists():
        return "skipped"
    part = dest.with_name(dest.name + ".part")
    for attempt in range(retries):
        try:
            have = part.stat().st_size if part.exists() else 0
            headers = {"Range": f"bytes={have}-"} if have else {}
            with session.get(url, headers=headers, stream=True, timeout=30) as r:
                if r.status_code == 416:  # stale partial; start clean
                    part.unlink(missing_ok=True)
                    raise IOError("range not satisfiable")
                r.raise_for_status()
                length = int(r.headers.get("Content-Length") or 0)
                if r.status_code == 206:
                    mode, expected = "ab", have + length
                else:
                    mode, expected = "wb", length
                if r.headers.get("Content-Encoding"):
                    expected = 0  # length isn't the file size when compressed
                with open(part, mode) as fh:
                    for chunk in r.iter_content(1 << 16):
                        fh.write(chunk)
            if expected and part.stat().st_size != expected:
                part.unlink(missing_ok=True)
                raise IOError("size mismatch")
            part.replace(dest)
            return "ok"
        except Exception:
            if attempt < retries - 1:
                time.sleep(retry_delay * (attempt + 1))
    return "failed"


def download_album(session, media, folder: Path, workers: int = 4, on_file=None, retry_delay: float = 1.5):
    folder.mkdir(parents=True, exist_ok=True)
    counts = {"ok": 0, "skipped": 0, "failed": 0}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(download_file, session, m.url, folder / filename(m.index or i, m.url), 3, retry_delay)
            for i, m in enumerate(media, 1)
        ]
        for fut in as_completed(futures):
            counts[fut.result()] += 1
            if on_file:
                on_file()
    return counts
