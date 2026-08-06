---
name: execute-setup
description: Execute an approved campaign setup on TikTok and/or Meta — create campaigns/adgroups/ads from Spark codes and Drive creatives, set budgets, then record everything. Use only after Terence explicitly approved a proposed setup.
---

# Execute an approved setup

Precondition: Terence approved a specific proposal (from `/ingest-batch` or an
ad-hoc request). If the approval doesn't match a recorded proposal, confirm
scope before touching anything.

## TikTok (Spark Ads) — `tools/tiktok/cli.py`
Per creative:
1. Ensure the post is bound (`spark-list`; else `spark-authorize`).
2. Create/locate campaign + ad group per the approved plan.
3. Create the Spark Ad: identity_type AUTH_CODE + identity_id +
   tiktok_item_id, array key `creatives`, no ad_text (post caption is used),
   set `dark_post_status` explicitly. Record auth_end_time in state.
Endpoint details + gotchas: `tools/tiktok/README.md`.

## Meta — `tools/meta/cli.py` (v26.0)
Per creative:
1. `upload-video` (from `downloads/` or Drive), poll `video-status` until
   ready; check `is_instagram_eligible`.
2. `create-creative` (thumbnail required, same aspect ratio; 9:16 for
   Reels/Stories — bad ratio fails at creation). If the creator is on
   Instagram and a partnership-ad code exists, use that path instead
   (keeps the creator handle — see `tools/meta/README.md`).
3. Create/locate campaign + ad set, then `create-ad`.

## Always
- Start new things PAUSED unless the approved plan explicitly says launch live.
- After every mutation, update `state/campaigns.json` with IDs, names,
  budgets, status; commit and push.
- Report back with what was created (names + IDs + status + budgets), and any
  failures verbatim.
