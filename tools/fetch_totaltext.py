#!/usr/bin/env python3
"""Downloads the Total-Text ground truth, test split.

The official cs-chan/Total-Text-Dataset repository does not host the
annotations themselves: its README links to Google Drive, which cannot be
fetched from a command line -- the same class of problem motchallenge.net
posed on A3. The working source is a HuggingFace mirror that serves the files
one by one.

Only the annotations are downloaded (300 files, ~257 KB). The images are
fetched by select_text.py, and only the ten that make the selection.

    python3 fetch_totaltext.py --out data/totaltext/gt
"""

import argparse
import concurrent.futures
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = "yunusserhat/Total-Text-Dataset"
TREE = f"https://huggingface.co/api/datasets/{REPO}/tree/main/txt_format/Test?limit=1000"
BASE = f"https://huggingface.co/datasets/{REPO}/resolve/main/"
EXPECTED_FILES = 300


def fetch(url: str, dest: Path, attempts: int = 4) -> int:
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                dest.write_bytes(r.read())
            return dest.stat().st_size
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if dest.exists():
                dest.unlink()
            if attempt == attempts:
                raise
            time.sleep(2 * attempt)
    raise RuntimeError("unreachable")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=Path("data/totaltext/gt"))
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(TREE, timeout=60) as r:
        tree = json.load(r)
    files = [e["path"] for e in tree
             if e["path"].endswith(".txt") and "/poly_gt_" in e["path"]]
    print(f"annotation files in the mirror: {len(files)}")

    todo = [p for p in files if not (args.out / Path(p).name).exists()]
    if not todo:
        total = sum(f.stat().st_size for f in args.out.glob("poly_gt_*.txt"))
        print(f"everything is already here: {len(files)} files, {total} B")
        return 0

    print(f"downloading {len(todo)}")
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(lambda p: fetch(BASE + p, args.out / Path(p).name), todo))

    have = sorted(args.out.glob("poly_gt_*.txt"))
    total = sum(f.stat().st_size for f in have)
    print(f"{args.out}: files {len(have)}, {total} B")
    if len(have) != EXPECTED_FILES:
        print(f"expected {EXPECTED_FILES} -- the mirror may have changed, "
              "check before computing anything")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
