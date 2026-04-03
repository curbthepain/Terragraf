// .scaffold/headers/project.h
// Declares the project's module structure and boundaries.
// AI reads this to understand WHAT exists without scanning every file.

#ifndef PROJECT_H
#define PROJECT_H

// ─── Project Declaration ─────────────────────────────────────────────

#project {
    name: "{{project.name}}",
    lang: "{{project.lang}}",
    type: "{{project.type}}"
}

// ─── Module Declarations ─────────────────────────────────────────────
// Each module: what it does, where it lives, what it exports, what it needs.
//
// #module NAME {
//     #path "relative/path"
//     #exports [PublicThing1, PublicThing2]
//     #depends [other_module]
//     #desc "One-line purpose"
// }

// Add modules below:

#endif // PROJECT_H
