"""Load finances YAML data."""

from pathlib import Path
from typing import Any, Dict

import yaml


def load_finances(path: Path) -> Dict[str, Any]:
    """Load a finances YAML file into a dict."""
    with open(path, "r") as f:
        return yaml.safe_load(f)
