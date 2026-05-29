"""Load finances data from YAML or SQLite database."""

from pathlib import Path
from typing import Any, Dict

import yaml


def load_finances(path: Path) -> Dict[str, Any]:
    """Load a finances YAML file into a dict."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_finances_from_db(conn, snapshot_id: int) -> Dict[str, Any]:
    """Load finances data from DB and return same structure as load_finances."""
    from finances.repository.accounts import get_accounts
    from finances.repository.assets import get_asset_entries
    from finances.repository.budget import get_budget_entries

    raw_accounts = get_accounts(conn, snapshot_id)
    raw_budget = get_budget_entries(conn, snapshot_id)
    raw_assets = get_asset_entries(conn, snapshot_id)

    # Strip internal _db_id keys before returning
    budget = [{k: v for k, v in e.items() if k != "_db_id"} for e in raw_budget]
    assets = [{k: v for k, v in e.items() if k != "_db_id"} for e in raw_assets]

    return {
        "accounts": list(raw_accounts),
        "budget": budget,
        "assets": assets,
    }
