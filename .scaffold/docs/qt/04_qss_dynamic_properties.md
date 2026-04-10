# Qt Style Sheets + Dynamic Properties

> Source: Stack Overflow Q&A (2020) + Qt docs on the `[prop="val"]`
> selector syntax + our own experience in this repo.

The #1 QSS misconception: **QSS can't read an arbitrary Q_PROPERTY
value as a color or size**. It can only *react* to properties via the
attribute-selector syntax `Widget[prop="value"]` — and only for
discrete, known values. Continuous values (any RGB color, any size in
pixels) must flow through the palette, inline stylesheets, or be
expressed as a finite set of CSS classes.

This file captures the rules, the failure modes, and the escape
hatches.

---

## What DOES work

### 1. Writing a property from QSS (`qproperty-*`)
You can **set** a `Q_PROPERTY` on a widget from its stylesheet:
```css
MyWidget {
    qproperty-color: red;                          /* sets a QColor prop */
    qproperty-iconSize: 24px 24px;                 /* sets a QSize prop  */
    qproperty-customText: "Hello";                 /* sets a QString prop */
}
```
This runs once when the stylesheet is applied. It's the stylesheet
*writing* into the widget, not reading from it. Useful for
designer-driven configuration of custom widgets.

### 2. Reacting to a property via attribute selector
```css
IconButton[state="active"] {
    background-color: #6EE0B0;
    color: #0A0E14;
}
IconButton[state="disabled"] {
    background-color: #2A3240;
    color: #5A6878;
}
```
On the Python side, you **must** call `unpolish()`/`polish()` or
`style().unpolish(w); style().polish(w)` after changing the property,
or QSS won't re-evaluate the selector:
```python
button.setProperty("state", "active")
button.style().unpolish(button)
button.style().polish(button)
button.update()                    # force repaint
```
Or the shorter idiom using a class property on self:
```python
def set_state(self, state: str):
    self.setProperty("state", state)
    self.style().unpolish(self)
    self.style().polish(self)
```
**This only works for discrete, enumerable values** you can list in
your QSS. You can't write `[color="#3A7BD5"]` to match any color.

### 3. Class-based selectors (preferred for "N states")
Instead of a property, use a dynamic `class` property and select by
that:
```css
QPushButton[class="primary"]   { background: #3A7BD5; color: white; }
QPushButton[class="secondary"] { background: #2A3240; color: #C8D4E2; }
QPushButton[class~="danger"]   { border: 1px solid #E83030; }
```
- `[class="x"]` — exact match
- `[class~="x"]` — matches if `x` is one of space-separated values
  (allows combining classes: `button.setProperty("class", "primary danger")`)

Python:
```python
btn.setProperty("class", "primary")
btn.style().polish(btn)
```
This is what we use throughout the Kohala stylesheet — see
`.scaffold/app/themes/kohala.qss` for examples
(`QPushButton[class="ws-tab"]`, `QLabel[class="brand-mark"]`,
`QFrame[class="panel"]`, etc.).

---

## What DOESN'T work

### 1. Reading a property as a value (no "qproperty read" syntax)
```css
MyWidget {
    background-color: qproperty-color;       /* ❌ INVALID — not a thing */
    background-color: var(--color);          /* ❌ no CSS vars in QSS */
    background-color: attr(color);           /* ❌ no attr() in QSS */
}
```
QSS has no mechanism to inline a Q_PROPERTY value into a declaration.
The `qproperty-` prefix is **write-only** (stylesheet → widget).

### 2. `palette(window)` is actually `QApplication.palette()`
```css
MyWidget {
    background-color: palette(window);
}
```
The Qt docs suggest this reads the widget's palette — but as the
Stack Overflow thread confirms, **it reads the application palette,
not the widget's own palette**. If you call `widget.setPalette(p)`
expecting `palette(window)` to pick up the widget-local override, it
won't. You're stuck with whatever `QApplication::palette()` returns.

### 3. Matching continuous property values
```css
MyWidget[color="#3A7BD5"] { ... }        /* ❌ only matches exactly */
MyWidget[width>100]       { ... }        /* ❌ no numeric comparisons */
```
Attribute selectors are string-equality only. You cannot match a
range or a type-converted value.

---

## Escape hatches

### Option A: Use the palette (Fusion style)
The Stack Overflow answerer's recommendation: ditch QSS for
palette-sensitive colors, set the app style to `Fusion` (which
respects `QPalette` overrides more completely than the default
platform styles), and drive colors through `QPalette`:
```python
from PySide6.QtGui     import QPalette, QColor
from PySide6.QtWidgets import QApplication, QStyleFactory

QApplication.setStyle(QStyleFactory.create("Fusion"))
pal = QApplication.palette()
pal.setColor(QPalette.ColorRole.Window, QColor("#0A0E14"))
pal.setColor(QPalette.ColorRole.WindowText, QColor("#C8D4E2"))
QApplication.setPalette(pal)
```
To let a child widget draw its own palette background:
```python
widget.setAutoFillBackground(True)     # required or parent bg shows through
pal = widget.palette()
pal.setColor(QPalette.ColorRole.Window, QColor("#1A2230"))
widget.setPalette(pal)
```
Caveat: you still need `setAutoFillBackground(True)` for child widgets
— otherwise Qt lets the parent paint through them and your palette
color is invisible.

### Option B: Regenerate the stylesheet with the color baked in
For one-off dynamic colors (e.g. a user-picked theme color), build
the QSS string in Python with the color substituted and reapply:
```python
def apply_accent_color(app, accent: QColor):
    hex_color = accent.name()
    qss = f"""
        QPushButton[class="primary"] {{
            background-color: {hex_color};
        }}
        QLabel[class="accent"] {{
            color: {hex_color};
        }}
    """
    # Prepend to the existing stylesheet, don't replace it.
    app.setStyleSheet(qss + app.styleSheet())
```
Cheap, works everywhere. Re-polishes all widgets automatically
because `setStyleSheet` at the app level triggers a global restyle.

### Option C: Inline stylesheet on the specific widget
Set a stylesheet directly on the affected widget with the color
baked in:
```python
widget.setStyleSheet(f"background-color: {color.name()};")
```
Inline widget stylesheets override the application stylesheet for
that widget and its children. Use sparingly — it defeats centralised
theming. Good for one-off per-instance colors (e.g. user avatar
initial backgrounds).

### Option D: Override `paintEvent` and draw with the property value
For widgets where the color is truly dynamic and central to the
widget, skip QSS entirely:
```python
class ColorSwatch(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#888")

    def set_color(self, c: QColor):
        self._color = c
        self.update()                  # triggers repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._color)
```
This is the C++-Qt way of doing custom widgets and is often cleaner
than trying to force QSS into a shape it wasn't designed for.

---

## Our rules of thumb for Terragraf

1. **Use `[class="x"]` attribute selectors** for discrete widget
   variants. This is what `kohala.qss` does and it works well.

2. **Use `qproperty-*`** for designer-level config of custom widgets
   (e.g. `qproperty-iconSize`, `qproperty-cornerRadius` on a widget
   that exposes those as `Q_PROPERTY`).

3. **Call `style().polish(widget)`** after any `setProperty("class",
   …)` call that affects styling. This is the most common source of
   "my QSS selector doesn't apply" bugs — Qt caches the style
   computation and only invalidates it on polish.

4. **Don't fight `palette(window)`** — it reads the app palette, and
   if you need widget-local colors, either bake them into the
   stylesheet string or override `paintEvent`.

5. **Continuous values → Python string formatting**, not QSS selectors.
   Build the stylesheet with the value substituted and apply it.

6. **No `QGraphicsEffect` in a stylesheet** — effects are set in Python
   (`setGraphicsEffect`) and QSS has no hook for them. Don't try to
   express a drop shadow via QSS — there is no `box-shadow` in QSS.
   (QSS `border` + `padding` tricks can approximate insets, but not
   true shadows.)

---

## Pattern: animating a background color without re-parsing QSS

The naive approach — rebuild the stylesheet string every animation
tick and call `setStyleSheet()` — is **~100× slower** than animating
through the palette or a custom `Q_PROPERTY`. Every `setStyleSheet`
forces Qt to re-parse, re-match selectors, and re-polish the whole
widget subtree.

### The fast path: Q_PROPERTY + QPalette
```python
from PySide6.QtCore    import Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui     import QColor, QPalette
from PySide6.QtWidgets import QWidget

class ColorBox(QWidget):
    """A widget whose background color is an animatable Q_PROPERTY."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self._bg = QColor("#eeeeee")
        self._apply_bg()

    def _apply_bg(self) -> None:
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, self._bg)
        self.setPalette(pal)

    # @Property exposes _bg as a real Qt property QPropertyAnimation can drive.
    def _get_bg(self) -> QColor:
        return self._bg

    def _set_bg(self, c: QColor) -> None:
        self._bg = c
        self._apply_bg()

    bg = Property(QColor, _get_bg, _set_bg)   # PySide6 decorator form

# Animate bg from white to blue over 250ms.
anim = QPropertyAnimation(box, b"bg", box)
anim.setDuration(250)
anim.setStartValue(QColor("#ffffff"))
anim.setEndValue(QColor("#2d7ff9"))
anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
```

Three things make this work:

1. **`QVariantAnimation` natively interpolates `QColor`** — no
   per-channel code required. Same for `QPoint`, `QSize`, `QRect`,
   numeric types.
2. **Setting the `QPalette::Window` role** is what actually draws the
   background, but only if `autoFillBackground` is true. Forget that
   flag and the palette change is invisible.
3. **No stylesheet is touched**. The `QSS` rules above the widget
   still apply; we're just changing the palette underneath, which
   some styles respect.

### Caveat: `palette(window)` won't see this

As covered above in §2 "What DOESN'T work": QSS `palette(window)` reads
the **application** palette, not the widget's. So this pattern
animates the background that Qt renders via `autoFillBackground`, but
any QSS rule that references `palette(window)` will still see the app
palette. If you need QSS to react to the new color, use Escape Hatch B
(regenerate the stylesheet) and eat the re-parse cost for that one
transition.

### When to use which color-change path

| Need                                                 | Path                                         |
|------------------------------------------------------|----------------------------------------------|
| Smooth continuous color animation, one widget        | `Q_PROPERTY` + `QPalette` (this pattern)     |
| Discrete state change across many widgets            | `[class="x"]` selectors + `polish/unpolish`  |
| One-off theme reload (e.g. accent color picker)      | Regenerate stylesheet string + `setStyleSheet` |
| Fully custom paint (no palette, no QSS)              | `paintEvent` override — see `06_painter_custom_paint.md` |

---

## Killing built-in Qt style motion

`widget-animation-duration` is the one QSS property that *does*
affect motion — it controls Qt's **built-in** style animations
(Fusion progress-bar chunk movement, spinbox scroll, some
scroll-bar behaviours). Set it to `0` to disable.

```python
app.setStyleSheet("* { widget-animation-duration: 0; }")
```

One line, global. Combine with the `MotionSettings` singleton from
`01_animation_framework.md` (which disables our own animations) to
cover both surfaces:

- **`MotionSettings.set_scale(0)`** → our `QPropertyAnimation`s
  become instant.
- **`widget-animation-duration: 0`** → Qt's internal style animations
  become instant.

Together this is the closest Qt gets to an OS-level "reduce motion"
toggle.

**Caveat**: `widget-animation-duration` is the *only* animation-
related property in all of QSS. It is not a general animation timing
function and has no effect on your own `QPropertyAnimation` code.
