"""SolveDialog — terra solve <op>."""

from ..command_dialog import CommandDialog, FieldSpec


class SolveDialog(CommandDialog):
    TITLE = "Solve Math"
    _run_async = True
    _run_streaming = True
    FIELDS = [
        FieldSpec("operation", "Operation", kind="choice",
                  choices=["eigenvalues", "eigenvectors", "svd", "solve",
                           "inverse", "fit", "roots", "describe",
                           "regression", "ttest", "dct", "hilbert"],
                  default="eigenvalues"),
        FieldSpec("matrix", "Matrix file", kind="file",
                  file_filter="Numpy (*.npy);;CSV (*.csv);;All (*.*)"),
        FieldSpec("A", "A (inline)", kind="text",
                  placeholder="[[1,2],[3,4]]"),
        FieldSpec("b", "b (inline)", kind="text", placeholder="[5,6]"),
        FieldSpec("x", "x (inline)", kind="text"),
        FieldSpec("y", "y (inline)", kind="text"),
        FieldSpec("data", "data (inline)", kind="text"),
        FieldSpec("degree", "Polynomial degree", kind="number",
                  default=2, minimum=0, maximum=20),
    ]

    def run(self, values: dict) -> str:
        args: list[str] = [values["operation"]]
        if values.get("matrix"):
            args += ["--matrix", values["matrix"]]
        for key in ("A", "b", "x", "y", "data"):
            v = values.get(key, "").strip()
            if v:
                args += [f"--{key}", v]
        if values.get("degree"):
            args += ["--degree", str(values["degree"])]
        return self.run_skill_streaming("math_solve", args)
