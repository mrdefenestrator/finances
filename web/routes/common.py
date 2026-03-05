"""Shared utilities for web routes."""

import os
import re
from datetime import date
from pathlib import Path

from flask import abort

import finances

# Data file: env FINANCES_DATA or default data/finances.yaml relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_env_data = os.environ.get("FINANCES_DATA")
DATA_DIR = Path(_env_data).parent if _env_data else PROJECT_ROOT / "data"
DEFAULT_DATA_FILE = DATA_DIR / "finances.yaml"


def get_default_filename() -> str:
    """Stem of the default data file (e.g. 'finances')."""
    env_path = os.environ.get("FINANCES_DATA")
    return Path(env_path).stem if env_path else DEFAULT_DATA_FILE.stem


def validate_url_filename(filename: str) -> Path:
    """Validate a URL filename component and return the full path.

    Aborts 400 if invalid, 404 if file not found.
    Flask's <string:filename> converter already rejects forward slashes.
    """
    if "\\" in filename or ".." in filename:
        abort(400, description="Invalid filename")
    if not re.match(r"^[a-zA-Z0-9 _\-.]+$", filename):
        abort(400, description="Invalid filename")
    full_path = (DATA_DIR / (filename + ".yaml")).resolve()
    if not str(full_path).startswith(str(DATA_DIR.resolve())):
        abort(400, description="Invalid path")
    if not full_path.exists():
        abort(404, description=f"File not found: {filename}.yaml")
    return full_path


def get_common_context(path: Path, edit_mode: bool):
    """Data and computed values shared by all views."""
    data = finances.load_finances(path)
    accounts = data.get("accounts") or []
    budget = data.get("budget") or []
    assets = data.get("assets") or []

    today = date.today()
    year, month, day = today.year, today.month, today.day

    n2 = finances.liquid_minus_cc(accounts)
    n3 = finances.projected_change_to_eom(budget, year, month, day)
    n6 = finances.net_nonliquid_total(assets)
    account_display = finances._account_display_by_id(accounts)

    # File picker context — emit stems (no .yaml)
    available_files = (
        sorted(
            f.stem
            for f in DATA_DIR.iterdir()
            if f.is_file() and f.suffix in (".yaml", ".yml")
        )
        if DATA_DIR.exists()
        else []
    )

    return {
        "data_file": str(path),
        "filename": path.stem,
        "active_file": path.stem,
        "available_files": available_files,
        "as_of_date": today.isoformat(),
        "budget_label": f"budget to end of {today.strftime('%b %Y')}",
        "accounts": accounts,
        "budget": budget,
        "assets": assets,
        "year": year,
        "month": month,
        "day": day,
        "n2": n2,
        "n3": n3,
        "n6": n6,
        "account_display_by_id": account_display,
        "edit_mode": edit_mode,
    }


def drop_separator_rows(rows):
    """Remove separator rows (all cells are dashes) from table rows."""
    return [
        row
        for row in rows
        if not all(isinstance(c, str) and set(c.strip()) <= {"-"} for c in row)
    ]


# =============================================================================
# Accounts table configuration
# =============================================================================

# Column mapping for accounts table (index -> field name)
ACCOUNTS_FIELD_TO_COL = [
    "name",
    "institution",
    "type",
    "balance",
    "limit",
    "available",
    "rewards_balance",
    "statement_balance",
    "statement_due_day_of_month",
    "paymentAccountRef",
]

# Right-aligned column indices for accounts
ACCOUNTS_RIGHT_ALIGN_COLS = (3, 4, 5, 6, 7, 8)

# Fields that are right-aligned in accounts
ACCOUNTS_RIGHT_ALIGN_FIELDS = {
    "balance",
    "limit",
    "available",
    "rewards_balance",
    "statement_balance",
    "statement_due_day_of_month",
}


def account_field_editable(acc, field: str) -> bool:
    """Credit card rows: balance not editable (calculated); only CC can edit
    limit, available, rewards, statement, due. Non-CC: balance editable;
    limit/available/rewards/statement/due not."""
    is_cc = acc.get("type") == "credit_card"
    if is_cc and field == "balance":
        return False
    if not is_cc and field in (
        "limit",
        "available",
        "rewards_balance",
        "statement_balance",
        "statement_due_day_of_month",
        "paymentAccountRef",
    ):
        return False
    return True


def account_field_right_align(field: str) -> bool:
    """Return True if field should be right-aligned."""
    return field in ACCOUNTS_RIGHT_ALIGN_FIELDS


# =============================================================================
# Budget table configuration (income/expense)
# =============================================================================

# Column mapping for budget table (index -> field name, None = computed/non-editable)
PROJECTION_FIELD_TO_COL = [
    None,  # Kind (income/expense label)
    "description",
    "type",
    "amount",
    None,  # Subtotal (computed)
    "recurrence",
    "dayOfMonth",
    "autoAccountRef",
]

# Right-aligned column indices for budget
BUDGET_RIGHT_ALIGN_COLS = (3, 4, 6)

# Fields that are right-aligned in budget
BUDGET_RIGHT_ALIGN_FIELDS = {"amount", "dayOfMonth", "month", "dayOfYear"}


def budget_field_editable(kind: str, field: str) -> bool:
    """Return True if the field is editable for this budget entry kind.
    Kind column (0) and Subtotal column (4) are never editable."""
    # These fields are always editable for both income and expense
    editable_fields = {
        "description",
        "type",
        "amount",
        "recurrence",
        "dayOfMonth",
        "month",
        "dayOfYear",
        "autoAccountRef",
        "date",
    }
    return field in editable_fields


def budget_field_right_align(field: str) -> bool:
    """Return True if field should be right-aligned."""
    return field in BUDGET_RIGHT_ALIGN_FIELDS


# =============================================================================
# Assets table configuration (assets/debts)
# =============================================================================

# Column mapping for assets table - different for asset vs debt
# (index -> field name, None = non-editable for that kind)
ASSETS_FIELD_TO_COL_ASSET = [
    None,  # Kind label
    "institution",
    "name",
    "value",
    "quantity",
    None,  # Subtotal (computed)
    "source",
    None,  # Interest (N/A for assets)
]

ASSETS_FIELD_TO_COL_DEBT = [
    None,  # Kind label
    "institution",
    "name",
    "balance",  # per-unit balance
    "quantity",  # quantity
    None,  # Subtotal — computed
    "assetRef",
    "interestRate",
]

# Right-aligned column indices for assets
ASSETS_RIGHT_ALIGN_COLS = (3, 4, 5, 7)

# Fields that are right-aligned in assets
ASSETS_RIGHT_ALIGN_FIELDS = {"value", "quantity", "balance", "interestRate"}


def assets_field_editable(kind: str, field: str) -> bool:
    """Return True if the field is editable for this asset/debt kind."""
    if kind == "asset":
        editable_fields = {"institution", "name", "value", "quantity", "source"}
    else:  # debt
        editable_fields = {
            "institution",
            "name",
            "balance",
            "quantity",
            "assetRef",
            "interestRate",
        }
    return field in editable_fields


def assets_field_right_align(field: str) -> bool:
    """Return True if field should be right-aligned."""
    return field in ASSETS_RIGHT_ALIGN_FIELDS


def assets_get_field_for_col(kind: str, col_index: int) -> str | None:
    """Get the field name for a column index, or None if not editable."""
    if kind == "asset":
        if 0 <= col_index < len(ASSETS_FIELD_TO_COL_ASSET):
            return ASSETS_FIELD_TO_COL_ASSET[col_index]
    else:  # debt
        if 0 <= col_index < len(ASSETS_FIELD_TO_COL_DEBT):
            return ASSETS_FIELD_TO_COL_DEBT[col_index]
    return None
