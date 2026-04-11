"""TrainDialog — full ML training pipeline configuration.

Mirrors flags from .scaffold/skills/train_model/run.py argparse.
SOURCE-OF-TRUTH: keep field list in sync with that file's cli().
"""

from ..command_dialog import CommandDialog, FieldSpec


class TrainDialog(CommandDialog):
    TITLE = "Train Model"
    _run_async = True  # training is the canonical long-running case
    _run_streaming = True  # incremental stdout via runner.run_skill_stream

    FIELDS = [
        FieldSpec("arch", "Architecture", kind="choice",
                  choices=["cnn", "transformer", "base"], default="cnn"),
        FieldSpec("data_dir", "Data directory", kind="dir",
                  placeholder="(or leave blank and use --dataset)"),
        FieldSpec("dataset", "Built-in dataset", kind="text",
                  placeholder="cifar10",
                  help="Use a built-in loader instead of data_dir"),
        FieldSpec("epochs", "Epochs", kind="number", default=5,
                  minimum=1, maximum=10000),
        FieldSpec("batch_size", "Batch size", kind="number", default=32,
                  minimum=1, maximum=4096),
        FieldSpec("lr", "Learning rate", kind="float", default=1e-3,
                  minimum=1e-7, maximum=10.0, step=1e-4),
        FieldSpec("optimizer", "Optimizer", kind="choice",
                  choices=["adam", "adamw", "sgd"], default="adam"),
        FieldSpec("scheduler", "Scheduler", kind="choice",
                  choices=["cosine", "step", "plateau", "none"], default="cosine"),
        FieldSpec("num_classes", "Num classes", kind="number", default=10,
                  minimum=1, maximum=10000),
        FieldSpec("early_stopping", "Early stopping patience",
                  kind="number", default=0, minimum=0, maximum=1000),
        FieldSpec("grad_clip", "Gradient clip norm", kind="float",
                  default=0.0, minimum=0.0, maximum=100.0, step=0.1),
        FieldSpec("weight_decay", "Weight decay", kind="float",
                  default=1e-4, minimum=0.0, maximum=1.0, step=1e-4),
        FieldSpec("export", "Export format", kind="choice",
                  choices=["none", "onnx", "safetensors", "torchscript"],
                  default="none"),
        FieldSpec("config", "Config (TOML)", kind="file",
                  file_filter="TOML (*.toml);;All files (*.*)"),
        FieldSpec("resume", "Resume from checkpoint", kind="file",
                  file_filter="Checkpoints (*.pt);;All files (*.*)"),
    ]

    def run(self, values: dict) -> str:
        args: list[str] = []
        if values.get("data_dir"):
            args.append(values["data_dir"])
        args += ["--arch", values["arch"]]
        if values.get("dataset"):
            args += ["--dataset", values["dataset"]]
        args += ["--epochs", str(values["epochs"])]
        args += ["--batch-size", str(values["batch_size"])]
        args += ["--lr", str(values["lr"])]
        args += ["--optimizer", values["optimizer"]]
        args += ["--scheduler", values["scheduler"]]
        args += ["--num-classes", str(values["num_classes"])]
        if values.get("early_stopping"):
            args += ["--early-stopping", str(values["early_stopping"])]
        if values.get("grad_clip"):
            args += ["--grad-clip", str(values["grad_clip"])]
        args += ["--weight-decay", str(values["weight_decay"])]
        if values.get("export") and values["export"] != "none":
            args += ["--export", values["export"]]
        if values.get("config"):
            args += ["--config", values["config"]]
        if values.get("resume"):
            args += ["--resume", values["resume"]]
        return self.run_skill_streaming("train_model", args)
