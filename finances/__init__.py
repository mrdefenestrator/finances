"""
Finances tracker: shared logic for CLI and web.

Submodules:
  types       - TypedDict definitions for Account, BudgetEntry, AssetEntry, FinancesData
  loader      - load_finances
  calculations - liquid_total, liquid_minus_cc, projected_change_to_eom, net_nonliquid_*, constants
  filters     - filter_accounts_by_type, apply_budget_filters, filter_assets_by_kind
  formatting  - fmt_money, fmt_qty, fmt_type_display, fmt_recurrence_display, fmt_day_ordinal, fmt_month_short
  tables      - _account_display_by_id, _build_*_table (for CLI and web)
  writer      - CRUD operations with validation
  cli         - main (CLI entrypoint)
"""

from .types import (
    Account,
    AccountType,
    AssetEntry,
    BudgetEntry,
    ExpenseType,
    FinancesData,
    IncomeType,
    Recurrence,
)
from .calculations import (
    ACCOUNT_TYPES,
    ASSETS_KINDS,
    BUDGET_ALL_TYPES,
    BUDGET_EXPENSE_TYPES,
    BUDGET_INCOME_TYPES,
    BUDGET_KINDS,
    RECURRENCE_OPTIONS,
    _ACCOUNT_TYPE_TO_CALCULATION,
    account_funding_needed,
    credit_card_total,
    liquid_minus_cc,
    liquid_total,
    net_nonliquid_paired,
    net_nonliquid_total,
    projected_change_to_eom,
)
from .filters import (
    apply_budget_filters,
    filter_accounts_by_type,
    filter_assets_by_kind,
)
from .formatting import (
    fmt_day_ordinal,
    fmt_money,
    fmt_month_short,
    fmt_qty,
    fmt_recurrence_display,
    fmt_type_display,
)
from .cli import main
from .loader import load_finances
from .tables import (
    _account_display_by_id,
    _build_accounts_table,
    _build_budget_table,
    _build_funding_table,
    _build_net_worth_table,
)
from .writer import (
    add_budget_entry,
    update_budget_entry,
    delete_budget_entry,
    move_budget_entry,
    add_asset_entry,
    update_asset_entry,
    delete_asset_entry,
    move_asset_entry,
)

__all__ = [
    # Types
    "Account",
    "AccountType",
    "AssetEntry",
    "BudgetEntry",
    "ExpenseType",
    "FinancesData",
    "IncomeType",
    "Recurrence",
    # Constants
    "ACCOUNT_TYPES",
    "ASSETS_KINDS",
    "BUDGET_ALL_TYPES",
    "BUDGET_EXPENSE_TYPES",
    "BUDGET_INCOME_TYPES",
    "BUDGET_KINDS",
    "RECURRENCE_OPTIONS",
    # Functions
    "apply_budget_filters",
    "credit_card_total",
    "filter_accounts_by_type",
    "filter_assets_by_kind",
    "fmt_day_ordinal",
    "fmt_money",
    "fmt_month_short",
    "fmt_qty",
    "fmt_recurrence_display",
    "fmt_type_display",
    "liquid_minus_cc",
    "liquid_total",
    "load_finances",
    "main",
    "net_nonliquid_paired",
    "net_nonliquid_total",
    "projected_change_to_eom",
    "_ACCOUNT_TYPE_TO_CALCULATION",
    "_account_display_by_id",
    "_build_accounts_table",
    "_build_budget_table",
    "_build_funding_table",
    "_build_net_worth_table",
    "account_funding_needed",
    # Writer
    "add_budget_entry",
    "update_budget_entry",
    "delete_budget_entry",
    "move_budget_entry",
    "add_asset_entry",
    "update_asset_entry",
    "delete_asset_entry",
    "move_asset_entry",
]
