"""Migration script: combine assets/debts into unified assets array with kind field.

Usage:
    uv run python migrate_to_assets.py <file.yaml> [--dry-run]
"""

import sys
from pathlib import Path

import yaml

import validate_yaml


def migrate_file(path: Path, dry_run: bool = False) -> bool:
    """Migrate a single finances YAML file. Returns True on success."""
    with open(path) as f:
        data = yaml.safe_load(f)

    if data is None:
        print(f"  {path}: empty file, skipping")
        return True

    # Check if already migrated (no 'debts' key and assets have 'kind')
    if "debts" not in data:
        assets = data.get("assets") or []
        if all(e.get("kind") in ("asset", "debt") for e in assets) or not assets:
            print(f"  {path}: already migrated (no 'debts' key), skipping")
            return True

    old_assets = data.get("assets") or []
    old_debts = data.get("debts") or []

    # Add kind field to each entry
    new_assets = []
    for entry in old_assets:
        e = dict(entry)
        e["kind"] = "asset"
        new_assets.append(e)
    for entry in old_debts:
        e = dict(entry)
        e["kind"] = "debt"
        new_assets.append(e)

    # Build migrated data
    migrated = dict(data)
    migrated["assets"] = new_assets
    migrated.pop("debts", None)

    # Validate against updated schema
    schema = validate_yaml.load_schema()
    errors = validate_yaml.validate_finances_data(migrated, schema)
    if errors:
        print(f"  {path}: VALIDATION ERRORS after migration:")
        for err in errors:
            print(f"    - {err}")
        return False

    if dry_run:
        print(
            f"  {path}: would migrate {len(old_assets)} assets + {len(old_debts)} debts "
            f"→ {len(new_assets)} unified entries (dry run)"
        )
        return True

    with open(path, "w") as f:
        yaml.dump(
            migrated,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )

    print(
        f"  {path}: migrated {len(old_assets)} assets + {len(old_debts)} debts "
        f"→ {len(new_assets)} unified entries"
    )
    return True


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    files = [a for a in args if not a.startswith("--")]

    if not files:
        print("Usage: uv run python migrate_to_assets.py <file.yaml> [--dry-run]")
        return 1

    all_ok = True
    for f in files:
        path = Path(f)
        if not path.exists():
            print(f"  {path}: file not found")
            all_ok = False
            continue
        ok = migrate_file(path, dry_run=dry_run)
        if not ok:
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
