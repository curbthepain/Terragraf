"""AnalyzeDialog — terra analyze <input>."""

from ..command_dialog import CommandDialog, FieldSpec


class AnalyzeDialog(CommandDialog):
    TITLE = "Analyze Signal"
    _run_async = True
    _run_streaming = True
    FIELDS = [
        FieldSpec("input", "Input file", kind="file",
                  file_filter="Audio (*.wav *.mp3 *.flac);;All (*.*)"),
        FieldSpec("synthetic", "Use synthetic signal", kind="checkbox",
                  default=False),
        FieldSpec("bandpass_low", "Bandpass low (Hz)", kind="float",
                  default=0.0, minimum=0.0, maximum=100000.0, step=10.0),
        FieldSpec("bandpass_high", "Bandpass high (Hz)", kind="float",
                  default=0.0, minimum=0.0, maximum=100000.0, step=10.0),
        FieldSpec("mel", "Mel spectrogram", kind="checkbox", default=False),
        FieldSpec("output", "Output file", kind="file",
                  file_filter="All (*.*)"),
        FieldSpec("no_render", "Skip render", kind="checkbox", default=False),
    ]

    def run(self, values: dict) -> str:
        args: list[str] = []
        if values.get("input"):
            args.append(values["input"])
        elif values.get("synthetic"):
            args.append("--synthetic")
        else:
            return "Provide an input file or check 'synthetic'."

        low = values.get("bandpass_low") or 0.0
        high = values.get("bandpass_high") or 0.0
        if low > 0 and high > 0:
            args += ["--bandpass", f"{low}-{high}"]
        if values.get("mel"):
            args.append("--mel")
        if values.get("output"):
            args += ["--output", values["output"]]
        if values.get("no_render"):
            args.append("--no-render")
        return self.run_skill_streaming("signal_analyze", args)
