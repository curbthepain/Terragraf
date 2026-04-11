# Qt Knowledge Base

Reference material on Qt 6.11 / PySide6 animation, effects,
stylesheets, state machines, and custom painting. Curated from
official Qt 6.11 docs, PySide6 docs, and resolved community
threads. Each file is the consolidated, PySide6-translated,
gotcha-aware working reference for its topic.

## Index

| File | Topic | Load when working on... |
|------|-------|-------------------------|
| `01_animation_framework.md` | `QPropertyAnimation`, `QParallelAnimationGroup`, `QSequentialAnimationGroup`, `QEasingCurve`, motion tokens, reduced-motion, interruptible animations, Qt 6.11 release notes | Any property tween, chained animations, easing choice, motion design, accessibility |
| `02_abstract_variant_animation.md` | `QAbstractAnimation` (states, loops, direction, `DeletionPolicy`), `QVariantAnimation` (key frames, custom interpolators, subclass vs signal), staggered list entrance pattern | Custom animation classes, key frames, scrubbing, time-driven behaviour without property binding, list entrance orchestration |
| `03_opacity_effect_and_fade.md` | `QGraphicsEffect` base class, `QGraphicsOpacityEffect` fade patterns, `QGraphicsDropShadowEffect` + animated elevation on hover, `QGraphicsBlurEffect`, `QGraphicsColorizeEffect`, effect/shadow exclusivity workaround | Fade-in/out of child widgets, card elevation, hover lift, gradient masks, custom `QGraphicsEffect` subclasses |
| `04_qss_dynamic_properties.md` | QSS `[class="x"]` attribute selectors, `qproperty-*` write-only syntax, the `palette(window)` trap, 4 escape hatches for dynamic colors, `Q_PROPERTY` + palette color animation pattern, `widget-animation-duration: 0` kill switch | Any stylesheet work, dynamic theming, smooth color animation without re-parsing QSS, reduced-motion override |
| `05_state_machine.md` | `QStateMachine` C++/Python path (`assignProperty`, `addDefaultAnimation`, error enums) + QML `states` / `transitions` / `Behavior` path, wildcard transitions, reversible transitions | 3+ visual states with many property changes, guaranteed consistent configurations, declarative property changes instead of imperative animations |
| `06_painter_custom_paint.md` | Custom `paintEvent` + `Q_PROPERTY` pattern (the `ProgressRing` idiom), task-oriented `QPainter` API summary, high-DPI pen cosmetic mode, `update()` vs `repaint()`, Qt 6.11 Canvas Painter comparison | Custom-painted widgets, progress rings, gauges, morphing icons, anything QSS cannot express |
| `07_qt_quick_escape_hatch.md` | `Behavior`, `Transition`, `Animator` (render-thread), `SpringAnimation`, Material/Universal/Fusion styles, `QQuickWidget` embedding, widgets vs QML decision table | Comparing widget animation to QML equivalents, embedding a single animated surface, future decisions about moving off widgets |

## How to use this in a Qt/UX session

Before editing any Qt-related code:

1. `Read .scaffold/docs/qt/README.md` (this file) to see what's covered.
2. `Read` the specific topic file(s) for the problem at hand.
3. Pattern-match against the gotchas section BEFORE writing new code.
4. If you hit a new pattern or gotcha not covered here, add it to the
   relevant topic file so the next session is faster.

## Source files (local only — not committed)

Raw Qt 6.11 documentation exports live alongside the `.md`
consolidations as `.txt` / `.rtf` files. They are **gitignored**
(`.scaffold/docs/qt/*.txt`, `.scaffold/docs/qt/*.rtf`) — the `.md`
files are the tracked source of truth. The raw docs are kept locally
for traceability: if a consolidated `.md` seems wrong, the raw
source is two files over.

Coverage:
- `QAbstractAnimation Class.txt`
- `QVariantAnimation Class.txt`
- `QEasingCurve Class.txt`
- `QSequentialAnimationGroup Class.txt`
- `QGraphicsEffect Class.txt`
- `QGraphicsOpacityEffect Class.txt` + `PySide6.QtWidgets.QGraphicsOpacityEffect.txt`
- `QGraphicsDropShadowEffect Class.txt`
- `QStateMachine Class.txt` + `QStateMachine Transition.txt`
- `QPainter Class.txt`
- `Qt read dynamic qproperties in stylesheets.txt` (Stack Overflow thread)
- `QtHoverTransitionsAnimations.rtf` (research source for the motion
  token and reduced-motion material in topic 01)

## To be added (as material arrives)

- `QGraphicsBlurEffect` + `QGraphicsColorizeEffect` deep-dive
  (currently stub-level in topic 03)
- High-DPI font metrics, baseline alignment, and crisp-pixel rules
- Performance profiling: when does an animation drop frames and
  why; `QGraphicsEffect` rasterisation cost at scale
- `QGraphicsScene` animation at scale (1000+ items) — batching,
  `ItemIgnoresTransformations`, LOD
- Qt Quick 3D motion system, if Terragraf ever touches it
