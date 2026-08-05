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

## 2. Download
```
uv tool install "yt-dlp[default]" 2>/dev/null; uv run tools/downloader/download.py batches/inbox/<file>.yaml
```
Verify every item downloaded (report lists ok/failed). On proxy 403 CONNECT
failures, the network policy is blocking the domain — tell Terence which
domain to allowlist in the environment settings, don't retry forever.

## 3. Archive to Google Drive
Upload each video to `01_Inbox_Raw/<batch_id>/` (folder IDs in
`docs/SETUP.md`). Prefer the Drive uploader in `tools/drive/`; the Drive MCP
connector works for small files but not large videos. Also upload a
`manifest.md` listing each file with its post URL, Spark code, and hook label.

## 4. Record
Append the batch to `state/batches.json` (id, date, items with post_url,
spark_code, drive file IDs, local status). Move the YAML to
`batches/processed/`. Commit and push state + batch files.

## 5. Propose (draft only — never launch)
Read `state/campaigns.json` for current structure. Draft a setup: which
campaigns/adgroups get which creatives, TikTok side (Spark codes) and Meta
side (downloaded files), suggested budgets based on current spend. Send the
proposal to Terence (Slack if available, otherwise chat) and STOP. Execution
happens only after his explicit approval, via `/execute-setup`.
