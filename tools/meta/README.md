# Meta Marketing API tooling

Thin CLI over Graph API **v26.0** (shipped 2026-07-29). System-user token in
`META_ACCESS_TOKEN` (never expires). Own-account management needs no App
Review / Business Verification — Meta's own doc: "If your app is only
managing your ad account, standard access to the ads_read and ads_management
permissions are sufficient."

## ⚠️ Dated warnings

- **2026-10-27**: v26 breaking changes propagate to ALL supported API
  versions. Do not use `instagram_positions: ['explore']` (removed) or
  Delivery Estimate fields.
- Rate limits (dev tier, per ad account): score 60 per 300s (read=1,
  write=3); ads_management 300 + 40×active ads per hour. Watch
  `X-Business-Use-Case-Usage` (the CLI warns >85%). Upgrade to Advanced
  Access only if throttled (needs Business Verification + 1,500 calls/15d).

## Creative pipeline (UGC videos)

1. `upload-video` → `POST /act_X/advideos` (multipart <90MB, chunked
   start/transfer/finish above). Max 2.3GB.
2. Poll `video-status` until `status.video_status == "ready"`; check
   `is_instagram_eligible`.
3. `create-creative` → `object_story_spec` with page_id (+
   `instagram_user_id` — `instagram_actor_id` is gone in v26), `video_data`
   {video_id, image_hash/image_url thumbnail (**required**, same aspect ratio
   ≥600px), message, call_to_action}.
4. `create-campaign` / `create-adset` / `create-ad` — all forced PAUSED;
   `activate` is explicit.

Video specs: 9:16 for Reels/Stories, 4:5 feed; ≥1080px recommended; videos
are never auto-cropped — out-of-spec ratio fails at creative creation.

## Partnership Ads (Meta's Spark Ads equivalent — prefer when creator is on IG)

Creator sends an ad code (`POST /{ig-media-id}/partnership_ad_code` on their
side, or Instagram app → Post → ⋯ → Partnership ads). Brand side: creative
with `branded_content: {"instagram_boost_post_access_token": "<AD_CODE>",
"ad_format": 1}` — keeps the creator's handle + social proof, like TikTok
Spark. Requires `instagram_branded_content_ads_brand` permission on the
token. Re-uploaded files become plain brand ads — use only when no
partnership code exists.

## MCP note

Optional read/analysis convenience in interactive sessions:
`uvx meta-ads-mcp` (pipeboard, 1.1k★, headless via META_ACCESS_TOKEN, but no
video upload, pinned v24). The execution path stays this CLI. Meta's official
Ads MCP (`mcp.facebook.com/ads`, ~29 tools, everything lands PAUSED per
secondary sources) — evaluate once network opens; auth model unverified.
