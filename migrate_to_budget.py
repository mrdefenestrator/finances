"""Migration script: combine income/expenses arrays into unified budget array.

Usage:
    uv run python migrate_to_budget.py <file.yaml>

Adds kind: income/expense to each entry, merges into budget array,
removes income and expenses keys, validates against updated schema.
"""

import sys
from pathlib import Path

import yaml

import validate_yaml


def migrate(path: Path) -> int:
    with open(path) as f:
        data = yaml.safe_load(f)

    if "budget" in data and "income" not in data and "expenses" not in data:
        print(f"{path}: already migrated (has 'budget', no 'income'/'expenses')")
        return 0

    income = data.pop("income", []) or []
    expenses = data.pop("expenses", []) or []

    budget = []
    for entry in income:
        e = dict(entry)
        e["kind"] = "income"
        # Move kind to front for readability
        e = {"kind": e.pop("kind"), **e}
        budget.append(e)
    for entry in expenses:
        e = dict(entry)
        e["kind"] = "expense"
        e = {"kind": e.pop("kind"), **e}
        budget.append(e)

    data["budget"] = budget

    # Reorder keys: accounts, budget, assets, debts (plus $schema if present)
    ordered = {}
    if "$schema" in data:
        ordered["$schema"] = data.pop("$schema")
    ordered["accounts"] = data.pop("accounts", [])
    ordered["budget"] = data.pop("budget", [])
    ordered["assets"] = data.pop("assets", [])
    ordered["debts"] = data.pop("debts", [])
    ordered.update(data)  # any remaining keys

    schema = validate_yaml.load_schema()
    errors = validate_yaml.validate_finances_data(ordered, schema)
    if errors:
        print("Validation errors after migration:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    with open(path, "w") as f:
        yaml.dump(
            ordered,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )

    print(
        f"{path}: migrated {len(income)} income + {len(expenses)} expense → {len(budget)} budget entries"
    )
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file.yaml> [file2.yaml ...]", file=sys.stderr)
        return 1
    exit_code = 0
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f"Error: file not found: {path}", file=sys.stderr)
            exit_code = 1
            continue
        exit_code |= migrate(path)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
