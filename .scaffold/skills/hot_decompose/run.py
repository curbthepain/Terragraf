"""
hot_decompose — Triage HOT_CONTEXT into scaffold files.

Parses HOT_CONTEXT.md, classifies each block by type, and routes non-session
content to its permanent home (KNOWLEDGE.toml, project.h, structure.route,
deps.table). HOT_CONTEXT is rewritten to contain only session-scoped blocks.

Usage:
    python run.py [decompose] [--dry-run] [--threshold N]

    decompose  (default) Parse, classify, route, rewrite
    --dry-run  Show what would move where without writing
    --threshold N  Override max line count (default from MANIFEST.toml or 80)
"""

import argparse
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TERRA_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCAFFOLD = TERRA_ROOT / ".scaffold"
HOT_CONTEXT = SCAFFOLD / "HOT_CONTEXT.md"
MANIFEST = SCAFFOLD / "MANIFEST.toml"
LOCKFILE = SCAFFOLD / ".hot_decompose.lock"
LOCK_STALE_SECONDS = 60
KNOWLEDGE_WRITER = TERRA_ROOT / "projects" / "knowledge_writer.py"
PROJECT_H = SCAFFOLD / "headers" / "project.h"
STRUCTURE_ROUTE = SCAFFOLD / "routes" / "structure.route"
DEPS_TABLE = SCAFFOLD / "tables" / "deps.table"

# ANSI
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"

DEFAULT_MAX_LINES = 80
DEFAULT_RETAIN_SESSIONS = 3
DEFAULT_HARD_MAX_LINES = 1000

# H3 sub-section headings that the forcer is allowed to extract from a
# retained session block when the hard cap is exceeded. Listed in priority
# order — heaviest / least-conversational sections first.
EXTRACTABLE_H3_KEYWORDS = (
    "key files",
    "verification",
    "tests",
    "decisions made",
    "decisions",
)

# Matches "(Session 12)", "(Session 19b)", "(Session 21 — in progress)",
# "(Sessions 1-8)", etc. Captures digits; uses upper bound when a range.
_SESSION_RE = re.compile(r"\(Sessions?\s+(\d+)(?:\s*[-–]\s*(\d+))?[^)]*\)", re.IGNORECASE)
# Matches "Everything above is Session 12" / "Sessions 1-8" separator lines
_SEPARATOR_RE = re.compile(r"Everything above is Sessions?\s+(\d+)", re.IGNORECASE)
# Matches headings that are pure visual dividers (dashes, em-dashes, no words)
_DECORATIVE_RE = re.compile(r"^##\s*[\W_]+$")

# ── Block types ─────────────────────────────────────────────────────

SESSION_KEYWORDS = [
    "status:", "what's done", "what was done", "this session",
    "debug notes", "plan:", "next session", "backlog",
    "key files", "verification", "session roadmap",
]

DECISION_KEYWORDS = ["decisions made", "decided", "chose", "decision:"]

PATTERN_KEYWORDS = ["pattern", "caveat", "gotcha", "always do", "never do", "workaround"]

PLATFORM_KEYWORDS = ["win32", "wayland", "x11", "platform-specific", "linux-specific", "windows-specific"]


@dataclass
class Block:
    heading: str
    body: list[str] = field(default_factory=list)
    block_type: str = "session"  # session, decision, pattern, module_decl, route_map, dependency, platform, discard
    session_number: int | None = None  # Populated from heading via extract_session_number()


def extract_session_number(heading: str) -> int | None:
    """Return the session number referenced in a heading, or None.

    Handles "(Session N)", "(Sessions M-N)" (uses upper bound), and the
    "Everything above is Session N" separator lines.
    """
    m = _SESSION_RE.search(heading)
    if m:
        hi = m.group(2) or m.group(1)
        try:
            return int(hi)
        except ValueError:
            return None
    m = _SEPARATOR_RE.search(heading)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _archive_category(heading: str) -> str:
    """Map an aged-out block heading to a KNOWLEDGE.toml category."""
    h = heading.lower()
    if "decision" in h:
        return "decision"
    if any(k in h for k in ("pattern", "caveat", "gotcha", "workaround")):
        return "pattern"
    if any(k in h for k in ("incident", "issue", "bug", "fix")):
        return "caveat"
    return "domain"


def apply_age_out(blocks: list[Block], retain_count: int) -> tuple[list[Block], list[Block], set[int]]:
    """Partition blocks by session age.

    Returns (keep_blocks, archive_blocks, retained_session_set).
    Blocks with no session_number are always kept (architectural notes,
    backlog, status, etc). Blocks whose session_number is in the retained
    set are kept verbatim and forced to block_type="session" so the
    existing classifier doesn't extract their sub-sections. Older session
    blocks are returned as archive_blocks. Separator lines are dropped
    (not returned in either list).
    """
    numbers = sorted({b.session_number for b in blocks if b.session_number is not None})
    retained: set[int] = set(numbers[-retain_count:]) if retain_count > 0 else set()

    keep: list[Block] = []
    archive: list[Block] = []
    for b in blocks:
        # Drop separator and pure-decorative blocks unconditionally
        if _SEPARATOR_RE.search(b.heading) or _DECORATIVE_RE.match(b.heading):
            continue
        if b.session_number is None:
            keep.append(b)
        elif b.session_number in retained:
            b.block_type = "session"
            keep.append(b)
        else:
            archive.append(b)
    return keep, archive, retained


def _find_extractable_h3(block: Block) -> tuple[int, int, str, list[str]] | None:
    """Find the first extractable h3 sub-section in a block's body.

    Returns (start_idx, end_idx, heading, section_lines) where:
      - start_idx is the index of the "### " line in block.body
      - end_idx is exclusive (next h3 or len(body))
      - section_lines is body[start+1:end] (excludes the heading itself)

    Returns None if no extractable section is present.
    """
    h3_indices = [i for i, line in enumerate(block.body) if line.startswith("### ")]
    for i, start in enumerate(h3_indices):
        heading = block.body[start]
        heading_lower = heading.lower()
        if not any(kw in heading_lower for kw in EXTRACTABLE_H3_KEYWORDS):
            continue
        end = h3_indices[i + 1] if i + 1 < len(h3_indices) else len(block.body)
        section_lines = block.body[start + 1 : end]
        return (start, end, heading, section_lines)
    return None


def _count_total_lines(blocks: list[Block]) -> int:
    """Compute the line count of the rewritten HOT_CONTEXT for these blocks."""
    return len(rewrite_hot_context(blocks, dry_run=True).splitlines())


def apply_hard_cap(
    keep_blocks: list[Block],
    hard_max: int,
    dry_run: bool,
) -> tuple[int, int]:
    """Forcer pass: iteratively extract h3 sub-sections from retained
    session blocks (oldest first) into KNOWLEDGE.toml until the rewritten
    HOT_CONTEXT is at or below ``hard_max`` lines.

    Mutates ``keep_blocks`` in place by removing extracted sections from
    each block's body. Returns (extracted_count, final_line_count).

    The loop terminates when:
      - line count <= hard_max, OR
      - no retained session block has any extractable h3 left.
    """
    extracted = 0
    line_count = _count_total_lines(keep_blocks)
    if line_count <= hard_max:
        return (0, line_count)

    print(f"  {YELLOW}hard cap {hard_max} exceeded ({line_count} lines) — forcing extraction{RESET}")

    while line_count > hard_max:
        # Walk retained-session blocks oldest-first
        session_candidates = sorted(
            (b for b in keep_blocks if b.session_number is not None),
            key=lambda b: b.session_number,
        )

        target_block = None
        target_section = None
        for block in session_candidates:
            section = _find_extractable_h3(block)
            if section is not None:
                target_block = block
                target_section = section
                break

        if target_block is None:
            print(f"  {DIM}forcer: no more extractable h3 sections — stopping at {line_count} lines{RESET}")
            break

        start, end, heading, section_lines = target_section
        # Build a synthetic block to feed route_to_knowledge. The slug must
        # be unique per (session, h3) pair, so we append the session number
        # to the heading text before slugify runs.
        heading_clean = re.sub(r"^#+\s*", "", heading).strip()
        synthetic_heading = f"## {heading_clean} (Session {target_block.session_number})"
        synthetic = Block(
            heading=synthetic_heading,
            body=section_lines,
            session_number=target_block.session_number,
        )

        category = _archive_category(heading)
        tags = [
            "hot-context",
            f"session-{target_block.session_number}",
            "archived",
            "hard-cap",
        ]
        print(f"  {CYAN}force-extract{RESET} session {target_block.session_number}: {heading_clean[:60]} [{category}]")
        route_to_knowledge(synthetic, category, tags, dry_run)

        # Remove the section from the parent block's body
        target_block.body = target_block.body[:start] + target_block.body[end:]
        extracted += 1

        new_line_count = _count_total_lines(keep_blocks)
        if new_line_count >= line_count:
            # Defensive: if removal didn't shrink the count (shouldn't happen),
            # bail out to avoid an infinite loop.
            print(f"  {RED}forcer: line count did not decrease — stopping{RESET}")
            break
        line_count = new_line_count

    return (extracted, line_count)


# ── Parser ──────────────────────────────────────────────────────────

def parse_blocks(content: str) -> list[Block]:
    """Split HOT_CONTEXT content into blocks by ## headings."""
    lines = content.splitlines()
    blocks: list[Block] = []
    current: Block | None = None

    for line in lines:
        if line.startswith("## "):
            if current is not None:
                blocks.append(current)
            current = Block(heading=line)
        elif current is not None:
            current.body.append(line)
        # Lines before first ## are ignored (title line, etc.)

    if current is not None:
        blocks.append(current)

    return blocks


# ── Classifier ──────────────────────────────────────────────────────

def classify_block(block: Block) -> str:
    """Classify a block by its heading and body content."""
    heading_lower = block.heading.lower()
    body_text = "\n".join(block.body).lower()
    full_text = heading_lower + "\n" + body_text

    # Session breaks are discarded
    if "session break" in heading_lower or "session break" in body_text:
        return "discard"

    # Session-scoped content stays
    for kw in SESSION_KEYWORDS:
        if kw in heading_lower:
            return "session"

    # Module declarations
    if "#module" in full_text or ("#exports" in full_text and "#path" in full_text):
        return "module_decl"

    # Route mappings (concept -> path)
    route_lines = [l for l in block.body if "->" in l and not l.strip().startswith("#")]
    if len(route_lines) >= 2:
        return "route_map"

    # Dependency lines (pipe-delimited)
    dep_lines = [l for l in block.body if "|" in l and not l.strip().startswith("#")]
    if len(dep_lines) >= 2:
        return "dependency"

    # Platform-specific gotchas
    for kw in PLATFORM_KEYWORDS:
        if kw in full_text:
            # Only if it reads like a gotcha/caveat, not just mentioning platform in passing
            if any(pk in full_text for pk in ["gotcha", "caveat", "workaround", "fallback", "platform-specific"]):
                return "platform"

    # Decisions
    for kw in DECISION_KEYWORDS:
        if kw in heading_lower:
            return "decision"

    # Patterns/caveats
    for kw in PATTERN_KEYWORDS:
        if kw in heading_lower:
            return "pattern"

    # Default: session-scoped (conservative — keep what we can't classify)
    return "session"


def classify_all(blocks: list[Block]) -> list[Block]:
    """Classify all blocks in place and return them."""
    for block in blocks:
        block.block_type = classify_block(block)
    return blocks


# ── Routing functions ───────────────────────────────────────────────

def _slugify(text: str) -> str:
    """Convert heading text to a knowledge entry slug."""
    text = re.sub(r"^#+\s*", "", text)  # strip markdown heading prefix
    text = re.sub(r"[^a-z0-9\s-]", "", text.lower())
    return re.sub(r"[\s]+", "-", text.strip())[:60]


def route_to_knowledge(block: Block, category: str, tags: list[str], dry_run: bool) -> bool:
    """Route a block to KNOWLEDGE.toml via knowledge_writer."""
    slug = _slugify(block.heading)
    if not slug:
        return False

    heading_clean = re.sub(r"^#+\s*", "", block.heading).strip()
    body_text = "\n".join(l for l in block.body if l.strip()).strip()
    summary = heading_clean[:120]
    detail = body_text[:500] if body_text else summary

    if dry_run:
        print(f"    {CYAN}-> KNOWLEDGE.toml{RESET} [{category}] id={slug}")
        return True

    if not KNOWLEDGE_WRITER.exists():
        print(f"    {RED}! knowledge_writer.py not found{RESET}")
        return False

    cmd = [
        sys.executable, str(KNOWLEDGE_WRITER),
        "--id", slug,
        "--source", "hot-context-decompose",
        "--category", category,
        "--summary", summary,
        "--detail", detail,
        "--tags", ",".join(tags),
    ]
    result = subprocess.run(cmd, cwd=str(TERRA_ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        if "already exists" in stderr or "already exists" in result.stdout:
            print(f"    {DIM}skip (exists): {slug}{RESET}")
        else:
            print(f"    {RED}! knowledge_writer failed: {stderr}{RESET}")
        return False
    print(f"    {GREEN}+ KNOWLEDGE.toml{RESET} [{category}] {slug}")
    return True


def route_to_header(block: Block, dry_run: bool) -> bool:
    """Route #module declarations to project.h."""
    body_text = "\n".join(block.body)
    modules = re.findall(r"#module\s+(\w+)", body_text)
    if not modules:
        return False

    if not PROJECT_H.exists():
        print(f"    {RED}! project.h not found{RESET}")
        return False

    existing = PROJECT_H.read_text(encoding="utf-8")
    existing_modules = set(re.findall(r"#module\s+(\w+)", existing))

    routed = False
    for mod in modules:
        if mod in existing_modules:
            print(f"    {DIM}skip (exists): #module {mod}{RESET}")
            continue
        if dry_run:
            print(f"    {CYAN}-> project.h{RESET} #module {mod}")
            routed = True
        else:
            # Extract the full module block from body
            pattern = rf"(#module\s+{re.escape(mod)}\s*\{{[^}}]*\}})"
            match = re.search(pattern, body_text, re.DOTALL)
            if match:
                module_block = "\n" + match.group(1) + "\n"
                # Insert before #endif
                new_content = existing.replace("#endif // PROJECT_H",
                                               module_block + "\n#endif // PROJECT_H")
                PROJECT_H.write_text(new_content, encoding="utf-8")
                print(f"    {GREEN}+ project.h{RESET} #module {mod}")
                existing = new_content
                existing_modules.add(mod)
                routed = True
    return routed


def route_to_routes(block: Block, dry_run: bool) -> bool:
    """Route concept -> path mappings to structure.route."""
    route_lines = []
    for line in block.body:
        line_s = line.strip()
        if "->" in line_s and not line_s.startswith("#"):
            route_lines.append(line_s)

    if not route_lines:
        return False

    if not STRUCTURE_ROUTE.exists():
        print(f"    {RED}! structure.route not found{RESET}")
        return False

    existing = STRUCTURE_ROUTE.read_text(encoding="utf-8")
    existing_concepts = set()
    for line in existing.splitlines():
        line_s = line.strip()
        if "->" in line_s and not line_s.startswith("#"):
            concept = line_s.split("->")[0].strip()
            existing_concepts.add(concept.lower())

    routed = False
    new_lines = []
    for rl in route_lines:
        concept = rl.split("->")[0].strip()
        if concept.lower() in existing_concepts:
            print(f"    {DIM}skip (exists): {concept}{RESET}")
            continue
        if dry_run:
            print(f"    {CYAN}-> structure.route{RESET} {rl}")
        else:
            new_lines.append(rl)
        routed = True

    if new_lines and not dry_run:
        with open(STRUCTURE_ROUTE, "a", encoding="utf-8") as f:
            f.write("\n# ── Decomposed from HOT_CONTEXT ──────────────────────────────\n")
            for nl in new_lines:
                f.write(nl + "\n")
                print(f"    {GREEN}+ structure.route{RESET} {nl}")
    return routed


def route_to_deps(block: Block, dry_run: bool) -> bool:
    """Route dependency lines to deps.table."""
    dep_lines = []
    for line in block.body:
        line_s = line.strip()
        if "|" in line_s and not line_s.startswith("#"):
            parts = line_s.split("|")
            if len(parts) >= 2:
                dep_lines.append(line_s)

    if not dep_lines:
        return False

    if not DEPS_TABLE.exists():
        print(f"    {RED}! deps.table not found{RESET}")
        return False

    existing = DEPS_TABLE.read_text(encoding="utf-8")
    existing_pairs = set()
    for line in existing.splitlines():
        line_s = line.strip()
        if "|" in line_s and not line_s.startswith("#"):
            parts = line_s.split("|")
            if len(parts) >= 2:
                pair = (parts[0].strip().lower(), parts[1].strip().lower())
                existing_pairs.add(pair)

    routed = False
    new_lines = []
    for dl in dep_lines:
        parts = dl.split("|")
        pair = (parts[0].strip().lower(), parts[1].strip().lower())
        if pair in existing_pairs:
            print(f"    {DIM}skip (exists): {pair[0]} | {pair[1]}{RESET}")
            continue
        if dry_run:
            print(f"    {CYAN}-> deps.table{RESET} {dl}")
        else:
            new_lines.append(dl)
        routed = True

    if new_lines and not dry_run:
        with open(DEPS_TABLE, "a", encoding="utf-8") as f:
            for nl in new_lines:
                f.write(nl + "\n")
                print(f"    {GREEN}+ deps.table{RESET} {nl}")
    return routed


# ── Rewriter ────────────────────────────────────────────────────────

def rewrite_hot_context(session_blocks: list[Block], dry_run: bool) -> str:
    """Rewrite HOT_CONTEXT.md with only session-scoped blocks."""
    lines = ["# Hot Context — Terragraf", ""]
    for block in session_blocks:
        lines.append(block.heading)
        lines.extend(block.body)
        if not block.body or block.body[-1].strip():
            lines.append("")

    content = "\n".join(lines)

    if not dry_run:
        HOT_CONTEXT.write_text(content, encoding="utf-8")

    return content


# ── Threshold ───────────────────────────────────────────────────────

def get_max_lines() -> int:
    """Read max_lines from MANIFEST.toml [hot_context] or return default."""
    if not MANIFEST.exists():
        return DEFAULT_MAX_LINES
    try:
        data = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
        return data.get("hot_context", {}).get("max_lines", DEFAULT_MAX_LINES)
    except Exception:
        return DEFAULT_MAX_LINES


def get_retain_sessions() -> int:
    """Read retain_sessions from MANIFEST.toml [hot_context] or return default."""
    if not MANIFEST.exists():
        return DEFAULT_RETAIN_SESSIONS
    try:
        data = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
        return data.get("hot_context", {}).get("retain_sessions", DEFAULT_RETAIN_SESSIONS)
    except Exception:
        return DEFAULT_RETAIN_SESSIONS


def get_hard_max_lines() -> int:
    """Read hard_max_lines from MANIFEST.toml [hot_context] or return default.

    This is the absolute ceiling — the forcer pass extracts h3 sub-sections
    from retained session blocks until total HOT_CONTEXT line count is at or
    below this value (or nothing more is extractable).
    """
    if not MANIFEST.exists():
        return DEFAULT_HARD_MAX_LINES
    try:
        data = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
        return data.get("hot_context", {}).get("hard_max_lines", DEFAULT_HARD_MAX_LINES)
    except Exception:
        return DEFAULT_HARD_MAX_LINES


def check_threshold(line_count: int, max_lines: int) -> bool:
    """Return True if over threshold. Prints warning."""
    if line_count > max_lines:
        print(f"  {YELLOW}HOT_CONTEXT is {line_count} lines (threshold: {max_lines}){RESET}")
        return True
    return False


# ── Lockfile (re-entry guard) ───────────────────────────────────────

def is_locked() -> bool:
    """Return True if a fresh decompose lockfile exists.

    A lockfile is considered stale (and ignored) if its mtime is older
    than LOCK_STALE_SECONDS — protects against crashed runs leaving the
    lock behind. Callers should check this before invoking cmd_decompose
    when they cannot tolerate re-entrant execution (e.g. the
    on_hot_threshold hook).
    """
    if not LOCKFILE.exists():
        return False
    try:
        import time
        age = time.time() - LOCKFILE.stat().st_mtime
        if age > LOCK_STALE_SECONDS:
            return False
        return True
    except Exception:
        return False


def _acquire_lock() -> bool:
    """Create the lockfile. Returns True if newly acquired, False if already held."""
    if is_locked():
        return False
    try:
        LOCKFILE.parent.mkdir(parents=True, exist_ok=True)
        LOCKFILE.write_text(f"pid={os.getpid()}\n", encoding="utf-8")
        return True
    except Exception:
        return False


def _release_lock() -> None:
    """Remove the lockfile if present. Never raises."""
    try:
        if LOCKFILE.exists():
            LOCKFILE.unlink()
    except Exception:
        pass


# ── Main ────────────────────────────────────────────────────────────

def cmd_decompose(dry_run: bool = False, threshold: int | None = None):
    """Parse, classify, route, and rewrite HOT_CONTEXT."""
    if not HOT_CONTEXT.exists():
        print(f"  {RED}No HOT_CONTEXT.md found{RESET}")
        return 1

    # Re-entry guard: refuse to run if another decompose is already in
    # progress in this process tree. The lockfile is created here and
    # removed in the finally block below.
    acquired = _acquire_lock()
    if not acquired:
        print(f"  {YELLOW}hot_decompose already in progress (lockfile present) — skipping{RESET}")
        return 0
    try:
        return _cmd_decompose_inner(dry_run, threshold)
    finally:
        _release_lock()


def _cmd_decompose_inner(dry_run: bool, threshold: int | None):
    """Body of cmd_decompose, wrapped by the lockfile guard above."""
    if not HOT_CONTEXT.exists():
        print(f"  {RED}No HOT_CONTEXT.md found{RESET}")
        return 1

    content = HOT_CONTEXT.read_text(encoding="utf-8")
    line_count = len(content.splitlines())
    max_lines = threshold if threshold is not None else get_max_lines()

    print(f"{BOLD}HOT_CONTEXT Decompose{RESET}")
    if dry_run:
        print(f"  {DIM}(dry run — no files will be modified){RESET}")
    print(f"  Lines: {line_count} / {max_lines} max")
    print()

    blocks = parse_blocks(content)
    for b in blocks:
        b.session_number = extract_session_number(b.heading)
    classify_all(blocks)

    if not blocks:
        print(f"  {DIM}No blocks found{RESET}")
        return 0

    # Age-out: keep only the most recent N sessions verbatim, archive the rest
    retain_count = get_retain_sessions()
    keep_blocks, archive_blocks, retained = apply_age_out(blocks, retain_count)

    print(f"  {DIM}retain_sessions={retain_count} retained={sorted(retained)}{RESET}")
    archived_session_set: set[int] = set()
    for block in archive_blocks:
        category = _archive_category(block.heading)
        tags = ["hot-context", f"session-{block.session_number}", "archived"]
        heading_short = block.heading[:60]
        print(f"  {CYAN}archive{RESET} {heading_short} [{category}]")
        route_to_knowledge(block, category, tags, dry_run)
        archived_session_set.add(block.session_number)

    # Route non-session blocks
    session_blocks = []
    routed_count = len(archive_blocks)

    for block in keep_blocks:
        btype = block.block_type
        heading_short = block.heading[:60]

        if btype == "session":
            session_blocks.append(block)
            print(f"  {GREEN}keep{RESET}  {heading_short}")

        elif btype == "discard":
            print(f"  {DIM}drop{RESET}  {heading_short}")
            routed_count += 1

        elif btype == "decision":
            print(f"  {CYAN}route{RESET} {heading_short}")
            route_to_knowledge(block, "decision", ["hot-context"], dry_run)
            routed_count += 1

        elif btype == "pattern":
            print(f"  {CYAN}route{RESET} {heading_short}")
            route_to_knowledge(block, "pattern", ["hot-context"], dry_run)
            routed_count += 1

        elif btype == "platform":
            print(f"  {CYAN}route{RESET} {heading_short}")
            route_to_knowledge(block, "caveat", ["platform", "hot-context"], dry_run)
            routed_count += 1

        elif btype == "module_decl":
            print(f"  {CYAN}route{RESET} {heading_short}")
            route_to_header(block, dry_run)
            routed_count += 1

        elif btype == "route_map":
            print(f"  {CYAN}route{RESET} {heading_short}")
            route_to_routes(block, dry_run)
            routed_count += 1

        elif btype == "dependency":
            print(f"  {CYAN}route{RESET} {heading_short}")
            route_to_deps(block, dry_run)
            routed_count += 1

        else:
            # Unknown — keep conservatively
            session_blocks.append(block)
            print(f"  {GREEN}keep{RESET}  {heading_short}")

    print()

    # Hard cap forcer pass: extract h3 sub-sections from retained sessions
    # until at or below the absolute ceiling (or nothing more is extractable)
    hard_max = get_hard_max_lines()
    force_extracted, _ = apply_hard_cap(session_blocks, hard_max, dry_run)
    if force_extracted:
        routed_count += force_extracted
        print(f"  {DIM}forcer extracted {force_extracted} h3 section(s) → KNOWLEDGE.toml{RESET}")
        print()

    # Rewrite
    new_content = rewrite_hot_context(session_blocks, dry_run)
    new_lines = len(new_content.splitlines())

    print(f"  Archived: {len(archive_blocks)} block(s) from {len(archived_session_set)} aged-out session(s)")
    print(f"  Routed: {routed_count} block(s)")
    print(f"  Kept:   {len(session_blocks)} block(s)")
    print(f"  Result: {new_lines} lines", end="")
    if new_lines <= max_lines:
        print(f" {GREEN}(under threshold){RESET}")
    elif new_lines <= hard_max:
        print(f" {YELLOW}(over {max_lines} soft threshold, under {hard_max} hard cap){RESET}")
    else:
        print(f" {RED}(STILL over {hard_max} hard cap — nothing extractable left){RESET}")

    return 0


def cli():
    parser = argparse.ArgumentParser(description="Triage HOT_CONTEXT into scaffold files")
    parser.add_argument("action", nargs="?", default="decompose",
                        choices=["decompose"],
                        help="Action to perform (default: decompose)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would move where without writing")
    parser.add_argument("--threshold", type=int, default=None,
                        help="Override max line count")
    args = parser.parse_args()

    return cmd_decompose(dry_run=args.dry_run, threshold=args.threshold)


if __name__ == "__main__":
    sys.exit(cli())
