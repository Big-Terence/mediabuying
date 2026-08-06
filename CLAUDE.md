# Media Buying Automation — Operating Manual

You are an agent working on NewQuest AI's automated media buying system. The
human is Terence (terence@newquest.ai). The mission: **Terence never opens
Meta Ads Manager or TikTok Ads Manager again.** Agents handle creative intake,
archiving, campaign setup, and budget management; Terence only approves.

## Key facts

- **Product**: Quest, NewQuest AI's personal-life agent app. Creatives are
  tested per use case (e.g. diabetes, ADHD, debt payoff, sleep, quarter-life
  crisis) to find the CAC per use case — typically ~10 creatives per use case.
  Read `#ext-quest-scroll` history to absorb the current briefs.
- **Agency**: Scroll (scroll.fr). Slack channel `#ext-quest-scroll`
  (`C0BH13QSRDM`), contacts Leo and Benjamin. They announce "the new batch is
  live", deliver via their portal `portal.scroll.fr` + TikTok creator post
  links in Slack.
- **Terence's Slack user ID**: `U0BA6LKTVQV`. Ping him there for approvals —
  always by DM, never in `#ext-quest-scroll` (it's a Slack Connect channel:
  bot posts are refused there, and draft proposals must not be visible to the
  agency anyway).
- **Approval gate is at campaign launch**, not at Spark-code redemption or
  downloading — ingest/archive runs unattended.

## The workflow (end to end)

1. **Intake** — The agency delivers batches of creatives: TikTok post links +
   Spark Ads codes, sometimes raw files. They arrive via Slack, a portal, or
   Terence pasting them in chat. Every batch becomes a YAML file in
   `batches/inbox/` (format: `batches/TEMPLATE.yaml`).
2. **Ingest** — Download every video in full quality (`tools/downloader/`),
   upload to Google Drive (three-folder structure, see below), record the
   batch in `state/batches.json`, move the YAML to `batches/processed/`.
3. **Propose** — Prepare a DRAFT campaign setup (targeting, budget, structure)
   as a short plan. Ping Terence (Slack preferred) with "new batch ready —
   here's the proposed setup, go?". **Never launch anything without an
   explicit yes.**
4. **Execute** — On approval, create/update campaigns via the CLIs
   (`tools/tiktok/cli.py`, `tools/meta/cli.py`). Plain scripts + env vars are
   the execution path by design: repo `.mcp.json` servers do NOT auto-load in
   cloud sessions (untrusted-folder rule), CLIs work identically in
   interactive sessions, Routines, and Actions. Spark Ads posts run natively
   on TikTok via their Spark code (redemption is automated via API);
   downloaded files are used as creatives on Meta.
5. **Record** — Update `state/campaigns.json` after every mutation. This file
   is the shared memory between sessions — read it before proposing anything,
   write it after changing anything, commit and push both state files.

## Hard rules

- **Draft first, launch on approval only.** New campaigns and budget increases
  always require Terence's explicit OK. Pausing something that's clearly
  burning money with zero results is allowed, but report it immediately.
- **State lives in git.** `state/*.json` must be committed and pushed after
  every change so parallel/future sessions don't collide. Pull before you act.
- **Secrets live in environment variables, never in git.** See
  `docs/SETUP.md` for the variable names.
- **Videos never go in git.** They go to Google Drive; `downloads/` is
  gitignored scratch space.
- Report spend/results numbers exactly as the APIs return them — no rounding
  optimism.

## Where things live

| Path | What |
|---|---|
| `docs/SETUP.md` | Every credential/access step, status of each |
| `docs/ARCHITECTURE.md` | How the pieces fit, diagrams |
| `batches/` | Batch YAMLs: `inbox/` = to process, `processed/` = done |
| `state/` | Shared memory: batches + campaigns registries |
| `tools/downloader/` | yt-dlp batch downloader (`uv run tools/downloader/download.py`) |
| `tools/drive/` | Google Drive uploader |
| `tools/meta/`, `tools/tiktok/` | Ads API CLIs |
| `.claude/skills/` | Slash-command workflows (`/ingest-batch`, etc.) |

## Google Drive structure

Three folders under the "Media Buying" root (IDs in `docs/SETUP.md` once
created): `01_Inbox_Raw` (fresh downloads, per-batch subfolders),
`02_TikTok_SparkAds` (creatives running on TikTok + their Spark codes),
`03_Meta_Creatives` (files used for Meta ads).

## Environment notes

- Install tools on demand: `uv tool install "yt-dlp[default]"`; scripts use
  PEP 723 inline deps, run them with `uv run`.
- The container's network policy must allow the target domains (tiktok.com,
  tiktokcdn.com, business-api.tiktok.com, graph.facebook.com, …). If a
  download fails with a proxy 403 CONNECT rejection, that's the network
  policy, not the tool — tell Terence which domain to allow in the
  environment settings.
- Google Drive, Slack, and Gmail are available as claude.ai connectors in
  interactive sessions. Headless/scheduled sessions may not have them — the
  fallback for Drive is `tools/drive/` with the token from env vars.

## Current status

See `docs/SETUP.md` → "Access checklist" for what's live and what's still
waiting on Terence. Update it whenever access changes.
