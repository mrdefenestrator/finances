"""Write finances YAML data: add, edit, delete with validation after each write."""

from pathlib import Path
from typing import Any, Callable, Dict

import yaml

from .loader import load_finances

# Validation at project root (validate_yaml); run from repo root so it's on path
import validate_yaml


def _save_finances(path: Path, data: Dict[str, Any]) -> None:
    """Write data to YAML file. Preserves key order; use camelCase keys in data."""
    with open(path, "w") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def _validate_and_save(path: Path, data: Dict[str, Any]) -> None:
    """Validate data against schema; if OK write to path, else raise ValueError with errors."""
    schema = validate_yaml.load_schema()
    errors = validate_yaml.validate_finances_data(data, schema)
    if errors:
        raise ValueError("\n".join(errors))
    _save_finances(path, data)


# =============================================================================
# Generic CRUD helpers
# =============================================================================


def _add_entry(
    path: Path,
    collection_key: str,
    entry: Dict[str, Any],
    auto_id: bool = False,
) -> int | None:
    """Add an entry to a collection. If auto_id=True, assigns next id. Returns new id or None."""
    data = load_finances(path)
    entries = data.get(collection_key) or []
    new_entry = dict(entry)
    new_id = None
    if auto_id:
        existing_ids = [e.get("id") for e in entries if isinstance(e.get("id"), int)]
        new_id = max(existing_ids, default=0) + 1
        new_entry["id"] = new_id
    entries.append(new_entry)
    data[collection_key] = entries
    _validate_and_save(path, data)
    return new_id


def _update_entry_by_id(
    path: Path,
    collection_key: str,
    entry_id: int,
    updates: Dict[str, Any],
) -> None:
    """Update entry by id field. Raises ValueError if not found or validation fails."""
    data = load_finances(path)
    entries = data.get(collection_key) or []
    for i, e in enumerate(entries):
        if e.get("id") == entry_id:
            merged = dict(e)
            merged.update(updates)
            entries[i] = merged
            data[collection_key] = entries
            _validate_and_save(path, data)
            return
    raise ValueError(f"{collection_key[:-1].title()} id {entry_id} not found")


def _update_entry_by_index(
    path: Path,
    collection_key: str,
    index: int,
    updates: Dict[str, Any],
    delete_keys: list[str] | None = None,
) -> None:
    """Update entry by index. Raises ValueError if index out of range or validation fails.

    delete_keys: optional list of keys to remove from the entry after applying updates.
    """
    data = load_finances(path)
    entries = data.get(collection_key) or []
    if index < 0 or index >= len(entries):
        raise ValueError(
            f"{collection_key.title()} index {index} out of range (0..{len(entries) - 1})"
        )
    merged = dict(entries[index])
    merged.update(updates)
    for key in delete_keys or []:
        merged.pop(key, None)
    entries[index] = merged
    data[collection_key] = entries
    _validate_and_save(path, data)


def _delete_entry_by_id(
    path: Path,
    collection_key: str,
    entry_id: int,
    pre_delete_check: Callable[[Dict[str, Any], int], None] | None = None,
) -> None:
    """Delete entry by id. Optional pre_delete_check(data, id) can raise ValueError."""
    data = load_finances(path)
    if pre_delete_check:
        pre_delete_check(data, entry_id)
    entries = data.get(collection_key) or []
    new_entries = [e for e in entries if e.get("id") != entry_id]
    if len(new_entries) == len(entries):
        raise ValueError(f"{collection_key[:-1].title()} id {entry_id} not found")
    data[collection_key] = new_entries
    _validate_and_save(path, data)


def _delete_entry_by_index(
    path: Path,
    collection_key: str,
    index: int,
    pre_delete_check: Callable[[Dict[str, Any], int], None] | None = None,
) -> None:
    """Delete entry by index. Optional pre_delete_check(data, index) can raise ValueError."""
    data = load_finances(path)
    entries = data.get(collection_key) or []
    if index < 0 or index >= len(entries):
        raise ValueError(
            f"{collection_key.title()} index {index} out of range (0..{len(entries) - 1})"
        )
    if pre_delete_check:
        pre_delete_check(data, index)
    entries.pop(index)
    data[collection_key] = entries
    _validate_and_save(path, data)


def _move_entry_by_id(
    path: Path,
    collection_key: str,
    entry_id: int,
    direction: str,
) -> None:
    """Move entry up or down by one position. direction is 'up' or 'down'."""
    if direction not in ("up", "down"):
        raise ValueError("direction must be 'up' or 'down'")
    data = load_finances(path)
    entries = data.get(collection_key) or []
    idx = next((i for i, e in enumerate(entries) if e.get("id") == entry_id), None)
    if idx is None:
        raise ValueError(f"{collection_key[:-1].title()} id {entry_id} not found")
    if direction == "up" and idx <= 0:
        return
    if direction == "down" and idx >= len(entries) - 1:
        return
    swap = idx - 1 if direction == "up" else idx + 1
    entries[idx], entries[swap] = entries[swap], entries[idx]
    data[collection_key] = entries
    _validate_and_save(path, data)


def _move_entry_by_index(
    path: Path,
    collection_key: str,
    index: int,
    direction: str,
) -> None:
    """Move entry up or down by one position. direction is 'up' or 'down'."""
    if direction not in ("up", "down"):
        raise ValueError("direction must be 'up' or 'down'")
    data = load_finances(path)
    entries = data.get(collection_key) or []
    if index < 0 or index >= len(entries):
        raise ValueError(f"{collection_key.title()} index {index} out of range")
    if direction == "up" and index <= 0:
        return
    if direction == "down" and index >= len(entries) - 1:
        return
    swap = index - 1 if direction == "up" else index + 1
    entries[index], entries[swap] = entries[swap], entries[index]
    data[collection_key] = entries
    _validate_and_save(path, data)


# =============================================================================
# Reference integrity checks
# =============================================================================


def _check_account_not_referenced(data: Dict[str, Any], account_id: int) -> None:
    """Raise ValueError if any budget entry or account references this account id."""
    for entry in data.get("budget") or []:
        if entry.get("autoAccountRef") == account_id:
            raise ValueError(
                f"Account id {account_id} is referenced by a budget entry; "
                "remove or change autoAccountRef first"
            )
    for acct in data.get("accounts") or []:
        if acct.get("paymentAccountRef") == account_id:
            raise ValueError(
                f"Account id {account_id} is referenced by a credit card's paymentAccountRef; "
                "remove or change paymentAccountRef first"
            )


def _check_asset_not_referenced(data: Dict[str, Any], index: int) -> None:
    """Raise ValueError if any debt entry in assets references this asset's id."""
    assets = data.get("assets") or []
    asset_id = assets[index].get("id")
    for entry in assets:
        if entry.get("kind") == "debt" and entry.get("assetRef") == asset_id:
            raise ValueError(
                f"Asset id {asset_id} is referenced by a debt; "
                "remove or change assetRef first"
            )


# =============================================================================
# Account operations (id-based)
# =============================================================================


def add_account(path: Path, account: Dict[str, Any]) -> int:
    """Append an account; assign next id. Returns the new account id."""
    return _add_entry(path, "accounts", account, auto_id=True)


def update_account(path: Path, account_id: int, updates: Dict[str, Any]) -> None:
    """Update account by id."""
    _update_entry_by_id(path, "accounts", account_id, updates)


def delete_account(path: Path, account_id: int) -> None:
    """Remove account by id. Forbids if any income/expense references it."""
    _delete_entry_by_id(path, "accounts", account_id, _check_account_not_referenced)


def move_account(path: Path, account_id: int, direction: str) -> None:
    """Move account up or down by one position."""
    _move_entry_by_id(path, "accounts", account_id, direction)


# =============================================================================
# Budget operations (index-based, unified income+expense)
# =============================================================================


def add_budget_entry(path: Path, entry: Dict[str, Any]) -> None:
    """Append a budget entry (income or expense)."""
    _add_entry(path, "budget", entry)


def update_budget_entry(
    path: Path,
    index: int,
    updates: Dict[str, Any],
    delete_keys: list[str] | None = None,
) -> None:
    """Update budget entry at index."""
    _update_entry_by_index(path, "budget", index, updates, delete_keys)


def delete_budget_entry(path: Path, index: int) -> None:
    """Remove budget entry at index."""
    _delete_entry_by_index(path, "budget", index)


def move_budget_entry(path: Path, index: int, direction: str) -> None:
    """Move budget entry up or down by one."""
    _move_entry_by_index(path, "budget", index, direction)


# =============================================================================
# Asset operations (index-based, unified asset+debt)
# =============================================================================


def add_asset_entry(path: Path, entry: Dict[str, Any]) -> int | None:
    """Append an asset entry. Auto-assigns id only when kind == 'asset'. Returns new id or None."""
    data = load_finances(path)
    entries = data.get("assets") or []
    new_entry = dict(entry)
    new_id = None
    if entry.get("kind") == "asset":
        existing_ids = [e.get("id") for e in entries if isinstance(e.get("id"), int)]
        new_id = max(existing_ids, default=0) + 1
        new_entry["id"] = new_id
    entries.append(new_entry)
    data["assets"] = entries
    _validate_and_save(path, data)
    return new_id


def update_asset_entry(
    path: Path,
    index: int,
    updates: Dict[str, Any],
    delete_keys: list[str] | None = None,
) -> None:
    """Update asset entry at index (global index in unified assets list)."""
    _update_entry_by_index(path, "assets", index, updates, delete_keys)


def delete_asset_entry(path: Path, index: int) -> None:
    """Remove asset entry at index. For asset entries, checks reference integrity."""
    data = load_finances(path)
    entries = data.get("assets") or []
    if index < 0 or index >= len(entries):
        raise ValueError(f"Assets index {index} out of range (0..{len(entries) - 1})")
    if entries[index].get("kind") == "asset":
        _check_asset_not_referenced(data, index)
    entries.pop(index)
    data["assets"] = entries
    _validate_and_save(path, data)


def move_asset_entry(path: Path, index: int, direction: str) -> None:
    """Move asset entry up or down by one (can cross asset/debt boundary)."""
    _move_entry_by_index(path, "assets", index, direction)
