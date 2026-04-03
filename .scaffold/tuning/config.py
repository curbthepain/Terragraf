"""
.scaffold/tuning/config.py
Configuration for the thematic calibration engine.
Mirrors sharpen/config.py pattern.
"""

from dataclasses import dataclass


@dataclass
class TuningConfig:
    profiles_dir: str = "tuning/profiles"
    analytics_file: str = "tuning/analytics.json"
    max_history_entries: int = 500
    lock_timeout_seconds: float = 5.0
    default_profile: str = ""
