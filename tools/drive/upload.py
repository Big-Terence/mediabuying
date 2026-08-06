# /// script
# requires-python = ">=3.10"
# dependencies = ["google-api-python-client", "google-auth"]
# ///
"""Google Drive uploader for creative batches.

Auth: user OAuth refresh token (3 env vars) — NOT a service account (SAs have
0 storage quota since 2023 and cannot own files in My Drive), NOT the Drive
MCP connector (base64-through-context is arithmetically impossible for video).
Scope is drive.file: this script can only see folders IT created, so the
whole Media Buying tree must be created by this script (run `bootstrap`),
never by hand or via the connector.

Env: GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN,
     GDRIVE_ROOT_FOLDER_ID (set after `bootstrap` prints it).

Usage:
    uv run tools/drive/upload.py bootstrap
    uv run tools/drive/upload.py upload --files downloads/b1/*.mp4 \
        --lane 01_Inbox_Raw --batch-id 2026-08-05_batch12
    uv run tools/drive/upload.py check   # credential + quota health check
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

FOLDER = "application/vnd.google-apps.folder"
LANES = ["01_Inbox_Raw", "02_TikTok_SparkAds", "03_Meta_Creatives"]
CHUNK = 16 * 1024 * 1024  # 16 MiB: bounded re-send on failure, multiple of 256 KiB


def service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GDRIVE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GDRIVE_CLIENT_ID"],
        client_secret=os.environ["GDRIVE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
    return build("drive", "v3", credentials=creds,
                 static_discovery=True, cache_discovery=False)


def ensure_folder(svc, name, parent_id):
    safe = name.replace("'", "\\'")
    q = (f"name = '{safe}' and '{parent_id}' in parents and "
         f"mimeType = '{FOLDER}' and trashed = false")
    hits = svc.files().list(q=q, spaces="drive", fields="files(id,name)",
                            pageSize=2).execute().get("files", [])
    if hits:
        return hits[0]["id"]
    return svc.files().create(body={"name": name, "mimeType": FOLDER,
                                    "parents": [parent_id]},
                              fields="id").execute()["id"]


def local_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def upload_one(svc, path, folder_id, props):
    name = os.path.basename(path)
    md5 = local_md5(path)
    safe = name.replace("'", "\\'")
    dup = svc.files().list(
        q=f"name = '{safe}' and '{folder_id}' in parents and trashed = false",
        fields="files(id,md5Checksum,webViewLink)").execute().get("files", [])
    for d in dup:
        if d.get("md5Checksum") == md5:
            return {**d, "name": name, "skipped": "already uploaded (md5 match)"}

    media = MediaFileUpload(path, mimetype="video/mp4", chunksize=CHUNK, resumable=True)
    req = svc.files().create(
        body={"name": name, "parents": [folder_id], "appProperties": props},
        media_body=media, fields="id,name,size,md5Checksum,webViewLink")
    resp, tries = None, 0
    while resp is None:
        try:
            status, resp = req.next_chunk(num_retries=3)
            tries = 0
        except HttpError as e:
            retryable = e.resp.status in (500, 502, 503, 504) or "ateLimit" in str(e)
            tries += 1
            if not retryable or tries > 6:
                raise
            time.sleep(min(2 ** tries, 32) + random.random())
    if resp.get("md5Checksum") != md5:
        resp["warning"] = f"md5 mismatch: local {md5} vs drive {resp.get('md5Checksum')}"
    return resp


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bootstrap")
    sub.add_parser("check")
    p = sub.add_parser("upload")
    p.add_argument("--files", nargs="+", required=True)
    p.add_argument("--lane", choices=LANES, default="01_Inbox_Raw")
    p.add_argument("--batch-id", required=True)
    p.add_argument("--props", help='extra appProperties as JSON, e.g. {"spark_code":"..."}')
    args = ap.parse_args()
    svc = service()

    if args.cmd == "bootstrap":
        root = ensure_folder(svc, "Media Buying", "root")
        out = {"GDRIVE_ROOT_FOLDER_ID": root}
        for lane in LANES:
            out[lane] = ensure_folder(svc, lane, root)
        print(json.dumps(out, indent=2))
        print("\n-> set GDRIVE_ROOT_FOLDER_ID in the environment and record all IDs in docs/SETUP.md",
              file=sys.stderr)
    elif args.cmd == "check":
        about = svc.about().get(fields="storageQuota,user").execute()
        print(json.dumps(about, indent=2))
    else:
        root = os.environ["GDRIVE_ROOT_FOLDER_ID"]
        lane_id = ensure_folder(svc, args.lane, root)
        year_id = ensure_folder(svc, time.strftime("%Y"), lane_id)
        batch_id = ensure_folder(svc, args.batch_id, year_id)
        props = {"batch_id": args.batch_id, **(json.loads(args.props) if args.props else {})}
        results = []
        for f in args.files:
            try:
                results.append(upload_one(svc, f, batch_id, props))
            except Exception as e:
                results.append({"name": os.path.basename(f), "error": str(e)[:500]})
        print(json.dumps({"folder_id": batch_id, "files": results}, indent=2))
        if any("error" in r for r in results):
            sys.exit(1)


if __name__ == "__main__":
    main()
