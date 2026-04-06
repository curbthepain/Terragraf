"""
.scaffold/ml/datasets/hf.py
HuggingFace datasets integration — wraps datasets.load_dataset() for PyTorch.
"""

import torch
from torch.utils.data import Dataset


class HFDatasetWrapper(Dataset):
    """Wraps a HuggingFace dataset as a PyTorch Dataset."""

    def __init__(self, hf_dataset, text_col="text", label_col="label", tokenizer=None, max_length=512):
        self.data = hf_dataset
        self.text_col = text_col
        self.label_col = label_col
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]

        if self.tokenizer is not None:
            text = item[self.text_col]
            encoding = self.tokenizer(text, truncation=True, padding="max_length",
                                      max_length=self.max_length, return_tensors="pt")
            input_ids = encoding["input_ids"].squeeze(0)
            attention_mask = encoding["attention_mask"].squeeze(0)
            label = torch.tensor(item[self.label_col], dtype=torch.long)
            return {"input_ids": input_ids, "attention_mask": attention_mask}, label

        # Non-text: return raw values as tensors
        features = item[self.text_col] if self.text_col in item else list(item.values())[0]
        label = item.get(self.label_col, 0)
        if not isinstance(features, torch.Tensor):
            features = torch.tensor(features, dtype=torch.float32)
        return features, torch.tensor(label, dtype=torch.long)


def hf_dataset(name, split="train", tokenizer=None, text_col="text", label_col="label", **kwargs):
    """Load a HuggingFace dataset and wrap it as a PyTorch Dataset."""
    from datasets import load_dataset
    ds = load_dataset(name, split=split, **kwargs)
    return HFDatasetWrapper(ds, text_col=text_col, label_col=label_col, tokenizer=tokenizer)
