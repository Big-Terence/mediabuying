# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "imageio-ffmpeg"]
# ///
"""Batch creative downloader.

Parses a batch YAML (see batches/TEMPLATE.yaml), downloads every post via
tools/downloader/fetch_creatives.sh (yt-dlp, best quality, watermark-free,
bytevc2 excluded), then writes a combined manifest that joins yt-dlp metadata
with the batch's Spark codes / hooks. Files land in downloads/<batch_id>/.

Usage:
    uv run tools/downloader/download.py batches/inbox/2026-08-05_example.yaml
    uv run tools/downloader/download.py --urls URL1 URL2 --batch-id manual-test

Prereqs (once per container):
    uv tool install "yt-dlp[default,curl-cffi]"   # curl-cffi is REQUIRED for TikTok
Network: tiktok.com / tiktokv.com / tiktokcdn*.com must be allowed by the
environment policy. Do NOT pass cookies for TikTok (known audio-loss bug);
IG/FB need a cookies file via COOKIES_FILE env var.

Note: for Spark-code items, the TikTok Business API is the preferred source
(true full-quality file + MD5, see tools/tiktok/) once API access exists;
this downloader is the universal fallback and the path for non-TikTok links.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FETCH = Path(__file__).resolve().parent / "fetch_creatives.sh"

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

    items = []
    if args.batch_file:
        batch = load_batch(Path(args.batch_file))
        batch_id = batch["batch_id"]
        items = [i for i in batch.get("items", []) if i.get("post_url")]
    elif args.urls:
        batch_id = args.batch_id or "manual"
        items = [{"post_url": u} for u in args.urls]
    else:
        ap.error("need a batch file or --urls")

    out_dir = REPO_ROOT / "downloads" / batch_id
    out_dir.mkdir(parents=True, exist_ok=True)
    urls_file = out_dir / "urls.txt"
    urls_file.write_text("\n".join(i["post_url"] for i in items) + "\n")

    proc = subprocess.run(["bash", str(FETCH), str(urls_file), str(out_dir)])

    # Join yt-dlp's manifest with batch metadata (spark codes, hooks) by URL id.
    manifest_path = out_dir / "manifest.json"
    downloaded = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    by_id = {d["id"]: d for d in downloaded if d.get("id")}
    combined = []
    for item in items:
        url = item["post_url"]
        match = next((d for i, d in by_id.items() if i in url), None) or \
                next((d for d in downloaded if d.get("webpage_url") == url), None)
        combined.append({**item, "download": match,
                         "status": "ok" if match and match.get("file") else "failed"})
    (out_dir / "batch_manifest.json").write_text(
        json.dumps({"batch_id": batch_id, "items": combined}, indent=2, ensure_ascii=False))

    ok = sum(1 for c in combined if c["status"] == "ok")
    print(json.dumps({"batch_id": batch_id, "output_dir": str(out_dir),
                      "ok": ok, "failed": len(combined) - ok}, indent=2))
    return 0 if ok == len(combined) and proc.returncode == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
