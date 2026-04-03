#!/usr/bin/env bash
# .scaffold/git/branch.sh
# Create and switch branches following project conventions.
# Reads branch_prefix and strategy from MANIFEST.toml.
#
# Usage:
#   ./branch.sh feature my-feature-name
#   ./branch.sh fix crash-on-startup
#   ./branch.sh refactor extract-module
#
# Types: feature, fix, refactor, docs, ci, test, chore

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCAFFOLD_DIR="$(dirname "$SCRIPT_DIR")"

# Defaults (override via MANIFEST.toml parsing or env vars)
DEFAULT_BRANCH="${GIT_DEFAULT_BRANCH:-main}"
BRANCH_PREFIX="${GIT_BRANCH_PREFIX:-}"

TYPE="${1:?Usage: branch.sh <type> <name>}"
NAME="${2:?Usage: branch.sh <type> <name>}"

# Validate type
case "$TYPE" in
    feature|fix|refactor|docs|ci|test|chore) ;;
    *) echo "Error: Unknown type '$TYPE'. Use: feature, fix, refactor, docs, ci, test, chore" >&2; exit 1 ;;
esac

# Build branch name
BRANCH="${BRANCH_PREFIX}${TYPE}/${NAME}"

# Ensure we're up to date with default branch
echo "Fetching latest ${DEFAULT_BRANCH}..."
git fetch origin "$DEFAULT_BRANCH" 2>/dev/null || true

# Create and switch
echo "Creating branch: ${BRANCH}"
git checkout -b "$BRANCH" "origin/${DEFAULT_BRANCH}" 2>/dev/null || git checkout "$BRANCH"

echo "On branch: $(git branch --show-current)"
