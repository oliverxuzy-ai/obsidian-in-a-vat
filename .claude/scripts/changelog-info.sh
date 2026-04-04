#!/usr/bin/env bash
# Collect info about the commits just pushed and output a structured message
# for Claude to append to design_doc/CHANGELOG.md

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
CHANGELOG="$REPO_ROOT/design_doc/CHANGELOG.md"

# Get the remote tracking branch to find what was just pushed
REMOTE_BRANCH=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "origin/main")

# Find commits that are ahead of the previous remote HEAD
# After push, local and remote should match, so use reflog to find pre-push state
PREV_REMOTE=$(git reflog show "$REMOTE_BRANCH" --format="%H" -n 2 | tail -1 2>/dev/null || echo "")

if [ -z "$PREV_REMOTE" ]; then
  # Fallback: show last 5 commits
  COMMITS=$(git log --oneline -5)
  DIFFSTAT=$(git diff --stat HEAD~5..HEAD 2>/dev/null || echo "unable to compute")
else
  COMMITS=$(git log --oneline "$PREV_REMOTE"..HEAD)
  DIFFSTAT=$(git diff --stat "$PREV_REMOTE"..HEAD)
fi

DATETIME=$(date "+%Y-%m-%d %H:%M")
LATEST_MSG=$(git log --oneline -1 | cut -d' ' -f2-)

echo "CHANGELOG_UPDATE_NEEDED"
echo "datetime: $DATETIME"
echo "latest_commit_msg: $LATEST_MSG"
echo "---commits---"
echo "$COMMITS"
echo "---diffstat---"
echo "$DIFFSTAT"
echo "---end---"
echo ""
echo "Please append a new entry to design_doc/CHANGELOG.md using this exact format:"
echo ""
echo "## {datetime} — {latest_commit_msg}"
echo ""
echo "**Commits:**"
echo "- \`{hash}\` {message}  (one line per commit above)"
echo ""
echo "**Summary:**"
echo "{2-3 sentence Chinese summary of what these changes accomplish}"
echo ""
echo "**Files changed:** {from diffstat summary line}"
echo ""
echo "---"
