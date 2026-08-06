---
name: ingest-batch
description: Ingest a new creative batch from the agency — parse links + Spark Ads codes, download videos in full quality, archive to Google Drive, update state, and propose a draft campaign setup. Use whenever Terence provides TikTok links/Spark codes, says "new batch", or a batch YAML lands in batches/inbox/.
---

# Ingest a creative batch

## 1. Normalize the input
Whatever form the batch arrives in (pasted links + Spark codes, a Slack
message, a portal export, an existing YAML), produce a batch YAML in
`batches/inbox/` following `batches/TEMPLATE.yaml`. Rules:
- `batch_id` = `YYYY-MM-DD_<short-name>`, unique against `state/batches.json`.
- Pair each Spark code with its post URL. If codes and links arrive unpaired,
  match by order; if ambiguous, ask Terence rather than guess.
- Spark codes are copied EXACTLY (they are case-sensitive tokens).

## 2. Download (order of preference)
1. **TikTok API** (items with a Spark code, once `TIKTOK_ACCESS_TOKEN`
   exists): `uv run tools/tiktok/cli.py spark-download --auth-code '...'` —
   full-quality MP4 with MD5 verification, then
   `spark-authorize` to bind (automated; no approval needed at this stage).
2. **Portal master files** (once portal access exists) — best quality.
3. **yt-dlp fallback** (no code / no token / non-TikTok):
   `uv tool install "yt-dlp[default,curl-cffi]"` (curl-cffi is mandatory for
   TikTok), then `uv run tools/downloader/download.py batches/inbox/<file>.yaml`.

Verify every item (reports list ok/failed). On proxy 403 CONNECT failures the
network policy blocks the domain — tell Terence WHICH host (this is expected
once for the TikTok CDN, see SETUP.md round 2), don't retry forever.

## 3. Archive to Google Drive
`uv run tools/drive/upload.py upload --files downloads/<batch>/*.mp4 --lane
01_Inbox_Raw --batch-id <batch_id> --props '{"spark_code":"..."}'` — the
uploader creates `<lane>/<year>/<batch_id>/`, dedupes by MD5, stamps
appProperties. Never upload video bytes through the Drive MCP connector
(context-size impossible); connector is fine for the manifest text file.
Also upload a `manifest.md` listing each file with post URL, Spark code,
auth window, and hook label.

## 4. Record
Append the batch to `state/batches.json` (id, date, items with post_url,
spark_code, drive file IDs, local status). Move the YAML to
`batches/processed/`. Commit and push state + batch files.

## 5. Propose (draft only — never launch)
Read `state/campaigns.json` for current structure. Draft a setup: which
campaigns/adgroups get which creatives, TikTok side (Spark codes, note each
code's auth_end_time) and Meta side (downloaded files; prefer partnership-ad
codes when the creator is on Instagram), suggested budgets based on current
spend. Creatives map to use cases (see channel briefs) — flag any creative
that doesn't match a briefed use case, like Terence does. DM the proposal to
Terence (`U0BA6LKTVQV`; chat if Slack unavailable) and STOP. Execution only
after explicit approval, via `/execute-setup`.
