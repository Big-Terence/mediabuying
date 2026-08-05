# Media Buying Automation

Agent-operated media buying for NewQuest AI. The agency ships creative batches
(TikTok posts + Spark Ads codes); Claude agents download and archive the
videos, propose campaign setups, and — on approval — run the campaigns on
TikTok and Meta so nobody has to open an Ads Manager by hand.

**Agents:** start with [CLAUDE.md](CLAUDE.md) (operating manual).
**Humans:** [docs/SETUP.md](docs/SETUP.md) tracks access/credentials status,
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) explains the design.

## Quick map

- `batches/` — creative batch files (inbox → processed)
- `tools/` — downloader, Drive uploader, Meta & TikTok CLIs
- `state/` — shared memory between sessions (batches, campaigns, watcher cursors)
- `.claude/skills/` — workflows: `/ingest-batch`, `/execute-setup`, `/check-inbox`, `/report`
