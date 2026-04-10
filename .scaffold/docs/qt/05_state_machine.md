# QStateMachine + QML States/Transitions

> Sources: Qt 6.11 `QStateMachine` class reference + QML `states`/
> `transitions` documentation. PySide6 mirrors the C++ API.

State machines are the declarative alternative to "fire an animation
on every button click". Instead of saying *how* the UI should move,
you describe *what* it looks like in each state — and the framework
fills in the interpolation between states automatically.

Two implementations coexist in Qt 6.11: the C++/Python
`QStateMachine` framework for widgets, and the QML
`states: [...] / transitions: [...]` system for Qt Quick. They share
concepts but live in different modules and have different
ergonomics.

---

## When to use a state machine (vs. imperative animation)

Use a state machine when:
- The widget has **3+ visual configurations** and transitions between
  any pair are possible (not just forward/backward).
- You want to guarantee the widget can never get stuck in a
  "half-expanded" or "partially animated" inconsistent state.
- Multiple properties must change together per state (size, color,
  opacity, icon) and you'd rather declare the configurations than
  wire up N parallel animations per click.
- You want to attach default animations to a transition and have the
  framework pick up any property that changed.

Stick with imperative `QPropertyAnimation` when:
- You have **2 states** (open/closed, active/inactive) — the overhead
  of a state machine is larger than the code it saves.
- The transition is a one-shot (a pop-up fade-in-fade-out).
- You need to animate to a target value that's computed at
  transition time, not declared upfront.

---

## The C++/Python path: `QStateMachine`

### Module

```
Header:    #include <QStateMachine>
CMake:     find_package(Qt6 REQUIRED COMPONENTS StateMachine)
           target_link_libraries(mytarget PRIVATE Qt6::StateMachine)
qmake:     QT += statemachine
PySide6:   from PySide6.QtStateMachine import QStateMachine, QState, ...
```

**Gotcha**: State Machine is a **separate module** in Qt 6 — not part
of Core. You must add it explicitly to your CMake `find_package`
and link line. In PySide6 it lives under `PySide6.QtStateMachine`,
not `PySide6.QtCore`.

### Core classes

```
QAbstractState
 ├── QState                    — a regular state
 │    ├── QFinalState          — terminal; machine emits finished()
 │    └── QHistoryState        — remembers the last sub-state visited
 └── (QStateMachine inherits QState)

QAbstractTransition
 ├── QSignalTransition         — triggered by a Qt signal
 ├── QEventTransition          — triggered by a QEvent on a watched object
 └── QKeyEventTransition / QMouseEventTransition
```

### Canonical example: collapsible panel

```python
from PySide6.QtStateMachine import QStateMachine, QState
from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QPushButton, QFrame

class CollapsiblePanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._toggle_btn = QPushButton("Toggle", self)

        # 1. Build the state machine
        self._machine = QStateMachine(self)

        collapsed = QState(self._machine)
        collapsed.assignProperty(self, b"maximumHeight", 40)

        expanded = QState(self._machine)
        expanded.assignProperty(self, b"maximumHeight", 300)

        # 2. Wire transitions — button click flips states
        collapsed.addTransition(self._toggle_btn.clicked, expanded)
        expanded.addTransition(self._toggle_btn.clicked, collapsed)

        # 3. Default animation — the machine will apply this to any
        # transition that touches maximumHeight.
        anim = QPropertyAnimation(self, b"maximumHeight")
        anim.setDuration(240)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._machine.addDefaultAnimation(anim)

        # 4. Start
        self._machine.setInitialState(collapsed)
        self._machine.start()
```

The machine **guarantees** `maximumHeight` is either 40 or 300 at
rest, and always animated between them. There is no code path that
can leave the panel half-expanded. Button clicks that arrive while
the animation is running are queued and processed after the current
transition completes — no race conditions.

### `assignProperty` + `addDefaultAnimation`: the magic

- **`state.assignProperty(target, propertyName, value)`** declares
  "when this state is entered, `target.propertyName` should be set
  to `value`". Multiple `assignProperty` calls per state stack.
- **`machine.addDefaultAnimation(anim)`** registers an animation
  that the machine will try to use for any property change during a
  transition. When a state change causes multiple properties to
  change, the machine looks up a default animation for each and
  applies them in parallel.

This lets you declare three states touching five properties each,
and get smooth transitions between any pair with only one animation
per property.

### Signals you care about
- **`started()`** — fires after initial state is entered.
- **`finished()`** — fires when a `QFinalState` is entered.
- **`stopped()`** — fires when `stop()` is called explicitly.
- **`runningChanged(bool)`** — state machine start/stop.

### Event-driven transitions (non-signal)

`QSignalTransition` is the common case. For event-driven transitions
(e.g. "transition when the widget is resized"), use
`QEventTransition`:

```python
from PySide6.QtStateMachine import QEventTransition
from PySide6.QtCore import QEvent

transition = QEventTransition(self, QEvent.Type.Resize)
transition.setTargetState(expanded)
collapsed.addTransition(transition)
```

`postEvent()` / `postDelayedEvent()` lets you drive the machine
manually from outside — e.g. a timer that posts a custom event
after 5 seconds of idle to trigger a screensaver state.

### Errors to watch for

From the `QStateMachine::Error` enum:

- **`NoInitialStateError`** — you added child states to a parent
  `QState` without calling `setInitialState()` on the parent. The
  machine enters the parent, looks for a default child, finds none,
  and errors. Always set an initial state on any composite state.
- **`NoCommonAncestorForTransitionError`** — you wired a transition
  between states that aren't in the same state tree (one isn't in
  the machine yet, or it's in a different machine). Build your state
  graph fully before calling `start()`.
- **`StateMachineChildModeSetToParallelError`** — you called
  `machine.setChildMode(QState.ChildMode.ParallelStates)` on the
  **machine itself**. This is illegal in Qt 6. Only regular `QState`
  instances may be parallel; the top-level machine must be
  `ExclusiveStates` (the default). Leave this alone unless you know
  you're building a nested parallel state.

### Other things worth knowing

- **`machine.animated : bool`** — defaults `True`. Set `False` to
  disable *all* default animations on the machine. Useful for
  reduced-motion mode without tearing down the state graph.
- **`machine.globalRestorePolicy`** — when a property is assigned by
  a state, should its previous value be restored on exit? Default
  `DontRestoreProperties`. Set to `RestoreProperties` if you want
  "revert on leave" semantics instead of "stick at last assigned".
- **Thread safety**: `postEvent`, `postDelayedEvent`, and
  `cancelDelayedEvent` are thread-safe. Everything else runs on the
  thread that owns the machine.

---

## The QML path: `states` + `transitions`

QML expresses state machines declaratively inside an `Item`. Much
terser than the C++ version, but only works in Qt Quick.

### Anatomy

```qml
import QtQuick

Item {
    id: root
    width: 400; height: 300

    Rectangle {
        id: box
        width: 100; height: 100
        color: "#2d7ff9"
        radius: 8
    }

    // 1. Named states — property configurations
    states: [
        State {
            name: "topLeft"
            PropertyChanges { target: box; x: 0; y: 0; rotation: 0 }
        },
        State {
            name: "bottomRight"
            PropertyChanges {
                target: box
                x: root.width - box.width
                y: root.height - box.height
                rotation: 180
            }
        }
    ]

    // 2. Transitions — how to animate between states
    transitions: [
        Transition {
            from: "*"; to: "*"          // wildcard: any → any
            ParallelAnimation {
                NumberAnimation   { properties: "x,y"; duration: 420; easing.type: Easing.InOutCubic }
                RotationAnimation { duration: 420; direction: RotationAnimation.Shortest; easing.type: Easing.InOutCubic }
            }
        }
    ]

    // 3. Drive the state from application logic
    MouseArea {
        anchors.fill: parent
        onClicked: root.state = (root.state === "bottomRight" ? "topLeft" : "bottomRight")
    }
}
```

### Key ideas

**Named states vs. `when` expressions.** States can have a `name`
(transition with `root.state = "foo"`), or a `when:` boolean
expression that activates the state whenever the expression is true.
Only one `when` state should evaluate to true at a time — otherwise
the last one wins. Choose named when you drive state from code; use
`when` for stateless reactive bindings.

**Wildcard transitions.** `from: "*"; to: "*"` matches any state
change. If every state change should animate the same way, one
wildcard transition collapses dozens of per-pair transitions.

**Reversible transitions.** `Transition { reversible: true; from: "A"; to: "B"; ... }`
means the same animation applies in both directions — no need to
declare a separate B→A transition.

**`RotationAnimation.Shortest`.** A plain `NumberAnimation` on
`rotation` from 180 to 0 snaps across the full 180° arc. Use
`RotationAnimation` with `direction: RotationAnimation.Shortest` to
pick the shorter arc (0° via the 360° wrap). Other options:
`Clockwise`, `Counterclockwise`, `Numerical`.

### Two easy-to-hit pitfalls

1. **`state` defaults to empty string, not your first state name.**
   If you don't set an initial state, the `Item` starts in an
   unnamed base state where no `PropertyChanges` apply. Always set
   `state: "initial"` explicitly.

2. **Unmentioned properties revert to the original declaration, not
   the previous state's value.** If state A sets `color: "red"` and
   state B doesn't mention `color`, entering B reverts color to the
   original `color: "blue"` from the `Rectangle`'s declaration —
   *not* the "red" you set in A. Explicitly list every property in
   every state if you need precise control.

### Behaviors vs transitions (they're different)

- **`Behavior on propName`** → "whenever this property changes, for
  any reason, animate the change". Covered in
  `07_qt_quick_escape_hatch.md`.
- **`Transition { from; to; }`** → "when the state changes from X to
  Y, animate the property changes declared by the states".

If both match the same property on the same state change, **the
Transition wins** — Behaviors are suppressed during a Transition.
You cannot share a single animation instance between multiple
Transitions or Behaviors; each needs its own.

---

## Cross-cutting: pick your state-machine path

| Context                                  | Use                                    |
|------------------------------------------|----------------------------------------|
| `QWidget`-based app                      | `QStateMachine` (Python or C++)        |
| Qt Quick / QML app                       | `states` + `transitions`               |
| 3+ states with many property changes    | State machine (either flavour)         |
| 2 states, one-shot animation             | Plain `QPropertyAnimation`, no machine |
| Need guaranteed "cannot be half-state"   | State machine — enforced by the machine |
| Need mid-transition reversal             | Imperative `QPropertyAnimation`        |
| Timed auto-advance (screensaver, tour)   | `postDelayedEvent` + state machine     |
| Driving animations from UI input only    | Either; QML is terser                  |

The machine's guarantee of consistent configuration is its biggest
value. If you find yourself writing `if self._state == "expanded":`
branches everywhere to keep properties in sync, that's a signal to
reach for a state machine instead.
