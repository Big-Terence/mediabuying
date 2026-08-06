#!/usr/bin/env bash
# SessionStart hook: sync state and orient every cloud session/Routine run.
[ "$CLAUDE_CODE_REMOTE" != "true" ] && exit 0
cd "$CLAUDE_PROJECT_DIR" || exit 0
git pull --ff-only --quiet 2>/dev/null || true
python3 - <<'PY' 2>/dev/null || true
import json
ctx = []
try:
    b = json.load(open('state/batches.json')).get('batches', [])
    c = json.load(open('state/campaigns.json'))
    w = json.load(open('state/watcher.json'))
    ctx.append(f"Media-buying state: {len(b)} batches ingested; "
               f"{len(c.get('tiktok', []))} TikTok + {len(c.get('meta', []))} Meta campaigns tracked; "
               f"Slack watermark {w.get('slack', {}).get('last_ts')}.")
    latest = b[-1] if b else None
    if latest:
        ctx.append(f"Latest batch: {latest.get('batch_id')}.")
except Exception as e:
    ctx.append(f"State files unreadable ({e}) — investigate before acting.")
ctx.append("Read CLAUDE.md rules and the docs/SETUP.md access checklist before assuming any integration works.")
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": " ".join(ctx)}}))
PY
exit 0
