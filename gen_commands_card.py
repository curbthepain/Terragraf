#!/usr/bin/env python3
"""Generate an SVG commands card for Terragraf's GitHub page."""

COMMANDS = [
    ("SETUP", [
        ("terra init", "wire hooks, check env"),
    ]),
    ("NAVIGATE", [
        ("terra status", "what's here, what works"),
        ("terra route <intent>", "where do I go for this?"),
    ]),
    ("LOOK UP", [
        ("terra lookup <error>", "known fix for this error?"),
        ("terra pattern [name]", "what design pattern fits?"),
        ("terra dep [module]", "what depends on what?"),
    ]),
    ("BUILD", [
        ("terra gen module <name>", "generate a new module"),
        ("terra gen model <name>", "generate a PyTorch model"),
        ("terra gen shader <name>", "generate a compute shader"),
        ("terra generate <type> <n>", "unified code generation"),
    ]),
    ("LIFECYCLE", [
        ("terra hook enter", "run the entry hook"),
        ("terra hook commit", "run the commit hook"),
        ("terra hook generate", "run after file generation"),
        ("terra hook instance", "run on instance spawn"),
    ]),
    ("IMGUI", [
        ("terra imgui build", "build the ImGui app"),
        ("terra imgui run", "launch interactive viewer"),
        ("terra imgui bridge", "start Python bridge server"),
    ]),
    ("VISUALIZE", [
        ("terra viz spectrogram", "render spectrogram"),
        ("terra viz heatmap", "render 2D heatmap"),
        ("terra viz stream", "real-time data plotter"),
        ("terra viz 3d nodes", "3D node graph"),
        ("terra viz 3d mesh", "3D mesh/surface"),
        ("terra viz 3d volume", "volumetric rendering"),
    ]),
    ("ANALYZE", [
        ("terra analyze <input>", "signal/audio FFT analysis"),
        ("terra solve <op>", "math computation router"),
    ]),
    ("MATH", [
        ("terra math eval <expr>", "evaluate expression"),
        ("terra math linalg <op>", "linear algebra info"),
        ("terra math stats [op]", "statistics info"),
    ]),
    ("GIT", [
        ("terra branch <type> <n>", "create conventional branch"),
        ("terra commit <msg>", "structured commit"),
        ("terra pr --preview", "PR template/preview"),
    ]),
    ("INSTANCES", [
        ("terra queue", "show task queue"),
        ("terra queue add <task>", "add task to queue"),
        ("terra dispatch <task>", "parallel instance dispatch"),
    ]),
    ("SHARPEN", [
        ("terra sharpen", "run self-sharpening"),
        ("terra sharpen --dry-run", "preview changes"),
        ("terra sharpen status", "analytics summary"),
    ]),
    ("TUNING", [
        ("terra tune", "show active profile"),
        ("terra tune list", "list profiles"),
        ("terra tune load <name>", "load profile"),
        ("terra tune zone <name>", "enter zone"),
        ("terra tune zone --exit", "exit current zone"),
        ("terra tune set <id> <val>", "set knob value"),
        ("terra tune axes", "show thematic axes"),
        ("terra tune directive", "show bot directive"),
        ("terra tune instructions", "behavioral output"),
        ("terra tune promise", "show thematic promise"),
    ]),
    ("MODE", [
        ("terra mode", "show CI or App mode"),
        ("terra mode check", "exit 0=app, 1=ci"),
        ("terra mode can <cap>", "check capability"),
    ]),
    ("SKILLS", [
        ("terra skill list", "list registered skills"),
        ("terra skill run <name>", "execute a skill by name"),
        ("terra hot [action]", "session hot context"),
        ("terra health", "full system diagnostic"),
    ]),
    ("KNOWLEDGE", [
        ("terra knowledge", "list knowledge entries"),
        ("terra knowledge search <q>", "search by keyword"),
        ("terra knowledge add ...", "add a knowledge entry"),
    ]),
    ("PROJECTS", [
        ("terra project new <name>", "scaffold a new project"),
    ]),
    ("ML", [
        ("terra train <dir>", "ML training pipeline"),
        ("terra viewer", "ImGui viewer lifecycle"),
        ("terra render <type> <in>", "3D visualization"),
        ("terra test [module]", "run test suite"),
    ]),
    ("APP", [
        ("terra app", "launch Qt container"),
        ("terra app --offscreen", "headless mode (testing)"),
    ]),
]

# Layout — sized for GitHub README (~880px content width)
CARD_WIDTH = 880
CARD_PADDING = 24
COL_GAP = 24
ROW_GAP = 4
SECTION_GAP = 14
LINE_HEIGHT = 18
HEADER_HEIGHT = 26
FONT_SIZE = 12
HEADER_FONT_SIZE = 10
NUM_COLS = 2
USABLE_WIDTH = CARD_WIDTH - CARD_PADDING * 2 - COL_GAP * (NUM_COLS - 1)
COL_WIDTH = USABLE_WIDTH // NUM_COLS
CMD_COL_WIDTH = int(COL_WIDTH * 0.55)

# Colors — GitHub dark theme
BG = "#0d1117"
BG_HEADER = "#161b22"
BORDER = "#30363d"
TEXT_CMD = "#e6edf3"
TEXT_DESC = "#7d8590"
TEXT_SECTION = "#58a6ff"
TEXT_TITLE = "#e6edf3"


def split_into_columns(sections, num_cols):
    """Split sections across N columns, with the last section centered below if it balances better."""
    section_sizes = [(name, cmds, 1 + len(cmds)) for name, cmds in sections]
    total_lines = sum(s for _, _, s in section_sizes)

    # Try pulling last section(s) to a centered bottom row
    # Find how many trailing sections to center: keep pulling until columns are balanced
    bottom = []
    remaining = list(section_sizes)

    # Check if moving the last section to center improves balance
    for _ in range(2):  # try pulling up to 2 sections
        if len(remaining) <= num_cols:
            break
        candidate = remaining[-1]
        rem_lines = sum(s for _, _, s in remaining[:-1])
        target = rem_lines / num_cols
        # Check column balance without this section
        cols_test = _split_greedy(remaining[:-1], num_cols, target)
        heights = [sum(1 + len(c) for _, c in col) for col in cols_test]
        diff = max(heights) - min(heights)
        if diff <= 3:
            bottom.insert(0, (candidate[0], candidate[1]))
            remaining = remaining[:-1]
        else:
            break

    rem_lines = sum(s for _, _, s in remaining)
    target = rem_lines / num_cols
    columns = _split_greedy(remaining, num_cols, target)
    return columns, bottom


def _split_greedy(section_sizes, num_cols, target):
    columns = []
    current_col = []
    current_lines = 0

    for name, cmds, size in section_sizes:
        if current_lines + size > target and current_col and len(columns) < num_cols - 1:
            columns.append(current_col)
            current_col = []
            current_lines = 0
        current_col.append((name, cmds))
        current_lines += size

    if current_col:
        columns.append(current_col)
    return columns


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_svg():
    total_cmds = sum(len(cmds) for _, cmds in COMMANDS)
    columns, bottom_sections = split_into_columns(COMMANDS, NUM_COLS)

    # Calculate height from tallest column
    col_heights = []
    for col_sections in columns:
        h = 0
        for i, (_, cmds) in enumerate(col_sections):
            h += HEADER_HEIGHT + len(cmds) * (LINE_HEIGHT + ROW_GAP)
            if i < len(col_sections) - 1:
                h += SECTION_GAP
        col_heights.append(h)

    max_col_height = max(col_heights)

    # Bottom centered sections height
    bottom_height = 0
    if bottom_sections:
        bottom_height += SECTION_GAP
        for i, (_, cmds) in enumerate(bottom_sections):
            bottom_height += HEADER_HEIGHT + len(cmds) * (LINE_HEIGHT + ROW_GAP)
            if i < len(bottom_sections) - 1:
                bottom_height += SECTION_GAP

    title_bar_h = 44
    height = CARD_PADDING + title_bar_h + max_col_height + bottom_height + CARD_PADDING

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{height}" viewBox="0 0 {CARD_WIDTH} {height}">')

    # Background
    lines.append(f'  <rect width="{CARD_WIDTH}" height="{height}" rx="10" fill="{BG}" stroke="{BORDER}" stroke-width="1" />')

    # Title bar
    lines.append(f'  <rect width="{CARD_WIDTH}" height="{title_bar_h}" rx="10" fill="{BG_HEADER}" />')
    lines.append(f'  <rect x="0" y="{title_bar_h - 10}" width="{CARD_WIDTH}" height="10" fill="{BG_HEADER}" />')
    lines.append(f'  <line x1="0" y1="{title_bar_h}" x2="{CARD_WIDTH}" y2="{title_bar_h}" stroke="{BORDER}" stroke-width="1" />')

    # Title bar labels
    dot_y = title_bar_h // 2
    num_categories = len(COMMANDS)
    title_font = "'SF Mono','Cascadia Code','Consolas',monospace"
    lines.append(f'  <text x="{CARD_PADDING}" y="{dot_y + 4}" '
                 f'font-family="{title_font}" font-size="10" '
                 f'fill="{TEXT_DESC}">{num_categories} categories</text>')

    # Title
    lines.append(f'  <text x="{CARD_WIDTH // 2}" y="{dot_y + 4}" text-anchor="middle" '
                 f'font-family="\'SF Mono\',\'Cascadia Code\',\'Consolas\',monospace" font-size="13" font-weight="bold" '
                 f'fill="{TEXT_TITLE}">terragraf commands</text>')

    # Badge
    lines.append(f'  <text x="{CARD_WIDTH - CARD_PADDING}" y="{dot_y + 4}" text-anchor="end" '
                 f'font-family="\'SF Mono\',\'Cascadia Code\',\'Consolas\',monospace" font-size="10" '
                 f'fill="{TEXT_DESC}">{total_cmds} commands</text>')

    # Columns
    font = "'SF Mono','Cascadia Code','Consolas',monospace"
    content_y = title_bar_h + CARD_PADDING

    for col_idx, col_sections in enumerate(columns):
        col_x = CARD_PADDING + col_idx * (COL_WIDTH + COL_GAP)
        y = content_y

        for sec_idx, (section_name, cmds) in enumerate(col_sections):
            # Section header — centered over command block
            col_center_x = col_x + COL_WIDTH // 2
            lines.append(f'  <text x="{col_center_x}" y="{y + 11}" text-anchor="middle" '
                         f'font-family="{font}" font-size="{HEADER_FONT_SIZE}" '
                         f'font-weight="bold" fill="{TEXT_SECTION}" '
                         f'letter-spacing="1.2">{escape(section_name)}</text>')
            underline_w = len(section_name) * 7
            lines.append(f'  <line x1="{col_center_x - underline_w // 2}" y1="{y + 15}" '
                         f'x2="{col_center_x + underline_w // 2}" y2="{y + 15}" '
                         f'stroke="{TEXT_SECTION}" stroke-width="1" opacity="0.25" />')
            y += HEADER_HEIGHT

            for cmd, desc in cmds:
                lines.append(f'  <text x="{col_x + 6}" y="{y + 12}" '
                             f'font-family="{font}" font-size="{FONT_SIZE}" '
                             f'fill="{TEXT_CMD}">{escape(cmd)}</text>')
                lines.append(f'  <text x="{col_x + CMD_COL_WIDTH}" y="{y + 12}" '
                             f'font-family="{font}" font-size="{FONT_SIZE}" '
                             f'fill="{TEXT_DESC}">{escape(desc)}</text>')
                y += LINE_HEIGHT + ROW_GAP

            if sec_idx < len(col_sections) - 1:
                y += SECTION_GAP

    # Bottom centered sections
    if bottom_sections:
        y = content_y + max_col_height + SECTION_GAP
        center_x = CARD_WIDTH // 2 - COL_WIDTH // 2

        for sec_idx, (section_name, cmds) in enumerate(bottom_sections):
            card_center_x = CARD_WIDTH // 2
            lines.append(f'  <text x="{card_center_x}" y="{y + 11}" text-anchor="middle" '
                         f'font-family="{font}" font-size="{HEADER_FONT_SIZE}" '
                         f'font-weight="bold" fill="{TEXT_SECTION}" '
                         f'letter-spacing="1.2">{escape(section_name)}</text>')
            underline_w = len(section_name) * 7
            lines.append(f'  <line x1="{card_center_x - underline_w // 2}" y1="{y + 15}" '
                         f'x2="{card_center_x + underline_w // 2}" y2="{y + 15}" '
                         f'stroke="{TEXT_SECTION}" stroke-width="1" opacity="0.25" />')
            y += HEADER_HEIGHT

            for cmd, desc in cmds:
                lines.append(f'  <text x="{center_x + 6}" y="{y + 12}" '
                             f'font-family="{font}" font-size="{FONT_SIZE}" '
                             f'fill="{TEXT_CMD}">{escape(cmd)}</text>')
                lines.append(f'  <text x="{center_x + CMD_COL_WIDTH}" y="{y + 12}" '
                             f'font-family="{font}" font-size="{FONT_SIZE}" '
                             f'fill="{TEXT_DESC}">{escape(desc)}</text>')
                y += LINE_HEIGHT + ROW_GAP

            if sec_idx < len(bottom_sections) - 1:
                y += SECTION_GAP

    lines.append("</svg>")
    return "\n".join(lines)


if __name__ == "__main__":
    svg = generate_svg()
    out_path = "commands-card.svg"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out_path}")
