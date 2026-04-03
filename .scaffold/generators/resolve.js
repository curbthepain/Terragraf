#!/usr/bin/env node
/**
 * .scaffold/generators/resolve.js
 * Resolves #include directives in .inc and .scaffold files.
 *
 * Like a C preprocessor: reads a file, finds #include "file.inc",
 * inlines the content, and substitutes {{variables}} from MANIFEST.toml.
 *
 * Usage:
 *   node resolve.js <input_file> [--vars key=value ...]
 *   node resolve.js includes/file_header.inc --vars module_name=core file_path=src/main.py
 *
 * Reads MANIFEST.toml [vars] section for default variable values.
 * CLI --vars override MANIFEST defaults.
 */

const fs = require("fs");
const path = require("path");

const SCAFFOLD_DIR = path.resolve(__dirname, "..");
const INCLUDES_DIR = path.join(SCAFFOLD_DIR, "includes");

// ─── TOML parser (minimal, for [vars] section) ──────────────────────

function parseManifestVars(manifestPath) {
  const vars = {};
  if (!fs.existsSync(manifestPath)) return vars;

  const content = fs.readFileSync(manifestPath, "utf-8");
  let inVars = false;

  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (trimmed === "[vars]") {
      inVars = true;
      continue;
    }
    if (trimmed.startsWith("[") && trimmed !== "[vars]") {
      inVars = false;
      continue;
    }
    if (inVars && trimmed && !trimmed.startsWith("#")) {
      const match = trimmed.match(/^(\w+)\s*=\s*"(.*)"/);
      if (match) vars[match[1]] = match[2];
    }
  }
  return vars;
}

// ─── Include resolver ────────────────────────────────────────────────

function resolveIncludes(content, resolved = new Set()) {
  return content.replace(/#include\s+"([^"]+)"/g, (match, includePath) => {
    // Guard against circular includes
    if (resolved.has(includePath)) {
      return `// [already included: ${includePath}]`;
    }
    resolved.add(includePath);

    // Look in includes/ directory
    const fullPath = path.join(INCLUDES_DIR, includePath);
    if (!fs.existsSync(fullPath)) {
      return `// [include not found: ${includePath}]`;
    }

    const includeContent = fs.readFileSync(fullPath, "utf-8");
    // Recursively resolve nested includes
    return resolveIncludes(includeContent, resolved);
  });
}

// ─── Variable substitution ──────────────────────────────────────────

function substituteVars(content, vars) {
  return content.replace(/\{\{(\w[\w.]*)\}\}/g, (match, varName) => {
    // Support dotted paths: {{project.name}} → vars["project.name"] or vars["project_name"]
    return vars[varName] || vars[varName.replace(/\./g, "_")] || match;
  });
}

// ─── Include guard processing ────────────────────────────────────────

function processGuards(content) {
  const defined = new Set();
  const lines = content.split("\n");
  const output = [];
  let skipping = false;
  let skipGuard = "";

  for (const line of lines) {
    const trimmed = line.trim();

    if (trimmed.startsWith("#ifndef ")) {
      const guard = trimmed.slice(8).trim();
      if (defined.has(guard)) {
        skipping = true;
        skipGuard = guard;
        continue;
      }
    }
    if (trimmed.startsWith("#define ") && !skipping) {
      const guard = trimmed.slice(8).trim();
      defined.add(guard);
      continue; // Don't emit #define lines
    }
    if (trimmed.startsWith("#endif") && skipping) {
      if (trimmed.includes(skipGuard)) {
        skipping = false;
        skipGuard = "";
        continue;
      }
    }
    if (!skipping && !trimmed.startsWith("#ifndef ") && !trimmed.startsWith("#endif")) {
      output.push(line);
    }
  }

  return output.join("\n");
}

// ─── Main ────────────────────────────────────────────────────────────

function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error("Usage: node resolve.js <file> [--vars key=value ...]");
    process.exit(1);
  }

  const inputFile = args[0];
  const inputPath = path.isAbsolute(inputFile)
    ? inputFile
    : path.join(process.cwd(), inputFile);

  if (!fs.existsSync(inputPath)) {
    console.error(`File not found: ${inputPath}`);
    process.exit(1);
  }

  // Parse variables
  const vars = parseManifestVars(path.join(SCAFFOLD_DIR, "MANIFEST.toml"));

  // Override with CLI vars
  const varsIdx = args.indexOf("--vars");
  if (varsIdx !== -1) {
    for (let i = varsIdx + 1; i < args.length; i++) {
      const [key, ...rest] = args[i].split("=");
      if (rest.length > 0) vars[key] = rest.join("=");
    }
  }

  // Add built-in vars
  vars.year = vars.year || new Date().getFullYear().toString();

  // Process
  let content = fs.readFileSync(inputPath, "utf-8");
  content = resolveIncludes(content);
  content = processGuards(content);
  content = substituteVars(content, vars);

  // Output
  process.stdout.write(content);
}

main();
