#!/usr/bin/env python3
"""Validate finances YAML files against the schema."""

import sys
from pathlib import Path

import yaml
from jsonschema import validate, ValidationError

_INCOME_ONLY_TYPES = frozenset(["salary", "refund", "bonus", "remittance"])
_EXPENSE_ONLY_TYPES = frozenset(
    ["housing", "insurance", "service", "utility", "product", "transport", "food"]
)
_ASSET_DEBT_FIELDS = frozenset(["balance", "assetRef", "interestRate", "nextDueDate"])
_DEBT_ASSET_FIELDS = frozenset(["id", "value", "source"])
_CC_ONLY_FIELDS = frozenset(
    [
        "limit",
        "available",
        "rewards_balance",
        "statement_balance",
        "statement_due_day_of_month",
        "paymentAccountRef",
    ]
)
_NON_CC_ONLY_FIELDS = frozenset(["balance", "minimum_balance"])


def load_schema() -> dict:
    """Load the JSON schema from schema.yaml."""
    schema_path = Path(__file__).parent / "schema.yaml"
    with open(schema_path) as f:
        return yaml.safe_load(f)


def _check_junk_fields(data: dict) -> list:
    """Report kind-mismatched fields on budget, asset, and account entries."""
    errors = []

    for i, entry in enumerate(data.get("budget") or []):
        kind = entry.get("kind")
        label = f"Budget entry {i} '{entry.get('description', '')}'"
        if kind == "income":
            if "continuous" in entry:
                errors.append(
                    f"{label}: 'continuous' is only valid for expense entries"
                )
            if entry.get("type") in _EXPENSE_ONLY_TYPES:
                errors.append(
                    f"{label}: type '{entry['type']}' is only valid for expense entries"
                )
        elif kind == "expense":
            if entry.get("type") in _INCOME_ONLY_TYPES:
                errors.append(
                    f"{label}: type '{entry['type']}' is only valid for income entries"
                )

    for i, entry in enumerate(data.get("assets") or []):
        kind = entry.get("kind")
        label = f"Asset entry {i} '{entry.get('name', '')}'"
        if kind == "asset":
            for field in _ASSET_DEBT_FIELDS:
                if field in entry:
                    errors.append(f"{label}: '{field}' is only valid for debt entries")
        elif kind == "debt":
            for field in _DEBT_ASSET_FIELDS:
                if field in entry:
                    errors.append(f"{label}: '{field}' is only valid for asset entries")

    for i, account in enumerate(data.get("accounts") or []):
        atype = account.get("type")
        label = f"Account {i} '{account.get('name', '')}'"
        if atype == "credit_card":
            for field in _NON_CC_ONLY_FIELDS:
                if field in account:
                    errors.append(
                        f"{label}: '{field}' is not valid for credit_card accounts"
                    )
        else:
            for field in _CC_ONLY_FIELDS:
                if field in account:
                    errors.append(
                        f"{label}: '{field}' is only valid for credit_card accounts"
                    )

    return errors


def validate_finances_data(data: dict, schema: dict) -> list:
    """Validate a finances data dict against the schema. Returns list of error strings."""
    errors = _check_junk_fields(data)
    if errors:
        return errors
    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        errors.append(f"Schema validation error: {getattr(e, 'message', str(e))}")
        if e.path:
            errors.append(f"  at path: {'.'.join(str(p) for p in e.path)}")
    except Exception as e:
        errors.append(f"Error: {e}")
    return errors


def validate_finances_file(filepath: Path, schema: dict) -> list:
    """Validate a single finances YAML file. Returns list of errors."""
    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]
    except Exception as e:
        return [f"Error: {e}"]
    return validate_finances_data(data, schema)


def main():
    """Validate all finances YAML files in the data/ directory."""
    schema = load_schema()
    data_dir = Path(__file__).parent / "data"

    if not data_dir.exists():
        print(f"Warning: data directory not found: {data_dir}")
        return 0

    yaml_files = sorted(data_dir.glob("*.yaml")) + sorted(data_dir.glob("*.yml"))

    if not yaml_files:
        print(f"Warning: No YAML files found in {data_dir}")
        return 0

    all_valid = True
    for filepath in yaml_files:
        errors = validate_finances_file(filepath, schema)
        if errors:
            print(f"FAIL: {filepath.name}")
            for error in errors:
                print(f"  {error}")
            all_valid = False
        else:
            print(f"OK: {filepath.name}")

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
