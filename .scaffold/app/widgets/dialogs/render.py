"""RenderDialog — terra render <type> <input>."""

from ..command_dialog import CommandDialog, FieldSpec


class RenderDialog(CommandDialog):
    TITLE = "3D Render"
    _run_async = True
    _run_streaming = True
    FIELDS = [
        FieldSpec("type", "Type", kind="choice",
                  choices=["surface", "volume", "nodes", "points", "demo"],
                  default="demo"),
        FieldSpec("input", "Input file", kind="file"),
        FieldSpec("output", "Output file", kind="file"),
    ]

    def run(self, values: dict) -> str:
        args: list[str] = [values["type"]]
        if values.get("input"):
            args.append(values["input"])
        if values.get("output"):
            args += ["--output", values["output"]]
        return self.run_skill_streaming("render_3d", args)
