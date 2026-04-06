"""
Terragraf Kohala UI — animated browser preview.

Self-contained stdlib Python script that renders an animated HTML mockup
of the Terragraf workspace window (top bar, sidebar, welcome tab with
Scaffold Health + Recent Tabs panels, status bar) and opens it in the
default browser.

Usage:
    python additions/terragraf_preview_web.py          # write + open
    python additions/terragraf_preview_web.py --no-open # write only

Output:
    additions/terragraf_preview.html
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path


# ── Palette (mirrors .scaffold/app/theme.py, Kohala Session 26) ────────
PALETTE = {
    "BG_PRIMARY":   "#060D17",
    "BG_SECONDARY": "#0E1A2E",
    "BG_ELEVATED":  "#1A2A40",
    "BG_INPUT":     "#06121E",
    "BG_HOVER":     "#172841",
    "BG_PRESSED":   "#22344F",
    "BORDER":       "#1F2A3C",
    "BORDER_STRONG":"#2C3A52",
    "TEXT_PRIMARY":   "#F0EDE6",
    "TEXT_SECONDARY": "#B6C3D2",
    "TEXT_DIM":       "#6B7D90",
    "ACCENT":         "#E83030",
    "ACCENT_HOVER":   "#FF5040",
    "ACCENT_PRESSED": "#C0221F",
    "GREEN":   "#6EE0B0",
    "YELLOW":  "#fbbf24",
    "CYAN":    "#22d3ee",
    "MAGENTA": "#c084fc",
}

# ── Mock data for the preview ──────────────────────────────────────────
HEALTH_STATS = [
    ("Header files",     "27"),
    ("Modules",          "43"),
    ("Route files",      "12"),
    ("Routes",           "61"),
    ("Table files",      "9"),
    ("Queue pending",    "3"),
    ("Queue running",    "1"),
    ("HOT_CONTEXT lines","455"),
    ("Recent events",    "128"),
]

RECENT_TABS = [
    # (name, slug, state, is_active)
    ("WELCOME",          "welcome · a1f203", "ACTIVE", True),
    ("HOT_CONTEXT.md",   "native  · 9c44de", "RECENT", False),
    ("theme.py",         "native  · 7b12ff", "RECENT", False),
    ("terra health",     "proc    · 3e88a0", "RECENT", False),
    ("tune zone rehearse","native · 5501cc", "RECENT", False),
]

SIDEBAR_ITEMS = [
    ("\u25A0", "Workspace"),   # ■
    ("\u2731", "Skills"),      # ✱
    ("\u25C6", "Routes"),      # ◆
    ("\u25B2", "Tune"),        # ▲
    ("\u25CF", "Health"),      # ●
    ("\u2699", "Settings"),    # ⚙
]


def html_doc() -> str:
    p = PALETTE

    health_cells = "\n".join(
        f'''
        <div class="stat" style="--i:{i}">
          <div class="stat-key">{k}</div>
          <div class="stat-val" data-target="{v}">0</div>
        </div>'''
        for i, (k, v) in enumerate(HEALTH_STATS)
    )

    tab_rows = "\n".join(
        f'''
        <div class="tab-row {"active" if active else ""}" style="--i:{i}">
          <span class="dot"></span>
          <span class="tab-name">{name}</span>
          <span class="tab-slug">{slug}</span>
          <span class="tab-state">{state}</span>
        </div>'''
        for i, (name, slug, state, active) in enumerate(RECENT_TABS)
    )

    sidebar_items = "\n".join(
        f'''
        <div class="side-item {"active" if i == 0 else ""}" style="--i:{i}">
          <span class="side-ico">{ico}</span>
          <span class="side-label">{lbl}</span>
        </div>'''
        for i, (ico, lbl) in enumerate(SIDEBAR_ITEMS)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Terragraf — Kohala preview</title>
<style>
  :root {{
    --bg-primary: {p["BG_PRIMARY"]};
    --bg-secondary: {p["BG_SECONDARY"]};
    --bg-elevated: {p["BG_ELEVATED"]};
    --bg-input: {p["BG_INPUT"]};
    --bg-hover: {p["BG_HOVER"]};
    --bg-pressed: {p["BG_PRESSED"]};
    --border: {p["BORDER"]};
    --border-strong: {p["BORDER_STRONG"]};
    --text: {p["TEXT_PRIMARY"]};
    --text-2: {p["TEXT_SECONDARY"]};
    --text-dim: {p["TEXT_DIM"]};
    --accent: {p["ACCENT"]};
    --accent-hover: {p["ACCENT_HOVER"]};
    --accent-pressed: {p["ACCENT_PRESSED"]};
    --green: {p["GREEN"]};
    --cyan: {p["CYAN"]};
    --yellow: {p["YELLOW"]};
    --side-w: 240px;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; padding: 0;
    background: radial-gradient(ellipse at top, #10182a 0%, var(--bg-primary) 55%, #02060d 100%);
    color: var(--text);
    font-family: "Barlow","Inter","Segoe UI","Helvetica Neue",system-ui,sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
  }}
  .window {{
    width: min(1440px, 96vw);
    height: min(860px, 92vh);
    margin: 3vh auto;
    background: var(--bg-primary);
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    box-shadow:
      0 30px 80px rgba(0,0,0,0.6),
      0 0 0 1px rgba(232,48,48,0.06),
      inset 0 1px 0 rgba(255,255,255,0.04);
    overflow: hidden;
    display: grid;
    grid-template-rows: 44px 1fr 26px;
    animation: fadeUp .8s ease both;
  }}
  @keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}

  /* ── top bar ───────────────────────────────────────────────────── */
  .topbar {{
    display: flex; align-items: center;
    padding: 0 14px;
    background: linear-gradient(180deg, #122036 0%, var(--bg-secondary) 100%);
    border-bottom: 1px solid var(--border);
    gap: 12px;
  }}
  .traffic {{ display: flex; gap: 6px; }}
  .traffic span {{
    width: 11px; height: 11px; border-radius: 50%;
    background: var(--border-strong);
  }}
  .traffic span:nth-child(1) {{ background: var(--accent); }}
  .traffic span:nth-child(2) {{ background: var(--yellow); }}
  .traffic span:nth-child(3) {{ background: var(--green); }}
  .brand {{
    font-family: "Barlow Condensed","Barlow",sans-serif;
    font-weight: 700; letter-spacing: 0.18em;
    font-size: 15px; text-transform: uppercase;
    color: var(--text);
  }}
  .brand .mark {{ color: var(--accent); }}
  .tabstrip {{
    display: flex; gap: 4px; margin-left: 20px; flex: 1;
  }}
  .tabchip {{
    padding: 6px 14px;
    font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--text-dim);
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px 4px 0 0;
    border-bottom: 2px solid transparent;
    animation: slideDown .6s ease both;
    animation-delay: calc(var(--i,0) * 80ms + .3s);
  }}
  @keyframes slideDown {{
    from {{ opacity: 0; transform: translateY(-6px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
  .tabchip.active {{
    color: var(--text);
    background: rgba(232,48,48,0.08);
    border-color: rgba(232,48,48,0.35);
    border-bottom: 2px solid var(--accent);
    box-shadow: 0 -1px 0 rgba(232,48,48,0.25) inset, 0 0 18px rgba(232,48,48,0.15);
  }}
  .topbar .spacer {{ flex: 1; }}
  .chip {{
    font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--text-2); padding: 4px 8px;
    border: 1px solid var(--border-strong); border-radius: 3px;
    background: rgba(255,255,255,0.02);
  }}

  /* ── body: sidebar + main ─────────────────────────────────────── */
  .body {{
    display: grid;
    grid-template-columns: var(--side-w) 1fr;
    min-height: 0;
  }}
  .sidebar {{
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
    padding: 14px 0;
    transition: width .45s cubic-bezier(.4,.8,.2,1);
    overflow: hidden;
  }}
  .side-eyebrow {{
    padding: 4px 16px 10px;
    font-family: "JetBrains Mono",monospace;
    font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase;
    color: var(--accent);
  }}
  .side-item {{
    display: flex; align-items: center; gap: 12px;
    padding: 10px 16px;
    color: var(--text-2);
    cursor: pointer;
    font-size: 13px;
    border-left: 2px solid transparent;
    animation: fadeRight .6s ease both;
    animation-delay: calc(var(--i,0) * 70ms + .4s);
    transition: background .15s, color .15s, border-color .15s;
  }}
  @keyframes fadeRight {{
    from {{ opacity: 0; transform: translateX(-8px); }}
    to   {{ opacity: 1; transform: translateX(0); }}
  }}
  .side-item:hover {{ background: var(--bg-hover); color: var(--text); }}
  .side-item.active {{
    background: rgba(232,48,48,0.10);
    color: var(--text);
    border-left-color: var(--accent);
  }}
  .side-ico {{
    display: inline-block; width: 18px; text-align: center;
    color: var(--accent); font-size: 12px;
  }}

  /* ── main content ─────────────────────────────────────────────── */
  .main {{
    padding: 22px 26px; min-width: 0; min-height: 0;
    display: flex; flex-direction: column; gap: 16px;
    overflow: hidden;
  }}
  .page-title {{
    font-family: "Barlow Condensed","Barlow",sans-serif;
    font-size: 26px; font-weight: 700; letter-spacing: 0.05em;
    text-transform: uppercase;
  }}
  .page-title .accent {{ color: var(--accent); }}
  .eyebrow {{
    font-family: "JetBrains Mono",monospace;
    font-size: 10px; letter-spacing: 0.22em; text-transform: uppercase;
    color: var(--accent); margin-bottom: 4px;
  }}

  .cards {{
    display: grid;
    grid-template-columns: 3fr 2fr;
    gap: 18px;
    flex: 1; min-height: 0;
  }}
  .panel {{
    position: relative;
    background:
      linear-gradient(180deg, rgba(232,48,48,0.04) 0%, rgba(14,26,46,0.0) 25%),
      var(--bg-elevated);
    border: 1px solid var(--border-strong);
    border-radius: 8px;
    padding: 18px 20px 16px;
    box-shadow:
      0 1px 0 rgba(255,255,255,0.04) inset,
      0 20px 50px rgba(0,0,0,0.35);
    animation: panelIn .9s cubic-bezier(.2,.8,.2,1) both;
    overflow: hidden;
  }}
  .panel::before {{
    content: "";
    position: absolute; inset: 0 0 auto 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(232,48,48,0.8), transparent);
    opacity: 0.5;
  }}
  .panel:nth-child(1) {{ animation-delay: .35s; }}
  .panel:nth-child(2) {{ animation-delay: .5s; }}
  @keyframes panelIn {{
    from {{ opacity: 0; transform: translateY(20px) scale(.98); }}
    to   {{ opacity: 1; transform: translateY(0) scale(1); }}
  }}
  .panel h3 {{
    margin: 0 0 14px;
    font-family: "Barlow Condensed","Barlow",sans-serif;
    font-size: 18px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text);
  }}

  /* Scaffold Health 3x3 grid */
  .grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px 28px;
  }}
  .stat {{
    display: flex; flex-direction: column; gap: 2px;
    animation: fadeUp .6s ease both;
    animation-delay: calc(var(--i,0) * 60ms + .7s);
  }}
  .stat-key {{
    font-family: "JetBrains Mono",monospace;
    font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase;
    color: var(--text-dim);
  }}
  .stat-val {{
    font-family: "Barlow Condensed","Barlow",sans-serif;
    font-size: 26px; font-weight: 700;
    color: var(--text);
  }}

  /* Recent Tabs list */
  .tabs-list {{ display: flex; flex-direction: column; gap: 2px; }}
  .tab-row {{
    display: grid;
    grid-template-columns: 14px 1.3fr 1.5fr auto;
    align-items: center;
    gap: 12px;
    padding: 8px 4px;
    border-bottom: 1px dashed rgba(44,58,82,0.5);
    animation: fadeRight .6s ease both;
    animation-delay: calc(var(--i,0) * 80ms + .85s);
  }}
  .tab-row:last-child {{ border-bottom: none; }}
  .tab-row .dot {{
    width: 10px; height: 10px; border-radius: 50%;
    background: #8FA0B6;
    box-shadow: 0 0 0 0 rgba(0,0,0,0);
  }}
  .tab-row.active .dot {{
    background: var(--green);
    animation: pulse 1.8s ease-in-out infinite;
  }}
  @keyframes pulse {{
    0%,100% {{ box-shadow: 0 0 0 0 rgba(110,224,176,0.6); }}
    50%     {{ box-shadow: 0 0 0 6px rgba(110,224,176,0); }}
  }}
  .tab-name {{
    font-family: "JetBrains Mono",monospace;
    font-size: 11px; letter-spacing: 0.06em;
    color: var(--text);
  }}
  .tab-slug {{
    font-family: "JetBrains Mono",monospace;
    font-size: 10px; color: var(--text-dim);
  }}
  .tab-state {{
    font-family: "JetBrains Mono",monospace;
    font-size: 9px; letter-spacing: 0.18em;
    color: var(--text-dim);
  }}
  .tab-row.active .tab-state {{ color: var(--green); }}

  /* ── status bar ────────────────────────────────────────────────── */
  .statusbar {{
    display: flex; align-items: center; gap: 18px;
    padding: 0 16px;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
    font-family: "JetBrains Mono",monospace;
    font-size: 10px; letter-spacing: 0.1em;
    color: var(--text-dim);
  }}
  .statusbar .sb-accent {{ color: var(--accent); }}
  .statusbar .sb-ok {{ color: var(--green); }}
  .statusbar .spacer {{ flex: 1; }}
  .blink {{ animation: blink 1.4s steps(2, end) infinite; }}
  @keyframes blink {{ 50% {{ opacity: 0.2; }} }}

  /* ── controls strip ────────────────────────────────────────────── */
  .controls {{
    position: fixed; bottom: 18px; right: 22px;
    display: flex; gap: 8px;
    font-family: "JetBrains Mono",monospace; font-size: 10px;
    letter-spacing: 0.15em; text-transform: uppercase;
    z-index: 50;
  }}
  .controls button {{
    background: rgba(14,26,46,0.85);
    color: var(--text-2);
    border: 1px solid var(--border-strong);
    padding: 7px 12px; border-radius: 3px;
    cursor: pointer;
    backdrop-filter: blur(4px);
  }}
  .controls button:hover {{
    color: var(--text);
    border-color: var(--accent);
    box-shadow: 0 0 12px rgba(232,48,48,0.25);
  }}

  body.collapsed .window {{ --side-w: 56px; }}
  body.collapsed .side-label {{ opacity: 0; }}
  .side-label {{ transition: opacity .25s; }}
</style>
</head>
<body>
  <div class="window">

    <!-- ── TOP BAR ─────────────────────────────────────────────── -->
    <div class="topbar">
      <div class="traffic"><span></span><span></span><span></span></div>
      <div class="brand">TERRA<span class="mark">GRAF</span></div>
      <div class="tabstrip">
        <div class="tabchip active" style="--i:0">Welcome</div>
        <div class="tabchip" style="--i:1">HOT_CONTEXT.md</div>
        <div class="tabchip" style="--i:2">theme.py</div>
        <div class="tabchip" style="--i:3">terra health</div>
      </div>
      <div class="spacer"></div>
      <div class="chip">Kohala · Session 25</div>
    </div>

    <!-- ── BODY ────────────────────────────────────────────────── -->
    <div class="body">
      <div class="sidebar">
        <div class="side-eyebrow">// Workspace</div>
        {sidebar_items}
      </div>
      <div class="main">
        <div>
          <div class="eyebrow">// Welcome</div>
          <div class="page-title">
            <span class="accent">Terragraf</span> Workspace
          </div>
        </div>
        <div class="cards">
          <div class="panel">
            <h3>Scaffold Health</h3>
            <div class="grid">
              {health_cells}
            </div>
          </div>
          <div class="panel">
            <h3>Recent Tabs</h3>
            <div class="tabs-list">
              {tab_rows}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── STATUS BAR ──────────────────────────────────────────── -->
    <div class="statusbar">
      <span class="sb-accent">● KOHALA</span>
      <span>branch: <span style="color:var(--text-2)">Yibb</span></span>
      <span>tests: <span class="sb-ok">931 passed</span></span>
      <span>health: <span class="sb-ok">Grade A</span></span>
      <span class="spacer"></span>
      <span class="blink">READY_</span>
    </div>
  </div>

  <div class="controls">
    <button id="btn-toggle-side">Toggle Sidebar</button>
    <button id="btn-replay">Replay</button>
  </div>

<script>
  // ── Count-up animation for Scaffold Health values ──
  function runCountUps() {{
    document.querySelectorAll(".stat-val").forEach((el) => {{
      const target = parseInt(el.dataset.target, 10);
      if (isNaN(target)) return;
      const dur = 900 + Math.random() * 400;
      const start = performance.now();
      el.textContent = "0";
      function tick(now) {{
        const t = Math.min(1, (now - start) / dur);
        const eased = 1 - Math.pow(1 - t, 3);
        el.textContent = Math.round(target * eased).toString();
        if (t < 1) requestAnimationFrame(tick);
      }}
      requestAnimationFrame(tick);
    }});
  }}
  setTimeout(runCountUps, 900);

  // ── Sidebar toggle ──
  document.getElementById("btn-toggle-side").addEventListener("click", () => {{
    document.body.classList.toggle("collapsed");
  }});

  // ── Replay animations ──
  document.getElementById("btn-replay").addEventListener("click", () => {{
    const win = document.querySelector(".window");
    const clone = win.cloneNode(true);
    win.parentNode.replaceChild(clone, win);
    setTimeout(runCountUps, 900);
  }});
</script>
</body>
</html>
"""


def main() -> int:
    out = Path(__file__).resolve().parent / "terragraf_preview.html"
    out.write_text(html_doc(), encoding="utf-8")
    print(f"wrote {out}  ({out.stat().st_size:,} bytes)")
    if "--no-open" not in sys.argv:
        url = out.as_uri()
        print(f"opening {url}")
        try:
            webbrowser.open(url)
        except Exception as e:  # pragma: no cover
            print(f"(could not auto-open browser: {e})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
