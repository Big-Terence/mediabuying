---
name: report
description: Pull current performance from TikTok and Meta ads (spend, results, CPA/ROAS by campaign and creative) and summarize for Terence. Use when he asks how ads are doing, or as part of scheduled check-ins.
---

# Performance report

1. Read `state/campaigns.json` for the campaigns we manage.
2. Pull insights for the requested window (default: last 7 days + yesterday)
   from both platforms via their tooling (`tools/tiktok/`, `tools/meta/`, or
   MCP servers).
3. Summarize: spend, results (installs/purchases per the account's objective),
   cost per result, trend vs previous period — per platform, per campaign,
   and per creative (so we learn which hooks win).
4. Flag: creatives with spend but zero results, campaigns hitting budget caps,
   anything anomalous. Suggest actions but take none without approval (except
   the emergency-pause rule in CLAUDE.md).
5. Numbers exactly as the APIs return them.
