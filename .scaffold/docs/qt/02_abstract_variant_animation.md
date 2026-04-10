# QAbstractAnimation + QVariantAnimation — Base Classes

> Source: Qt 6.11 docs. PySide6 mirrors the API; property names are `bytes`.

The inheritance chain is:

```
QAbstractAnimation   (abstract, time/state only)
    └── QVariantAnimation   (adds value interpolation)
            └── QPropertyAnimation   (adds QObject property binding)
    └── QAnimationGroup
            ├── QParallelAnimationGroup
            └── QSequentialAnimationGroup
    └── QPauseAnimation
```

When you write a custom animation (e.g. animating a progress ring's sweep
angle that isn't tied to a Qt property), you either subclass
`QVariantAnimation` and override `updateCurrentValue`, or use
`QPropertyAnimation` against a custom `Q_PROPERTY`/`@Property`.

---

## QAbstractAnimation

Base of all animations. Defines time, state, direction, looping. Cannot
be instantiated directly — must subclass and implement `duration()` and
`updateCurrentTime()`.

### The three states
```
Stopped  ──start()──▶  Running  ──pause()──▶  Paused
   ▲                      │                      │
   │                      └──stop() / finish─────┘
   │                      │
   └──stop() ◀─resume()───┘
```

- **Stopped** — default / terminal. `currentTime` retained across stops,
  resets on next `start()`.
- **Running** — event loop updates `currentTime` at ~60 Hz (not
  guaranteed; don't depend on interval).
- **Paused** — frozen. `currentTime` held. `resume()` → Running.

`stateChanged(newState, oldState)` fires on every transition.
`finished()` fires after the final loop ends (Running → Stopped).

### Time, loops, direction
| Property       | Meaning                                                               |
|----------------|-----------------------------------------------------------------------|
| `duration`     | ms of a single loop. `-1` = indefinite (loopCount ignored).           |
| `loopCount`    | `1` default. `0` = never runs. `-1` = infinite. Cannot loop if `duration == -1`. |
| `currentLoop`  | 0-indexed current iteration. Read-only. Emits `currentLoopChanged`.   |
| `currentTime`  | ms into the **total** animation (0 .. `totalDuration()`).             |
| `currentLoopTime()` | ms into the **current loop** (0 .. `duration()`).                |
| `totalDuration()` | `duration * loopCount`, or `-1` if either is `-1`.                 |
| `direction`    | `Forward` (default) / `Backward`. Can be toggled mid-run.             |

### DeletionPolicy (fire-and-forget)
```python
anim.start(QAbstractAnimation.DeleteWhenStopped)
```
`KeepWhenStopped` (default) leaves the animation alive after it finishes
— good for reusable animations. `DeleteWhenStopped` frees it when it
hits the Stopped state the next time — good for one-shot animations
(hover pop, toast fade) so they don't leak.

### Custom subclass pattern
```python
from PySide6.QtCore import QAbstractAnimation

class SpinnerAnimation(QAbstractAnimation):
    def __init__(self, widget, parent=None):
        super().__init__(parent)
        self._widget = widget

    def duration(self) -> int:
        return 1200  # one rotation per 1.2s

    def updateCurrentTime(self, current_ms: int) -> None:
        # progress 0..1 across the current loop
        t = self.currentLoopTime() / self.duration()
        self._widget.set_angle(t * 360.0)
```
Use this when you need a time driver but the "value" isn't a single
interpolable variant — e.g. driving three coupled values, or triggering
side effects on tick. For simple value tweens, use `QVariantAnimation`
or `QPropertyAnimation` instead.

### `setCurrentTime` for scrubbing
You can drive the animation manually by repeatedly calling
`setCurrentTime(ms)` — useful for scrubbing / preview sliders / unit
tests. The animation doesn't need to be in `Running` state for this.
Caveat: setting `currentTime` **cancels any QProperty binding on
currentTime** — the docs explicitly warn against binding to it.

### Useful signals
- `stateChanged(newState, oldState)` — state transitions
- `finished()` — fires after reaching the end (natural completion only)
- `currentLoopChanged(int)` — each new loop iteration
- `directionChanged(Direction)` — direction toggled

---

## QVariantAnimation

Adds value interpolation on top of `QAbstractAnimation`. You give it a
start value, an end value, a duration, and an easing curve — it emits
`valueChanged(QVariant)` on every tick with the interpolated value.

`QPropertyAnimation` is a thin subclass that writes that value into a
property; `QVariantAnimation` by itself is what you use when you want
to interpolate *something* without tying it to a QObject property.

### Supported QVariant types (built-in interpolation)
```
int, uint, double, float
QPoint, QPointF
QSize,  QSizeF
QLine,  QLineF
QRect,  QRectF
QColor
```
Anything else needs either a custom interpolator (see below) or a
subclass that overrides `interpolated()`.

### Canonical use (subclass, no property binding)
```python
from PySide6.QtCore import QVariantAnimation, QEasingCurve

def animate_progress(widget, target: float):
    anim = QVariantAnimation(widget)              # parent = widget → GC-safe
    anim.setDuration(400)
    anim.setStartValue(widget.progress)
    anim.setEndValue(target)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.valueChanged.connect(widget.set_progress)
    anim.start(QVariantAnimation.DeleteWhenStopped)
```
This is the idiom for animating a Python attribute or calling a setter
that isn't exposed as a `Q_PROPERTY`. Cheaper than declaring a property
just to animate it once.

### Key frames (multi-step animations in one object)
Instead of one start → end pair, you can set intermediate values:
```python
anim = QVariantAnimation(self)
anim.setDuration(1000)
anim.setKeyValueAt(0.0,  QColor("#ff0000"))   # at 0%
anim.setKeyValueAt(0.5,  QColor("#ffff00"))   # at 50%
anim.setKeyValueAt(1.0,  QColor("#00ff00"))   # at 100%
anim.valueChanged.connect(lambda c: widget.setStyleSheet(f"background:{c.name()}"))
```
Steps are `qreal` in `[0.0, 1.0]`. Useful for color cycles, path-like
motion, or staged reveals inside a single animation.

**Important**: the easing curve still applies over the whole
`[0,1]` progress — so an `InOutQuad` curve across three key values
compresses time around the edges and stretches it in the middle. For
linear progress between key values, use `QEasingCurve.Linear`.

### Custom interpolator (preferred for a new type)
For a new type you want to animate across your whole app, register
a free-function interpolator once at startup:
```cpp
// C++
QVariant myColorInterpolator(const QColor &a, const QColor &b, qreal t) {
    return QColor::fromRgbF(
        a.redF()   + (b.redF()   - a.redF())   * t,
        a.greenF() + (b.greenF() - a.greenF()) * t,
        a.blueF()  + (b.blueF()  - a.blueF())  * t,
        a.alphaF() + (b.alphaF() - a.alphaF()) * t);
}
qRegisterAnimationInterpolator<QColor>(myColorInterpolator);
```
PySide6 doesn't expose `qRegisterAnimationInterpolator`, so in Python
you subclass `QVariantAnimation` and override `interpolated()` instead:
```python
class HSLColorAnimation(QVariantAnimation):
    def interpolated(self, a, b, progress: float):
        # hue-aware interpolation (shorter arc around the wheel)
        ...
        return QColor.fromHslF(h, s, l)
```

### Overriding `updateCurrentValue` vs connecting `valueChanged`
Both work. Rule of thumb:
- **Connect `valueChanged`** when the animation drives an existing
  widget you don't own — it's the "observer" pattern and keeps the
  widget decoupled.
- **Subclass + override `updateCurrentValue`** when the animation *is*
  the behaviour (you're building a reusable custom animation class).
  Slightly faster — no signal/slot dispatch per tick.

### Beware: easing + extrapolation
Curves like `InBack`/`OutBack`/`InElastic`/`OutElastic` return progress
values **outside** `[0, 1]` (that's what makes them overshoot). Built-in
interpolators for numbers handle extrapolation fine; your custom
`interpolated()` implementations **must** handle `progress < 0` or
`progress > 1` gracefully, or animations with those curves will clip or
crash.

---

## Cross-class cheat sheet

| Want to...                                         | Use                                   |
|----------------------------------------------------|---------------------------------------|
| Animate a Qt property on any QObject               | `QPropertyAnimation`                  |
| Animate a value and call a setter / emit signals   | `QVariantAnimation` + `valueChanged`  |
| Animate a Python attribute (no Q_PROPERTY)         | `QVariantAnimation` + `valueChanged`  |
| Run N animations together                          | `QParallelAnimationGroup`             |
| Run N animations one after another                 | `QSequentialAnimationGroup`           |
| Delay between steps in a sequence                  | `group.addPause(msecs)`               |
| Time-driven custom behaviour (no interpolation)    | Subclass `QAbstractAnimation`         |
| New type interpolation (one-off, Python)           | Subclass `QVariantAnimation.interpolated` |
| New type interpolation (reusable, C++)             | `qRegisterAnimationInterpolator<T>`   |
| Fire-and-forget animation                          | `start(DeleteWhenStopped)`            |
| Pause / resume without losing progress             | `pause()` / `resume()`                |
| Reset time and replay                              | `stop()` then `start()`               |
| Scrub manually (slider, test)                      | `setCurrentTime(ms)` while Stopped    |
| Indefinite duration (event-driven end)             | `duration() returns -1`, call `stop()` to end |
| Loop forever                                       | `setLoopCount(-1)`                    |

---

## Pattern: staggered list entrance

The canonical use of `QSequentialAnimationGroup.addPause` — card 1
enters, 50ms later card 2 enters, 50ms later card 3 enters, each
fading and sliding up simultaneously. The inner animation for each
card is a `QParallelAnimationGroup` (fade + slide together); the
outer is a `QSequentialAnimationGroup` with pauses between.

```python
from PySide6.QtCore import (
    QPropertyAnimation, QParallelAnimationGroup, QSequentialAnimationGroup,
    QEasingCurve, QAbstractAnimation, QRect,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect

def animate_list_entrance(cards, stagger_ms: int = 50, per_card_ms: int = 260):
    """Stagger the entrance of a list of widgets."""
    seq = QSequentialAnimationGroup(cards[0].parent())

    for i, card in enumerate(cards):
        effect = QGraphicsOpacityEffect(card)
        effect.setOpacity(0.0)
        card.setGraphicsEffect(effect)

        parallel = QParallelAnimationGroup()

        fade = QPropertyAnimation(effect, b"opacity")
        fade.setDuration(per_card_ms)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        parallel.addAnimation(fade)

        end_rect = card.geometry()
        start_rect = end_rect.translated(0, 20)   # start 20px below
        card.setGeometry(start_rect)

        slide = QPropertyAnimation(card, b"geometry")
        slide.setDuration(per_card_ms)
        slide.setStartValue(start_rect)
        slide.setEndValue(end_rect)
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        parallel.addAnimation(slide)

        if i > 0:
            seq.addPause(stagger_ms)
        seq.addAnimation(parallel)

    seq.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
    return seq
```

**Sizing the stagger**: with 50ms stagger and 260ms per card, 8 items
total ~610ms — on the edge of acceptable. Beyond ~8 items, cap the
stagger total or batch the rest without animation. More than ~10
simultaneously animating items becomes "motion noise" that the user
cannot parse.

See also `QStateMachine.addDefaultAnimation` in `05_state_machine.md`
for a declarative alternative when the entrance is tied to a state
transition rather than a one-shot.
