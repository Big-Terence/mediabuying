# Setup & Access Checklist

Single source of truth for what agents can and cannot reach. **Update the
status column whenever something changes.**

## Access checklist

| # | Access | Status | Notes |
|---|--------|--------|-------|
| 1 | Slack (read agency channel, message Terence) | ✅ live | claude.ai connector; channel `C0BH13QSRDM` |
| 2 | Google Drive (create folders/files) | ✅ live | claude.ai connector; large-video upload path TBD (tools/drive) |
| 3 | Gmail (read portal notifications) | ✅ live | claude.ai connector |
| 4 | GitHub (this repo) | ✅ live | via session |
| 5 | Environment network allowlist | ⏳ waiting on Terence | see "Network allowlist" below |
| 6 | Scroll portal (portal.scroll.fr) | ⏳ waiting on Terence | needs login/invite for agent use |
| 7 | TikTok Ads API | ❌ not started | see docs/ARCHITECTURE.md + research notes |
| 8 | Meta Marketing API | ❌ not started | idem |
| 9 | Drive credential for headless sessions | ❌ not started | env-var token so cron sessions can upload |

## Network allowlist (environment settings)

The Claude Code **environment** (not per-session) network policy must allow
these domains. Where the settings UI covers subdomains automatically, the
apex entry is enough; specific hosts are listed in case it doesn't.

Priority 1 — creative pipeline (downloads + archive):
```
tiktok.com
tiktokv.com
tiktokcdn.com
tiktokcdn-us.com
tiktokcdn-eu.com
ibyteimg.com
scroll.fr
googleapis.com
accounts.google.com
googleusercontent.com
```

Priority 2 — ads management APIs:
```
business-api.tiktok.com
ads.tiktok.com
facebook.com
graph.facebook.com
graph-video.facebook.com
fbcdn.net
```

Priority 3 — nice to have:
```
instagram.com
cdninstagram.com
slack.com
files.slack.com
github.com
raw.githubusercontent.com
objects.githubusercontent.com
```

Notes:
- Package registries (pypi, npm) are already reachable — no need to add.
- The Scroll portal may serve files from a cloud bucket (S3/GCS); the first
  real batch download will reveal the domain — expect one follow-up addition.
- Alternative: switch the environment to full network access and skip this
  list entirely (Terence's call; broader but zero friction).

## Watcher sources

Live config in `state/watcher.json`. Slack channel `#ext-quest-scroll` is the
primary trigger ("the new batch is live"), Gmail (`from:scroll.fr`) is the
backup, the portal itself is the delivery surface.

## Google Drive folders

To create on first ingest (record IDs here):
- `Media Buying/01_Inbox_Raw` — ID: _TBD_
- `Media Buying/02_TikTok_SparkAds` — ID: _TBD_
- `Media Buying/03_Meta_Creatives` — ID: _TBD_

## Environment variables (to configure in the Claude environment)

None configured yet. Planned (names final once tooling lands):
- `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`
- `TIKTOK_ACCESS_TOKEN`, `TIKTOK_ADVERTISER_ID`
- `GDRIVE_TOKEN` (headless Drive uploads)
