"""ANSI SGR escape sequence helpers.

Tiny self-contained converter for the subset of SGR codes that the project's
skills actually emit (`\\033[1m`, `\\033[2m`, `\\033[3Xm`, `\\033[9Xm`,
`\\033[0m`). No external dependencies.
"""

import re

from .. import theme


# Matches CSI ... m (Select Graphic Rendition only).
ANSI_RE = re.compile(r"\x1B\[([0-9;]*)m")
# Matches any non-SGR CSI sequence (final byte is anything except 'm').
ANSI_OTHER_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-ln-~]")


# 30–37 / 90–97 → palette colour. Aligned with theme.py constants so terminal
# output rendered in the app blends with the rest of the UI.
_FG_COLORS: dict[int, str] = {
    30: "#000000",
    31: theme.RED,
    32: theme.GREEN,
    33: theme.YELLOW,
    34: theme.ACCENT,         # blue
    35: "#c084fc",            # magenta
    36: theme.CYAN,
    37: theme.TEXT_PRIMARY,
    90: theme.TEXT_DIM,
    91: theme.RED,
    92: theme.GREEN,
    93: theme.YELLOW,
    94: theme.ACCENT,
    95: "#c084fc",
    96: theme.CYAN,
    97: "#ffffff",
}


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from ``text``."""
    text = ANSI_RE.sub("", text)
    return ANSI_OTHER_RE.sub("", text)


def _escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )


def ansi_to_html(text: str) -> str:
    """Convert a string containing ANSI SGR codes into a Qt-friendly HTML
    fragment wrapped in a monospaced ``<pre>``.

    Supports: reset (0), bold (1), dim (2), italic (3), underline (4),
    foreground colours (30–37, 90–97). Unknown codes are dropped silently.
    Any non-SGR CSI sequences are also stripped.
    """
    # Drop non-SGR CSI sequences first so they don't leak through as text.
    text = ANSI_OTHER_RE.sub("", text)

    out: list[str] = []
    open_span = False
    pos = 0

    def close_span():
        nonlocal open_span
        if open_span:
            out.append("</span>")
            open_span = False

    for match in ANSI_RE.finditer(text):
        # Emit literal text up to this escape.
        out.append(_escape_html(text[pos:match.start()]))
        pos = match.end()

        codes_str = match.group(1)
        # Empty payload (`\x1b[m`) is treated as reset.
        codes = [int(c) for c in codes_str.split(";") if c.isdigit()] or [0]

        styles: list[str] = []
        for code in codes:
            if code == 0:
                close_span()
                styles = []
                break
            elif code == 1:
                styles.append("font-weight:bold")
            elif code == 2:
                styles.append(f"color:{theme.TEXT_DIM}")
            elif code == 3:
                styles.append("font-style:italic")
            elif code == 4:
                styles.append("text-decoration:underline")
            elif code in _FG_COLORS:
                styles.append(f"color:{_FG_COLORS[code]}")

        if styles:
            close_span()
            out.append(f'<span style="{";".join(styles)}">')
            open_span = True

    out.append(_escape_html(text[pos:]))
    close_span()

    body = "".join(out)
    return (
        '<pre style="font-family: \'JetBrains Mono\', \'Consolas\', monospace; '
        'white-space: pre-wrap; margin: 0;">'
        f"{body}"
        "</pre>"
    )
