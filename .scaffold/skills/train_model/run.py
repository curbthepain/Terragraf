"""
train_model — ML training pipeline workflow.

Orchestrates dataset loading, model selection, training loop, evaluation,
and checkpoint management using the scaffold ML modules.

Usage:
    python run.py <data_dir> --arch cnn --epochs 50
    python run.py --dataset cifar10 --arch cnn --epochs 20
    python run.py <data_dir> --arch transformer --lr 1e-4
    python run.py --resume <checkpoint> <data_dir>
    python run.py --eval-only <checkpoint> <data_dir>
    python run.py --info
"""

import argparse
import importlib.util
import inspect
import sys
import time
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCAFFOLD))

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def cmd_info():
    """Show available model architectures and training options."""
    print(f"{BOLD}ML Training Pipeline{RESET}")
    print()
    print(f"  {BOLD}Architectures:{RESET}")
    print(f"    {CYAN}base{RESET}          ScaffoldModel (override forward())")
    print(f"    {CYAN}cnn{RESET}           3-block conv + adaptive pool + classifier")
    print(f"    {CYAN}transformer{RESET}   Multi-head attention stack + classifier head")
    print()
    print(f"  {BOLD}Optimizers:{RESET}  adam | adamw | sgd")
    print(f"  {BOLD}Schedulers:{RESET}  cosine | step | plateau | none")
    print(f"  {BOLD}Loggers:{RESET}     console | tensorboard | wandb")
    print(f"  {BOLD}Export:{RESET}      onnx | safetensors | torchscript")
    print()
    print(f"  {BOLD}Datasets:{RESET}")
    print(f"    {CYAN}--dataset cifar10{RESET}      Built-in CIFAR-10 loader")
    print(f"    {CYAN}<data_dir>/dataset.py{RESET}  ScaffoldDataset subclass")
    print(f"    {CYAN}<data_dir>/{{classA,B}}/{RESET}  ImageFolder structure")
    print()
    print(f"  {BOLD}Device:{RESET} auto-detected (CUDA > MPS > CPU)")
    print()

    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else (
            "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu"
        )
        print(f"  {GREEN}PyTorch {torch.__version__}{RESET} ({device})")
    except ImportError:
        print(f"  {RED}PyTorch not installed{RESET}")
    return 0


def _detect_device():
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _build_model(arch, args):
    """Instantiate a model from CLI args."""
    if arch == "cnn":
        from ml.models.cnn import CNN
        return CNN(in_channels=args.in_channels, num_classes=args.num_classes)
    elif arch == "transformer":
        from ml.models.transformer import Transformer
        return Transformer(
            d_model=args.d_model,
            n_layers=args.n_layers,
            num_classes=args.num_classes,
        )
    else:
        print(f"  {YELLOW}Base model — you must implement forward() in a subclass{RESET}")
        return None


def _load_dataset_py(data_dir):
    """Load a ScaffoldDataset subclass from <data_dir>/dataset.py."""
    from ml.datasets.base_dataset import ScaffoldDataset

    dataset_file = data_dir / "dataset.py"
    spec = importlib.util.spec_from_file_location("user_dataset", str(dataset_file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, ScaffoldDataset) and obj is not ScaffoldDataset:
            return obj(root_dir=str(data_dir))
    raise RuntimeError(f"No ScaffoldDataset subclass found in {dataset_file}")


def _discover_loaders(args):
    """Discover and load train/val DataLoaders based on CLI args."""
    from ml.datasets.dataloader import create_dataloader

    # Priority 1: --dataset built-in
    if args.dataset:
        if args.dataset == "cifar10":
            from ml.datasets.vision import cifar10_loaders
            root = args.data_dir or "./data/cifar10"
            return cifar10_loaders(root=root, batch_size=args.batch_size)
        raise RuntimeError(f"Unknown built-in dataset: {args.dataset}")

    # Priority 2: data_dir/dataset.py
    data_dir = Path(args.data_dir)
    if (data_dir / "dataset.py").exists():
        dataset = _load_dataset_py(data_dir)
        return create_dataloader(dataset, batch_size=args.batch_size)

    # Priority 3: ImageFolder structure (subdirectories = classes)
    subdirs = [p for p in data_dir.iterdir() if p.is_dir()] if data_dir.exists() else []
    if subdirs:
        from ml.datasets.vision import image_folder_loaders
        return image_folder_loaders(root=str(data_dir), batch_size=args.batch_size)

    raise RuntimeError(
        f"No dataset found in {data_dir}. Provide dataset.py, class folders, or --dataset cifar10."
    )


def _make_bridge_callback(arch, device, total_params, epochs):
    """Try to connect to the ImGui bridge as a client; return a callback dict."""
    bridge = None
    try:
        sys.path.insert(0, str(SCAFFOLD / "imgui"))
        from bridge import Bridge
        bridge = Bridge()
        bridge.start(as_server=False)
        time.sleep(0.1)
        bridge.send("training_started", {
            "arch": arch,
            "device": device,
            "params": total_params,
            "epochs": epochs,
        })
    except Exception as e:
        print(f"  {DIM}[bridge offline: {e}]{RESET}")
        bridge = None

    start_time = time.time()

    def on_epoch(epoch, train_loss, val_loss, lr):
        if bridge is None:
            return
        try:
            bridge.send("training_update", {
                "epoch": epoch,
                "total_epochs": epochs,
                "train_loss": float(train_loss),
                "val_loss": float(val_loss) if val_loss is not None else 0.0,
                "lr": float(lr),
                "elapsed": time.time() - start_time,
                "status": "training",
            })
        except Exception:
            pass

    def on_finish(final_metrics):
        if bridge is None:
            return
        try:
            bridge.send("training_finished", final_metrics or {})
            bridge.stop()
        except Exception:
            pass

    return {"on_epoch": on_epoch, "on_finish": on_finish, "enabled": bridge is not None}


def cmd_train(args):
    """Run training loop end-to-end."""
    try:
        import torch
        import torch.nn as nn
    except ImportError:
        print(f"  {RED}PyTorch required. pip install -r requirements-ml.txt{RESET}")
        return 1

    from ml.training import (
        Trainer, create_optimizer, create_scheduler, create_logger,
    )

    # Optional TOML config
    if args.config:
        from ml.config import load_config
        cfg = load_config(args.config)
        # CLI args override config
        if args.epochs == 50:
            args.epochs = cfg.epochs
        if args.lr == 1e-3:
            args.lr = cfg.learning_rate
        if args.batch_size == 32:
            args.batch_size = cfg.batch_size

    # Validate data source
    if not args.dataset and not args.data_dir:
        print(f"  {RED}Provide <data_dir> or --dataset cifar10{RESET}")
        return 1

    if args.data_dir:
        data_dir = Path(args.data_dir)
        if not data_dir.exists() and not args.dataset:
            print(f"  {RED}Data directory not found: {data_dir}{RESET}")
            return 1

    arch = args.arch
    device = _detect_device()

    print(f"{BOLD}Training{RESET}")
    print(f"  arch       {CYAN}{arch}{RESET}")
    print(f"  dataset    {args.dataset or args.data_dir}")
    print(f"  epochs     {args.epochs}")
    print(f"  optimizer  {args.optimizer}  lr={args.lr}  wd={args.weight_decay}")
    print(f"  scheduler  {args.scheduler}")
    print(f"  batch      {args.batch_size}")
    print(f"  device     {GREEN}{device}{RESET}")
    print()

    # Build model
    model = _build_model(arch, args)
    if model is None:
        return 1
    model = model.to_device(device)
    print(f"  params     {model.num_parameters:,} ({model.num_trainable:,} trainable)")

    # Optimizer + scheduler
    optimizer = create_optimizer(
        model, name=args.optimizer, lr=args.lr, weight_decay=args.weight_decay,
    )
    scheduler = create_scheduler(optimizer, name=args.scheduler, epochs=args.epochs)
    logger = create_logger(args.log_backend)
    criterion = nn.CrossEntropyLoss()

    # Resume checkpoint
    start_epoch = 0
    if args.resume:
        ckpt = model.load_checkpoint(args.resume, optimizer=optimizer)
        start_epoch = ckpt.get("epoch", 0)
        print(f"  {GREEN}Resumed from epoch {start_epoch}{RESET}")

    # Dataset
    try:
        train_loader, val_loader = _discover_loaders(args)
    except Exception as e:
        print(f"  {RED}Dataset error: {e}{RESET}")
        return 1

    print(f"  train      {len(train_loader)} batches")
    print(f"  val        {len(val_loader) if val_loader else 0} batches")
    print()

    # Trainer
    trainer = Trainer(
        model=model,
        optimizer=optimizer,
        criterion=criterion,
        device=device,
        scheduler=scheduler,
        logger=logger,
        max_grad_norm=args.grad_clip,
        early_stopping_patience=args.early_stopping,
    )

    # Bridge integration — optional live metrics to ImGui
    callback = _make_bridge_callback(arch, device, model.num_parameters, args.epochs)
    if callback["enabled"]:
        original_on_epoch_end = trainer.on_epoch_end
        def hooked(epoch, train_loss, val_loss):
            original_on_epoch_end(epoch, train_loss, val_loss)
            lr = trainer.optimizer.param_groups[0]["lr"]
            callback["on_epoch"](epoch, train_loss, val_loss, lr)
        trainer.on_epoch_end = hooked

    # Train
    history = trainer.train(
        train_loader,
        val_loader=val_loader,
        epochs=args.epochs,
        start_epoch=start_epoch,
    )

    # Summary
    print()
    print(f"{BOLD}Training complete{RESET}")
    if history["train_loss"]:
        print(f"  final train_loss  {history['train_loss'][-1]:.4f}")
    if history["val_loss"]:
        print(f"  final val_loss    {history['val_loss'][-1]:.4f}")

    # Optional export
    if args.export:
        print()
        print(f"{BOLD}Exporting{RESET} ({args.export})")
        from ml import export_onnx, export_safetensors, export_torchscript

        export_dir = Path("checkpoints")
        export_dir.mkdir(parents=True, exist_ok=True)

        if args.export == "safetensors":
            export_safetensors(model, export_dir / "model.safetensors")
        else:
            # ONNX/TorchScript need a dummy input
            sample_x, _ = next(iter(train_loader))
            dummy = sample_x[:1].to(device)
            if args.export == "onnx":
                export_onnx(model, dummy, export_dir / "model.onnx")
            elif args.export == "torchscript":
                export_torchscript(model, dummy, export_dir / "model.ts")

    callback["on_finish"]({})
    return 0


def cmd_eval(args):
    """Evaluate a checkpoint against a test dataset."""
    try:
        import torch
    except ImportError:
        print(f"  {RED}PyTorch required{RESET}")
        return 1

    from ml.training.evaluate import Evaluator

    checkpoint = Path(args.checkpoint)
    if not checkpoint.exists():
        print(f"  {RED}Checkpoint not found: {checkpoint}{RESET}")
        return 1

    print(f"{BOLD}Evaluation{RESET}")
    print(f"  checkpoint {checkpoint}")

    # Reconstruct model from --arch + dimension args
    model = _build_model(args.arch, args)
    if model is None:
        return 1

    device = _detect_device()
    model = model.to_device(device)
    model.load_checkpoint(str(checkpoint))

    # Need test data
    if not args.data_dir and not args.dataset:
        print(f"  {RED}Provide <data_dir> or --dataset for eval{RESET}")
        return 1

    try:
        _, val_loader = _discover_loaders(args)
    except Exception as e:
        print(f"  {RED}Dataset error: {e}{RESET}")
        return 1

    evaluator = Evaluator(model, device=device)
    results = evaluator.evaluate(val_loader)
    return 0


def cli():
    parser = argparse.ArgumentParser(description="ML training pipeline")
    parser.add_argument("data_dir", nargs="?", help="Dataset directory")
    parser.add_argument("--arch", default="cnn",
                        choices=["base", "cnn", "transformer"],
                        help="Model architecture")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--num-classes", type=int, default=10)
    parser.add_argument("--in-channels", type=int, default=3)
    parser.add_argument("--d-model", type=int, default=256)
    parser.add_argument("--n-layers", type=int, default=4)
    parser.add_argument("--optimizer", default="adam",
                        choices=["adam", "adamw", "sgd"])
    parser.add_argument("--scheduler", default="cosine",
                        choices=["cosine", "step", "plateau", "none"])
    parser.add_argument("--log-backend", default="console",
                        choices=["console", "tensorboard", "wandb"])
    parser.add_argument("--export",
                        choices=["onnx", "safetensors", "torchscript"],
                        help="Export format after training")
    parser.add_argument("--config", metavar="TOML", help="Training config file")
    parser.add_argument("--early-stopping", type=int, default=0, metavar="PATIENCE")
    parser.add_argument("--grad-clip", type=float, default=0.0, metavar="NORM")
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--dataset", help="Built-in dataset (e.g. cifar10)")
    parser.add_argument("--test-dir", help="Test data directory for eval")
    parser.add_argument("--resume", metavar="CHECKPOINT", help="Resume from checkpoint")
    parser.add_argument("--eval-only", metavar="CHECKPOINT", help="Evaluate checkpoint only")
    parser.add_argument("--info", action="store_true", help="Show architectures and options")
    args = parser.parse_args()

    if args.info:
        return cmd_info()
    elif args.eval_only:
        args.checkpoint = args.eval_only
        return cmd_eval(args)
    elif args.data_dir or args.dataset:
        return cmd_train(args)
    else:
        return cmd_info()


if __name__ == "__main__":
    sys.exit(cli())
