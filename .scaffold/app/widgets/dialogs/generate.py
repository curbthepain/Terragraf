"""GenerateDialog — terra gen <type> <name>."""

from ..command_dialog import CommandDialog, FieldSpec


class GenerateDialog(CommandDialog):
    TITLE = "Generate Code"
    _run_async = True
    _run_streaming = True
    FIELDS = [
        FieldSpec("type", "Type", kind="choice",
                  choices=["module", "model", "shader"], default="module"),
        FieldSpec("name", "Name", kind="text", placeholder="my_module"),
        FieldSpec("language", "Language", kind="choice",
                  choices=["auto", "py", "cpp", "glsl"], default="auto"),
    ]

    def run(self, values: dict) -> str:
        args = [values["type"], values["name"]]
        if values.get("language") and values["language"] != "auto":
            args += ["--lang", values["language"]]
        return self.run_skill_streaming("generate", args)
