#!/usr/bin/env bash
# .scaffold/git/commit.sh
# Commit with structured messages following project conventions.
#
# Usage:
#   ./commit.sh "feat(core): add initialization pipeline"
#   ./commit.sh "fix(vulkan): handle device lost gracefully"
#   ./commit.sh --auto   # AI generates message from staged diff
#
# Conventional commit format: type(scope): description
# Types: feat, fix, refactor, docs, test, ci, chore, perf, build, style

set -euo pipefail

MAX_SUBJECT=72

if [ "${1:-}" = "--auto" ]; then
    # Show staged changes for AI to craft a message
    echo "=== Staged changes ==="
    git diff --cached --stat
    echo ""
    echo "=== Recent commits (for style matching) ==="
    git log --oneline -5
    echo ""
    echo "AI: Craft a commit message based on the above."
    exit 0
fi

MSG="${1:?Usage: commit.sh <message> or commit.sh --auto}"

# Validate conventional commit format (if configured)
if [[ -n "${COMMIT_STYLE:-}" && "$COMMIT_STYLE" == "conventional" ]]; then
    if ! echo "$MSG" | grep -qE '^(feat|fix|refactor|docs|test|ci|chore|perf|build|style)(\(.+\))?: .+'; then
        echo "Warning: Message doesn't match conventional commit format" >&2
        echo "Expected: type(scope): description" >&2
    fi
fi

# Check subject length
SUBJECT=$(echo "$MSG" | head -1)
if [ ${#SUBJECT} -gt $MAX_SUBJECT ]; then
    echo "Warning: Subject is ${#SUBJECT} chars (max $MAX_SUBJECT)" >&2
fi

git commit -m "$MSG"
echo "Committed: $SUBJECT"
