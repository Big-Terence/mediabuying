# Setup & Access Checklist

Single source of truth for what agents can and cannot reach. **Update the
status column whenever something changes.** Agents: read this before assuming
any integration works.

## Access checklist

| # | Access | Status | Notes |
|---|--------|--------|-------|
| 1 | Slack (read `#ext-quest-scroll`, DM Terence) | ✅ live | claude.ai connector; channel `C0BH13QSRDM`; DMs only — bot posts refused in Slack Connect channels |
| 2 | Google Drive API (`www.googleapis.com`) | ✅ reachable now | credential still needed (step C) — the only leg that can go fully live today |
| 3 | Gmail (portal notification backup) | ✅ live | `from:scroll.fr` — note: not every batch emails |
| 4 | GitHub (this repo) | ✅ live | via session proxy; leave GH_TOKEN unset |
| 5 | Network allowlist round 1 | ⏳ Terence | step A below |
| 6 | Google Drive credential | ⏳ Terence | step C — start here, works before allowlist |
| 7 | TikTok developer app + token | ⏳ Terence | step D — approval takes days, start early |
| 8 | Meta system-user token | ⏳ Terence | step E — no review needed, ~15 min |
| 9 | Scroll portal login | ⏳ Terence | password asked to Leo 2026-08-05; nice-to-have, NOT critical path (links arrive in Slack) |
| 10 | Watcher Routine (hourly /check-inbox) | ✅ created | see "Always-on" below |
| 11 | @Claude in Slack (chat entry point) | ⏳ Terence | step F, optional |
| 12 | Network allowlist round 2 (TikTok CDN host) | 🔮 later | revealed by first successful `/tt_video/info/` call |

## Step A — Network allowlist (round 1)

Claude Code environment settings (claude.ai/code → cloud icon above the
message box → gear on this environment → Network access = Custom), tick
"Also include default list of common package managers", add:

```
business-api.tiktok.com
sandbox-ads.tiktok.com
ads.tiktok.com
graph.facebook.com
graph-video.facebook.com
developers.facebook.com
scroll.fr
portal.scroll.fr
tiktok.com
tiktokv.com
tiktokcdn.com
tiktokcdn-us.com
tiktokcdn-eu.com
byteimg.com
ibyteimg.com
fbcdn.net
instagram.com
cdninstagram.com
slack.com
files.slack.com
github.com
raw.githubusercontent.com
objects.githubusercontent.com
googleapis.com
accounts.google.com
googleusercontent.com
```

(googleapis/accounts.google.com are reachable today via the default trusted
list, but adding them explicitly protects against a policy tightening.)
Alternative: Network access = Full — zero friction, broader surface,
Terence's call. Expect ONE more addition later (round 2): the CDN hostname
that TikTok's `preview_url` actually returns, unknowable until the first
successful call.

## Step B — Environment variables

Same dialog, "Environment variables" field (one KEY=value per line). ⚠️ No
encrypted secrets store exists — values are visible to anyone using the
environment (= only Terence). Scope tokens minimally. Sessions copy values at
START — restart the session after editing.

```
TIKTOK_APP_ID=          # step D
TIKTOK_SECRET=          # step D
TIKTOK_ACCESS_TOKEN=    # step D (never expires)
TIKTOK_ADVERTISER_ID=   # step D
META_ACCESS_TOKEN=      # step E (system user, never expires)
META_AD_ACCOUNT_ID=     # act_...
META_PAGE_ID=
META_IG_USER_ID=        # optional
META_PIXEL_ID=          # optional
GDRIVE_CLIENT_ID=       # step C
GDRIVE_CLIENT_SECRET=   # step C
GDRIVE_REFRESH_TOKEN=   # step C
GDRIVE_ROOT_FOLDER_ID=  # printed by tools/drive/upload.py bootstrap
```

Do NOT set GH_TOKEN/GITHUB_TOKEN (the GitHub proxy injects auth).

## Step C — Google Drive credential (works today, do first)

1. Is terence@newquest.ai Google Workspace (admin.google.com loads) or
   consumer Gmail? This picks the branch in 3.
2. console.cloud.google.com → create project `newquest-mediabuying` → enable
   the Drive API (apis/library/drive.googleapis.com).
3. Google Auth Platform → Branding (fill in) → Audience:
   - **Workspace** → user type **Internal**. Done — no expiry issues.
   - **Consumer** → **External**, then **PUBLISH APP** (status must read
     "In production", NOT "Testing" — Testing kills refresh tokens every
     7 days; this is the #1 silent-death cause).
4. Scopes: add ONLY `https://www.googleapis.com/auth/drive.file`
   (non-sensitive → no review/CASA). Full `drive` scope only if Internal.
5. Clients → Create client → **Desktop app** → save client ID + secret.
6. On your laptop (one time): `pip install google-auth-oauthlib` then
   ```
   python -c "from google_auth_oauthlib.flow import InstalledAppFlow; c=InstalledAppFlow.from_client_secrets_file('client.json',['https://www.googleapis.com/auth/drive.file']).run_local_server(port=0, access_type='offline', prompt='consent'); print(c.refresh_token)"
   ```
7. Put the three values in env vars (step B). Then have any session run
   `uv run tools/drive/upload.py bootstrap` — it creates
   `Media Buying/01_Inbox_Raw|02_TikTok_SparkAds|03_Meta_Creatives` and
   prints the IDs → record below + set GDRIVE_ROOT_FOLDER_ID.
   ⚠️ Do NOT create these folders by hand or via the Drive connector — the
   `drive.file` scope makes them invisible to the uploader (404).

**Drive folder IDs** (fill after bootstrap):
- Media Buying (root): _TBD_
- 01_Inbox_Raw: _TBD_ | 02_TikTok_SparkAds: _TBD_ | 03_Meta_Creatives: _TBD_

## Step D — TikTok Business API

1. Confirm the ad account: Business Center + `advertiser_id` (visible in Ads
   Manager). Tell Scroll this is the ONLY account Spark codes should target —
   a code binds to exactly one advertiser_id; wrong binding needs a fresh
   code from the creator.
2. business-api.tiktok.com/portal → My Apps → Create App. Redirect URL: any
   page you own (you copy auth_code from the URL bar once).
3. Scopes: **tick first-level scope 6 "Creative Management"** (covers the
   whole Spark path: 690/691/692/693) + Ads Management + Reporting + Account
   Management. Ads Management alone silently omits `tt_video/*` and the
   pipeline dies at redemption.
4. Submit for review (2-3 days to weeks, no SLA). Meanwhile create a Sandbox
   Ad Account (no review) for campaign-scaffolding tests.
5. Once approved: open the app's authorization URL, approve with the account
   that admins the advertiser, copy `auth_code` from the redirect, then a
   session can mint the token: `POST /oauth2/access_token/ {app_id, secret,
   auth_code}` → token never expires → env vars (step B).
6. High-leverage ask to Scroll: can their creators authorize our app with
   `biz.spark.auth` scope (or do they use TikTok One)? Unlocks programmatic
   Spark-code minting — removes ALL copy-paste from the loop.

## Step E — Meta Marketing API (~15 min, no review)

1. business.facebook.com portfolio must own: ad account, Facebook Page,
   Instagram account (or use a Page-Backed IG Account).
2. developers.facebook.com/apps → Create app → type **Business** → connect
   portfolio → Add Product → **Marketing API**. That's all the "review".
3. Business Settings → Users → System Users → Add (Admin) → assign assets
   with Full control: ad account, Page, IG account, Pixel.
4. System user → Add Apps → your app → **Generate New Token**: check
   `ads_management, ads_read, business_management, pages_read_engagement,
   read_insights` (+ `instagram_basic, instagram_branded_content_ads_brand`
   for partnership ads). Leave 60-day expiry OFF → never expires.
5. Verify at developers.facebook.com/tools/debug/accesstoken: Expires =
   Never, scopes include ads_management. Env vars per step B.
6. 📅 Put **2026-10-27** in your calendar: Meta v26 breaking changes hit all
   API versions that day (repo tooling is already on v26).

## Step F — @Claude in Slack (optional, the "talk to me in Slack" entry point)

Install the Claude app (slack.com/marketplace/A08SF47R6P4, workspace admin) →
App Home → Connect with your claude.ai account → Routing "Code + Chat".
@Claude works in channels (not DMs) and starts real cloud sessions on this
repo. Note: `#ext-quest-scroll` is Slack Connect — better to create an
internal channel (e.g. `#media-buying`) and @Claude there.

## Always-on (Routines)

The watcher is an account-level Routine (survives all sessions):
**"Media buying — check inbox"** — hourly, fresh session per fire, connectors
Slack+Gmail+Google Drive, push notification on noteworthy runs. It runs
`/check-inbox`: Slack watermark poll of `C0BH13QSRDM` → Gmail backup → ingest
+ DM Terence a draft proposal when a batch lands. Manage at
claude.ai/code/routines. A second "daily report" Routine is worth adding once
ad-platform tokens exist.

## Asks to Scroll (social fixes worth more than code)

1. Always post batch announcements + TikTok links in `#ext-quest-scroll`
   (briefs currently leak to WhatsApp, which no watcher can see).
2. Deliver the ORIGINAL master video files in the portal alongside Spark
   codes (strictly better quality than any download, no ToS issues).
3. Standardize Spark codes on 365 days (short codes silently kill live ads).
4. Portal password for Terence (asked 2026-08-05); later, agency-side app
   authorization for programmatic codes (step D.6).
