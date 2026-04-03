"""
.scaffold/sharpen/config.py
Configuration for the self-sharpening engine.
"""

from dataclasses import dataclass


@dataclass
class SharpenConfig:
    stale_threshold_days: int = 30
    hot_threshold_multiplier: float = 3.0
    min_hits_for_hot: int = 5
    min_error_occurrences: int = 3
    max_instance_outcomes: int = 200
    max_queries_per_entry: int = 20
    lock_timeout_seconds: float = 5.0
