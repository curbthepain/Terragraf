#!/usr/bin/env python3
"""Generate an SVG skills card for Terragraf's GitHub page."""

SKILLS = [
    ("GENERATORS", [
        ("scaffold_project", "scaffold a new project"),
        ("generate", "module, model, shader with lang detection"),
    ]),
    ("ANALYZERS", [
        ("signal_analyze", "FFT, spectral features, spectrogram export"),
        ("math_solve", "linalg, algebra, stats, transforms"),
    ]),
    ("VALIDATORS", [
        ("consistency_scan", "verify headers, routes, tables integrity"),
        ("test_suite", "discover, run, report tests by subsystem"),
    ]),
    ("WORKFLOWS", [
        ("git_flow", "branch, commit, PR with conventions"),
    ]),
    ("OPTIMIZERS", [
        ("sharpen_run", "self-sharpening: analyze, preview, apply"),
        ("tune_session", "thematic calibration: profiles, zones, knobs"),
    ]),
    ("LAUNCHERS", [
        ("viewer", "ImGui viewer: build, bridge, launch"),
        ("render_3d", "surfaces, volumes, node graphs, point clouds"),
    ]),
    ("PIPELINES", [
        ("train_model", "ML training: dataset, model, evaluation"),
        ("instance_dispatch", "parallel instance orchestration"),
    ]),
    ("UTILITIES", [
        ("hot_context", "read, display, update session context"),
        ("health_check", "full system diagnostic"),
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
NAME_COL_WIDTH = int(COL_WIDTH * 0.42)

# Colors — GitHub dark theme
BG = "#0d1117"
BG_HEADER = "#161b22"
BORDER = "#30363d"
TEXT_NAME = "#e6edf3"
TEXT_DESC = "#7d8590"
TEXT_SECTION = "#d2a8ff"
TEXT_TITLE = "#e6edf3"


def split_into_columns(sections, num_cols):
    """Split sections across N columns, balancing height."""
    section_sizes = [(name, items, 1 + len(items)) for name, items in sections]
    total_lines = sum(s for _, _, s in section_sizes)

    bottom = []
    remaining = list(section_sizes)

    for _ in range(2):
        if len(remaining) <= num_cols:
            break
        candidate = remaining[-1]
        rem_lines = sum(s for _, _, s in remaining[:-1])
        target = rem_lines / num_cols
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

    for name, items, size in section_sizes:
        if current_lines + size > target and current_col and len(columns) < num_cols - 1:
            columns.append(current_col)
            current_col = []
            current_lines = 0
        current_col.append((name, items))
        current_lines += size

    if current_col:
        columns.append(current_col)
    return columns


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_svg():
    total_skills = sum(len(items) for _, items in SKILLS)
    columns, bottom_sections = split_into_columns(SKILLS, NUM_COLS)

    # Calculate height from tallest column
    col_heights = []
    for col_sections in columns:
        h = 0
        for i, (_, items) in enumerate(col_sections):
            h += HEADER_HEIGHT + len(items) * (LINE_HEIGHT + ROW_GAP)
            if i < len(col_sections) - 1:
                h += SECTION_GAP
        col_heights.append(h)

    max_col_height = max(col_heights)

    # Bottom centered sections height
    bottom_height = 0
    if bottom_sections:
        bottom_height += SECTION_GAP
        for i, (_, items) in enumerate(bottom_sections):
            bottom_height += HEADER_HEIGHT + len(items) * (LINE_HEIGHT + ROW_GAP)
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
    num_categories = len(SKILLS)
    title_font = "'SF Mono','Cascadia Code','Consolas',monospace"
    lines.append(f'  <text x="{CARD_PADDING}" y="{dot_y + 4}" '
                 f'font-family="{title_font}" font-size="10" '
                 f'fill="{TEXT_DESC}">{num_categories} categories</text>')

    # Title
    lines.append(f'  <text x="{CARD_WIDTH // 2}" y="{dot_y + 4}" text-anchor="middle" '
                 f'font-family="\'SF Mono\',\'Cascadia Code\',\'Consolas\',monospace" font-size="13" font-weight="bold" '
                 f'fill="{TEXT_TITLE}">terragraf skills</text>')

    # Badge
    lines.append(f'  <text x="{CARD_WIDTH - CARD_PADDING}" y="{dot_y + 4}" text-anchor="end" '
                 f'font-family="\'SF Mono\',\'Cascadia Code\',\'Consolas\',monospace" font-size="10" '
                 f'fill="{TEXT_DESC}">{total_skills} skills</text>')

    # Columns
    font = "'SF Mono','Cascadia Code','Consolas',monospace"
    content_y = title_bar_h + CARD_PADDING

    for col_idx, col_sections in enumerate(columns):
        col_x = CARD_PADDING + col_idx * (COL_WIDTH + COL_GAP)
        y = content_y

        for sec_idx, (section_name, items) in enumerate(col_sections):
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

            for name, desc in items:
                lines.append(f'  <text x="{col_x + 6}" y="{y + 12}" '
                             f'font-family="{font}" font-size="{FONT_SIZE}" '
                             f'fill="{TEXT_NAME}">{escape(name)}</text>')
                lines.append(f'  <text x="{col_x + NAME_COL_WIDTH}" y="{y + 12}" '
                             f'font-family="{font}" font-size="{FONT_SIZE}" '
                             f'fill="{TEXT_DESC}">{escape(desc)}</text>')
                y += LINE_HEIGHT + ROW_GAP

            if sec_idx < len(col_sections) - 1:
                y += SECTION_GAP

    # Bottom centered sections
    if bottom_sections:
        y = content_y + max_col_height + SECTION_GAP
        center_x = CARD_WIDTH // 2 - COL_WIDTH // 2

        for sec_idx, (section_name, items) in enumerate(bottom_sections):
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

            for name, desc in items:
                lines.append(f'  <text x="{center_x + 6}" y="{y + 12}" '
                             f'font-family="{font}" font-size="{FONT_SIZE}" '
                             f'fill="{TEXT_NAME}">{escape(name)}</text>')
                lines.append(f'  <text x="{center_x + NAME_COL_WIDTH}" y="{y + 12}" '
                             f'font-family="{font}" font-size="{FONT_SIZE}" '
                             f'fill="{TEXT_DESC}">{escape(desc)}</text>')
                y += LINE_HEIGHT + ROW_GAP

            if sec_idx < len(bottom_sections) - 1:
                y += SECTION_GAP

    lines.append("</svg>")
    return "\n".join(lines)


if __name__ == "__main__":
    svg = generate_svg()
    out_path = "skills-card.svg"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out_path}")
