"""
.scaffold/ml/training/metrics.py
Metrics for model evaluation. Wraps sklearn for standard classification metrics.
"""

import torch
import numpy as np


def accuracy(preds, labels):
    """Compute accuracy from tensors or arrays."""
    if isinstance(preds, torch.Tensor):
        preds = preds.cpu().numpy()
    if isinstance(labels, torch.Tensor):
        labels = labels.cpu().numpy()
    return float((preds == labels).mean())


def _to_numpy(t):
    if isinstance(t, torch.Tensor):
        return t.cpu().numpy()
    return np.asarray(t)


def precision_recall_f1(preds, labels, average="macro"):
    """Compute precision, recall, F1. Uses sklearn if available, else manual."""
    preds, labels = _to_numpy(preds), _to_numpy(labels)
    try:
        from sklearn.metrics import precision_recall_fscore_support
        p, r, f1, _ = precision_recall_fscore_support(preds, labels, average=average, zero_division=0)
        return {"precision": float(p), "recall": float(r), "f1": float(f1)}
    except ImportError:
        # Fallback: macro-averaged manual computation
        classes = np.unique(np.concatenate([preds, labels]))
        precisions, recalls, f1s = [], [], []
        for c in classes:
            tp = ((preds == c) & (labels == c)).sum()
            fp = ((preds == c) & (labels != c)).sum()
            fn = ((preds != c) & (labels == c)).sum()
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
            precisions.append(p)
            recalls.append(r)
            f1s.append(f1)
        return {"precision": float(np.mean(precisions)), "recall": float(np.mean(recalls)), "f1": float(np.mean(f1s))}


def confusion_matrix(preds, labels):
    """Compute confusion matrix. Uses sklearn if available, else manual."""
    preds, labels = _to_numpy(preds), _to_numpy(labels)
    try:
        from sklearn.metrics import confusion_matrix as sk_cm
        return sk_cm(preds, labels)
    except ImportError:
        classes = np.unique(np.concatenate([preds, labels]))
        n = len(classes)
        cm = np.zeros((n, n), dtype=int)
        class_to_idx = {c: i for i, c in enumerate(classes)}
        for p, l in zip(preds, labels):
            cm[class_to_idx[l], class_to_idx[p]] += 1
        return cm


def classification_report(preds, labels):
    """Full classification report string. Uses sklearn if available."""
    preds, labels = _to_numpy(preds), _to_numpy(labels)
    try:
        from sklearn.metrics import classification_report as sk_cr
        return sk_cr(preds, labels, zero_division=0)
    except ImportError:
        result = precision_recall_f1(preds, labels)
        return f"precision={result['precision']:.4f} recall={result['recall']:.4f} f1={result['f1']:.4f}"


class MetricsTracker:
    """Accumulates predictions across batches, computes epoch-level metrics."""

    def __init__(self):
        self.reset()

    def reset(self):
        self._preds = []
        self._labels = []

    def update(self, preds, labels):
        if isinstance(preds, torch.Tensor):
            preds = preds.detach().cpu()
        if isinstance(labels, torch.Tensor):
            labels = labels.detach().cpu()
        self._preds.append(preds)
        self._labels.append(labels)

    def compute(self):
        all_preds = torch.cat(self._preds) if isinstance(self._preds[0], torch.Tensor) else np.concatenate(self._preds)
        all_labels = torch.cat(self._labels) if isinstance(self._labels[0], torch.Tensor) else np.concatenate(self._labels)
        result = {"accuracy": accuracy(all_preds, all_labels)}
        result.update(precision_recall_f1(all_preds, all_labels))
        return result
