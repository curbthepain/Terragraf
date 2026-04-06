"""
scaffold_project — Creates a new project directory with standard structure.

Usage:
    python run.py <name> [--type qt-app|cli|lib|test]
"""

import argparse
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

TERRA_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROJECTS_DIR = TERRA_ROOT / "projects"

PROJECT_TYPES = ["cli", "qt-app", "lib", "test"]


def create_project(name, project_type="cli"):
    project_dir = PROJECTS_DIR / name

    if project_dir.exists():
        print(f"Error: project '{name}' already exists at {project_dir}")
        return 1

    project_dir.mkdir(parents=True)

    # PROJECT.toml
    now = datetime.now(timezone.utc).isoformat()
    (project_dir / "PROJECT.toml").write_text(textwrap.dedent(f"""\
        [project]
        name = "{name}"
        type = "{project_type}"
        version = "0.1"
        created = "{now}"
        description = ""

        [deps]
        python = ">=3.11"
    """))

    # requirements.txt
    reqs = _requirements_for_type(project_type)
    (project_dir / "requirements.txt").write_text(reqs)

    # main.py
    main_code = _main_for_type(name, project_type)
    (project_dir / "main.py").write_text(main_code)

    # README.md
    (project_dir / "README.md").write_text(f"# {name}\n\nA Terragraf {project_type} project.\n")

    print(f"Project '{name}' created at {project_dir}")
    print(f"  type: {project_type}")
    print(f"  files: PROJECT.toml, main.py, requirements.txt, README.md")
    print()
    print(f"  tip: use 'terra knowledge add' to record patterns and decisions as you build")
    return 0


def _requirements_for_type(project_type):
    if project_type == "qt-app":
        return "PySide6>=6.6\n"
    elif project_type == "test":
        return "pytest>=7.0\n"
    return "# add dependencies here\n"


def _main_for_type(name, project_type):
    if project_type == "qt-app":
        return textwrap.dedent(f'''\
            """
            {name} — Qt application.
            """
            import sys
            from pathlib import Path

            from PySide6.QtWidgets import QApplication, QMainWindow, QLabel

            # Import Terragraf theme
            SCAFFOLD = Path(__file__).resolve().parent.parent.parent / ".scaffold"
            sys.path.insert(0, str(SCAFFOLD))
            try:
                from app.theme import apply_theme
            except ImportError:
                apply_theme = None


            class MainWindow(QMainWindow):
                def __init__(self):
                    super().__init__()
                    self.setWindowTitle("{name}")
                    self.setMinimumSize(800, 600)
                    self.setCentralWidget(QLabel("{name}"))


            def main():
                app = QApplication(sys.argv)
                if apply_theme:
                    apply_theme(app)
                window = MainWindow()
                window.show()
                sys.exit(app.exec())


            if __name__ == "__main__":
                main()
        ''')
    elif project_type == "lib":
        return textwrap.dedent(f'''\
            """
            {name} — library module.
            """


            def hello():
                return "{name} is ready"
        ''')
    elif project_type == "test":
        return textwrap.dedent(f'''\
            """
            {name} — test project.
            """
            import pytest


            def test_placeholder():
                assert True, "{name} test scaffold"
        ''')
    else:  # cli
        return textwrap.dedent(f'''\
            """
            {name} — CLI application.
            """
            import argparse
            import sys


            def main():
                parser = argparse.ArgumentParser(description="{name}")
                parser.add_argument("--version", action="version", version="0.1")
                args = parser.parse_args()
                print("{name} is ready")


            if __name__ == "__main__":
                main()
        ''')


def cli():
    parser = argparse.ArgumentParser(description="Scaffold a new project")
    parser.add_argument("name", help="Project name")
    parser.add_argument("--type", choices=PROJECT_TYPES, default="cli",
                        help="Project type (default: cli)")
    args = parser.parse_args()
    sys.exit(create_project(args.name, args.type))


if __name__ == "__main__":
    cli()
