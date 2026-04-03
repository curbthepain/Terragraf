"""
.scaffold/ml/training/evaluate.py
Evaluation harness. Compute metrics on a trained model.
"""

import torch
from collections import defaultdict


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
            "accuracy": lambda p, t: (p == t).float().mean().item(),
        }

    results = {}
    for name, fn in metrics.items():
        results[name] = fn(all_preds, all_targets)

    # Print results
    print("=== Evaluation ===")
    for name, value in results.items():
        print(f"  {name}: {value:.4f}")

    return results
