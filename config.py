"""Settings: ~/.erome-dl/config.toml (override the folder with EROME_DL_HOME)."""
from __future__ import annotations

import os
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

DEFAULTS = {"output": "downloads", "workers": 4, "delay": 0.6, "proxy": None}


def home_dir() -> Path:
    return Path(os.environ.get("EROME_DL_HOME") or Path.home() / ".erome-dl")


def load_config(path: Path | None = None) -> dict:
    cfg = dict(DEFAULTS)
    path = path or home_dir() / "config.toml"
    if path.exists():
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
    return cfg
