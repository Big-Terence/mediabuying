# Architecture

How "agency ships creatives → ads run themselves" works, and why each piece
is built the way it is. Decisions are research-backed (Aug 2026); dated facts
carry their dates.

## The three layers

**Layer 1 — the repo is the brain.** CLAUDE.md, `.claude/skills/`,
`.claude/settings.json` (hooks, permissions), `tools/`, `state/` — all load
automatically in every cloud session, Routine run, and Slack-started session.
Nothing to install, nothing to remember. `state/*.json` is cross-session
memory: pull before acting, commit+push after mutating.

**Layer 2 — the environment carries secrets + network.** Env vars (tokens)
and the domain allowlist live in the Claude Code environment config, never in
git. Deliberate consequence: any session on this repo in this environment has
full access with zero setup — exactly the "every agent I launch can do
everything" requirement.

**Layer 3 — Routines make it always-on.** Account-level scheduled triggers
firing fresh cloud sessions (hourly watcher; later a daily reporter). They
survive container death, carry connector grants (Slack/Gmail/Drive), and can
push to Terence's phone. The in-session cron (`CronCreate`) dies with the
session and was rejected for this.

## Execution paths (and non-paths)

- **TikTok + Meta = thin CLIs over raw HTTP** (`tools/tiktok/cli.py` v1.3,
  `tools/meta/cli.py` v26.0), tokens from env. NOT MCP servers: repo
  `.mcp.json` doesn't auto-load in cloud sessions (untrusted-folder rule,
  verified), community MCPs are read-only (TikTok) or missing video upload
  (Meta/pipeboard), and both platforms' official MCPs (mcp.facebook.com/ads;
  TikTok Agentic Hub, both 2026) have unverified headless-auth stories.
  Re-evaluate the official MCPs once the network opens — as an interactive
  convenience, not the execution path.
- **Slack/Gmail/Drive-metadata = claude.ai connectors**, which run
  server-side and bypass the egress allowlist entirely.
- **Drive video upload = OAuth refresh token + resumable API**
  (`tools/drive/upload.py`). Service accounts can't own My-Drive files
  (0 quota since 2023); the Drive connector can't carry video bytes
  (base64-through-context).

## Creative flow

```
Scroll agency
  │  announcement + TikTok links (+ Spark codes) in #ext-quest-scroll
  ▼
hourly Routine → /check-inbox (watermark poll, idempotent by announcement ts)
  │  new batch detected
  ▼
/ingest-batch
  ├─ TikTok API path (once token exists): /tt_video/info per code
  │    → full-quality MP4 (day-one MD5 test decides if this replaces yt-dlp)
  │    → /tt_video/authorize (automated redemption, no human step)
  ├─ fallback: yt-dlp (curl-cffi impersonation, watermark-free, no bytevc2)
  ├─ Drive: 01_Inbox_Raw/<year>/<batch>/ + manifest, md5-deduped
  └─ state/batches.json updated, committed
  ▼
draft proposal → DM Terence (never the agency channel)          [HUMAN GATE]
  ▼
/execute-setup on approval
  ├─ TikTok: campaign → adgroup → Spark ad (identity_type AUTH_CODE +
  │    tiktok_item_id; dark_post_status explicit; created PAUSED)
  ├─ Meta: advideos upload → creative (object_story_spec) → campaign/adset/ad
  │    (all PAUSED; partnership-ad code path when creator is on IG)
  └─ state/campaigns.json updated (incl. auth_end_time per Spark creative)
  ▼
watcher monitors: performance (/report), Spark-code expiry (<7 days → warn —
an expired code silently kills a live ad), connector/token health (loud
degradation, never silent)
```

## Platform constraints that shaped the design

- **TikTok**: Spark Ads are the ONLY in-feed path since 2026-01-15 (Custom
  Identity ads blocked for TikTok placements, existing accounts included).
  Spark code = per-post, one ad account, time-boxed (7-365d), creator-minted
  (in-app only; `biz.spark.auth`/TCM can automate minting given agency
  cooperation). Sandbox has no `tt_video/*` — Spark leg develops against
  production on a throwaway code, PAUSED ad. Access-Token header; tokens
  never expire; ≤10 QPS.
- **Meta**: system-user token (never expires); own-account management needs
  no App Review. v26 breaking changes propagate to ALL versions 2026-10-27
  (no `explore` placement). Creatives need a thumbnail; videos are never
  auto-cropped — bad ratio fails at creation.
- **Slack**: agency channel is Slack Connect → bots can't post there; author
  fields resolve inconsistently (detect by channel+pattern+links, two-pass
  read+search). Marketplace Claude app is exempt from the 1 rpm
  non-Marketplace history throttle — don't build a custom bot.
- **Portal (portal.scroll.fr)**: bespoke, no API/webhooks. Not on the
  critical path — links arrive in Slack. Playwright + stored session is the
  someday-path for pulling master files.
- **Webhooks generally**: sessions have no inbound HTTP. If sub-hour latency
  ever matters: webhook → GitHub `repository_dispatch` →
  anthropics/claude-code-action (also the only path with encrypted secrets),
  or webhook → Zapier → Slack message → existing watcher.
- **WhatsApp**: rejected — can't read Terence's existing thread, needs
  Business Verification + dedicated number + hosted webhook. The fix is
  social: Scroll mirrors briefs into Slack.

## Failure-mode rules

1. Watcher advances its watermark even on empty runs (a parse bug must not
   re-trigger the same batch forever).
2. Pings are idempotent — keyed on announcement `ts` against
   `state/batches.json`.
3. Degradation is loud: missing connector/revoked token goes in the ping;
   a silently broken watcher is worse than none.
4. Everything is created PAUSED; activation is explicit and post-approval.
5. State commits are part of the mutation, not an afterthought.
