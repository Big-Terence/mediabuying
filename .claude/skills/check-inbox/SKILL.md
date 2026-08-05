---
name: check-inbox
description: The always-on watcher routine — check Slack, Gmail, and the agency portal for a new creative batch; if found, ingest it and ping Terence with a draft proposal. Designed to run in scheduled (cron) sessions.
---

# Check for new batches

Run these checks; sources and their config live in `docs/SETUP.md` →
"Watcher sources" (update it as sources are added).

1. **Slack**: read the configured agency channel since the last check
   (`state/watcher.json` stores the last-seen timestamp per source). Look for
   messages announcing creatives: TikTok links, Spark codes, file attachments,
   portal links.
2. **Gmail**: search for unread notification emails from the agency/portal
   domains listed in SETUP.md.
3. **Portal**: if a portal with API/URL is configured, check it per its
   section in SETUP.md.

If nothing new: update `state/watcher.json` timestamps, commit, end quietly —
no message to Terence.

If a batch is found: run `/ingest-batch` on it, then message Terence on Slack
(channel/DM per SETUP.md) with: batch summary (N creatives, hooks), Drive
links, and the draft proposal — phrased as "ready to go, want me to set it
up?". Do NOT execute anything.

If a source is unreachable (revoked token, missing connector in headless
session), note it in the Slack ping instead of failing silently.
