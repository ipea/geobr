#!/usr/bin/env bash
# Claude Code status line: shows permission mode, model, and git branch.
#
# Claude Code pipes a JSON session snapshot to stdin. Relevant keys:
#   .model.display_name      e.g. "Opus <version>"
#   .permission_mode         e.g. "bypassPermissions" | "plan" | "acceptEdits" | "default"
#   .workspace.current_dir   absolute path of the cwd
#
# Design goal: always show permission mode so prompt-fatigue is diagnosable at a glance.

set -euo pipefail

INPUT="$(cat)"

# Parse all three fields in a single python3 invocation. Status line renders
# on every turn; avoid three forks when one suffices.
parsed="$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
print(d.get('permission_mode', '?'))
print((d.get('model') or {}).get('display_name', '?'))
print((d.get('workspace') or {}).get('current_dir', '.'))
" 2>/dev/null || printf '?\n?\n\n')"

mode="$(printf '%s' "$parsed" | sed -n '1p')"
model="$(printf '%s' "$parsed" | sed -n '2p')"
cwd="$(printf '%s' "$parsed" | sed -n '3p')"
[ -n "$mode" ] || mode="?"
[ -n "$model" ] || model="?"
[ -n "$cwd" ] && [ "$cwd" != "." ] || cwd="$(pwd)"

case "$mode" in
    bypassPermissions) mode_badge="[BYPASS]" ;;
    acceptEdits)       mode_badge="[AUTO-EDIT]" ;;
    plan)              mode_badge="[PLAN]" ;;
    default)           mode_badge="[PROMPT]" ;;
    *)                 mode_badge="[$mode]" ;;
esac

# Optional enrichment (branch, dirty count, plan status, context %).
# Wrapped in `set +e` so a probe failure can never blank the status line.
set +e
branch=""
dirty=""
if [ -d "$cwd/.git" ] || git -C "$cwd" rev-parse --git-dir >/dev/null 2>&1; then
    branch="$(git -C "$cwd" branch --show-current 2>/dev/null)"
    n="$(git -C "$cwd" status --porcelain 2>/dev/null | grep -c '.')"
    [ "${n:-0}" -gt 0 ] 2>/dev/null && dirty="±${n}"
fi

# Most-recent plan's status (DRAFT / APPROVED / COMPLETED).
plan_badge=""
latest_plan="$(ls -t "$cwd"/quality_reports/plans/*.md 2>/dev/null | head -1)"
if [ -n "$latest_plan" ]; then
    if   grep -qi 'COMPLETED' "$latest_plan" 2>/dev/null; then plan_badge="plan:done"
    elif grep -qi 'APPROVED'  "$latest_plan" 2>/dev/null; then plan_badge="plan:approved"
    elif grep -qi 'DRAFT'     "$latest_plan" 2>/dev/null; then plan_badge="plan:DRAFT"
    fi
fi

# Context % — best-effort, persisted by context-monitor.py under the
# session dir keyed by md5(project_dir)[:8].
ctx=""
# Mirror context-monitor.py's get_session_dir() EXACTLY: CLAUDE_PROJECT_DIR set →
# hash it; unset/empty → the writer falls back to sessions/default/, so do the same
# (hashing the git toplevel here would point at the wrong folder on that path).
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    hash="$(printf '%s' "$CLAUDE_PROJECT_DIR" | python3 -c 'import sys,hashlib; print(hashlib.md5(sys.stdin.read().encode()).hexdigest()[:8])' 2>/dev/null)"
else
    hash="default"
fi
pct_file="$HOME/.claude/sessions/${hash}/context-pct.txt"
[ -f "$pct_file" ] && ctx="ctx $(cat "$pct_file" 2>/dev/null)%"
set -e

line="$mode_badge  $model"
[ -n "$branch" ] && line="$line  @ $branch"
[ -n "$dirty" ] && line="$line $dirty"
[ -n "$plan_badge" ] && line="$line  $plan_badge"
[ -n "$ctx" ] && line="$line  $ctx"

printf '%s' "$line"
