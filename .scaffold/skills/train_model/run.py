"""
train_model — ML training pipeline workflow.

Orchestrates dataset loading, model selection, training loop, evaluation,
and checkpoint management using the scaffold ML modules.

Usage:
    python run.py <data_dir> --arch cnn --epochs 50
    python run.py <data_dir> --arch transformer --lr 1e-4
    python run.py --resume <checkpoint>
    python run.py --eval-only <checkpoint> <test_dir>
    python run.py --info                  # Show available architectures
"""

import argparse
import sys
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
    print(f"    {CYAN}transformer{RESET}   Multi-head attention stack + positional encoding")
    print()
    print(f"  {BOLD}Modules:{RESET}")
    print(f"    models/     {DIM}.scaffold/ml/models/{RESET}")
    print(f"    training/   {DIM}.scaffold/ml/training/{RESET}")
    print(f"    datasets/   {DIM}.scaffold/ml/datasets/{RESET}")
    print()
    print(f"  {BOLD}Device:{RESET} auto-detected (CUDA > MPS > CPU)")
    print()

    # Check PyTorch availability
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else (
            "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu"
        )
        print(f"  {GREEN}PyTorch {torch.__version__}{RESET} ({device})")
    except ImportError:
        print(f"  {RED}PyTorch not installed{RESET}")
        print(f"  {DIM}pip install -r requirements-ml.txt{RESET}")
    return 0


def cmd_train(args):
    """Run training loop."""
    try:
        import torch
    except ImportError:
        print(f"  {RED}PyTorch required. pip install -r requirements-ml.txt{RESET}")
        return 1

    from ml.models.base_model import ScaffoldModel

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"  {RED}Data directory not found: {data_dir}{RESET}")
        return 1

    arch = args.arch
    print(f"{BOLD}Training{RESET}")
    print(f"  arch       {CYAN}{arch}{RESET}")
    print(f"  data       {data_dir}")
    print(f"  epochs     {args.epochs}")
    print(f"  lr         {args.lr}")
    print(f"  batch      {args.batch_size}")

    # Select device
    device = "cuda" if torch.cuda.is_available() else (
        "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu"
    )
    print(f"  device     {GREEN}{device}{RESET}")
    print()

    # Load model
    if arch == "cnn":
        from ml.models.cnn import CNN
        model = CNN(in_channels=args.in_channels, num_classes=args.num_classes)
    elif arch == "transformer":
        from ml.models.transformer import Transformer
        model = Transformer(d_model=args.d_model, n_layers=args.n_layers,
                            num_classes=args.num_classes)
    else:
        print(f"  {YELLOW}Base model — you must implement forward() in a subclass{RESET}")
        print(f"  {DIM}See .scaffold/ml/models/base_model.py{RESET}")
        return 1

    model = model.to_device(device)
    print(f"  params     {model.num_parameters:,} ({model.num_trainable:,} trainable)")

    # Training would happen here with real data
    # For now, show the configured pipeline
    print()
    print(f"  {YELLOW}Pipeline configured. Provide a ScaffoldDataset implementation{RESET}")
    print(f"  {DIM}in {data_dir} to begin training.{RESET}")
    print()
    print(f"  {BOLD}Next steps:{RESET}")
    print(f"    1. Create dataset.py in {data_dir} extending ScaffoldDataset")
    print(f"    2. Implement _load_samples() returning (data, labels)")
    print(f"    3. Run: terra train {data_dir} --arch {arch} --epochs {args.epochs}")

    return 0


def cmd_eval(args):
    """Evaluate a checkpoint."""
    try:
        import torch
    except ImportError:
        print(f"  {RED}PyTorch required{RESET}")
        return 1

    checkpoint = Path(args.checkpoint)
    if not checkpoint.exists():
        print(f"  {RED}Checkpoint not found: {checkpoint}{RESET}")
        return 1

    print(f"{BOLD}Evaluation{RESET}")
    print(f"  checkpoint {checkpoint}")
    print(f"  {DIM}Loading model state...{RESET}")

    data = torch.load(str(checkpoint), map_location="cpu", weights_only=False)
    print(f"  {GREEN}Loaded{RESET}")
    if "metadata" in data:
        for k, v in data["metadata"].items():
            print(f"  {k}: {v}")

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
    parser.add_argument("--resume", metavar="CHECKPOINT", help="Resume from checkpoint")
    parser.add_argument("--eval-only", metavar="CHECKPOINT", help="Evaluate checkpoint only")
    parser.add_argument("--info", action="store_true", help="Show architectures and options")
    args = parser.parse_args()

    if args.info:
        return cmd_info()
    elif args.eval_only:
        args.checkpoint = args.eval_only
        return cmd_eval(args)
    elif args.data_dir:
        return cmd_train(args)
    else:
        return cmd_info()


if __name__ == "__main__":
    sys.exit(cli())
