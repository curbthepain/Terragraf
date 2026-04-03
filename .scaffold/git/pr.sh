#!/usr/bin/env bash
# .scaffold/git/pr.sh
# Create pull requests with template, or output the template for AI to fill.
#
# Usage:
#   ./pr.sh --template    # Print PR template for AI to fill
#   ./pr.sh --preview     # Show what the PR would contain (commits, diff stats)
#   ./pr.sh "Title" body  # Create PR (requires gh CLI)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_BRANCH="${GIT_DEFAULT_BRANCH:-main}"
CURRENT_BRANCH="$(git branch --show-current)"

case "${1:-}" in
    --template)
        cat "$SCRIPT_DIR/templates/pull_request.md"
        ;;
    --preview)
        echo "=== PR Preview ==="
        echo "Branch: $CURRENT_BRANCH -> $DEFAULT_BRANCH"
        echo ""
        echo "=== Commits ==="
        git log --oneline "$DEFAULT_BRANCH".."$CURRENT_BRANCH" 2>/dev/null || echo "(no commits yet)"
        echo ""
        echo "=== Diff Stats ==="
        git diff --stat "$DEFAULT_BRANCH".."$CURRENT_BRANCH" 2>/dev/null || echo "(no diff)"
        ;;
    *)
        echo "Usage:"
        echo "  ./pr.sh --template    # Print PR template"
        echo "  ./pr.sh --preview     # Preview PR contents"
        echo ""
        echo "For actual PR creation, use: gh pr create"
        echo "Or have the AI use the GitHub MCP tools."
        ;;
esac
