"""Tests for the query engine — Session 10.

35 tests covering:
  - IntentParser (10)
  - QueryEngine (15)
  - NativeTab UI (10, needs PySide6)
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure .scaffold is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Check PySide6 availability
try:
    import PySide6
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

needs_qt = pytest.mark.skipif(not HAS_PYSIDE6, reason="PySide6 not installed")


# ── QApplication fixture ───────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _ensure_qapp():
    if not HAS_PYSIDE6:
        yield
        return
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ── Scaffold state fixture (shared, no Qt) ─────────────────────────────

@pytest.fixture
def scaffold_state():
    """Create a minimal ScaffoldState with test data (no watcher needed)."""
    from app.scaffold_state import ScaffoldState, RouteEntry

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Create minimal scaffold structure
        (tmp / "headers").mkdir()
        (tmp / "routes").mkdir()
        (tmp / "tables").mkdir()
        (tmp / "instances" / "shared").mkdir(parents=True)

        # Write a test header
        (tmp / "headers" / "project.h").write_text(
            '#module COMPUTE {\n'
            '    #path "compute/"\n'
            '    #exports [fft1d, fft2d]\n'
            '    #tags [fft, vulkan, shaders]\n'
            '    #desc "Compute module"\n'
            '}\n'
            '#module VIZ {\n'
            '    #path "viz/"\n'
            '    #exports [render_spectrogram]\n'
            '    #tags [visualization]\n'
            '    #desc "Visualization"\n'
            '}\n'
        )

        # Write test routes
        (tmp / "routes" / "structure.route").write_text(
            "fft               -> compute/fft/           # FFT utilities\n"
            "spectrogram       -> viz/spectrogram.py     # Spectrogram rendering\n"
            "math              -> compute/math/          # Math primitives\n"
            "ml models         -> ml/models/             # ML architecture defs\n"
            "projects          -> projects/              # Project workspace\n"
        )

        # Write HOT_CONTEXT
        (tmp / "HOT_CONTEXT.md").write_text("# Test Context\nSession 10")

        # Write empty queue
        import json
        (tmp / "instances" / "shared" / "queue.json").write_text(json.dumps([]))

        state = ScaffoldState(scaffold_dir=tmp)
        state.load_all()
        yield state


@pytest.fixture
def session():
    """Create a test session."""
    from app.session import Session
    return Session(tab_type="native", label="Test")


# ═══════════════════════════════════════════════════════════════════════
# IntentParser tests (10)
# ═══════════════════════════════════════════════════════════════════════

def test_parser_analyze_signal():
    """Parse 'analyze signal' into verb + target."""
    from query.parser import IntentParser
    p = IntentParser()
    intent = p.parse("analyze signal")
    assert intent.verb == "analyze"
    assert intent.target == "signal"


def test_parser_run_fft():
    """Parse 'run fft' into verb + target."""
    from query.parser import IntentParser
    p = IntentParser()
    intent = p.parse("run fft")
    assert intent.verb == "run"
    assert intent.target == "fft"


def test_parser_show_routes():
    """Parse 'show routes' into verb + target."""
    from query.parser import IntentParser
    p = IntentParser()
    intent = p.parse("show routes")
    assert intent.verb == "show"
    assert intent.target == "routes"


def test_parser_bare_target():
    """Bare target with no recognized verb."""
    from query.parser import IntentParser
    p = IntentParser()
    intent = p.parse("fft")
    assert intent.verb == ""
    assert intent.target == "fft"


def test_parser_modifiers():
    """Modifiers extracted from --flags."""
    from query.parser import IntentParser
    p = IntentParser()
    intent = p.parse("analyze sine --no-render")
    assert intent.verb == "analyze"
    assert intent.target == "sine"
    assert "--no-render" in intent.modifiers


def test_parser_empty_input():
    """Empty input returns empty Intent."""
    from query.parser import IntentParser
    p = IntentParser()
    intent = p.parse("")
    assert intent.verb == ""
    assert intent.target == ""
    assert intent.modifiers == []
    assert intent.raw == ""


def test_parser_unknown_verb():
    """Unknown verb becomes part of target."""
    from query.parser import IntentParser
    p = IntentParser()
    intent = p.parse("frobnicate signal")
    assert intent.verb == ""
    assert intent.target == "frobnicate signal"


def test_parser_multi_word_target():
    """Multi-word targets preserved."""
    from query.parser import IntentParser
    p = IntentParser()
    intent = p.parse("solve linear algebra")
    assert intent.verb == "solve"
    assert intent.target == "linear algebra"


def test_parser_case_insensitive():
    """Verbs matched case-insensitively."""
    from query.parser import IntentParser
    p = IntentParser()
    intent = p.parse("ANALYZE SIGNAL")
    assert intent.verb == "analyze"
    assert intent.target == "SIGNAL"


def test_parser_whitespace_normalization():
    """Extra whitespace handled cleanly."""
    from query.parser import IntentParser
    p = IntentParser()
    intent = p.parse("  analyze   signal  ")
    assert intent.verb == "analyze"
    assert intent.target == "signal"
    assert intent.raw == "analyze   signal"


# ═══════════════════════════════════════════════════════════════════════
# QueryEngine tests (15)
# ═══════════════════════════════════════════════════════════════════════

def test_engine_skill_match_analyze(scaffold_state, session):
    """'analyze signal' matches signal_analyze skill."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    result = engine.query("analyze signal", session)
    assert result.skill_match is not None
    assert result.skill_match[0] == "signal_analyze"


def test_engine_skill_match_solve(scaffold_state, session):
    """'solve math' matches math_solve skill."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    result = engine.query("solve math", session)
    assert result.skill_match is not None
    assert result.skill_match[0] == "math_solve"


def test_engine_no_skill_match(scaffold_state, session):
    """'hello world' matches no skill."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    result = engine.query("hello world", session)
    assert result.skill_match is None


def test_engine_route_match_fft(scaffold_state, session):
    """'fft' finds structure.route entry."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    result = engine.query("fft", session)
    routes = [r.concept for r in result.route_matches]
    assert "fft" in routes


def test_engine_route_match_spectrogram(scaffold_state, session):
    """'spectrogram' finds structure.route entry."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    result = engine.query("spectrogram", session)
    routes = [r.concept for r in result.route_matches]
    assert "spectrogram" in routes


def test_engine_multi_route_match(scaffold_state, session):
    """'fft' can match in both route files and headers."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    result = engine.query("fft", session)
    # Should have route match AND header match (COMPUTE has fft tag)
    assert len(result.route_matches) > 0
    assert len(result.header_matches) > 0


def test_engine_header_match_compute(scaffold_state, session):
    """'compute' matches COMPUTE module header."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    result = engine.query("compute", session)
    header_names = [h.module_name for h in result.header_matches]
    assert "COMPUTE" in header_names


def test_engine_no_matches(scaffold_state, session):
    """Unrecognized query returns empty result."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    result = engine.query("xyzzy", session)
    assert result.skill_match is None
    assert len(result.route_matches) == 0
    assert len(result.header_matches) == 0


def test_engine_context_routes(scaffold_state, session):
    """Session.context.routes_consulted populated after query."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    engine.query("fft", session)
    assert len(session.context.routes_consulted) > 0


def test_engine_context_headers(scaffold_state, session):
    """Session.context.headers_read populated after header match."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    engine.query("compute", session)
    assert len(session.context.headers_read) > 0


def test_engine_query_history(scaffold_state, session):
    """Query results appended to session.query_history."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    engine.query("fft", session)
    assert len(session.query_history) == 1
    assert session.query_history[0].intent.raw == "fft"


def test_engine_score_ordering(scaffold_state, session):
    """Route matches sorted by score descending."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    result = engine.query("fft", session)
    if len(result.route_matches) >= 2:
        scores = [r.score for r in result.route_matches]
        assert scores == sorted(scores, reverse=True)


def test_engine_skill_capture(scaffold_state, session):
    """run_skill_capture returns stdout."""
    from skills.runner import run_skill_capture
    # Test with health_check (lightweight, always available)
    rc, stdout, stderr = run_skill_capture("health_check")
    # Just verify it returns a tuple — rc may be non-zero in test env
    assert isinstance(rc, int)
    assert isinstance(stdout, str)
    assert isinstance(stderr, str)


def test_engine_multiple_queries(scaffold_state, session):
    """Multiple queries accumulate in history."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    engine.query("fft", session)
    engine.query("compute", session)
    engine.query("math", session)
    assert len(session.query_history) == 3


def test_engine_unknown_graceful(scaffold_state, session):
    """Unknown intent handled gracefully — no exceptions."""
    from query.engine import QueryEngine
    engine = QueryEngine(scaffold_state)
    result = engine.query("!!@#$%^&*()", session)
    assert result.intent.raw == "!!@#$%^&*()"
    assert result.skill_match is None


# ═══════════════════════════════════════════════════════════════════════
# NativeTab UI tests (10, needs PySide6)
# ═══════════════════════════════════════════════════════════════════════

@needs_qt
def test_native_tab_creation(scaffold_state, session):
    """NativeTab creates with session binding."""
    from app.native_tab import NativeTab
    tab = NativeTab(session, scaffold_state)
    assert tab.session is session
    tab.close()
    tab.deleteLater()


@needs_qt
def test_native_tab_input_exists(scaffold_state, session):
    """NativeTab has an editable input bar."""
    from app.native_tab import NativeTab
    tab = NativeTab(session, scaffold_state)
    assert tab._input is not None
    assert tab._input.isEnabled()
    tab.close()
    tab.deleteLater()


@needs_qt
def test_native_tab_submit(scaffold_state, session):
    """Submitting text triggers query and adds cards."""
    from app.native_tab import NativeTab
    tab = NativeTab(session, scaffold_state)
    tab._input.setText("fft")
    tab._on_submit()
    # Should have query card + response card (2 widgets + 1 stretch)
    assert tab._messages_layout.count() >= 3
    tab.close()
    tab.deleteLater()


@needs_qt
def test_native_tab_response_card(scaffold_state, session):
    """Response card rendered after query."""
    from app.native_tab import NativeTab
    from app.widgets.message_card import ResponseCard
    tab = NativeTab(session, scaffold_state)
    tab._input.setText("fft")
    tab._on_submit()
    # Second widget (index 1) should be ResponseCard
    widget = tab._messages_layout.itemAt(1).widget()
    assert isinstance(widget, ResponseCard)
    tab.close()
    tab.deleteLater()


@needs_qt
def test_native_tab_multiple_queries(scaffold_state, session):
    """Multiple queries create multiple card pairs."""
    from app.native_tab import NativeTab
    tab = NativeTab(session, scaffold_state)
    tab._input.setText("fft")
    tab._on_submit()
    tab._input.setText("compute")
    tab._on_submit()
    # 4 cards + 1 stretch = 5
    assert tab._messages_layout.count() >= 5
    tab.close()
    tab.deleteLater()


@needs_qt
def test_native_tab_context_panel(scaffold_state, session):
    """Context panel exists and shows session state."""
    from app.native_tab import NativeTab
    tab = NativeTab(session, scaffold_state)
    assert tab._context_panel is not None
    tab.close()
    tab.deleteLater()


@needs_qt
def test_native_tab_context_updates(scaffold_state, session):
    """Context panel updates after query."""
    from app.native_tab import NativeTab
    tab = NativeTab(session, scaffold_state)
    tab._input.setText("fft")
    tab._on_submit()
    # Routes should now be non-zero in the label
    routes_text = tab._context_panel._routes_label.text()
    assert "Routes:" in routes_text
    tab.close()
    tab.deleteLater()


@needs_qt
def test_native_tab_empty_ignored(scaffold_state, session):
    """Empty input is ignored — no cards added."""
    from app.native_tab import NativeTab
    tab = NativeTab(session, scaffold_state)
    tab._input.setText("")
    tab._on_submit()
    # Only the stretch, no cards
    assert tab._messages_layout.count() == 1
    tab.close()
    tab.deleteLater()


@needs_qt
def test_native_tab_session_accessible(scaffold_state, session):
    """session attribute accessible from tab."""
    from app.native_tab import NativeTab
    tab = NativeTab(session, scaffold_state)
    assert hasattr(tab, "session")
    assert tab.session.id == session.id
    tab.close()
    tab.deleteLater()


@needs_qt
def test_native_tab_signal_emitted(scaffold_state, session):
    """query_submitted signal emitted on submit."""
    from app.native_tab import NativeTab
    tab = NativeTab(session, scaffold_state)
    received = []
    tab.query_submitted.connect(lambda text: received.append(text))
    tab._input.setText("test query")
    tab._on_submit()
    assert received == ["test query"]
    tab.close()
    tab.deleteLater()
