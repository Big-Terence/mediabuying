#!/usr/bin/env bash
# Batch-download social videos (TikTok / IG Reels / Facebook) at best quality, no watermark.
# Usage: ./fetch_creatives.sh urls.txt out_dir
set -euo pipefail

URLS="${1:?usage: fetch_creatives.sh <urls.txt> <out_dir>}"
OUT="${2:-./creatives}"
COOKIES="${COOKIES_FILE:-}"          # optional: Netscape cookies.txt (needed for IG/FB)
IMPERSONATE="${IMPERSONATE:-chrome}"

mkdir -p "$OUT"

# ffmpeg: use system one, else the PyPI static build (pip install imageio-ffmpeg)
FFMPEG_LOC="$(command -v ffmpeg || true)"
if [[ -z "$FFMPEG_LOC" ]]; then
  FFMPEG_LOC="$(python3 -c 'import imageio_ffmpeg,os;print(os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()))' 2>/dev/null || true)"
fi

args=(
  --ignore-config
  --impersonate "$IMPERSONATE"
  # bytevc2 is ByteDance H.266/VVC and is UNPLAYABLE almost everywhere -> exclude it.
  -f 'bv*[vcodec!=none][vcodec!*=bytevc2]+ba/b[vcodec!*=bytevc2]/b'
  # highest resolution first, then bitrate; prefer h264 for ad-platform re-upload safety
  -S 'res,br,codec:h264'
  --merge-output-format mp4
  --remux-video mp4
  --write-info-json
  --no-write-playlist-metafiles
  --embed-metadata
  --retries 10 --fragment-retries 10 --retry-sleep 'http:exp=1:20'
  --sleep-requests 1.5 --min-sleep-interval 2 --max-sleep-interval 6
  --no-abort-on-error
  --download-archive "$OUT/.archive.txt"
  -o "$OUT/%(extractor_key)s__%(uploader,uploader_id,channel)s__%(id)s.%(ext)s"
  --print-to-file '%(id)s\t%(extractor_key)s\t%(uploader)s\t%(webpage_url)s\t%(duration)s\t%(width)sx%(height)s\t%(vcodec)s\t%(format_id)s\t%(title)s' "$OUT/index.tsv"
)
[[ -n "$FFMPEG_LOC" ]] && args+=( --ffmpeg-location "$FFMPEG_LOC" )
[[ -n "$COOKIES"    ]] && args+=( --cookies "$COOKIES" )

yt-dlp "${args[@]}" --batch-file "$URLS"

# Consolidate the .info.json sidecars into one manifest for the media-buying pipeline.
python3 - "$OUT" <<'PY'
import json, pathlib, sys
out = pathlib.Path(sys.argv[1])
rows = []
for p in sorted(out.glob("*.info.json")):
    d = json.loads(p.read_text())
    mp4 = p.with_suffix("").with_suffix(".mp4")
    rows.append({
        "id": d.get("id"),
        "platform": d.get("extractor_key"),
        "author": d.get("uploader") or d.get("uploader_id") or d.get("channel"),
        "author_url": d.get("uploader_url") or d.get("channel_url"),
        "caption": d.get("description") or d.get("title"),
        "webpage_url": d.get("webpage_url"),
        "upload_date": d.get("upload_date"),
        "duration": d.get("duration"),
        "width": d.get("width"), "height": d.get("height"),
        "vcodec": d.get("vcodec"), "format_id": d.get("format_id"),
        "view_count": d.get("view_count"), "like_count": d.get("like_count"),
        "comment_count": d.get("comment_count"), "repost_count": d.get("repost_count"),
        "track": (d.get("track") or (d.get("music") or {}).get("title") if isinstance(d.get("music"), dict) else d.get("track")),
        "file": mp4.name if mp4.exists() else None,
    })
(out / "manifest.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))
print(f"manifest.json: {len(rows)} items -> {out/'manifest.json'}")
PY
