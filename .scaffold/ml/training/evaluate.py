"""
.scaffold/ml/training/evaluate.py
Evaluation harness. Compute metrics on a trained model.
"""

import torch
from .metrics import accuracy, precision_recall_f1, MetricsTracker


@torch.no_grad()
def evaluate(model, loader, device="auto", metrics=None):
    """
    Evaluate model on a dataset.

    Args:
        model: trained nn.Module
        loader: DataLoader
        device: device string
        metrics: dict of {name: fn(preds, targets) -> scalar}

    Returns:
        dict of metric_name -> value
    """
    if device == "auto":
        device = next(model.parameters()).device

    model.eval()
    all_preds = []
    all_targets = []

    for inputs, targets in loader:
        inputs = inputs.to(device)
        outputs = model(inputs)
        preds = outputs.argmax(dim=-1).cpu()
        all_preds.append(preds)
        all_targets.append(targets)

    all_preds = torch.cat(all_preds)
    all_targets = torch.cat(all_targets)

    # Default metrics
    if metrics is None:
        metrics = {
            "accuracy": lambda p, t: accuracy(p, t),
        }

    results = {}
    for name, fn in metrics.items():
        results[name] = fn(all_preds, all_targets)

    # Print results
    print("=== Evaluation ===")
    for name, value in results.items():
        if isinstance(value, float):
            print(f"  {name}: {value:.4f}")
        else:
            print(f"  {name}: {value}")

    return results


class Evaluator:
    """Class-based evaluator with full metrics tracking."""

    def __init__(self, model, device="auto"):
        self.model = model
        if device == "auto":
            self.device = next(model.parameters()).device
        else:
            self.device = torch.device(device)

    @torch.no_grad()
    def evaluate(self, loader):
        """Evaluate model on a DataLoader, return full metrics dict."""
        self.model.eval()
        tracker = MetricsTracker()

        for inputs, targets in loader:
            inputs = inputs.to(self.device)
            outputs = self.model(inputs)
            preds = outputs.argmax(dim=-1).cpu()
            tracker.update(preds, targets)

        results = tracker.compute()

        print("=== Evaluation ===")
        for name, value in results.items():
            print(f"  {name}: {value:.4f}")

        return results
