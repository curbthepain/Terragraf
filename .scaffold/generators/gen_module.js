#!/usr/bin/env node
/**
 * .scaffold/generators/gen_module.js
 * Generates a new module directory with standard files.
 *
 * Reads project.h to understand existing modules, then creates a new one
 * following the same conventions.
 *
 * Usage:
 *   node gen_module.js <module_name> [--path src/modules] [--lang python]
 *
 * Generates:
 *   <path>/<module_name>/
 *   ├── __init__.py (or index.js, mod.rs, etc.)
 *   ├── <module_name>.py (or .js, .rs, etc.)
 *   └── test_<module_name>.py (or .test.js, etc.)
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const SCAFFOLD_DIR = path.resolve(__dirname, "..");

function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error("Usage: node gen_module.js <name> [--path dir] [--lang lang]");
    process.exit(1);
  }

  const name = args[0];
  let targetPath = "src";
  let lang = "python";

  for (let i = 1; i < args.length; i++) {
    if (args[i] === "--path" && args[i + 1]) targetPath = args[++i];
    if (args[i] === "--lang" && args[i + 1]) lang = args[++i];
  }

  const moduleDir = path.join(process.cwd(), targetPath, name);
  fs.mkdirSync(moduleDir, { recursive: true });

  // Resolve file header include
  let header = "";
  try {
    header = execSync(
      `node ${path.join(__dirname, "resolve.js")} ${path.join(SCAFFOLD_DIR, "includes/file_header.inc")} --vars module_name=${name}`,
      { encoding: "utf-8" }
    );
  } catch {
    header = `// Module: ${name}\n`;
  }

  const generators = {
    python: () => {
      fs.writeFileSync(path.join(moduleDir, "__init__.py"), `# ${name}\n`);
      fs.writeFileSync(path.join(moduleDir, `${name}.py`), `${commentify(header, "#")}\n\n`);
      fs.writeFileSync(path.join(moduleDir, `test_${name}.py`),
        `${commentify(header, "#")}\n\nimport pytest\nfrom .${name} import *\n\n\nclass Test${capitalize(name)}:\n    pass\n`);
    },
    javascript: () => {
      fs.writeFileSync(path.join(moduleDir, "index.js"), `${header}\n\nmodule.exports = {};\n`);
      fs.writeFileSync(path.join(moduleDir, `${name}.js`), `${header}\n\n`);
      fs.writeFileSync(path.join(moduleDir, `${name}.test.js`),
        `${header}\n\nconst ${name} = require('./${name}');\n\ndescribe('${name}', () => {\n});\n`);
    },
    cpp: () => {
      fs.writeFileSync(path.join(moduleDir, `${name}.h`),
        `#pragma once\n${header}\n\nnamespace ${name} {\n\n} // namespace ${name}\n`);
      fs.writeFileSync(path.join(moduleDir, `${name}.cpp`),
        `${header}\n\n#include "${name}.h"\n\nnamespace ${name} {\n\n} // namespace ${name}\n`);
    },
    rust: () => {
      fs.writeFileSync(path.join(moduleDir, "mod.rs"), `${commentify(header, "//")}\n\n`);
    },
  };

  const gen = generators[lang];
  if (!gen) {
    console.error(`Unknown language: ${lang}. Supported: python, javascript, cpp, rust`);
    process.exit(1);
  }

  gen();
  console.log(`Module '${name}' created at ${moduleDir} (${lang})`);
}

function commentify(text, prefix) {
  return text.split("\n").map(line => line.startsWith("//") ? line.replace("//", prefix) : `${prefix} ${line}`).join("\n");
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

main();
