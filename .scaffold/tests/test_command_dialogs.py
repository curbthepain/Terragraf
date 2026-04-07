"""Tests for Session 18 form dialogs — construction + field presence."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import PySide6  # noqa: F401
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

needs_qt = pytest.mark.skipif(not HAS_PYSIDE6, reason="PySide6 not installed")


@pytest.fixture(scope="session", autouse=True)
def _ensure_qapp():
    if not HAS_PYSIDE6:
        yield
        return
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


# ── Construction tests ────────────────────────────────────────────────

@needs_qt
def test_generate_dialog_constructs():
    from app.widgets.dialogs.generate import GenerateDialog
    dlg = GenerateDialog()
    assert dlg.windowTitle() == "Generate Code"
    assert "type" in dlg._widgets
    assert "name" in dlg._widgets


@needs_qt
def test_train_dialog_constructs():
    from app.widgets.dialogs.train import TrainDialog
    dlg = TrainDialog()
    assert dlg.windowTitle() == "Train Model"
    assert dlg._run_async is True


@needs_qt
def test_train_dialog_has_all_cli_flags():
    """TrainDialog must expose every flag from train_model/run.py."""
    from app.widgets.dialogs.train import TrainDialog
    dlg = TrainDialog()
    expected = {
        "arch", "data_dir", "dataset", "epochs", "batch_size", "lr",
        "optimizer", "scheduler", "num_classes", "early_stopping",
        "grad_clip", "weight_decay", "export", "config", "resume",
    }
    assert expected.issubset(set(dlg._widgets.keys()))


@needs_qt
def test_solve_dialog_constructs():
    from app.widgets.dialogs.solve import SolveDialog
    dlg = SolveDialog()
    assert dlg.windowTitle() == "Solve Math"
    # All operations from terra solve should be in choices
    op_widget = dlg._widgets["operation"]
    items = [op_widget.itemText(i) for i in range(op_widget.count())]
    assert "eigenvalues" in items
    assert "svd" in items
    assert "fit" in items


@needs_qt
def test_analyze_dialog_constructs():
    from app.widgets.dialogs.analyze import AnalyzeDialog
    dlg = AnalyzeDialog()
    assert "input" in dlg._widgets
    assert "synthetic" in dlg._widgets
    assert "mel" in dlg._widgets


@needs_qt
def test_render_dialog_constructs():
    from app.widgets.dialogs.render import RenderDialog
    dlg = RenderDialog()
    type_widget = dlg._widgets["type"]
    items = [type_widget.itemText(i) for i in range(type_widget.count())]
    assert {"surface", "volume", "nodes", "points", "demo"} <= set(items)


@needs_qt
def test_branch_dialog_constructs():
    from app.widgets.dialogs.branch import BranchDialog
    dlg = BranchDialog()
    type_widget = dlg._widgets["branch_type"]
    items = [type_widget.itemText(i) for i in range(type_widget.count())]
    assert {"feature", "fix", "refactor", "docs", "ci", "test", "chore"} <= set(items)


@needs_qt
def test_commit_dialog_constructs():
    from app.widgets.dialogs.commit import CommitDialog
    dlg = CommitDialog()
    assert "message" in dlg._widgets
    assert "auto" in dlg._widgets


@needs_qt
def test_git_flow_dialog_has_three_tabs():
    from app.widgets.dialogs.git_flow import GitFlowDialog
    dlg = GitFlowDialog()
    # GitFlowDialog uses a QTabWidget; verify three tabs
    from PySide6.QtWidgets import QTabWidget
    tab_widgets = dlg.findChildren(QTabWidget)
    assert tab_widgets
    assert tab_widgets[0].count() == 3


@needs_qt
def test_knowledge_add_dialog_constructs():
    from app.widgets.dialogs.knowledge_add import KnowledgeAddDialog
    dlg = KnowledgeAddDialog()
    assert {"id", "summary", "type", "content", "tags"} <= set(dlg._widgets.keys())


@needs_qt
def test_project_new_dialog_constructs():
    from app.widgets.dialogs.project_new import ProjectNewDialog
    dlg = ProjectNewDialog()
    assert "name" in dlg._widgets
    assert "type" in dlg._widgets


@needs_qt
def test_worktree_create_dialog_constructs():
    from app.widgets.dialogs.worktree_create import WorktreeCreateDialog
    dlg = WorktreeCreateDialog()
    assert "task_id" in dlg._widgets
    assert "base_ref" in dlg._widgets


@needs_qt
def test_dispatch_dialog_constructs():
    from app.widgets.dialogs.dispatch import DispatchDialog
    dlg = DispatchDialog()
    assert "task" in dlg._widgets
    assert "instance_count" in dlg._widgets
    assert "use_worktree" in dlg._widgets


# ── Streaming infrastructure ──────────────────────────────────────────

@needs_qt
def test_train_dialog_is_streaming():
    from app.widgets.dialogs.train import TrainDialog
    dlg = TrainDialog()
    assert dlg._run_streaming is True


@needs_qt
def test_train_dialog_streams_lines_sync(monkeypatch):
    """Force sync mode and monkeypatch run_skill_stream — verify chunks
    land in the output area incrementally instead of as a single dump."""
    from app.widgets.dialogs.train import TrainDialog
    import skills.runner as runner

    sample_lines = [
        "epoch 1/2 train_loss=0.5",
        "epoch 1/2 val_loss=0.42",
        "epoch 2/2 train_loss=0.3",
        "epoch 2/2 val_loss=0.28",
        "saved checkpoint to /tmp/model.pt",
    ]

    def fake_stream(name, args, on_line=None):
        assert name == "train_model"
        for line in sample_lines:
            if on_line is not None:
                on_line(line)
        return 0

    monkeypatch.setattr(runner, "run_skill_stream", fake_stream)

    dlg = TrainDialog()
    dlg._run_async = False  # force sync path so we can assert immediately
    dlg._on_run_clicked()

    text = dlg.output.toPlainText()
    for line in sample_lines:
        assert line in text
    assert dlg._chunks_received == len(sample_lines)


# ── Per-dialog streaming (Session 20) ─────────────────────────────────
#
# Every dialog that wraps a skill via run_skill_streaming should:
#   (a) declare _run_async = _run_streaming = True
#   (b) feed chunks from runner.run_skill_stream into self.output
#
# Each tuple is (module_basename, class_name, expected_skill_name, setup_fn)
# where setup_fn pre-populates widgets so the run() method gets past any
# validation guard and actually reaches run_skill_streaming().

STREAMING_DIALOGS = [
    ("generate", "GenerateDialog", "generate",
     lambda d: d._widgets["name"].setText("foo")),
    ("solve", "SolveDialog", "math_solve", None),
    ("analyze", "AnalyzeDialog", "signal_analyze",
     lambda d: d._widgets["synthetic"].setChecked(True)),
    ("render", "RenderDialog", "render_3d", None),
    ("branch", "BranchDialog", "git_flow",
     lambda d: d._widgets["name"].setText("foo")),
    ("commit", "CommitDialog", "git_flow", None),
    ("git_flow", "_PRDialog", "git_flow", None),
    ("project_new", "ProjectNewDialog", "scaffold_project",
     lambda d: d._widgets["name"].setText("foo")),
    ("dispatch", "DispatchDialog", "instance_dispatch",
     lambda d: d._widgets["task"].setPlainText("do stuff")),
]


@needs_qt
@pytest.mark.parametrize("module,cls_name,skill,setup", STREAMING_DIALOGS)
def test_dialog_is_streaming(module, cls_name, skill, setup):
    import importlib
    mod = importlib.import_module(f"app.widgets.dialogs.{module}")
    dlg = getattr(mod, cls_name)()
    assert dlg._run_streaming is True
    assert dlg._run_async is True


@needs_qt
@pytest.mark.parametrize("module,cls_name,skill,setup", STREAMING_DIALOGS)
def test_dialog_streams_lines_sync(monkeypatch, module, cls_name, skill, setup):
    """Force sync mode and monkeypatch run_skill_stream — verify chunks
    arrive incrementally and the dialog routes them to the right skill."""
    import importlib
    import skills.runner as runner

    sample = [f"chunk {i}" for i in range(3)]
    captured: list[str] = []

    def fake_stream(name, args, on_line=None):
        captured.append(name)
        for line in sample:
            if on_line is not None:
                on_line(line)
        return 0

    monkeypatch.setattr(runner, "run_skill_stream", fake_stream)

    mod = importlib.import_module(f"app.widgets.dialogs.{module}")
    dlg = getattr(mod, cls_name)()
    if setup:
        setup(dlg)
    dlg._run_async = False  # sync path so we can assert immediately
    dlg._on_run_clicked()

    text = dlg.output.toPlainText()
    for line in sample:
        assert line in text, f"missing {line!r} in output: {text!r}"
    assert dlg._chunks_received == len(sample)
    assert captured == [skill]


def test_run_skill_stream_invokes_on_line(tmp_path):
    """runner.run_skill_stream wires Popen to on_line callback line by line."""
    import sys as _sys
    from pathlib import Path as _P
    _sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
    import skills.runner as runner

    # Build a tiny throwaway skill in a tmp dir, point runner at it
    skill_dir = tmp_path / "stream_smoke"
    skill_dir.mkdir()
    (skill_dir / "SKILL.toml").write_text(
        '[skill]\nname = "stream_smoke"\nentry = "run.py"\n', encoding="utf-8"
    )
    (skill_dir / "run.py").write_text(
        "import sys\n"
        "for i in range(3):\n"
        "    print(f'line {i}')\n"
        "    sys.stdout.flush()\n",
        encoding="utf-8",
    )

    # Patch SKILLS_DIR temporarily
    original = runner.SKILLS_DIR
    runner.SKILLS_DIR = tmp_path
    try:
        received: list[str] = []
        rc = runner.run_skill_stream("stream_smoke", [], on_line=received.append)
        assert rc == 0
        assert received == ["line 0", "line 1", "line 2"]
    finally:
        runner.SKILLS_DIR = original
