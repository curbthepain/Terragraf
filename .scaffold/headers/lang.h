// .scaffold/headers/lang.h
// Language-specific contracts.
// Declares which languages are active and their idioms.
// Points to lang/ directory for language-specific scaffolding.

#ifndef LANG_H
#define LANG_H

#include "project.h"

// ─── Active Languages ────────────────────────────────────────────────
// Which languages does this project use?

#languages {
    primary:   "{{project.lang}}",
    secondary: [],      // Additional languages used

    // Available language scaffolds in lang/:
    //   lang/python/   — setup.py/pyproject.toml, venv, type hints
    //   lang/js/       — package.json, tsconfig, eslint
    //   lang/kotlin/   — gradle module, coroutines, Android
    //   lang/cpp/      — CMakeLists, headers, namespaces
    //   lang/rust/     — Cargo.toml, modules, traits
}

// ─── Language Interop ────────────────────────────────────────────────
// How languages talk to each other in this project

#interop {
    // Bridges between languages:
    //   "jni"     — Java/Kotlin ↔ C/C++ (Android NDK)
    //   "pybind"  — Python ↔ C++
    //   "napi"    — Node.js ↔ C++
    //   "ffi"     — Rust ↔ C
    //   "wasm"    — Any → WebAssembly
    //   "grpc"    — Any ↔ Any (network boundary)

    bridges: [
        // { from: "kotlin", to: "cpp", via: "jni" }
        // { from: "python", to: "cpp", via: "pybind" }
    ]
}

// ─── Per-Language Config ─────────────────────────────────────────────

#python_config {
    version: "{{ml.python_version}}",
    package_manager: "pip",     // "pip", "poetry", "conda", "uv"
    type_checking: "mypy",      // "mypy", "pyright", "none"
    formatter: "black",         // "black", "ruff", "autopep8"
    linter: "ruff",             // "ruff", "flake8", "pylint"
}

#js_config {
    runtime: "node",            // "node", "deno", "bun"
    typescript: true,
    package_manager: "npm",     // "npm", "yarn", "pnpm"
    formatter: "prettier",
    linter: "eslint",
}

#cpp_config {
    standard: "c++20",          // "c++17", "c++20", "c++23"
    build: "cmake",             // "cmake", "make", "meson", "bazel"
    compiler: "",               // "gcc", "clang", "msvc"
    formatter: "clang-format",
}

#kotlin_config {
    version: "",
    android: true,
    compose: false,
    coroutines: true,
}

#rust_config {
    edition: "2021",            // "2018", "2021", "2024"
    async_runtime: "tokio",     // "tokio", "async-std"
}

#endif // LANG_H
