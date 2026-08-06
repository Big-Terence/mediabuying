---
name: check-inbox
description: The always-on watcher routine — check Slack, Gmail, and Drive for a new creative batch from the Scroll agency; if found, ingest it and DM Terence a draft proposal. Designed to run in scheduled (Routine) sessions; must end silently when nothing is new.
---

# Check for new batches

`git pull` first. Cursors live in `state/watcher.json`.

## 1. Slack — primary signal (two passes)

- **Pass A** (authoritative): `slack_read_channel(channel_id="C0BH13QSRDM",
  oldest=<slack.last_ts>)`, paginate via cursor.
- **Pass B** (safety net): `slack_search_public_and_private(query="in:#ext-quest-scroll batch", after=<last_ts>)` —
  catches messages whose author fails to resolve in Pass A (known bug: agency
  members sometimes render with empty author; NEVER key detection on author).

A batch is live when any of: text matches `/batch.{0,20}(is|now|est)\s+live/i`;
≥3 distinct TikTok video URLs (`tiktok\.com/(@[\w.]+/video/\d{17,20}|t/[A-Za-z0-9]+)`);
a `portal.scroll.fr/invite` link.

**Always advance `slack.last_ts` to the newest message seen — including on
empty runs.** A parse bug must not re-trigger the same batch forever.

## 2. Gmail — weak backup
`search_threads(query="from:scroll.fr newer_than:2d")`. Not every batch
emails (07-31 didn't). If Gmail fires with no Slack match, that mismatch
itself goes in the ping.

## 3. Drive — archive check (optional)
`search_files`: `sharedWithMe = true and createdTime > '<watermark>' and mimeType contains 'video/'`.

## Outcomes

**Nothing new** → update watcher.json cursors, commit, push, end WITHOUT
messaging anyone.

**Batch found** → idempotency first: key = the announcement message `ts`; if
already in `state/batches.json`, just advance cursors and end. Otherwise run
`/ingest-batch`, then DM Terence (`U0BA6LKTVQV` — never the agency channel):
batch summary (N creatives, hooks/use cases), Drive links, draft proposal,
"ready to set up — go?". Do NOT execute.

**Degradation** (connector missing, token revoked, download failures) → say
so in a DM instead of failing silently. Also warn when any Spark code in
`state/campaigns.json` expires in <7 days.
