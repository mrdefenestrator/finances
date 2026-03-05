#!/usr/bin/env python3
"""Validate finances YAML files against the schema."""

import sys
from pathlib import Path

import yaml
from jsonschema import validate, ValidationError


def load_schema() -> dict:
    """Load the JSON schema from schema.yaml."""
    schema_path = Path(__file__).parent / "schema.yaml"
    with open(schema_path) as f:
        return yaml.safe_load(f)


def _validate_accounts(data: dict, filepath: Path = None) -> list:
    """Validate account rules: credit_card requires limit+available; all other types require balance."""
    errors = []
    for i, a in enumerate(data.get("accounts") or []):
        name = a.get("name", f"<account {i}>")
        atype = a.get("type")
        if atype == "credit_card":
            if a.get("limit") is None:
                errors.append(f"Account '{name}': credit_card requires 'limit'")
            if a.get("available") is None:
                errors.append(f"Account '{name}': credit_card requires 'available'")
        else:
            # All other types (checking, savings, gift_card, wallet, digital_wallet, loan, other)
            if "balance" not in a:
                errors.append(
                    f"Account '{name}': {atype or 'unknown'} requires 'balance'"
                )
    return errors


def validate_finances_data(data: dict, schema: dict) -> list:
    """Validate a finances data dict against the schema. Returns list of error strings."""
    errors = []
    try:
        validate(instance=data, schema=schema)
        errors.extend(_validate_accounts(data))
    except ValidationError as e:
        errors.append(f"Schema validation error: {getattr(e, 'message', str(e))}")
        if e.path:
            errors.append(f"  at path: {'.'.join(str(p) for p in e.path)}")
    except Exception as e:
        errors.append(f"Error: {e}")
    return errors


def validate_finances_file(filepath: Path, schema: dict) -> list:
    """Validate a single finances YAML file. Returns list of errors."""
    errors = []
    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
        validate(instance=data, schema=schema)
        errors.extend(_validate_accounts(data, filepath))
    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
    except ValidationError as e:
        errors.append(f"Schema validation error: {getattr(e, 'message', str(e))}")
        if e.path:
            errors.append(f"  at path: {'.'.join(str(p) for p in e.path)}")
    except Exception as e:
        errors.append(f"Error: {e}")
    return errors


def main():
    """Validate all finances YAML files in the data/ directory."""
    schema = load_schema()
    data_dir = Path(__file__).parent / "data"

    if not data_dir.exists():
        print(f"Error: data directory not found: {data_dir}")
        return 1

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
