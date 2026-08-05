# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Batch creative downloader.

Takes a batch YAML (see batches/TEMPLATE.yaml) or raw URLs and downloads each
video in the best available quality via yt-dlp, with a .info.json metadata
sidecar per file. Files land in downloads/<batch_id>/.

Usage:
    uv run tools/downloader/download.py batches/inbox/2026-08-05_example.yaml
    uv run tools/downloader/download.py --urls URL1 URL2 --batch-id manual-test

Requires: yt-dlp on PATH (uv tool install "yt-dlp[default]"), and the
environment's network policy must allow tiktok.com / *.tiktokcdn.com (plus
instagram.com etc. for other platforms). ffmpeg recommended for format merging.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Highest-quality preference: H.265/H.264 source over adaptive re-encodes.
# yt-dlp picks the best matching format; TikTok watermark-free formats are
# preferred automatically by the extractor.
FORMAT = "bv*+ba/b"

def download_one(url: str, out_dir: Path, retries: int = 3) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "--format", FORMAT,
        "--write-info-json",
        "--no-playlist",
        "--retries", str(retries),
        "--output", str(out_dir / "%(uploader)s_%(id)s.%(ext)s"),
        "--print", "after_move:filepath",
        "--no-simulate",
        "--quiet",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return {"url": url, "status": "failed", "error": proc.stderr.strip()[-2000:]}
    filepath = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else None
    return {"url": url, "status": "ok", "file": filepath}

def load_batch(path: Path) -> dict:
    import yaml
    with open(path) as f:
        return yaml.safe_load(f)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_file", nargs="?", help="Path to a batch YAML")
    ap.add_argument("--urls", nargs="*", default=[], help="Raw URLs instead of a batch file")
    ap.add_argument("--batch-id", default=None)
    args = ap.parse_args()

    if args.batch_file:
        batch = load_batch(Path(args.batch_file))
        batch_id = batch["batch_id"]
        urls = [i["post_url"] for i in batch.get("items", []) if i.get("post_url")]
    elif args.urls:
        batch_id = args.batch_id or "manual"
        urls = args.urls
    else:
        ap.error("need a batch file or --urls")
        return 2

    out_dir = REPO_ROOT / "downloads" / batch_id
    results = [download_one(u, out_dir) for u in urls]

    report = {
        "batch_id": batch_id,
        "output_dir": str(out_dir),
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["failed"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
