// .scaffold/headers/git.h
// Git and GitHub workflow contract.
// Declares how this project uses version control — branching strategy,
// commit conventions, PR flow, CI expectations.

#ifndef GIT_H
#define GIT_H

#include "project.h"

// ─── Branching Strategy ──────────────────────────────────────────────

#branching {
    strategy: "{{git.commit_style}}",
    // "gitflow"       — main, develop, feature/*, release/*, hotfix/*
    // "trunk"         — main + short-lived feature branches
    // "github-flow"   — main + feature branches, PR to merge

    default_branch: "{{git.default_branch}}",
    branch_prefix:  "{{git.branch_prefix}}",

    // Branch naming convention:
    // {{branch_prefix}}/<type>/<short-description>
    // Types: feature, fix, refactor, docs, ci, test, chore
}

// ─── Commit Convention ───────────────────────────────────────────────

#commits {
    style: "{{git.commit_style}}",
    // "conventional"  — type(scope): description
    // "gitmoji"       — :emoji: description
    // "freeform"      — just be clear

    // Conventional commit types:
    // feat, fix, refactor, docs, test, ci, chore, perf, build, style

    sign: false,        // GPG signing required?
    max_subject: 72,    // Subject line character limit
}

// ─── Pull Request Flow ───────────────────────────────────────────────

#pull_requests {
    template: "{{git.pr_template}}",
    require_review: true,
    require_ci: true,
    auto_merge: false,
    squash: true,       // Squash merge by default?

    // PR title should match commit convention
    // PR body uses template from git/templates/pull_request.md
}

// ─── CI Expectations ─────────────────────────────────────────────────

#ci {
    platform: "github-actions",   // "github-actions", "gitlab-ci", "jenkins"
    required_checks: [
        // "build",
        // "test",
        // "lint"
    ],
    workflows_dir: "git/workflows/"
}

// ─── Release Strategy ────────────────────────────────────────────────

#releases {
    strategy: "",       // "semver", "calver", "git-tags"
    changelog: true,
    auto_release: false
}

#endif // GIT_H
