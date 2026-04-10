# QGraphicsOpacityEffect + Fade Patterns

> Sources: Qt 6.11 C++ docs + PySide6 QtWidgets docs.

Fading child widgets is the single most common "obvious thing that
doesn't work" in Qt. This file covers the pattern end-to-end so we
don't keep hitting the same rake.

---

## The problem

```python
widget.setWindowOpacity(0.0)   # ❌ only works on top-level windows
```

`QWidget.setWindowOpacity` exists but it's **a window-manager property**
— it only applies to widgets that have a native OS window (top-level
windows, `Qt.Window`, `Qt.Tool`, `Qt.Dialog`). For any child widget
inside a layout, it's a silent no-op: the call succeeds, no error
raised, the widget stays fully opaque.

You also can't just animate `QColor alpha` in a stylesheet for the
same reason — stylesheets control paint output, not the widget's
compositing alpha, so children drawn on top still appear fully opaque.

---

## The solution: `QGraphicsOpacityEffect`

`QGraphicsEffect` is Qt's post-processing hook for a widget. The
`QGraphicsOpacityEffect` subclass blends the widget's rendered output
with the background at a given opacity. It works on any widget,
top-level or child, because it operates on the pixel output, not the
window system.

### Basic setup
```python
from PySide6.QtCore    import QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QGraphicsOpacityEffect

effect = QGraphicsOpacityEffect(widget)   # parent = widget
widget.setGraphicsEffect(effect)
effect.setOpacity(1.0)                    # 0.0 = transparent, 1.0 = opaque
```

The effect's `opacity` property is a `qreal` in `[0.0, 1.0]`. Default
is **0.7** (not 1.0 — surprising; always set it explicitly after
constructing).

### Animating the opacity
```python
fade = QPropertyAnimation(effect, b"opacity", widget)
fade.setDuration(220)
fade.setStartValue(0.0)
fade.setEndValue(1.0)
fade.setEasingCurve(QEasingCurve.OutCubic)
fade.start(QPropertyAnimation.DeleteWhenStopped)
```

Because `opacity` is a real `Q_PROPERTY` on `QGraphicsOpacityEffect`,
`QPropertyAnimation` drives it directly — no subclassing, no custom
interpolator.

### Fade-out + hide helper (idiomatic)
```python
def fade_out_and_hide(widget, duration_ms=220):
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        effect.setOpacity(1.0)

    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(effect.opacity())
    anim.setEndValue(0.0)
    anim.setEasingCurve(QEasingCurve.InQuad)
    anim.finished.connect(widget.hide)      # hide *after* fade completes
    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim
```

Note: we check for an existing effect first (in case the widget is
mid-fade or already has one) — calling `setGraphicsEffect` twice
replaces the first effect silently, which can interrupt a running
animation.

### Fade-in-from-hidden
```python
def fade_in(widget, duration_ms=220):
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    effect.setOpacity(0.0)                  # start transparent
    widget.show()                           # then show (no flash)

    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim
```

Order matters: `setOpacity(0)` **before** `show()`. Otherwise there's a
one-frame flash of the fully-opaque widget before the effect kicks in.

---

## Opacity masks (gradient fades)

`opacityMask` is a separate property that takes a `QBrush`. It lets you
apply **non-uniform** opacity — e.g. fade the top and bottom of a widget
to transparent for a "fade-to-edge" scroll overlay.

```python
from PySide6.QtCore    import Qt
from PySide6.QtGui     import QLinearGradient
from PySide6.QtWidgets import QGraphicsOpacityEffect

gradient = QLinearGradient(0, 0, 0, widget.height())   # vertical
gradient.setColorAt(0.0, Qt.transparent)               # top = faded
gradient.setColorAt(0.2, Qt.black)                     # body = visible
gradient.setColorAt(0.8, Qt.black)
gradient.setColorAt(1.0, Qt.transparent)               # bottom = faded

effect = QGraphicsOpacityEffect(widget)
effect.setOpacityMask(gradient)
widget.setGraphicsEffect(effect)
```

The color in the gradient is interpreted as alpha (only the alpha
channel matters for masking). `Qt.transparent` = 0, `Qt.black` = opaque.

---

## Critical gotchas

### 1. **Only one QGraphicsEffect per widget**
`QWidget.setGraphicsEffect(effect)` replaces any existing effect.
You can't stack `QGraphicsOpacityEffect` + `QGraphicsDropShadowEffect`
on the same widget — the second `setGraphicsEffect` call silently
drops the first.

**Workaround**: wrap the widget in a `QFrame`. Put the shadow on the
outer frame and the opacity on the inner widget (or vice versa).
```python
frame = QFrame(parent)          # shadow goes here
frame.setGraphicsEffect(drop_shadow_effect)
layout = QVBoxLayout(frame)
layout.addWidget(my_widget)     # opacity goes here
my_widget.setGraphicsEffect(opacity_effect)
```

### 2. **Performance — `QGraphicsEffect` forces CPU compositing**
The effect is applied by rasterising the widget to an offscreen
pixmap and blending it in `QPainter`. This means:
- Every paint of the widget goes through an extra CPU pass.
- GPU-accelerated paths (QOpenGLWidget inside the widget) fall back
  to software rendering under the effect.
- On high-DPI displays with large widgets, expect measurable FPS
  drop when effects are active.

**Mitigation**: only set the effect *during* the animation, then
remove it afterward:
```python
def fade_in_clean(widget, ms=220):
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    effect.setOpacity(0.0)
    widget.show()

    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    # Remove the effect when done so the widget paints fast again.
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    anim.start(QPropertyAnimation.DeleteWhenStopped)
```
Caveat: if the widget's final state is meant to be a non-1.0 opacity,
leave the effect attached — removing it restores full opacity.

### 3. **Default opacity is 0.7, not 1.0**
Always call `effect.setOpacity(1.0)` right after construction if you
want the widget fully visible at rest. Forgetting this gives a
"why is everything slightly dim?" bug that's hard to spot in
screenshots.

### 4. **Effects don't compose with `autoFillBackground`**
If the widget has `setAutoFillBackground(True)` and a palette
background, the opacity effect may render the background at the
wrong alpha on some styles. Workaround: set the widget's
`Qt.WA_TranslucentBackground` attribute, or use stylesheet
backgrounds instead of palette ones.

### 5. **Effects and Qt Style Sheets fight each other**
QSS paints the widget; the effect rasterises the result. Generally
this works, but:
- QSS `background: rgba(…)` inside an effect can double-blend (QSS
  alpha × effect opacity), producing unexpectedly dim results.
- Use either pure QSS transparency or pure effect opacity — not both.
  For a full widget fade, use the effect. For a translucent
  background that stays constant while children fade, use QSS on the
  parent and effects on the children.

### 6. **No z-ordering across effects**
If sibling widgets both have opacity effects, overlap regions may
not blend the way you expect — each is rasterised to its own pixmap
and composited back in paint order. Keep it simple: one widget, one
effect, no overlap.

---

## When NOT to use `QGraphicsOpacityEffect`

| Scenario                                  | Better approach                                   |
|-------------------------------------------|---------------------------------------------------|
| Fade a top-level window                   | `setWindowOpacity()` + `QPropertyAnimation` on `windowOpacity` |
| Fade during a QSS `:hover` state          | QSS `background-color` with alpha on hover (no animation needed) |
| Animate a single paint property (e.g. text color) | Animate a custom `Q_PROPERTY` + `update()` in the paintEvent |
| Hide/show with no motion                  | `setVisible()` — fades aren't always the right answer |
| Many children fading at once              | Consider one effect on the parent container       |

---

## Reference: the fade-in-window recipe
For top-level windows (dialogs, tool windows, popups), skip the
effect entirely:
```python
dialog.setWindowOpacity(0.0)
dialog.show()
fade = QPropertyAnimation(dialog, b"windowOpacity", dialog)
fade.setDuration(160)
fade.setStartValue(0.0)
fade.setEndValue(1.0)
fade.setEasingCurve(QEasingCurve.OutCubic)
fade.start(QPropertyAnimation.DeleteWhenStopped)
```
This uses the window manager's alpha, which is GPU-accelerated on
every platform and doesn't incur the rasterise-to-pixmap penalty.

---

## The `QGraphicsEffect` base class

All four Qt effects inherit from `QGraphicsEffect`, which handles the
common pipeline: rasterise the source widget to an offscreen pixmap,
transform it through the effect's `draw()` implementation, and
composite the result. You rarely instantiate it directly, but you do
subclass it when you need an effect Qt doesn't ship.

### The pipeline
```
widget.paint  →  sourcePixmap()  →  effect.draw(painter)  →  screen
```

### Key members (inherited by every effect)
- **`enabled : bool`** — set to `False` to bypass the effect without
  detaching it. Cheaper than `setGraphicsEffect(None)` when you want
  to toggle frequently (e.g. disable shadows on slow platforms).
- **`update()`** — schedule a redraw of the effect (not the source).
- **`boundingRect()` / `boundingRectFor(rect)`** — the effective
  bounding box including any margin the effect adds (glow, shadow
  offset).
- **`sourceBoundingRect()`** — the source's bounding rect before the
  effect expands it.

### Enums
- **`ChangeFlag`** — `SourceAttached`, `SourceDetached`,
  `SourceBoundingRectChanged`, `SourceInvalidated`. Passed to
  `sourceChanged(flags)` so custom subclasses can invalidate caches.
- **`PixmapPadMode`** — `NoPad`, `PadToTransparentBorder`,
  `PadToEffectiveBoundingRect`. Controls how `sourcePixmap()` pads
  the returned pixmap for the effect's benefit.

### Custom subclass pattern (when you need something Qt doesn't ship)
```python
from PySide6.QtCore    import Qt
from PySide6.QtGui     import QPainter, QColor
from PySide6.QtWidgets import QGraphicsEffect

class TintEffect(QGraphicsEffect):
    """Tint the source with a colored overlay at a given strength."""
    def __init__(self, color: QColor, strength: float = 0.3, parent=None):
        super().__init__(parent)
        self._color = color
        self._strength = strength

    def draw(self, painter: QPainter) -> None:
        # Draw the source first
        self.drawSource(painter)
        # Then overlay the tint
        painter.save()
        painter.setOpacity(self._strength)
        painter.fillRect(self.sourceBoundingRect(), self._color)
        painter.restore()
```

Use `drawSource(painter)` for the fast path when your effect is a
simple overlay. Use `sourcePixmap()` when you need to run a shader-
like transform on the pixels (blur, distort). **Call
`updateBoundingRect()`** whenever a parameter change expands the
bounds the effect draws into.

---

## QGraphicsDropShadowEffect

The elevation tool. Adds a drop shadow behind the widget.

### Properties (all Q_PROPERTY, all animatable)
- **`blurRadius : qreal`** — default **1** (too sharp for modern
  looks; bump to 8+).
- **`color : QColor`** — default `QColor(63, 63, 63, 180)` (dark gray
  at ~71% alpha; looks harsh — swap for `QColor(0, 0, 0, 40)` for a
  softer modern look).
- **`offset : QPointF`** — default `(8, 8)` (towards lower-right;
  **too big** for most UIs — `(0, 2)` is the Material elevation 2
  convention).
- **`xOffset : qreal`** / **`yOffset : qreal`** — component access.

### "Material elevation 2" recipe
```python
from PySide6.QtCore    import QPointF
from PySide6.QtGui     import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect

shadow = QGraphicsDropShadowEffect(widget)
shadow.setColor(QColor(0, 0, 0, 40))       # 16% black
shadow.setOffset(QPointF(0, 2))            # 2px down, no horizontal
shadow.setBlurRadius(8)                    # soft
widget.setGraphicsEffect(shadow)
```

The defaults are **fifteen-year-old Qt defaults** that will never
look modern. Always set all three: color, offset, blur.

### Pattern: animated elevation on hover

Lift a card up when hovered — three parallel animations on the same
effect (blur, color, offset):

```python
from PySide6.QtCore    import (
    QPropertyAnimation, QParallelAnimationGroup, QEasingCurve,
    QAbstractAnimation, QPointF, QEvent,
)
from PySide6.QtGui     import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect

class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "panel")          # QSS styling unchanged
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setColor(QColor(0, 0, 0, 40))
        self._shadow.setOffset(QPointF(0, 2))
        self._shadow.setBlurRadius(8)
        self.setGraphicsEffect(self._shadow)

    def enterEvent(self, e: QEvent) -> None:
        self._animate_shadow(blur=24.0, color=QColor(0, 0, 0, 60),
                             offset=QPointF(0, 6))
        super().enterEvent(e)

    def leaveEvent(self, e: QEvent) -> None:
        self._animate_shadow(blur=8.0, color=QColor(0, 0, 0, 40),
                             offset=QPointF(0, 2))
        super().leaveEvent(e)

    def _animate_shadow(self, blur: float, color: QColor, offset: QPointF) -> None:
        group = QParallelAnimationGroup(self)

        blur_a = QPropertyAnimation(self._shadow, b"blurRadius")
        blur_a.setDuration(180)
        blur_a.setEndValue(blur)
        blur_a.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(blur_a)

        color_a = QPropertyAnimation(self._shadow, b"color")
        color_a.setDuration(180)
        color_a.setEndValue(color)
        group.addAnimation(color_a)

        offset_a = QPropertyAnimation(self._shadow, b"offset")
        offset_a.setDuration(180)
        offset_a.setEndValue(offset)
        offset_a.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(offset_a)

        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
```

180ms + `OutCubic` is the "responsive but not abrupt" sweet spot for
hover. Do not overdo the shadow lift — 8→24 blur + 2→6 offset is
plenty; going to `blur=48, offset=(0,12)` looks cartoonish.

### The single-effect caveat, revisited

You cannot combine `QGraphicsDropShadowEffect` + `QGraphicsOpacityEffect`
on the same widget — they're both `QGraphicsEffect` subclasses and
only one slot exists. Wrap the widget in a `QFrame`:

```
QFrame (drop shadow here)
  └── QWidget (opacity effect here)
```

The outer frame carries the elevation; the inner widget carries the
fade. The frame's shadow is drawn around whatever shape the inner
widget currently presents — which means fading the inner widget to
0 opacity fades the shadow too (the frame has nothing visible to
cast from). Usually this is what you want.

---

## QGraphicsBlurEffect

Gaussian blur. Useful for "frosted glass" backdrops behind modals
and for defocus effects on inactive panels.

### Properties
- **`blurRadius : qreal`** — default 0 (no blur). Values 4–16 look
  reasonable; above 32 gets expensive.
- **`blurHints : BlurHint`** — `PerformanceHint`, `QualityHint`,
  `AnimationHint`. **Use `AnimationHint` when animating** — it picks
  a faster implementation that sacrifices a bit of quality but won't
  drop frames.

```python
from PySide6.QtWidgets import QGraphicsBlurEffect

blur = QGraphicsBlurEffect(widget)
blur.setBlurRadius(12)
blur.setBlurHints(QGraphicsBlurEffect.BlurHint.AnimationHint)
widget.setGraphicsEffect(blur)
```

Same CPU-compositing cost as the opacity effect — expect FPS drop on
large widgets. Good for short transitions, bad for "permanent
frosted background behind a scrolling list."

---

## QGraphicsColorizeEffect

Tints the source toward a single color. Useful for disabled states
and for "ghosted" previews.

### Properties
- **`color : QColor`** — the tint target.
- **`strength : qreal`** — `0.0` (no effect) to `1.0` (fully tinted).

```python
from PySide6.QtWidgets import QGraphicsColorizeEffect

gray_out = QGraphicsColorizeEffect(widget)
gray_out.setColor(QColor("#888888"))
gray_out.setStrength(0.7)
widget.setGraphicsEffect(gray_out)
```

Animating `strength` from 0 to 0.7 gives a "fading into disabled"
look. Less visible than animating opacity to 0.3 because the widget
stays at full opacity — only its color saturation drops.
