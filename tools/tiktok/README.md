# TikTok Business API tooling

Thin client over TikTok Business API v1.3. No MCP dependency for writes: as of
Aug 2026 all inspectable TikTok Ads MCPs are read-only or third-party SaaS
proxies. TikTok's official first-party MCP server (announced May 2026,
docs: business-api.tiktok.com/portal/docs/tiktok-ads-mcp-server/v1.3) is worth
adopting for interactive sessions once verified — its write coverage and
headless-auth story were unverifiable at research time (network blocked).

## Essentials

- Base URL: `https://business-api.tiktok.com/open_api/v1.3/`
- Sandbox: `https://sandbox-ads.tiktok.com/open_api/v1.3/` (no app review
  needed). ⚠️ Sandbox supports only 22 endpoints — campaign/adgroup/ad CRUD,
  file upload, identity/create, report — and has **zero `tt_video/*`**
  coverage (error 40014). Use it for campaign scaffolding only; develop the
  Spark leg against production with one throwaway code on a PAUSED ad.
- Auth: header literally named `Access-Token`. Tokens DO NOT expire (no
  refresh dance). Env vars: `TIKTOK_APP_ID`, `TIKTOK_SECRET`,
  `TIKTOK_ACCESS_TOKEN`, `TIKTOK_ADVERTISER_ID`.
- Rate limit: stay ≤10 QPS sustained. Handle: 429 + codes 50002/60001 (retry
  w/ backoff), 40067 (shrink report date window), 40100 (token revoked — stop
  and tell Terence), 40002 (resource gone — skip).

## Spark Ads flow (the critical path — non-Spark TikTok ads are dead since Jan 15, 2026)

1. **Inspect code** (validation gate, read-only):
   `GET /tt_video/info/?advertiser_id=&auth_code=` → auth window
   (`auth_start_time`/`auth_end_time`), `item_id`, `item_type` VIDEO|CAROUSEL,
   status, `user_info.identity_id`, and `video_info` incl. **`preview_url` — a
   direct full-quality MP4 link valid ~1 hour** with size/bitrate/`signature`
   (MD5). URL-encode the code: `+` → `%2B` (codes contain `#/+=`).
2. **Download the master** (for archive + Meta reuse): stream `preview_url`
   immediately (1h validity — never persist the URL), verify MD5, upload to
   Drive. `/identity/video/info/` calls the same field `url`. CAROUSEL posts:
   `video_info` is null; use `carousel_info.image_info[].image_url` (90-day
   validity).
   **Day-one test** (docs label the field "preview"; full-quality is
   plausible, not proven): compare Content-Length to `size` and body MD5 to
   `signature` — `cli.py spark-download` does exactly this. Match ⇒ it's the
   real file and yt-dlp becomes unnecessary for TikTok archival. Also log the
   CDN hostname of the returned URL — it's unknown in advance and needs its
   own allowlist entry (egress round 2; likely `*.tiktokcdn.com` /
   `*.byteimg.com`).
3. **Bind**: `POST /tt_video/authorize/` `{advertiser_id, auth_code}` →
   empty data on success; re-read via `/tt_video/info/` or `/tt_video/list/`.
   Endpoint confirmed (doc_id 1738376435339265 + 25 independent
   implementations on GitHub) — redemption is fully automated, no Ads Manager
   detour, one code per call. Terence's approval gate is at campaign launch,
   not at redemption. Ads Manager UI (Tools → Creative library → Spark ads
   posts) remains the manual fallback.
   Duet/stitch posts need the second owner's code as `original_post_auth_code`.
4. **Create ad**: `POST /ad/create/` — array key is **`creatives`** (not
   `ads`): `{advertiser_id, adgroup_id, creatives:[{ad_name,
   identity_type:"AUTH_CODE", identity_id, ad_format:"SINGLE_VIDEO",
   tiktok_item_id, call_to_action}]}`. For Spark-pull: omit `ad_text` (post
   caption is used), never send `image_ids`. Set `dark_post_status`
   explicitly — API default flipped to ON on Jan 27, 2026.
5. **Monitor expiry**: `/tt_video/list/` → `auth_info.auth_end_time` per bound
   post. An expiring code silently kills a live ad. `state/campaigns.json`
   stores `auth_end_time` per creative; `/check-inbox` runs warn ≥7 days
   before expiry. Cleanup: `POST /tt_video/unbind/`.

## Campaign management endpoints

- Campaign: `campaign/create|update|get` + `campaign/status/update`
  (ENABLE/DISABLE = pause). Budget changes via `campaign/update`.
- Ad group: `adgroup/create|update|get` + `adgroup/status/update`. Budget/bid
  live here (`budget`, `budget_mode`, `bid_price` on update). Create requires:
  advertiser_id, campaign_id, adgroup_name, budget, budget_mode,
  billing_event, optimization_goal, pacing, schedule_type,
  schedule_start_time.
- Ads: `ad/create|update|get` + `ad/status/update`.
- Reporting: `GET report/integrated/get` (sync; report_type required); async
  for big pulls: `report/task/create` → `check` → result.
- Money: `advertiser/balance/get`, `advertiser/transaction/get`.

## Scopes (set at app creation)

Ads/Campaign Management, Reporting, Creative Management (first-level scope 6
covers tt_video/* + identity/*: sub-scopes 690 Query TikTok Posts, 691
Authorize TikTok Posts, 693 Query Identity), Account Management.

## Later upgrades

- Programmatic Spark codes: if the agency's creators authorize our app
  (`biz.spark.auth` scope), `POST /business/post/authorize/setting/` mints
  codes without any human copy-paste. Requires agency agreement.
- Smart+ (`smart_plus/*`), automated rules, GMV Max.
