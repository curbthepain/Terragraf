# Qt Quick as an Escape Hatch (for comparison)

> Qt 6.11 animation system for Qt Quick / QML, in context.

Terragraf is a widget-based app — `QMainWindow`, `QFrame`, `QWidget`,
QSS. This file is not a how-to for porting the app to QML. It's a
reference for:

1. **Comparison**: when widget animation feels awkward, what would
   the QML equivalent look like?
2. **Scoped escape hatches**: embedding a `QQuickWidget` for one
   animated subsurface (a chart, a gauge, an onboarding sequence)
   while keeping the rest of the app in widgets.
3. **Future decisions**: if we ever move Terragraf off widgets,
   what's the animation story on the other side?

If all you need is "animate a widget", read
`01_animation_framework.md` instead.

---

## Why the QML story is different

Qt Quick is **declarative and GPU-accelerated**. Every QML item is
a scene-graph node, animations can target either the GUI thread or
the render thread, and the equivalent of CSS `transition` ships in
the language as `Behavior`. The result: most things that take 30
lines of `QPropertyAnimation` + event filters + parent-tracking in
a widget take 3 lines in QML.

Cost: a separate rendering stack, a separate type system (QML), and
a harder debugging story if something paints wrong. For dense
data-app UIs Qt Quick is overkill; for modern motion-heavy UIs it's
a force multiplier.

---

## Animation primitives

| QML type            | What it animates                         | When to use                                   |
|---------------------|------------------------------------------|-----------------------------------------------|
| `PropertyAnimation` | Any QML property                         | Generic tween                                 |
| `NumberAnimation`   | `real`/`int` properties                  | Faster path when you know the type is numeric |
| `ColorAnimation`    | Colors (interpolates in color space)     | Color morphs — smoother than component-wise   |
| `RotationAnimation` | Rotation with direction control          | Avoids 359°→0° snap (`direction: Shortest`)   |
| `Vector3dAnimation` | `vector3d` properties                    | 3D scene work                                 |
| `AnchorAnimation`   | Anchor changes                           | Otherwise instantaneous in QML                |
| `ParentAnimation`   | Reparenting                              | Smooth move between parents                   |
| `PathAnimation`     | Item following a `Path`                  | Curved motion                                 |
| `SmoothedAnimation` | Continuous smoothing toward a target     | Camera follow, mouse tracking                 |
| `SpringAnimation`   | Physical spring model                    | Natural bounce, drag-release                  |
| `PauseAnimation`    | Timed no-op                              | Gaps in sequences                             |

All animations take `duration`, `easing.type`, and optional
`easing.amplitude` / `easing.overshoot` / `easing.period`. Easing
enum mirrors `QEasingCurve` exactly.

---

## The three ways to trigger an animation in QML

### 1. `Behavior on propertyName` — the "CSS transition" analogue

```qml
Rectangle {
    id: card
    width: 240; height: 120
    radius: 12
    color: ma.containsMouse ? "#2d7ff9" : "#ffffff"

    Behavior on color {
        ColorAnimation { duration: 180; easing.type: Easing.OutCubic }
    }
    Behavior on scale {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    scale: ma.pressed ? 0.97 : 1.0

    MouseArea {
        id: ma
        anchors.fill: parent
        hoverEnabled: true
    }
}
```

A full hover + press interaction with color fade and press-scale in
~20 lines. There is no widget equivalent this short. `Behavior`
says "whenever this property changes *for any reason*, animate the
change with this animation." No event filters, no `enterEvent`
overrides, no manual cleanup.

### 2. `states` + `transitions` — state-driven

See `05_state_machine.md` — same mechanism. Declare states with
`PropertyChanges`, declare transitions with `from` / `to` /
animation bodies, then set `root.state = "foo"` to trigger.

### 3. `Animation on propertyName` — imperative start

```qml
Image {
    source: "qrc:/spinner.png"
    RotationAnimator on rotation {
        from: 0; to: 360
        duration: 1000
        loops: Animation.Infinite
    }
}
```

Starts the animation when the item is created. Use for ambient
motion: spinners, onboarding attract-modes, idle screensavers.

---

## `Animator` types: the render-thread escape hatch

Regular animations run on the **GUI thread**. If your GUI thread
blocks (loading a file, deserialising JSON, talking to a slow
backend), regular animations freeze.

`Animator` types run on the **scene-graph render thread** — they
keep ticking even when the GUI thread is wedged. Useful for loading
spinners that must stay spinning while the app hangs on I/O.

```qml
Image {
    id: spinner
    source: "qrc:/spinner.png"
    RotationAnimator on rotation {
        from: 0; to: 360
        duration: 1000
        loops: Animation.Infinite
    }
}
```

Available: `OpacityAnimator`, `RotationAnimator`, `ScaleAnimator`,
`XAnimator`, `YAnimator`, `NumberAnimator` (generic),
`UniformAnimator`. **Only animates the hot set** — you cannot animate
arbitrary properties with an Animator, only opacity/rotation/scale/
position/shader uniforms. For anything else, fall back to
`PropertyAnimation` and accept that it'll stall during GUI-thread
blocks.

---

## `SpringAnimation` — natural motion

Springs are physical models: you specify stiffness, damping, mass,
and the animation solves the ODE. Great for drag-release and
"settle into place" motion.

```qml
Rectangle {
    id: ball
    width: 60; height: 60; radius: 30; color: "#2d7ff9"
    x: 0; y: 0

    Behavior on x { SpringAnimation { spring: 2; damping: 0.2; epsilon: 0.25 } }
    Behavior on y { SpringAnimation { spring: 2; damping: 0.2; epsilon: 0.25 } }

    MouseArea {
        anchors.fill: parent
        drag.target: ball
        onReleased: { ball.x = 0; ball.y = 0 }
    }
}
```

Drag the ball, release — it springs back to origin with damped
oscillation. The same thing with a `NumberAnimation` feels dead by
comparison.

Parameters:
- **`spring`** — stiffness. Higher = faster return, more overshoot.
- **`damping`** — friction. `0` = undamped (oscillates forever),
  `1` = critically damped (no oscillation).
- **`mass`** — inertia. Higher = slower start, longer tail.
- **`epsilon`** — "close enough to target, stop" threshold.
- **`modulus`** — for wrap-around values (e.g. hue 0→360).

---

## Built-in styles that already animate

Qt Quick Controls ships with multiple styles. Several implement
motion out of the box — picking the right style gets you modern
animation for free:

- **Basic** — minimal, fewest animations. Embedded / low-end hardware.
- **Fusion** — platform-agnostic, driven by the system palette.
  Subtle hover and pressed transitions.
- **Material** — Google Material Design 2. Ripples, elevation
  shadows, the full Material motion vocabulary. Attached
  `Material.theme: Material.Dark` / `Material.Light`.
- **Universal** — Microsoft Fluent Design (Windows). Reveal
  highlights, acrylic, Fluent's state transitions.
- **iOS / macOS / Windows** — native looks on the matching platforms.
- **Imagine** — nine-patch image-driven style for heavily branded
  UIs.

### Picking a style

Three options, in order of preference:

```ini
# qtquickcontrols2.conf (compiled into the binary)
[Controls]
Style=Material

[Material]
Theme=Dark
Primary=BlueGrey
Accent=Cyan
```

```bash
# command-line
./myapp -style Material
```

```bash
# environment
QT_QUICK_CONTROLS_STYLE=Material ./myapp
```

The config file is the production path — it travels with the binary
and can be overridden by the other two for development.

### Qt Labs StyleKit (Qt 6.11, technology preview)

A new declarative styling framework where you define a single
`Style` object with grouped tokens
(`abstractButton.background.radius`, `textStyle.color`,
`motion.standard`, …) and every control picks them up. Under
`Qt.labs`, so the API is not covered by Qt's compatibility promise
and can change between releases. Worth tracking; not worth building
on yet.

---

## Embedding QML in a widget app

If we ever want QML animations for one specific surface without
rewriting the app, the pattern is `QQuickWidget`:

```python
from PySide6.QtCore       import QUrl
from PySide6.QtQuickWidgets import QQuickWidget

quick = QQuickWidget(parent)
quick.setSource(QUrl("qrc:/animations/OnboardingTour.qml"))
quick.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
layout.addWidget(quick)
```

`QQuickWidget` renders QML to an offscreen framebuffer and blits it
into the widget tree. Downsides: extra GPU cost, separate event
handling inside the QML subtree, harder to debug the seam. Good for
bounded surfaces (a chart widget, a gauge, a splash sequence). Bad
for peppering QML throughout the whole app — at that point, port to
`QQmlApplicationEngine` properly.

---

## Decision table: widgets vs QML vs QQuickWidget

| Situation                                          | Pick                            |
|----------------------------------------------------|---------------------------------|
| Existing widget-based app (Terragraf today)        | Widgets + `QPropertyAnimation`  |
| New app, motion-heavy, no legacy                   | Qt Quick                        |
| Widget app + one animated surface (chart, gauge)   | `QQuickWidget` for that surface |
| Widget app + many hover/fade polishings            | Widgets + effects (3-4 lines each) |
| Scientific dense data UI with thousands of widgets | Widgets — QML is overkill       |
| Embedded / automotive / HMI                        | Qt Quick                        |
| Need to ship on iOS/macOS with native look         | Qt Quick (iOS/macOS styles)     |

---

## Takeaway

For Terragraf's current scope, widgets + QSS + the Animation
Framework are the right tools. This file exists so that the next
time someone says "this would be one line in CSS", we know what
that one line of QML would look like, and whether it's worth
introducing a `QQuickWidget` for that surface or just writing the
20 lines of Python.
