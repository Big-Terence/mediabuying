# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""Meta Marketing API CLI (Graph API v26.0).

Thin client for the media-buying workflow. Auth: Business Manager SYSTEM USER
token (never expires) in META_ACCESS_TOKEN. Managing your own ad account
needs no App Review and no Business Verification.

Env: META_ACCESS_TOKEN, META_AD_ACCOUNT_ID (act_...), META_PAGE_ID,
     META_IG_USER_ID (optional), META_PIXEL_ID (optional).

Everything is created PAUSED. Activation is a separate explicit command.

Usage examples:
    uv run tools/meta/cli.py accounts
    uv run tools/meta/cli.py upload-video --file downloads/b1/clip.mp4
    uv run tools/meta/cli.py video-status --video-id 123
    uv run tools/meta/cli.py create-creative --video-id 123 --thumbnail-url URL \
        --message "ad text" --link https://... --name "b12_diabetes_hook1"
    uv run tools/meta/cli.py create-campaign --name "..." --objective OUTCOME_APP_PROMOTION
    uv run tools/meta/cli.py create-adset --campaign-id 1 --name "..." --daily-budget-cents 5000 \
        --optimization-goal OFFSITE_CONVERSIONS --billing-event IMPRESSIONS
    uv run tools/meta/cli.py create-ad --adset-id 1 --creative-id 2 --name "..."
    uv run tools/meta/cli.py budget --adset-id 1 --daily-budget-cents 8000
    uv run tools/meta/cli.py pause --ids 123 456 / activate --ids 123
    uv run tools/meta/cli.py insights --level ad --days 7
"""
import argparse
import json
import os
import sys
import time

import httpx

V = "v26.0"  # NOTE: v26 breaking changes hit ALL versions on 2026-10-27
BASE = f"https://graph.facebook.com/{V}"
CHUNK_THRESHOLD = 90 * 1024 * 1024  # chunked upload above ~90MB


def token() -> str:
    return os.environ["META_ACCESS_TOKEN"]


def acct() -> str:
    a = os.environ["META_AD_ACCOUNT_ID"]
    return a if a.startswith("act_") else f"act_{a}"


def call(method: str, path: str, *, params=None, data=None, files=None, max_tries=5):
    params = dict(params or {})
    for attempt in range(max_tries):
        r = httpx.request(method, f"{BASE}/{path}", params={**params, "access_token": token()},
                          data=data, files=files, timeout=300)
        body = r.json()
        if r.status_code < 400:
            usage = r.headers.get("x-business-use-case-usage")
            if usage and attempt == 0:
                try:
                    u = list(json.loads(usage).values())[0][0]
                    if max(u.get("call_count", 0), u.get("total_cputime", 0),
                           u.get("total_time", 0)) > 85:
                        print(f"warning: rate budget >85% used: {usage[:200]}", file=sys.stderr)
                except Exception:
                    pass
            return body
        err = body.get("error", {})
        if err.get("code") in (4, 17, 613, 80004) and attempt < max_tries - 1:
            time.sleep(30 * (attempt + 1))
            continue
        sys.exit(f"API error on {path}: {json.dumps(err)[:800]}")
    sys.exit(f"gave up after {max_tries} tries on {path}")


def upload_video(path: str) -> dict:
    size = os.path.getsize(path)
    if size < CHUNK_THRESHOLD:
        with open(path, "rb") as f:
            return call("POST", f"{acct()}/advideos", files={"source": (os.path.basename(path), f, "video/mp4")})
    start = call("POST", f"{acct()}/advideos", data={"upload_phase": "start", "file_size": size})
    session_id, so, eo = start["upload_session_id"], int(start["start_offset"]), int(start["end_offset"])
    with open(path, "rb") as f:
        while so < size:
            f.seek(so)
            chunk = f.read(eo - so)
            resp = call("POST", f"{acct()}/advideos",
                        data={"upload_phase": "transfer", "upload_session_id": session_id,
                              "start_offset": so},
                        files={"video_file_chunk": ("chunk", chunk, "application/octet-stream")})
            so, eo = int(resp["start_offset"]), int(resp["end_offset"])
    return call("POST", f"{acct()}/advideos",
                data={"upload_phase": "finish", "upload_session_id": session_id})


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("accounts")
    p = sub.add_parser("upload-video");  p.add_argument("--file", required=True)
    p = sub.add_parser("video-status");  p.add_argument("--video-id", required=True)
    p = sub.add_parser("create-creative")
    p.add_argument("--video-id", required=True); p.add_argument("--thumbnail-url")
    p.add_argument("--image-hash"); p.add_argument("--message", required=True)
    p.add_argument("--link", required=True); p.add_argument("--name", required=True)
    p.add_argument("--cta", default="LEARN_MORE")
    p = sub.add_parser("create-campaign")
    p.add_argument("--name", required=True)
    p.add_argument("--objective", default="OUTCOME_APP_PROMOTION",
                   choices=["OUTCOME_SALES", "OUTCOME_TRAFFIC", "OUTCOME_ENGAGEMENT",
                            "OUTCOME_LEADS", "OUTCOME_AWARENESS", "OUTCOME_APP_PROMOTION"])
    p.add_argument("--daily-budget-cents", type=int, help="set for CBO")
    p = sub.add_parser("create-adset")
    p.add_argument("--campaign-id", required=True); p.add_argument("--name", required=True)
    p.add_argument("--daily-budget-cents", type=int)
    p.add_argument("--optimization-goal", default="OFFSITE_CONVERSIONS")
    p.add_argument("--billing-event", default="IMPRESSIONS")
    p.add_argument("--countries", nargs="+", default=["US"])
    p.add_argument("--targeting-json", help="full targeting object, overrides --countries")
    p.add_argument("--promoted-object-json")
    p = sub.add_parser("create-ad")
    p.add_argument("--adset-id", required=True); p.add_argument("--creative-id", required=True)
    p.add_argument("--name", required=True)
    p = sub.add_parser("budget"); p.add_argument("--adset-id"); p.add_argument("--campaign-id")
    p.add_argument("--daily-budget-cents", type=int, required=True)
    p = sub.add_parser("pause");    p.add_argument("--ids", nargs="+", required=True)
    p = sub.add_parser("activate"); p.add_argument("--ids", nargs="+", required=True)
    p = sub.add_parser("insights")
    p.add_argument("--level", default="campaign", choices=["account", "campaign", "adset", "ad"])
    p.add_argument("--days", type=int, default=7)
    p = sub.add_parser("raw"); p.add_argument("--method", default="GET")
    p.add_argument("--path", required=True); p.add_argument("--params"); p.add_argument("--data")
    args = ap.parse_args()

    if args.cmd == "accounts":
        out = call("GET", "me/adaccounts", params={"fields": "id,name,account_status,currency"})
    elif args.cmd == "upload-video":
        out = upload_video(args.file)
    elif args.cmd == "video-status":
        out = call("GET", args.video_id, params={"fields": "status,is_instagram_eligible,picture"})
    elif args.cmd == "create-creative":
        video_data = {"video_id": args.video_id, "message": args.message,
                      "call_to_action": {"type": args.cta, "value": {"link": args.link}}}
        if args.image_hash:
            video_data["image_hash"] = args.image_hash
        elif args.thumbnail_url:
            video_data["image_url"] = args.thumbnail_url
        story = {"page_id": os.environ["META_PAGE_ID"], "video_data": video_data}
        if os.environ.get("META_IG_USER_ID"):
            story["instagram_user_id"] = os.environ["META_IG_USER_ID"]
        out = call("POST", f"{acct()}/adcreatives",
                   data={"name": args.name, "object_story_spec": json.dumps(story)})
    elif args.cmd == "create-campaign":
        data = {"name": args.name, "objective": args.objective, "status": "PAUSED",
                "special_ad_categories": "[]"}
        if args.daily_budget_cents:
            data["daily_budget"] = args.daily_budget_cents
        out = call("POST", f"{acct()}/campaigns", data=data)
    elif args.cmd == "create-adset":
        targeting = (json.loads(args.targeting_json) if args.targeting_json
                     else {"geo_locations": {"countries": args.countries}})
        data = {"campaign_id": args.campaign_id, "name": args.name, "status": "PAUSED",
                "optimization_goal": args.optimization_goal,
                "billing_event": args.billing_event, "targeting": json.dumps(targeting)}
        if args.daily_budget_cents:
            data["daily_budget"] = args.daily_budget_cents
        if args.promoted_object_json:
            data["promoted_object"] = args.promoted_object_json
        out = call("POST", f"{acct()}/adsets", data=data)
    elif args.cmd == "create-ad":
        out = call("POST", f"{acct()}/ads",
                   data={"name": args.name, "adset_id": args.adset_id, "status": "PAUSED",
                         "creative": json.dumps({"creative_id": args.creative_id})})
    elif args.cmd == "budget":
        target = args.adset_id or args.campaign_id or sys.exit("need --adset-id or --campaign-id")
        out = call("POST", target, data={"daily_budget": args.daily_budget_cents})
    elif args.cmd in ("pause", "activate"):
        status = "PAUSED" if args.cmd == "pause" else "ACTIVE"
        out = [call("POST", i, data={"status": status}) for i in args.ids]
    elif args.cmd == "insights":
        out = call("GET", f"{acct()}/insights", params={
            "level": args.level, "date_preset": f"last_{args.days}d" if args.days in (7, 14, 28, 30, 90) else None,
            "time_range": None if args.days in (7, 14, 28, 30, 90) else json.dumps({
                "since": time.strftime("%Y-%m-%d", time.localtime(time.time() - args.days * 86400)),
                "until": time.strftime("%Y-%m-%d")}),
            "fields": "campaign_name,adset_name,ad_name,spend,impressions,clicks,ctr,cpc,cpm,"
                      "actions,cost_per_action_type,purchase_roas",
            "limit": 200})
    else:
        out = call(args.method, args.path,
                   params=json.loads(args.params) if args.params else None,
                   data=json.loads(args.data) if args.data else None)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
