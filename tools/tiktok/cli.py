# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""TikTok Business API v1.3 CLI.

Thin client for the media-buying workflow. See README.md in this directory
for endpoint semantics and gotchas. Sandbox mode: set TIKTOK_SANDBOX=1.

Env: TIKTOK_ACCESS_TOKEN, TIKTOK_ADVERTISER_ID (TIKTOK_APP_ID/TIKTOK_SECRET
only needed for the one-time oauth token mint).

Usage examples:
    uv run tools/tiktok/cli.py spark-inspect --auth-code '#Xtjb...='
    uv run tools/tiktok/cli.py spark-download --auth-code '#Xtjb...=' --out downloads/x.mp4
    uv run tools/tiktok/cli.py spark-authorize --auth-code '#Xtjb...='
    uv run tools/tiktok/cli.py spark-list
    uv run tools/tiktok/cli.py campaigns
    uv run tools/tiktok/cli.py pause --campaign-ids 123 456
    uv run tools/tiktok/cli.py report --level AUCTION_CAMPAIGN --days 7
"""
import argparse
import hashlib
import json
import os
import sys
import time

import httpx

PROD = "https://business-api.tiktok.com/open_api/v1.3"
SANDBOX = "https://sandbox-ads.tiktok.com/open_api/v1.3"
RETRYABLE = {50002, 60001}


def base_url() -> str:
    return SANDBOX if os.environ.get("TIKTOK_SANDBOX") == "1" else PROD


def call(method: str, path: str, *, params=None, body=None, max_tries=5):
    token = os.environ["TIKTOK_ACCESS_TOKEN"]
    url = f"{base_url()}/{path.strip('/')}/"
    for attempt in range(max_tries):
        r = httpx.request(method, url, params=params, json=body,
                          headers={"Access-Token": token}, timeout=60)
        if r.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        data = r.json()
        code = data.get("code")
        if code == 0:
            return data["data"]
        if code in RETRYABLE and attempt < max_tries - 1:
            time.sleep(2 ** attempt)
            continue
        if code == 40100:
            sys.exit("FATAL: access token invalid/revoked (40100) — re-authorize the app and update TIKTOK_ACCESS_TOKEN")
        sys.exit(f"API error {code}: {data.get('message')} ({path})")
    sys.exit(f"gave up after {max_tries} tries on {path}")


def adv() -> str:
    return os.environ["TIKTOK_ADVERTISER_ID"]


def spark_inspect(auth_code: str) -> dict:
    # httpx encodes params; the '+' -> %2B gotcha applies to hand-built URLs only
    return call("GET", "tt_video/info", params={"advertiser_id": adv(), "auth_code": auth_code})


def cmd_spark_download(args):
    info = spark_inspect(args.auth_code)
    vi = info.get("video_info") or {}
    url = vi.get("preview_url") or vi.get("url")
    if not url:
        sys.exit(f"no video URL (expired code, non-public post, or carousel?): {json.dumps(info)[:500]}")
    out = args.out or f"{info['item_info']['item_id']}.mp4"
    md5 = hashlib.md5()
    with httpx.stream("GET", url, timeout=300, follow_redirects=True) as r, open(out, "wb") as f:
        for chunk in r.iter_bytes():
            f.write(chunk)
            md5.update(chunk)
    expected = vi.get("signature")
    status = "ok" if (not expected or md5.hexdigest() == expected) else "MD5 MISMATCH"
    print(json.dumps({"file": out, "size": os.path.getsize(out), "md5": md5.hexdigest(),
                      "expected_md5": expected, "status": status,
                      "width": vi.get("width"), "height": vi.get("height"),
                      "bit_rate": vi.get("bit_rate"),
                      "auth_end_time": (info.get("auth_info") or {}).get("auth_end_time")}, indent=2))


def cmd_report(args):
    end = time.strftime("%Y-%m-%d")
    start = time.strftime("%Y-%m-%d", time.localtime(time.time() - args.days * 86400))
    data = call("GET", "report/integrated/get", params={
        "advertiser_id": adv(), "report_type": "BASIC", "data_level": args.level,
        "dimensions": json.dumps([{"AUCTION_CAMPAIGN": "campaign_id",
                                   "AUCTION_ADGROUP": "adgroup_id",
                                   "AUCTION_AD": "ad_id"}[args.level]]),
        "metrics": json.dumps(["spend", "impressions", "clicks", "conversion",
                               "cost_per_conversion", "ctr", "cpc"]),
        "start_date": start, "end_date": end, "page_size": 200})
    print(json.dumps(data, indent=2))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("spark-inspect");   p.add_argument("--auth-code", required=True)
    p = sub.add_parser("spark-download");  p.add_argument("--auth-code", required=True); p.add_argument("--out")
    p = sub.add_parser("spark-authorize"); p.add_argument("--auth-code", required=True); p.add_argument("--original-post-auth-code")
    sub.add_parser("spark-list")
    sub.add_parser("campaigns")
    sub.add_parser("adgroups")
    p = sub.add_parser("pause");  p.add_argument("--campaign-ids", nargs="+", required=True)
    p = sub.add_parser("enable"); p.add_argument("--campaign-ids", nargs="+", required=True)
    p = sub.add_parser("budget"); p.add_argument("--adgroup-id", required=True); p.add_argument("--amount", type=float, required=True)
    p = sub.add_parser("report"); p.add_argument("--level", default="AUCTION_CAMPAIGN",
                                                 choices=["AUCTION_CAMPAIGN", "AUCTION_ADGROUP", "AUCTION_AD"])
    p.add_argument("--days", type=int, default=7)
    p = sub.add_parser("raw");    p.add_argument("--method", default="GET"); p.add_argument("--path", required=True)
    p.add_argument("--params"); p.add_argument("--body")
    args = ap.parse_args()

    if args.cmd == "spark-inspect":
        print(json.dumps(spark_inspect(args.auth_code), indent=2))
    elif args.cmd == "spark-download":
        cmd_spark_download(args)
    elif args.cmd == "spark-authorize":
        body = {"advertiser_id": adv(), "auth_code": args.auth_code}
        if args.original_post_auth_code:
            body["original_post_auth_code"] = args.original_post_auth_code
        call("POST", "tt_video/authorize", body=body)
        print(json.dumps(spark_inspect(args.auth_code), indent=2))
    elif args.cmd == "spark-list":
        print(json.dumps(call("GET", "tt_video/list", params={"advertiser_id": adv(), "page_size": 50}), indent=2))
    elif args.cmd == "campaigns":
        print(json.dumps(call("GET", "campaign/get", params={"advertiser_id": adv(), "page_size": 100}), indent=2))
    elif args.cmd == "adgroups":
        print(json.dumps(call("GET", "adgroup/get", params={"advertiser_id": adv(), "page_size": 100}), indent=2))
    elif args.cmd in ("pause", "enable"):
        status = "DISABLE" if args.cmd == "pause" else "ENABLE"
        print(json.dumps(call("POST", "campaign/status/update", body={
            "advertiser_id": adv(), "campaign_ids": args.campaign_ids, "operation_status": status}), indent=2))
    elif args.cmd == "budget":
        print(json.dumps(call("POST", "adgroup/update", body={
            "advertiser_id": adv(), "adgroup_id": args.adgroup_id, "budget": args.amount}), indent=2))
    elif args.cmd == "report":
        cmd_report(args)
    elif args.cmd == "raw":
        print(json.dumps(call(args.method, args.path,
                              params=json.loads(args.params) if args.params else None,
                              body=json.loads(args.body) if args.body else None), indent=2))


if __name__ == "__main__":
    main()
