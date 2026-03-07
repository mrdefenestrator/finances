"""Tests for finances writer module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from finances.writer import (
    add_account,
    add_asset_entry,
    add_budget_entry,
    delete_account,
    delete_asset_entry,
    delete_budget_entry,
    move_account,
    move_asset_entry,
    move_budget_entry,
    update_account,
    update_asset_entry,
    update_budget_entry,
)
from finances.loader import load_finances


@pytest.fixture
def temp_data_file():
    """Create a temporary finances YAML file with test data."""
    data = {
        "accounts": [
            {"id": 1, "name": "Checking", "type": "checking", "balance": 1000},
            {"id": 2, "name": "Savings", "type": "savings", "balance": 5000},
        ],
        "budget": [
            {
                "kind": "income",
                "description": "Salary",
                "amount": 5000,
                "recurrence": "monthly",
                "dayOfMonth": 1,
            },
            {
                "kind": "income",
                "description": "Bonus",
                "amount": 1000,
                "recurrence": "one_time",
                "date": "2025-12-25",
            },
            {
                "kind": "expense",
                "description": "Rent",
                "amount": 1500,
                "recurrence": "monthly",
                "dayOfMonth": 1,
            },
            {
                "kind": "expense",
                "description": "Food",
                "amount": 500,
                "recurrence": "monthly",
                "continuous": True,
            },
        ],
        "assets": [
            {"kind": "asset", "id": 1, "name": "Home", "value": 500000},
            {"kind": "asset", "id": 2, "name": "Car", "value": 25000},
            {"kind": "debt", "name": "Mortgage", "balance": 400000, "assetRef": 1},
            {"kind": "debt", "name": "Car Loan", "balance": 15000, "assetRef": 2},
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        return Path(f.name)


# =============================================================================
# Account tests
# =============================================================================


def test_add_account(temp_data_file):
    """Add account assigns next id and appends."""
    new_id = add_account(
        temp_data_file, {"name": "Gift Card", "type": "gift_card", "balance": 50}
    )
    assert new_id == 3
    data = load_finances(temp_data_file)
    assert len(data["accounts"]) == 3
    assert data["accounts"][2]["name"] == "Gift Card"
    assert data["accounts"][2]["id"] == 3


def test_update_account(temp_data_file):
    """Update account by id."""
    update_account(temp_data_file, 1, {"name": "Main Checking", "balance": 2000})
    data = load_finances(temp_data_file)
    acc = next(a for a in data["accounts"] if a["id"] == 1)
    assert acc["name"] == "Main Checking"
    assert acc["balance"] == 2000


def test_update_account_not_found(temp_data_file):
    """Update non-existent account raises ValueError."""
    with pytest.raises(ValueError, match="id 99 not found"):
        update_account(temp_data_file, 99, {"name": "X"})


def test_delete_account(temp_data_file):
    """Delete account by id."""
    delete_account(temp_data_file, 2)
    data = load_finances(temp_data_file)
    assert len(data["accounts"]) == 1
    assert data["accounts"][0]["id"] == 1


def test_delete_account_not_found(temp_data_file):
    """Delete non-existent account raises ValueError."""
    with pytest.raises(ValueError, match="id 99 not found"):
        delete_account(temp_data_file, 99)


def test_delete_account_referenced_by_budget(temp_data_file):
    """Cannot delete account referenced by budget autoAccountRef."""
    # First add budget entry that references account 1
    add_budget_entry(
        temp_data_file,
        {
            "kind": "income",
            "description": "Direct Deposit",
            "amount": 100,
            "recurrence": "monthly",
            "autoAccountRef": 1,
        },
    )
    with pytest.raises(ValueError, match="referenced by a budget entry"):
        delete_account(temp_data_file, 1)


def test_delete_account_referenced_by_payment_account_ref(temp_data_file):
    """Cannot delete account referenced by another account's paymentAccountRef."""
    # Set account 2 (Savings) as the paymentAccountRef for a new credit card
    add_account(
        temp_data_file,
        {
            "name": "Amex",
            "type": "credit_card",
            "limit": 5000,
            "available": 4500,
            "paymentAccountRef": 2,
        },
    )
    with pytest.raises(ValueError, match="paymentAccountRef"):
        delete_account(temp_data_file, 2)


def test_delete_account_not_referenced_by_payment_account_ref(temp_data_file):
    """Can delete account when no credit card references it via paymentAccountRef."""
    add_account(
        temp_data_file,
        {
            "name": "Amex",
            "type": "credit_card",
            "limit": 5000,
            "available": 4500,
            "paymentAccountRef": 1,
        },
    )
    # Deleting account 2 (not referenced) should succeed
    delete_account(temp_data_file, 2)
    data = load_finances(temp_data_file)
    assert all(a["id"] != 2 for a in data["accounts"])


def test_move_account(temp_data_file):
    """Move account up/down."""
    # Initial order: id 1, id 2
    move_account(temp_data_file, 2, "up")
    data = load_finances(temp_data_file)
    assert data["accounts"][0]["id"] == 2
    assert data["accounts"][1]["id"] == 1

    # Move back down
    move_account(temp_data_file, 2, "down")
    data = load_finances(temp_data_file)
    assert data["accounts"][0]["id"] == 1
    assert data["accounts"][1]["id"] == 2


def test_move_account_boundary(temp_data_file):
    """Move at boundary is no-op."""
    move_account(temp_data_file, 1, "up")  # Already at top
    data = load_finances(temp_data_file)
    assert data["accounts"][0]["id"] == 1

    move_account(temp_data_file, 2, "down")  # Already at bottom
    data = load_finances(temp_data_file)
    assert data["accounts"][1]["id"] == 2


# =============================================================================
# Budget tests (unified income+expense)
# =============================================================================


def test_add_budget_income(temp_data_file):
    """Add income budget entry."""
    add_budget_entry(
        temp_data_file,
        {
            "kind": "income",
            "description": "Refund",
            "amount": 100,
            "recurrence": "one_time",
            "date": "2025-03-01",
        },
    )
    data = load_finances(temp_data_file)
    assert len(data["budget"]) == 5
    assert data["budget"][4]["description"] == "Refund"
    assert data["budget"][4]["kind"] == "income"


def test_add_budget_expense(temp_data_file):
    """Add expense budget entry."""
    add_budget_entry(
        temp_data_file,
        {
            "kind": "expense",
            "description": "Gas",
            "amount": 200,
            "recurrence": "monthly",
            "continuous": True,
        },
    )
    data = load_finances(temp_data_file)
    assert len(data["budget"]) == 5
    assert data["budget"][4]["description"] == "Gas"
    assert data["budget"][4]["kind"] == "expense"


def test_update_budget_entry(temp_data_file):
    """Update budget entry by index."""
    update_budget_entry(temp_data_file, 0, {"amount": 6000})
    data = load_finances(temp_data_file)
    assert data["budget"][0]["amount"] == 6000


def test_update_budget_entry_out_of_range(temp_data_file):
    """Update budget entry out of range raises ValueError."""
    with pytest.raises(ValueError, match="index 99 out of range"):
        update_budget_entry(temp_data_file, 99, {"amount": 1})


def test_delete_budget_entry(temp_data_file):
    """Delete budget entry by index."""
    delete_budget_entry(temp_data_file, 1)  # Remove "Bonus" (index 1)
    data = load_finances(temp_data_file)
    assert len(data["budget"]) == 3
    assert data["budget"][0]["description"] == "Salary"
    assert data["budget"][1]["description"] == "Rent"


def test_move_budget_entry(temp_data_file):
    """Move budget entry up/down (can cross income/expense boundary)."""
    # Initial: [Salary(0), Bonus(1), Rent(2), Food(3)]
    # Move Rent (index 2) up to index 1
    move_budget_entry(temp_data_file, 2, "up")
    data = load_finances(temp_data_file)
    assert data["budget"][1]["description"] == "Rent"
    assert data["budget"][2]["description"] == "Bonus"


def test_move_budget_entry_crosses_kinds(temp_data_file):
    """Moving a budget entry can cross income/expense boundary."""
    # Move Bonus (index 1, income) down past Rent (index 2, expense)
    move_budget_entry(temp_data_file, 1, "down")
    data = load_finances(temp_data_file)
    assert data["budget"][1]["description"] == "Rent"
    assert data["budget"][2]["description"] == "Bonus"


# =============================================================================
# Asset entry tests (unified assets array: kind=asset and kind=debt)
# =============================================================================
# Fixture layout: assets[0]=Home(asset), assets[1]=Car(asset),
#                 assets[2]=Mortgage(debt, assetRef=1), assets[3]=CarLoan(debt, assetRef=2)


def test_add_asset_entry_asset(temp_data_file):
    """Add asset entry assigns next id and appends."""
    new_id = add_asset_entry(
        temp_data_file, {"kind": "asset", "name": "Stocks", "value": 10000}
    )
    assert new_id == 3
    data = load_finances(temp_data_file)
    assert len(data["assets"]) == 5
    assert data["assets"][4]["id"] == 3
    assert data["assets"][4]["kind"] == "asset"


def test_add_asset_entry_debt(temp_data_file):
    """Add debt entry does not assign id. Returns None."""
    result = add_asset_entry(
        temp_data_file, {"kind": "debt", "name": "Student Loan", "balance": 30000}
    )
    assert result is None
    data = load_finances(temp_data_file)
    assert len(data["assets"]) == 5
    assert data["assets"][4]["name"] == "Student Loan"
    assert data["assets"][4]["kind"] == "debt"
    assert "id" not in data["assets"][4]


def test_update_asset_entry(temp_data_file):
    """Update asset entry by global index."""
    update_asset_entry(temp_data_file, 0, {"value": 550000})
    data = load_finances(temp_data_file)
    assert data["assets"][0]["value"] == 550000

    # Update debt entry (index 2)
    update_asset_entry(temp_data_file, 2, {"balance": 395000})
    data = load_finances(temp_data_file)
    assert data["assets"][2]["balance"] == 395000


def test_delete_asset_entry_debt(temp_data_file):
    """Delete debt entry (no reference check needed)."""
    delete_asset_entry(temp_data_file, 3)  # Remove "Car Loan" (index 3)
    data = load_finances(temp_data_file)
    assert len(data["assets"]) == 3
    assert data["assets"][2]["name"] == "Mortgage"


def test_delete_asset_entry_asset(temp_data_file):
    """Delete asset entry after removing referencing debt."""
    delete_asset_entry(temp_data_file, 3)  # Remove "Car Loan" (index 3, assetRef=2)
    delete_asset_entry(temp_data_file, 1)  # Now delete "Car" (index 1)
    data = load_finances(temp_data_file)
    # Remaining: Home(0), Mortgage(1)
    assert len(data["assets"]) == 2
    assert data["assets"][0]["name"] == "Home"


def test_delete_asset_entry_referenced_by_debt(temp_data_file):
    """Cannot delete asset entry that is referenced by a debt entry."""
    with pytest.raises(ValueError, match="referenced by a debt"):
        delete_asset_entry(temp_data_file, 0)  # Home is referenced by Mortgage


def test_move_asset_entry(temp_data_file):
    """Move asset entry up/down within unified list."""
    # Move Car (index 1) up to index 0
    move_asset_entry(temp_data_file, 1, "up")
    data = load_finances(temp_data_file)
    assert data["assets"][0]["name"] == "Car"
    assert data["assets"][1]["name"] == "Home"


def test_move_asset_entry_crosses_kinds(temp_data_file):
    """Moving an asset entry can cross the asset/debt boundary."""
    # Move Mortgage (index 2, debt) up to index 1 (past Car, asset)
    move_asset_entry(temp_data_file, 2, "up")
    data = load_finances(temp_data_file)
    assert data["assets"][1]["name"] == "Mortgage"
    assert data["assets"][2]["name"] == "Car"


# =============================================================================
# Edge cases
# =============================================================================


def test_move_invalid_direction(temp_data_file):
    """Invalid direction raises ValueError."""
    with pytest.raises(ValueError, match="direction must be 'up' or 'down'"):
        move_account(temp_data_file, 1, "left")


# =============================================================================
# Sanitization tests
# =============================================================================


def test_sanitize_strips_continuous_from_income(temp_data_file):
    """Updating income entry to add 'continuous' strips it before saving."""
    # budget[0] is Salary (kind=income)
    update_budget_entry(temp_data_file, 0, {"continuous": True})
    data = load_finances(temp_data_file)
    assert "continuous" not in data["budget"][0]


def test_sanitize_strips_invalid_type_from_income(temp_data_file):
    """Updating income entry with expense-only type strips 'type' before saving."""
    update_budget_entry(temp_data_file, 0, {"type": "housing"})
    data = load_finances(temp_data_file)
    assert "type" not in data["budget"][0]


def test_sanitize_strips_balance_from_asset(temp_data_file):
    """Updating asset entry to add 'balance' strips it before saving."""
    # assets[0] is Home (kind=asset)
    update_asset_entry(temp_data_file, 0, {"balance": 999})
    data = load_finances(temp_data_file)
    assert "balance" not in data["assets"][0]


def test_sanitize_strips_value_from_debt(temp_data_file):
    """Updating debt entry to add 'value' strips it before saving."""
    # assets[2] is Mortgage (kind=debt)
    update_asset_entry(temp_data_file, 2, {"value": 500000})
    data = load_finances(temp_data_file)
    assert "value" not in data["assets"][2]


def test_sanitize_strips_limit_from_non_cc_account(temp_data_file):
    """Updating non-CC account to add 'limit' strips it before saving."""
    # account id=1 is Checking (type=checking)
    update_account(temp_data_file, 1, {"limit": 5000})
    data = load_finances(temp_data_file)
    acc = next(a for a in data["accounts"] if a["id"] == 1)
    assert "limit" not in acc


def test_sanitize_strips_balance_from_credit_card(temp_data_file):
    """Adding credit_card account with 'balance' strips it before saving."""
    add_account(
        temp_data_file,
        {
            "name": "Amex",
            "type": "credit_card",
            "limit": 5000,
            "available": 4500,
            "balance": 500,
        },
    )
    data = load_finances(temp_data_file)
    cc = next(a for a in data["accounts"] if a["name"] == "Amex")
    assert "balance" not in cc


def test_operations_on_empty_collections():
    """Operations on empty collections handle gracefully."""
    data = {
        "accounts": [],
        "budget": [],
        "assets": [],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        path = Path(f.name)

    # Add to empty should work
    new_id = add_account(path, {"name": "First", "type": "checking", "balance": 100})
    assert new_id == 1

    # Delete from empty should fail
    with pytest.raises(ValueError):
        delete_budget_entry(path, 0)
