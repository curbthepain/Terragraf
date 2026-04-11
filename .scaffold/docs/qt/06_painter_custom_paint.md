# QPainter + Custom `paintEvent` Patterns

> Source: Qt 6.11 `QPainter` class reference. PySide6 exposes the
> full API 1:1 — `painter.drawArc(...)` translates straight across.

When QSS cannot express the look you want (circular progress rings,
morphing icons, waveform overlays, animated gauges, radial menus),
the answer is a custom widget with a `paintEvent` override. This is
the oldest and most flexible pattern in Qt — and the one that
`QPropertyAnimation` pairs with most elegantly through custom
`Q_PROPERTY` declarations.

---

## The fundamental pattern

1. Expose a `Q_PROPERTY` (or `@Property` in PySide6) for anything
   you want to animate — a `qreal progress`, a `QColor color`, a
   `QPointF origin`.
2. In the setter, call `self.update()` to schedule a repaint.
3. In `paintEvent`, read the property and draw accordingly.
4. Drive the property with `QPropertyAnimation` from outside.

The animation framework does the interpolation; `paintEvent` does
the drawing; the `Q_PROPERTY` is the interface between them.

---

## Canonical example: animated progress ring

A circular progress indicator you cannot express in QSS because QSS
has no notion of arcs. Written as a full self-contained PySide6
widget:

```python
from PySide6.QtCore    import Property, QPropertyAnimation, QEasingCurve, Qt, QRectF
from PySide6.QtGui     import QPainter, QPen, QColor, QPaintEvent
from PySide6.QtWidgets import QWidget

class ProgressRing(QWidget):
    """Circular progress indicator. `progress` in [0.0, 1.0]."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress: float = 0.0
        self.setMinimumSize(80, 80)

    # -- Q_PROPERTY interface for QPropertyAnimation ----------------
    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, v: float) -> None:
        if abs(self._progress - v) < 1e-6:
            return
        self._progress = v
        self.update()            # schedule repaint

    progress = Property(float, _get_progress, _set_progress)

    # -- paintEvent -------------------------------------------------
    def paintEvent(self, ev: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = QRectF(self.rect()).adjusted(6, 6, -6, -6)   # padding

        # Track ring (gray background)
        track_pen = QPen(QColor("#e6e6e6"), 6)
        p.setPen(track_pen)
        p.drawEllipse(r)

        # Progress arc (colored foreground)
        arc_pen = QPen(QColor("#2d7ff9"), 6)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(arc_pen)
        # Qt arc angles: 1/16th of a degree; 0° = 3 o'clock; positive = CCW.
        # We want 12 o'clock start, clockwise, hence 90 * 16 start and negative span.
        start_angle = 90 * 16
        span_angle = -int(self._progress * 360 * 16)
        p.drawArc(r, start_angle, span_angle)

# -- usage ----------------------------------------------------------
ring = ProgressRing()
anim = QPropertyAnimation(ring, b"progress", ring)
anim.setDuration(1200)
anim.setStartValue(0.0)
anim.setEndValue(1.0)
anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
anim.start()
```

Three things to notice:

- **The `Property(float, ...)` line is the entire Q_PROPERTY
  declaration** in PySide6. No `Q_PROPERTY` macro, no MOC — just the
  `Property` descriptor. `QPropertyAnimation(ring, b"progress", ring)`
  binds to it by name.
- **`update()` is cheap** — it schedules a repaint, it doesn't force
  one. Multiple `update()` calls in the same event loop tick
  coalesce.
- **Qt arc angles are in 16ths of a degree**. `90 * 16` is the
  "12 o'clock" start point, not `90`. Positive angles go
  counter-clockwise, so to draw clockwise (the conventional
  progress direction) you negate the span. This is the single most
  common `drawArc` bug.

---

## QPainter API surface (task-oriented)

The full `QPainter` reference runs to a couple hundred methods.
Grouped by what you're trying to do:

### Primitives

- **Lines / polylines**: `drawLine`, `drawLines`, `drawPolyline`
- **Rectangles**: `drawRect`, `drawRects`, `drawRoundedRect`,
  `fillRect`, `eraseRect`
- **Ellipses / arcs**: `drawEllipse`, `drawArc`, `drawChord`,
  `drawPie` (pie slice)
- **Polygons**: `drawPolygon`, `drawConvexPolygon`
- **Paths**: `drawPath` (composite shape from a `QPainterPath`),
  `strokePath`, `fillPath`
- **Points**: `drawPoint`, `drawPoints`

### Images and text

- **Pixmaps**: `drawPixmap`, `drawTiledPixmap`, `drawPixmapFragments`
- **Images**: `drawImage`
- **Text**: `drawText`, `drawStaticText`, `drawGlyphRun`,
  `boundingRect(...)` (measure without drawing)

### Pen / brush (how things look)

- **`setPen(QPen)`** — controls stroke color, width, style
  (`SolidLine`, `DashLine`, `DotLine`, `DashDotLine`, `NoPen`),
  cap (`FlatCap`, `SquareCap`, `RoundCap`), join
  (`MiterJoin`, `BevelJoin`, `RoundJoin`).
- **`setBrush(QBrush)`** — fill color or pattern. Accepts gradients
  (`QLinearGradient`, `QRadialGradient`, `QConicalGradient`) or a
  `Qt::BrushStyle` (`SolidPattern`, `Dense1Pattern..Dense7Pattern`,
  `CrossPattern`, etc.).
- **`setOpacity(qreal)`** — global opacity multiplier on top of the
  pen/brush alpha.

### Render hints (quality tuning)

```python
p.setRenderHint(QPainter.RenderHint.Antialiasing)         # smooth edges
p.setRenderHint(QPainter.RenderHint.TextAntialiasing)     # smooth text
p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform) # bilinear image scaling
p.setRenderHint(QPainter.RenderHint.LosslessImageRendering) # 6.2+
```

`Antialiasing` is **off by default**. Every curve you draw without
turning it on will be jagged. It has a small perf cost but is always
worth it for UI work. For per-frame animations on very large widgets,
profile first.

### Transforms

- **`translate(dx, dy)`**, **`scale(sx, sy)`**, **`rotate(deg)`**,
  **`shear(sh, sv)`** — compose affine transforms. Applies to
  everything drawn until you `restore()`.
- **`save()` / `restore()`** — bracket transform and state changes.
  Always pair them. `save()` pushes the current pen, brush, font,
  transform, clip, opacity, and render hints onto a stack;
  `restore()` pops. Cheap.
- **`setTransform(QTransform, combine=False)`** — replace or combine
  with an arbitrary 3x3 transform. For rotating around a point,
  `translate(cx, cy); rotate(deg); translate(-cx, -cy)`.

### Clipping

- **`setClipRect(QRect)`**, **`setClipRegion(QRegion)`**,
  **`setClipPath(QPainterPath)`** — restrict subsequent drawing to
  a region.
- **`setClipping(bool)`** — toggle without changing the clip.

Clip paths are the trick behind masked shapes (e.g. rounded-corner
thumbnails): build a `QPainterPath.addRoundedRect(...)`, set it as
the clip, then `drawPixmap` — the pixmap is automatically clipped
to the rounded shape.

### Composition modes

- **`setCompositionMode(mode)`** — change how new pixels combine
  with existing pixels. Default is `SourceOver` (alpha blending).
  Others: `DestinationOver`, `Clear`, `Source`, `Destination`,
  `SourceIn`, `SourceOut`, `SourceAtop`, `Plus`, `Multiply`,
  `Screen`, `Overlay`, `Darken`, `Lighten`, `ColorDodge`, plus
  binary `RasterOp_*` modes.

Rarely needed for UI work but essential for image editors, blend
overlays, and custom highlight effects.

### Measurement (without drawing)

- **`fontMetrics()`** → `QFontMetrics` for "how wide is this string"
- **`boundingRect(rect, flags, text)`** → where `drawText` would
  draw. Use with `Qt.AlignmentFlag.AlignCenter` etc. to position
  text without guessing.

---

## Gotchas and idioms

### 1. `QPainter` must live inside `paintEvent`

Creating a `QPainter(self)` outside `paintEvent` or in a method
called from something other than `paintEvent` produces undefined
behaviour on most platforms and a warning on all of them. If you
need painting logic outside `paintEvent`, paint into a `QPixmap`
first and `drawPixmap` it in the real `paintEvent`.

### 2. Always destroy the painter before returning

```python
def paintEvent(self, ev):
    p = QPainter(self)
    try:
        self._paint_ring(p)
    finally:
        p.end()       # usually implicit when p goes out of scope,
                      # but explicit is safer in error paths
```

In Python, `QPainter` goes out of scope at the end of the function
and Qt's C++ destructor calls `end()`. If you raise mid-paint, the
painter is cleaned up on unwind. The explicit `finally` is only
needed if you're passing the painter around.

### 3. `update()` vs `repaint()`

- **`update()`** — schedule a paintEvent for the next event-loop
  tick. Coalesces multiple calls. **Use this.**
- **`repaint()`** — force immediate synchronous paint. Skips the
  event loop. Almost always wrong — it blocks, doesn't coalesce,
  and can cause flicker or recursion if called from inside
  `paintEvent`. **Don't use.**

### 4. High-DPI: work in logical pixels

Qt 6 handles high-DPI automatically. Draw in logical pixel
coordinates (`rect()` is logical, not physical), and Qt scales up
for Retina / 125%/150% displays. Do **not** multiply by
`devicePixelRatio()` yourself unless you're painting to a `QImage`
you created.

For crisp lines on Retina displays, use `setCosmetic(True)` on your
pen — cosmetic pens draw at a constant pixel width regardless of
the current transform.

### 5. Don't re-create pens and brushes per paint

```python
# BAD: allocates a new QPen every frame
def paintEvent(self, ev):
    p = QPainter(self)
    p.setPen(QPen(QColor("#2d7ff9"), 6))        # new allocation every call
    ...

# GOOD: pre-build in __init__, reuse
def __init__(self, parent=None):
    super().__init__(parent)
    self._arc_pen = QPen(QColor("#2d7ff9"), 6)
    self._arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

def paintEvent(self, ev):
    p = QPainter(self)
    p.setPen(self._arc_pen)
    ...
```

For a widget painted at 60 FPS this is measurable. For a widget
painted once every state change, it doesn't matter — don't
pre-optimize.

### 6. Animating a color property

`QPropertyAnimation` natively interpolates `QColor`, so the same
progress-ring pattern works for "fade a label from red to green":

```python
class ColorfulLabel(QWidget):
    def _get_color(self) -> QColor:
        return self._color

    def _set_color(self, c: QColor) -> None:
        self._color = c
        self.update()

    color = Property(QColor, _get_color, _set_color)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.fillRect(self.rect(), self._color)
```

No need for a `QVariantAnimation` subclass — `QColor` is a built-in
interpolable type.

---

## Qt 6.11 Canvas Painter — when to escape `QPainter`

Qt 6.11 introduced **`QCanvasPainter`**, a hardware-accelerated 2D
painter that runs on Qt's RHI (OpenGL/Vulkan/Metal/D3D). Benchmarks:

| Platform                 | Speedup vs QPainter |
|--------------------------|---------------------|
| Desktop, OpenGL          | ~2×                 |
| Lenovo Tab M10 HD        | ~5×                 |
| Samsung Galaxy Tab S8    | ~10×                |

**When to consider it**: per-frame heavy painting (custom charts
with thousands of points, particle systems, animated waveform
overlays, 3D-ish gauges). Bound to Qt Quick / QRhi render targets
— not a drop-in `QPainter` replacement for widgets. Effectively,
moving to Canvas Painter usually means moving the widget to
`QQuickItem` in Qt Quick, which is a meaningful port.

**When `QPainter` is still fine**: UI chrome, one-shot paints,
anything that paints fewer than ~100 primitives per frame on
desktop hardware. `QPainter` has been fast enough for 15 years of
Qt UIs — don't migrate without profiling first.

---

## Quick reference: idioms we'll reuse

| Need                                            | Code                                                                 |
|-------------------------------------------------|----------------------------------------------------------------------|
| Smooth edges                                    | `p.setRenderHint(QPainter.RenderHint.Antialiasing)`                  |
| Animatable float property                       | `Property(float, getter, setter)` + `setter.update()`                |
| Animatable color property                       | `Property(QColor, ...)`                                              |
| Draw arc starting at 12 o'clock, clockwise      | `drawArc(r, 90*16, -int(progress*360*16))`                           |
| Clip to rounded rect                            | `path = QPainterPath(); path.addRoundedRect(r, 8, 8); p.setClipPath(path)` |
| Rotate around a point                           | `p.translate(cx, cy); p.rotate(deg); p.translate(-cx, -cy)`           |
| Text width                                      | `p.fontMetrics().horizontalAdvance("some string")`                   |
| Force repaint                                   | `self.update()` — **never** `self.repaint()`                         |
| Push/pop state                                  | `p.save(); ...; p.restore()`                                         |
