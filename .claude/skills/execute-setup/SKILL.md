---
name: execute-setup
description: Execute an approved campaign setup on TikTok and/or Meta — create campaigns/adgroups/ads from Spark codes and Drive creatives, set budgets, then record everything. Use only after Terence explicitly approved a proposed setup.
---

# Execute an approved setup

Precondition: Terence approved a specific proposal (from `/ingest-batch` or an
ad-hoc request). If the approval doesn't match a recorded proposal, confirm
scope before touching anything.

## TikTok (Spark Ads)
Use the TikTok tooling (`tools/tiktok/` CLI or the MCP server if configured in
`.mcp.json`). Flow per creative:
1. Authorize the post in the ad account with its Spark code.
2. Create/locate the target campaign and ad group per the approved plan.
3. Create the Spark Ad referencing the authorized post.
Exact endpoints and auth are documented in `tools/tiktok/README.md` and
`docs/SETUP.md`.

## Meta
Use `tools/meta/` CLI or the Meta MCP server. Flow per creative:
1. Upload the video (from Drive `03_Meta_Creatives` or local `downloads/`).
2. Create/locate campaign + ad set per plan.
3. Create the ad with the uploaded creative.

## Always
- Start new things PAUSED unless the approved plan explicitly says launch live.
- After every mutation, update `state/campaigns.json` with IDs, names,
  budgets, status; commit and push.
- Report back with what was created (names + IDs + status + budgets), and any
  failures verbatim.
