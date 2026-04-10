# Qt Animation Framework — Reference

> Source: Qt 6.11 official C++ docs. PySide6 mirrors the API 1:1 — translate
> `QPropertyAnimation(button, "pos", this)` → `QPropertyAnimation(button, b"pos", self)`.
> Property names are `bytes` in Python (`b"pos"`, `b"geometry"`, `b"windowOpacity"`).

---

## QPropertyAnimation

Animates a single Qt property over time. Inherits `QVariantAnimation`.
Supports any property whose type is a registered `QVariant`
(int, qreal, QPoint, QSize, QRect, QColor, QFont, …).

### Requirements
- Target must be a `QObject` subclass.
- The property must have a **setter** (so the animation can write the
  interpolated value back).

### Constructors
```cpp
QPropertyAnimation(QObject *parent = nullptr);
QPropertyAnimation(QObject *target, const QByteArray &propertyName, QObject *parent = nullptr);
```

### Canonical example (C++)
```cpp
QPushButton *button = new QPushButton(tr("Animated Button"), this);
QPropertyAnimation *anim = new QPropertyAnimation(button, "pos", this);
anim->setDuration(10000);
anim->setStartValue(QPoint(0, 0));
anim->setEndValue(QPoint(100, 250));
anim->start();
```

### PySide6 equivalent
```python
from PySide6.QtCore import QPropertyAnimation, QPoint
from PySide6.QtWidgets import QPushButton

button = QPushButton("Animated Button", self)
anim = QPropertyAnimation(button, b"pos", self)   # parent=self keeps it alive
anim.setDuration(10000)
anim.setStartValue(QPoint(0, 0))
anim.setEndValue(QPoint(100, 250))
anim.start()
```

### Key behaviours
- **Default duration**: 250 ms when constructed with the
  `(target, propertyName, parent)` form.
- **Implicit start value**: if `setStartValue` is omitted, the animation
  uses whatever the property reads at the moment the state transitions
  Stopped → Running. Useful for "animate from current to X".
- **Lifetime**: the animation is a `QObject`. Pass a `parent` (or store
  it on `self`) — otherwise Python GC eats it mid-animation and the
  animation silently stops.
- **Delete-on-stop policy**: `anim.start(QAbstractAnimation.DeleteWhenStopped)`
  for fire-and-forget animations.

### Properties (bindable)
- `propertyName : QByteArray`  — must be set before start
- `targetObject : QObject*`    — must be set before start

### Reimplemented hooks
- `updateCurrentValue(value)` — called every tick with the interpolated value
- `updateState(newState, oldState)` — captures the implicit start value on Stopped→Running

---

## QParallelAnimationGroup

Container that runs all child animations **at the same time**. Group
finishes when the longest-lasting child finishes. Inherits
`QAnimationGroup`.

```cpp
QParallelAnimationGroup *group = new QParallelAnimationGroup;
group->addAnimation(anim1);
group->addAnimation(anim2);
group->start();
```

### PySide6
```python
from PySide6.QtCore import QParallelAnimationGroup, QPropertyAnimation

group = QParallelAnimationGroup(self)
group.addAnimation(fade_anim)
group.addAnimation(slide_anim)
group.start()
```

### Use cases
- Fade + slide simultaneously (opacity + geometry).
- Animate multiple widgets entering at once.
- Group reusable as a child of another `QSequentialAnimationGroup`.

### Behaviour notes
- `duration()` returns `max(child.duration() for child in children)`.
- Pause/resume/stop apply to all children.
- Adding the same animation to two groups is undefined — don't.
- The group **takes ownership** of added animations (they get reparented).

---

## QSequentialAnimationGroup

Container that runs children **one after another**, in insertion order.
Group finishes when the last child finishes.

```cpp
QSequentialAnimationGroup *group = new QSequentialAnimationGroup;
group->addAnimation(anim1);
group->addAnimation(anim2);
group->start();
```

### PySide6
```python
from PySide6.QtCore import QSequentialAnimationGroup

group = QSequentialAnimationGroup(self)
group.addAnimation(slide_in)
group.addPause(200)               # 200ms hold
group.addAnimation(fade_out)
group.start()
```

### Extras
- `addPause(msecs) -> QPauseAnimation` — explicit gap between steps.
- `insertPause(index, msecs)` — insert pause at a position.
- `currentAnimation` property + `currentAnimationChanged(QAbstractAnimation*)`
  signal — handy for "highlight the active step" UIs.
- `duration()` returns `sum(child.duration() for child in children)`.
- Each child runs to completion before the next starts; there's no overlap.

### Composing groups
You can nest: a `QParallelAnimationGroup` inside a
`QSequentialAnimationGroup` (or vice-versa). This is how you express
"slide three rows in one after another, but each row's slide+fade
happen together":

```python
sequence = QSequentialAnimationGroup(self)
for row in rows:
    parallel = QParallelAnimationGroup(sequence)
    parallel.addAnimation(make_slide(row))
    parallel.addAnimation(make_fade(row))
    sequence.addAnimation(parallel)
sequence.start()
```

---

## QEasingCurve

Controls the *shape* of interpolation between start and end. Default is
`Linear` (constant velocity), which almost always feels wrong for UI.

```python
from PySide6.QtCore import QEasingCurve, QPropertyAnimation

anim = QPropertyAnimation(widget, b"geometry", self)
anim.setDuration(1000)
anim.setEasingCurve(QEasingCurve.InOutQuad)
```

### When to use which curve (UI motion design heuristics)

| Intent                              | Curve              | Why                                              |
|-------------------------------------|--------------------|--------------------------------------------------|
| Element enters the screen           | `OutQuad` / `OutCubic` | Decelerates into place — feels "settled"     |
| Element exits the screen            | `InQuad` / `InCubic`   | Accelerates away — feels "purposeful"        |
| Mid-screen state change (resize, reposition) | `InOutQuad` / `InOutCubic` | Symmetric — feels balanced       |
| Emphasis / attention grab           | `OutBack`          | Slight overshoot then settles — playful          |
| Spring / bounce (notifications)     | `OutElastic` / `OutBounce` | Mechanical — use sparingly, can feel cheap |
| Material-design "standard"          | `InOutCubic` (close enough) | Matches Google's standard curve            |
| Dragging release / inertia          | `OutQuint`         | Strong deceleration — mimics physics             |
| Linear (rare in UI)                 | `Linear`           | Only for progress bars, loading spinners         |

### Curve families
Each family comes in four flavours:
- **InX**     — accelerate from zero
- **OutX**    — decelerate to zero
- **InOutX**  — accelerate then decelerate (full S-curve)
- **OutInX**  — decelerate then accelerate (rare; "valley" shape)

Families by aggressiveness (gentle → aggressive):
1. `Sine`   — softest, almost imperceptible
2. `Quad`   — t² — UI default if unsure
3. `Cubic`  — t³ — slightly snappier
4. `Quart`  — t⁴ — punchy
5. `Quint`  — t⁵ — very punchy, near-instant late
6. `Expo`   — 2ᵗ — extreme; slow start, blistering end
7. `Circ`   — circular — geometric, sharp
8. `Back`   — overshoots past the endpoint then returns (param: `overshoot`)
9. `Elastic`— spring-like, oscillates (params: `amplitude`, `period`)
10. `Bounce`— parabolic bounces

### Tunable parameters
- `setAmplitude(qreal)` — only for `Elastic` and `Bounce`. Higher = bigger swing.
- `setOvershoot(qreal)` — only for `Back` family. Higher = more overshoot past target.
- `setPeriod(qreal)` — only for `Elastic`. Higher = slower oscillation.

### Custom curves
- **Cubic Bezier**: `addCubicBezierSegment(c1, c2, endPoint)` — chain
  segments to define a custom curve via control points.
- **TCB spline**: `addTCBSegment(nextPoint, t, c, b)` — Tension-Continuity-Bias
  spline; `t`/`c`/`b` are -1.0..1.0 shape parameters.
- **Function pointer**: `setCustomType(func)` — pass a free function
  `qreal(qreal progress)` for full control. PySide6 supports a Python
  callable here.

### Inspecting a curve
```python
curve = QEasingCurve(QEasingCurve.InOutQuad)
for t in [i/10 for i in range(11)]:
    print(t, curve.valueForProgress(t))
```
`valueForProgress(0.0)` → 0.0, `valueForProgress(1.0)` → 1.0, everything
in between is shaped by the curve.

---

## Cross-cutting gotchas (these will bite us in Terragraf specifically)

1. **Parent or die**. In PySide6, animations without a parent get
   garbage-collected the instant the local variable goes out of scope.
   Always pass `parent=self` or store on the widget. The C++ examples
   above pass `this` for the same reason.

2. **`bytes` not `str` for property names**. `QPropertyAnimation(w, "pos")`
   raises `TypeError` in PySide6 — must be `b"pos"`.

3. **Geometry vs pos**. Animating `b"geometry"` (a `QRect`) gives full
   move + resize; animating `b"pos"` (a `QPoint`) only moves. Layouts
   will fight `b"pos"` on a laid-out widget — the layout snaps it back
   on the next layout pass. Either:
   - Animate `b"geometry"` instead, or
   - Take the widget out of its layout (`layout.removeWidget` then
     reinsert after), or
   - Animate a property the layout doesn't touch (`b"windowOpacity"`,
     `b"maximumHeight"`, a custom property).

4. **`b"windowOpacity"` only works on top-level windows**. For child
   widgets, use a `QGraphicsOpacityEffect` and animate its `b"opacity"`
   property instead. Note that `QGraphicsOpacityEffect` cannot be
   combined with `QGraphicsDropShadowEffect` on the same widget — Qt
   only allows one effect at a time per widget.

5. **`maximumHeight` / `maximumWidth` trick for collapse animations**.
   To "fold" a widget into nothing without it re-laying-out weirdly,
   animate `b"maximumHeight"` from current → 0. The widget collapses,
   layout reflows around the shrinking value.

6. **Easing curve choice matters more than duration**. A 200ms
   `OutCubic` feels faster *and better* than a 150ms `Linear`. When
   tuning UI motion, change the curve before reaching for the duration.

7. **Group ownership**. `group.addAnimation(anim)` reparents `anim`
   to the group. If the group is destroyed, the child animation goes
   with it. Don't keep a separate reference and expect to outlive the
   group.

8. **One-shot animations**: use
   `anim.start(QAbstractAnimation.DeleteWhenStopped)` so the animation
   cleans itself up after firing. Otherwise it lives until its parent
   does, accumulating memory if you create them in a hot path.

---

## What Qt 6.11 adds (for context)

Qt 6.11 (March 2026) is an intermediate release. Items that touch the
animation/effect/styling stack:

- **Qt Canvas Painter** — new hardware-accelerated 2D painter on RHI
  (OpenGL / Vulkan / Metal / D3D). Benchmarks ~2× `QPainter` on
  desktop OpenGL, ~5–10× on mobile. Consider for heavy per-frame
  custom-painted widgets; see `06_painter_custom_paint.md`.
- **Qt Labs StyleKit** (technology preview) — declarative styling for
  Qt Quick Controls with design-token flow and motion as a
  first-class token. Covered in `07_qt_quick_escape_hatch.md`.
- **Qt Lottie** — path fill rules, shape morphing, matte layers,
  shapes-along-paths. Bigger slice of AE files now renders.
- **Qt SVG** — parses CSS `offset-path` / `offset-distance` and the
  standard timing functions for SVG-embedded animations. Does **not**
  extend to QSS.
- **Qt Quick Effects** — `RectangularShadow` per-corner radii.
- **Flickable** — `positionViewAtChild`, `flickToChild`, `flickTo`
  animated scrolling helpers.

What 6.11 did **not** add: CSS-style transitions to QSS. The
transition gap covered in `04_qss_dynamic_properties.md` is the same
in 6.11 as it was in 5.6.

---

## Motion tokens — recommended defaults

Coherence comes from reuse. Put these in one module and reference
them everywhere instead of hardcoding numbers. Calibrated against
Material 3 / Carbon / Apple HIG recommendations.

```python
# app/motion.py
from PySide6.QtCore import QEasingCurve

class Motion:
    # Durations (ms)
    MICRO     = 120   # button press, toggle flip, checkbox
    FAST      = 180   # hover, small local transition
    STANDARD  = 240   # default local transition (menu, dropdown)
    SLOW      = 320   # view transition (drawer, panel slide)
    EXTRA_SLOW = 480  # full-screen or modal

    # Easing curves
    ENTER    = QEasingCurve.Type.OutCubic   # things appearing
    EXIT     = QEasingCurve.Type.InCubic    # things leaving
    EMPHASIS = QEasingCurve.Type.InOutCubic # on-screen motion
    POP      = QEasingCurve.Type.OutBack    # attention moments
```

Duration bands (from UX research, widely agreed):

| Band              | Range       | Example                                |
|-------------------|-------------|----------------------------------------|
| Micro-interaction | 100–200 ms  | Button press, toggle, checkbox         |
| Local transition  | 200–300 ms  | Menu open, dropdown, tooltip, card flip |
| View transition   | 300–500 ms  | Drawer slide, tab switch, detail panel |
| Large surface     | 500–700 ms  | Hero transition, full-screen modal     |

**Rules of thumb**:
- Exit should be slightly faster than entry (user has already seen it).
- `OutCubic` for entering elements, `InCubic` for exits,
  `InOutCubic` for on-screen reflows, `OutBack` for pop-ins that
  should feel "locked in place".
- Linear is almost always wrong for discrete state changes. Reserve
  it for spinners and determinate progress bars.
- Motion should scale with distance: 50px slides faster than 500px.
  Material's rule of thumb: duration ∝ √distance, clamped to bands.

---

## Reduced motion

A meaningful slice of users (~2–3%, higher in older demographics and
vestibular disorders) experience nausea or vertigo from UI motion.
WCAG 2.1 technique C39 covers this on the web via
`prefers-reduced-motion`; Qt does **not** expose a cross-platform
query for it. Roll our own:

```python
# app/motion.py (continued)
class MotionSettings:
    """Singleton. Multiply every animation duration by .scale before start()."""
    _instance = None
    _scale: float = 1.0

    @classmethod
    def instance(cls) -> "MotionSettings":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def scale(self) -> float:
        return self._scale

    def set_scale(self, s: float) -> None:
        self._scale = max(0.0, min(1.0, s))

    def scaled(self, ms: int) -> int:
        """Scale a duration by the current motion setting. 0 => instant."""
        return round(ms * self._scale)

# usage at the animation site:
anim.setDuration(MotionSettings.instance().scaled(Motion.FAST))
```

`set_scale(0.0)` collapses every animation to 0ms (instant).
`set_scale(0.3)` keeps a hint of motion but shrinks duration by 70%.

**Also kill built-in Qt style animations** (Fusion progress shimmer,
spinbox scroll, etc.) with the one-line QSS override:

```python
app.setStyleSheet("* { widget-animation-duration: 0; }")
```

Combine the two — `MotionSettings` for our animations,
`widget-animation-duration: 0` for Qt's — to cover the full surface.
The platform-specific OS query hooks (Windows
`SPI_GETCLIENTAREAANIMATION`, macOS
`accessibilityDisplayShouldReduceMotion`, GNOME `enable-animations`)
can feed `MotionSettings.set_scale` at startup if we ever care to
read the OS setting.

**Accessibility fallback**: if a user has reduced motion on, prefer
cross-fades to slides. Fades don't trigger vestibular symptoms;
translates do.

---

## Interruptible animations

Users cancel things mid-motion. A drawer half-open should close from
its current position, not snap to fully open first. The pattern:

```python
from PySide6.QtCore import QPropertyAnimation, QAbstractAnimation, QRect
from PySide6.QtCore import QEasingCurve
from PySide6.QtWidgets import QWidget

class Drawer(QWidget):
    def __init__(self, open_rect: QRect, closed_rect: QRect, parent=None):
        super().__init__(parent)
        self._open_rect = open_rect
        self._closed_rect = closed_rect
        self._current_anim: QPropertyAnimation | None = None

    def open(self) -> None:
        self._animate_to(self._open_rect)

    def close(self) -> None:
        self._animate_to(self._closed_rect)

    def _animate_to(self, target: QRect) -> None:
        if self._current_anim is not None and self._current_anim.state() == QAbstractAnimation.State.Running:
            self._current_anim.stop()     # no snap — we pick up from wherever we are

        anim = QPropertyAnimation(self, b"geometry", self)
        anim.setDuration(Motion.SLOW)
        # No setStartValue — let QPropertyAnimation read current geometry()
        anim.setEndValue(target)
        anim.setEasingCurve(Motion.ENTER)
        anim.finished.connect(lambda: setattr(self, "_current_anim", None))
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self._current_anim = anim
```

Key detail: **no `setStartValue`**. `QPropertyAnimation` reads the
current property value when it starts, so a mid-animation reversal
begins from the interrupted position, not the original start.
Setting `startValue` explicitly would cause the visible snap.
