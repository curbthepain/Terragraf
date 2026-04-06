"""
Terragraf Kohala UI — animated browser preview.

Self-contained stdlib Python script that renders an animated HTML mockup
of the Terragraf workspace window, faithful to
``additions/terragraf_preview.py`` + ``additions/kohala_theme.qss``
(floating-card sidebar + topbar, warm-glass panels, red section
eyebrows, red gradient dividers, glowing WELCOME workspace pill,
TERRA/GRAF wordmark, red mono footer).

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


# ── Mock data (matches terragraf_preview.py) ───────────────────────────
HEALTH_STATS = [
    ("Header files",      "12"),
    ("Modules",           "23"),
    ("Route files",       "3"),
    ("Routes",            "204"),
    ("Table files",       "3"),
    ("Queue pending",     "0"),
    ("Queue running",     "1"),
    ("HOT_CONTEXT lines", "457"),
    ("Recent events",     "0"),
]

RECENT_TABS = [
    # (name, slug, state, is_active)
    ("Welcome", "welcome · 523434", "ACTIVE", True),
    ("Modules", "modules · 511298", "RECENT", False),
    ("Routes",  "routes · 488221",  "RECENT", False),
]

# Sidebar nav items: (icon, label, checked). Mirrors the real preview
# layout, including the two visual groups separated by a gap.
NAV_ITEMS = [
    ("+",  "New Native",   True),
    ("\u25A2", "New External", False),   # ▢
    ("\u25A2", "New Project\u2026", False),
    None,  # gap
    ("\u2665", "Health Check", False),   # ♥
    ("\u25C9", "Status",       False),   # ◉
    ("\u25C9", "Mode",         False),
    ("\u2713", "Scan",         False),   # ✓
    ("\u2261", "Knowledge",    False),   # ≡
    None,  # gap
    ("\u2699", "Settings",     False),   # ⚙
]


def html_doc() -> str:
    health_cells = "\n".join(
        f'''
        <div class="stat-row" style="--i:{i}">
          <span class="stat-key">\u2014 {k.upper()}</span>
          <span class="stat-compact" data-target="{v}">0</span>
        </div>'''
        for i, (k, v) in enumerate(HEALTH_STATS)
    )

    tab_rows = "\n".join(
        f'''
        <div class="tab-row{' active' if active else ''}" style="--i:{i}">
          <span class="dot"></span>
          <span class="tab-name">{name.upper()}</span>
          <span class="tab-slug">{slug}</span>
          <span class="tab-state">{state}</span>
        </div>'''
        for i, (name, slug, state, active) in enumerate(RECENT_TABS)
    )

    nav_html_parts: list[str] = []
    i = 0
    for item in NAV_ITEMS:
        if item is None:
            nav_html_parts.append('<div class="nav-gap"></div>')
            continue
        icon, text, checked = item
        cls = "nav-item checked" if checked else "nav-item"
        nav_html_parts.append(
            f'<button class="{cls}" style="--i:{i}">'
            f'<span class="nav-ico">{icon}</span>'
            f'<span class="nav-text">{text.upper()}</span>'
            f'</button>'
        )
        i += 1
    nav_items_html = "\n        ".join(nav_html_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Terragraf \u2014 Kohala preview</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Barlow:wght@400;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  /* ── Palette constants from .scaffold/app/theme.py ─────────────── */
  :root {{
    --accent: #E83030;
    --accent-hi: #FF5040;
    --accent-lo: #C0221F;
    --text: #F0EDE6;
    --text-2: #B6C3D2;
    --text-dim: #6B7D90;
    --green: #6EE0B0;
    --card-radius: 18px;
    --topbar-radius: 14px;
    --font-ui: "Barlow","Segoe UI","Helvetica Neue",system-ui,sans-serif;
    --font-display: "Barlow Condensed","Barlow",sans-serif;
    --font-mono: "JetBrains Mono","Consolas",monospace;
  }}

  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; padding: 0;
    min-height: 100vh;
    color: var(--text);
    font-family: var(--font-ui);
    /* QMainWindow sunset gradient (top navy → bottom warm basalt) */
    background: linear-gradient(180deg,
        #060D17 0%,
        #060D17 50%,
        #070E19 68%,
        #0A0B12 80%,
        #0E0C11 88%,
        #130D10 94%,
        #180E0F 100%);
  }}

  /* ── Window shell ──────────────────────────────────────────────── */
  .window {{
    width: min(1440px, 96vw);
    min-height: min(820px, 92vh);
    margin: 3vh auto;
    padding: 14px 16px 6px;
    display: flex; flex-direction: column; gap: 10px;
    animation: fadeUp .9s cubic-bezier(.2,.8,.2,1) both;
  }}
  @keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(14px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}

  .row-body {{
    display: grid;
    grid-template-columns: 258px 1fr;
    gap: 14px;
    flex: 1; min-height: 0;
  }}
  .col-right {{
    display: flex; flex-direction: column; gap: 12px;
    min-width: 0;
  }}

  /* ── Warm-glass card material (sidebar / topbar / panel) ──────── */
  .card-material {{
    background: linear-gradient(180deg,
        rgba(26, 42, 64, 0.88) 0%,
        rgba(20, 34, 54, 0.87) 4%,
        rgba(12, 22, 38, 0.84) 55%,
        rgba(6,  12, 22, 0.82) 100%);
    border: 1px solid rgba(255,255,255,0.10);
    border-top: 1px solid rgba(255,240,220,0.22);
    border-bottom: 1px solid rgba(0,0,0,0.40);
    box-shadow:
      0 20px 50px rgba(0,0,0,0.45),
      inset 0 1px 0 rgba(255,240,220,0.06);
  }}

  /* ── Sidebar ───────────────────────────────────────────────────── */
  .sidebar {{
    border-radius: var(--card-radius);
    padding: 22px 18px 18px 18px;
    display: flex; flex-direction: column;
    animation: slideRight .8s cubic-bezier(.2,.8,.2,1) .15s both;
  }}
  @keyframes slideRight {{
    from {{ opacity: 0; transform: translateX(-14px); }}
    to   {{ opacity: 1; transform: translateX(0); }}
  }}
  .sidebar-header {{
    font-family: var(--font-mono);
    font-size: 10px; font-weight: 700;
    color: var(--accent);
    letter-spacing: 2.5px;
    padding: 0 4px 10px;
  }}
  .nav-gap {{ height: 8px; }}
  .nav-item {{
    display: flex; align-items: center; gap: 12px;
    width: 100%;
    height: 36px;
    padding: 10px 14px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
    color: var(--text-2);
    font-family: var(--font-ui);
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.4px;
    text-align: left;
    cursor: pointer;
    animation: fadeLeft .55s ease both;
    animation-delay: calc(var(--i,0) * 55ms + .4s);
    transition: background .18s, border-color .18s, color .18s, transform .18s;
  }}
  @keyframes fadeLeft {{
    from {{ opacity: 0; transform: translateX(-8px); }}
    to   {{ opacity: 1; transform: translateX(0); }}
  }}
  .nav-item .nav-ico {{
    display: inline-block;
    width: 18px; text-align: center;
    font-family: "Segoe UI Symbol","Segoe UI",sans-serif;
    font-size: 15px;
    color: #C6D2E0;
  }}
  .nav-item:hover {{
    background: linear-gradient(180deg,
        rgba(28, 44, 66, 0.80) 0%,
        rgba(10, 20, 36, 0.86) 100%);
    border: 1px solid rgba(255,255,255,0.10);
    border-top: 1px solid rgba(255,240,220,0.20);
    color: var(--text);
  }}
  .nav-item.checked {{
    background: linear-gradient(180deg,
        rgba(80, 18, 20, 0.90) 0%,
        rgba(50, 12, 14, 0.92) 50%,
        rgba(28, 8,  12, 0.95) 100%);
    border: 1px solid rgba(232,48,48,0.50);
    border-top: 1px solid rgba(255,140,120,0.55);
    color: #FFFFFF;
    box-shadow: 0 0 24px rgba(232,48,48,0.20);
  }}
  .nav-item.checked .nav-ico {{ color: #FFFFFF; }}

  .sidebar-stretch {{ flex: 1; }}
  .ws-divider {{
    height: 1px;
    background: linear-gradient(90deg,
        transparent 0%,
        rgba(232,48,48,0.10) 15%,
        rgba(232,48,48,0.45) 50%,
        rgba(232,48,48,0.10) 85%,
        transparent 100%);
    margin: 10px 0;
  }}
  .ws-footer-row {{
    display: flex; align-items: center; gap: 8px;
    padding: 0 2px;
  }}
  .ws-footer-row .spacer {{ flex: 1; }}
  .hint {{
    color: var(--text-dim);
    font-size: 11px;
    font-family: var(--font-mono);
    letter-spacing: 0.5px;
  }}

  /* ── Top bar ──────────────────────────────────────────────────── */
  .topbar {{
    height: 58px;
    border-radius: var(--topbar-radius);
    padding: 10px 24px 10px 14px;
    display: flex; align-items: center; gap: 10px;
    animation: fadeDown .8s cubic-bezier(.2,.8,.2,1) .2s both;
  }}
  @keyframes fadeDown {{
    from {{ opacity: 0; transform: translateY(-10px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
  .iconbtn {{
    width: 38px; height: 32px;
    display: inline-flex; align-items: center; justify-content: center;
    background: linear-gradient(180deg,
        rgba(28, 44, 66, 0.86) 0%,
        rgba(8,  18, 32, 0.91) 100%);
    border: 1px solid rgba(255,255,255,0.10);
    border-top: 1px solid rgba(255,240,220,0.22);
    border-bottom: 1px solid rgba(0,0,0,0.34);
    border-radius: 10px;
    color: var(--text-2);
    font-size: 14px;
    cursor: pointer;
    transition: border-color .15s, color .15s;
  }}
  .iconbtn:hover {{
    color: #FFFFFF;
    border-top-color: rgba(255,240,220,0.32);
  }}
  .ws-tab {{
    min-height: 34px;
    padding: 8px 22px;
    background: linear-gradient(180deg,
        rgba(80, 18, 20, 0.92) 0%,
        rgba(50, 12, 14, 0.94) 50%,
        rgba(28, 8, 12, 0.96) 100%);
    border: 1px solid rgba(232,48,48,0.50);
    border-top: 1px solid rgba(255,140,120,0.55);
    border-bottom: 1px solid rgba(40,4,4,0.50);
    border-radius: 16px;
    color: #FFFFFF;
    font-family: var(--font-display);
    font-weight: 800;
    font-size: 12px;
    letter-spacing: 1.8px;
    cursor: pointer;
    box-shadow: 0 0 32px rgba(232,48,48,0.28),
                inset 0 1px 0 rgba(255,180,160,0.35);
    animation: glowPulse 3.6s ease-in-out infinite;
  }}
  @keyframes glowPulse {{
    0%,100% {{ box-shadow: 0 0 26px rgba(232,48,48,0.22),
                           inset 0 1px 0 rgba(255,180,160,0.30); }}
    50%     {{ box-shadow: 0 0 40px rgba(232,48,48,0.40),
                           inset 0 1px 0 rgba(255,200,180,0.45); }}
  }}
  .topbar .spacer {{ flex: 1; }}
  .brand-mark, .brand-mark-red {{
    font-family: var(--font-display);
    font-weight: 900;
    font-size: 18px;
    letter-spacing: 2px;
  }}
  .brand-mark {{ color: #FFFFFF; }}
  .brand-mark-red {{ color: var(--accent); margin-left: -6px; }}

  /* ── Main content row (Health + Recent Tabs) ──────────────────── */
  .hs-row {{
    display: grid;
    grid-template-columns: 3fr 2fr;
    gap: 14px;
    flex: 1; min-height: 0;
  }}
  .panel {{
    border-radius: var(--card-radius);
    padding: 20px 24px;
    display: flex; flex-direction: column;
    animation: panelIn .95s cubic-bezier(.2,.8,.2,1) both;
    min-height: 0;
  }}
  .panel.p-health   {{ animation-delay: .40s; }}
  .panel.p-sessions {{ animation-delay: .55s; }}
  @keyframes panelIn {{
    from {{ opacity: 0; transform: translateY(18px) scale(.985); }}
    to   {{ opacity: 1; transform: translateY(0) scale(1); }}
  }}
  .section-sub {{
    font-family: var(--font-mono);
    font-size: 10px; font-weight: 700;
    color: var(--accent);
    letter-spacing: 2.5px;
    padding-bottom: 6px;
  }}
  .panel .ws-divider {{ margin: 0 0 10px; }}

  /* Scaffold Health 3×3 grid of stat rows */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    column-gap: 28px;
    row-gap: 8px;
    flex: 1;
  }}
  .stat-row {{
    display: flex; align-items: center;
    padding: 2px 0;
    animation: fadeUp .55s ease both;
    animation-delay: calc(var(--i,0) * 55ms + .85s);
  }}
  .stat-row .stat-key {{
    font-family: var(--font-mono);
    font-size: 10px; font-weight: 700;
    color: var(--accent);
    letter-spacing: 1.8px;
  }}
  .stat-row .stat-compact {{
    flex: 1; text-align: right;
    font-family: var(--font-display);
    font-size: 15px; font-weight: 800;
    color: #FFFFFF;
    letter-spacing: 0.5px;
  }}

  /* Recent Tabs list */
  .tabs-list {{ display: flex; flex-direction: column; gap: 2px; }}
  .tab-row {{
    display: grid;
    grid-template-columns: 14px auto 1fr auto;
    align-items: center;
    gap: 12px;
    padding: 6px 0;
    animation: fadeLeft .55s ease both;
    animation-delay: calc(var(--i,0) * 80ms + 1.0s);
  }}
  .tab-row .dot {{
    width: 10px; height: 10px; border-radius: 50%;
    background: #8FA0B6;
    box-shadow: 0 0 0 0 rgba(0,0,0,0);
  }}
  .tab-row.active .dot {{
    background: var(--green);
    animation: dotPulse 1.9s ease-in-out infinite;
  }}
  @keyframes dotPulse {{
    0%,100% {{ box-shadow: 0 0 0 0 rgba(110,224,176,0.55); }}
    50%     {{ box-shadow: 0 0 0 7px rgba(110,224,176,0); }}
  }}
  .tab-row .tab-name {{
    font-family: var(--font-display);
    font-size: 15px; font-weight: 800;
    color: #FFFFFF;
    letter-spacing: 0.5px;
  }}
  .tab-row .tab-slug {{
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-dim);
    letter-spacing: 0.5px;
  }}
  .tab-row .tab-state {{
    font-family: var(--font-mono);
    font-size: 10px; font-weight: 700;
    color: var(--accent);
    letter-spacing: 1.8px;
  }}
  .tab-row.active .tab-state {{ color: var(--green); }}

  /* ── Footer (reuses topbar material) ───────────────────────────── */
  .footer {{
    height: 44px;
    border-radius: var(--topbar-radius);
    padding: 8px 24px;
    display: flex; align-items: center; justify-content: center;
    animation: fadeUp .9s ease 1.2s both;
  }}
  .footer-text {{
    color: var(--accent);
    font-family: var(--font-mono);
    font-size: 10px; font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    text-shadow: 0 0 12px rgba(232,48,48,0.45);
    animation: footerFlicker 5s ease-in-out infinite;
  }}
  @keyframes footerFlicker {{
    0%, 92%, 100% {{ opacity: 1; }}
    94% {{ opacity: 0.55; }}
    96% {{ opacity: 1; }}
  }}

  /* ── Floating controls ─────────────────────────────────────────── */
  .controls {{
    position: fixed; bottom: 18px; right: 22px;
    display: flex; gap: 8px;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    z-index: 50;
  }}
  .controls button {{
    background: rgba(14,26,46,0.82);
    color: var(--text-2);
    border: 1px solid rgba(255,255,255,0.10);
    border-top: 1px solid rgba(255,240,220,0.22);
    padding: 8px 14px;
    border-radius: 10px;
    cursor: pointer;
    backdrop-filter: blur(6px);
    font-weight: 700;
  }}
  .controls button:hover {{
    color: #FFFFFF;
    border-color: rgba(232,48,48,0.45);
    box-shadow: 0 0 18px rgba(232,48,48,0.30);
  }}
</style>
</head>
<body>
  <div class="window">

    <div class="row-body">

      <!-- ── SIDEBAR ───────────────────────────────────────────── -->
      <div class="sidebar card-material">
        <div class="sidebar-header">\u2014 WELCOME \u2014</div>
        {nav_items_html}
        <div class="sidebar-stretch"></div>
        <div class="ws-divider"></div>
        <div class="ws-footer-row">
          <span class="sidebar-header" style="padding:0;">\u2014 WORKSPACE //</span>
          <span class="spacer"></span>
          <span class="hint">v0.4.2</span>
        </div>
      </div>

      <!-- ── RIGHT COLUMN ──────────────────────────────────────── -->
      <div class="col-right">

        <!-- Top bar -->
        <div class="topbar card-material">
          <button class="iconbtn">\u2261</button>
          <button class="iconbtn">\u25A3</button>
          <button class="ws-tab">WELCOME</button>
          <div class="spacer"></div>
          <span class="brand-mark">TERRA</span>
          <span class="brand-mark-red">GRAF</span>
        </div>

        <!-- Health + Recent Tabs -->
        <div class="hs-row">
          <div class="panel p-health card-material">
            <div class="section-sub">\u2014 SCAFFOLD HEALTH</div>
            <div class="ws-divider"></div>
            <div class="stats-grid">
              {health_cells}
            </div>
          </div>

          <div class="panel p-sessions card-material">
            <div class="section-sub">\u2014 RECENT TABS</div>
            <div class="ws-divider"></div>
            <div class="tabs-list">
              {tab_rows}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── FOOTER ──────────────────────────────────────────────── -->
    <div class="footer card-material">
      <div class="footer-text">
        BRIDGE: OFFLINE &nbsp;&nbsp;\u00B7&nbsp;&nbsp; 1 SESSION &nbsp;&nbsp;\u00B7&nbsp;&nbsp; PATENT PENDING
      </div>
    </div>
  </div>

  <div class="controls">
    <button id="btn-replay">Replay Animations</button>
  </div>

<script>
  // ── Count-up animation for Scaffold Health values ──
  function runCountUps() {{
    document.querySelectorAll(".stat-compact[data-target]").forEach((el) => {{
      const target = parseInt(el.dataset.target, 10);
      if (isNaN(target)) return;
      const dur = 850 + Math.random() * 500;
      const start = performance.now() + 850;  // wait for stat-row fadeUp
      el.textContent = "0";
      function tick(now) {{
        const t = Math.min(1, Math.max(0, (now - start) / dur));
        const eased = 1 - Math.pow(1 - t, 3);
        el.textContent = Math.round(target * eased).toString();
        if (t < 1) requestAnimationFrame(tick);
      }}
      requestAnimationFrame(tick);
    }});
  }}
  runCountUps();

  // ── Replay ──
  document.getElementById("btn-replay").addEventListener("click", () => {{
    const win = document.querySelector(".window");
    const clone = win.cloneNode(true);
    win.parentNode.replaceChild(clone, win);
    runCountUps();
  }});

  // ── Nav item click → toggle checked state (visual only) ──
  document.addEventListener("click", (e) => {{
    const t = e.target.closest(".nav-item");
    if (!t) return;
    document.querySelectorAll(".nav-item.checked").forEach(n => n.classList.remove("checked"));
    t.classList.add("checked");
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
