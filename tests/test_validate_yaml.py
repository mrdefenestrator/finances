"""Tests for validate_yaml — schema constraint and junk-field checks."""

import pytest

from validate_yaml import _check_junk_fields, load_schema, validate_finances_data


def _minimal_data(**overrides):
    """Return a valid minimal finances data dict, with optional collection overrides."""
    data = {
        "accounts": [{"id": 1, "name": "Checking", "type": "checking", "balance": 100}],
        "budget": [
            {
                "kind": "income",
                "description": "Salary",
                "amount": 1000,
                "recurrence": "monthly",
            }
        ],
        "assets": [{"kind": "asset", "name": "Home", "value": 100000}],
    }
    data.update(overrides)
    return data


@pytest.fixture(scope="module")
def schema():
    return load_schema()


# =============================================================================
# _check_junk_fields
# =============================================================================


def test_check_junk_income_with_continuous():
    data = _minimal_data(
        budget=[
            {
                "kind": "income",
                "description": "X",
                "amount": 1,
                "recurrence": "monthly",
                "continuous": True,
            }
        ]
    )
    errors = _check_junk_fields(data)
    assert any("continuous" in e for e in errors)


def test_check_junk_income_with_expense_type():
    data = _minimal_data(
        budget=[
            {
                "kind": "income",
                "description": "X",
                "amount": 1,
                "recurrence": "monthly",
                "type": "housing",
            }
        ]
    )
    errors = _check_junk_fields(data)
    assert any("housing" in e for e in errors)


def test_check_junk_expense_with_income_type():
    data = _minimal_data(
        budget=[
            {
                "kind": "expense",
                "description": "X",
                "amount": 1,
                "recurrence": "monthly",
                "type": "salary",
            }
        ]
    )
    errors = _check_junk_fields(data)
    assert any("salary" in e for e in errors)


def test_check_junk_asset_with_balance():
    data = _minimal_data(
        assets=[{"kind": "asset", "name": "Home", "value": 100000, "balance": 50000}]
    )
    errors = _check_junk_fields(data)
    assert any("balance" in e for e in errors)


def test_check_junk_asset_with_assetref():
    data = _minimal_data(
        assets=[{"kind": "asset", "name": "Home", "value": 100000, "assetRef": 1}]
    )
    errors = _check_junk_fields(data)
    assert any("assetRef" in e for e in errors)


def test_check_junk_debt_with_value():
    data = _minimal_data(
        assets=[{"kind": "debt", "name": "Mortgage", "balance": 200000, "value": 999}]
    )
    errors = _check_junk_fields(data)
    assert any("value" in e for e in errors)


def test_check_junk_debt_with_id():
    data = _minimal_data(
        assets=[{"kind": "debt", "name": "Mortgage", "balance": 200000, "id": 99}]
    )
    errors = _check_junk_fields(data)
    assert any("'id'" in e for e in errors)


def test_check_junk_credit_card_with_balance():
    data = _minimal_data(
        accounts=[
            {
                "id": 1,
                "name": "Amex",
                "type": "credit_card",
                "limit": 5000,
                "available": 5000,
                "balance": 0,
            }
        ]
    )
    errors = _check_junk_fields(data)
    assert any("balance" in e for e in errors)


def test_check_junk_non_cc_with_limit():
    data = _minimal_data(
        accounts=[
            {
                "id": 1,
                "name": "Checking",
                "type": "checking",
                "balance": 100,
                "limit": 5000,
            }
        ]
    )
    errors = _check_junk_fields(data)
    assert any("limit" in e for e in errors)


def test_check_junk_clean_data_no_errors():
    data = _minimal_data()
    errors = _check_junk_fields(data)
    assert errors == []


# =============================================================================
# Schema oneOf enforcement via validate_finances_data
# =============================================================================


def test_schema_rejects_income_with_continuous(schema):
    data = _minimal_data(
        budget=[
            {
                "kind": "income",
                "description": "X",
                "amount": 1,
                "recurrence": "monthly",
                "continuous": True,
            }
        ]
    )
    errors = validate_finances_data(data, schema)
    assert errors


def test_schema_rejects_expense_with_income_type(schema):
    data = _minimal_data(
        budget=[
            {
                "kind": "expense",
                "description": "X",
                "amount": 1,
                "recurrence": "monthly",
                "type": "salary",
            }
        ]
    )
    errors = validate_finances_data(data, schema)
    assert errors


def test_schema_rejects_asset_with_balance(schema):
    data = _minimal_data(
        assets=[{"kind": "asset", "name": "Home", "value": 100000, "balance": 50000}]
    )
    errors = validate_finances_data(data, schema)
    assert errors


def test_schema_rejects_debt_with_value(schema):
    data = _minimal_data(
        assets=[{"kind": "debt", "name": "Mortgage", "balance": 200000, "value": 999}]
    )
    errors = validate_finances_data(data, schema)
    assert errors


def test_schema_rejects_debt_with_id(schema):
    data = _minimal_data(
        assets=[{"kind": "debt", "name": "Mortgage", "balance": 200000, "id": 1}]
    )
    errors = validate_finances_data(data, schema)
    assert errors


def test_schema_rejects_credit_card_with_balance(schema):
    data = _minimal_data(
        accounts=[
            {
                "id": 1,
                "name": "Amex",
                "type": "credit_card",
                "limit": 5000,
                "available": 5000,
                "balance": 0,
            }
        ]
    )
    errors = validate_finances_data(data, schema)
    assert errors


def test_schema_rejects_non_cc_with_limit(schema):
    data = _minimal_data(
        accounts=[
            {
                "id": 1,
                "name": "Checking",
                "type": "checking",
                "balance": 100,
                "limit": 5000,
            }
        ]
    )
    errors = validate_finances_data(data, schema)
    assert errors


def test_schema_rejects_credit_card_missing_limit(schema):
    data = _minimal_data(
        accounts=[{"id": 1, "name": "Amex", "type": "credit_card", "available": 5000}]
    )
    errors = validate_finances_data(data, schema)
    assert errors


def test_schema_rejects_non_cc_missing_balance(schema):
    data = _minimal_data(accounts=[{"id": 1, "name": "Checking", "type": "checking"}])
    errors = validate_finances_data(data, schema)
    assert errors


def test_schema_valid_income_entry(schema):
    data = _minimal_data(
        budget=[
            {
                "kind": "income",
                "description": "Salary",
                "amount": 5000,
                "recurrence": "monthly",
                "type": "salary",
                "dayOfMonth": 1,
            }
        ]
    )
    errors = validate_finances_data(data, schema)
    assert errors == []


def test_schema_valid_expense_entry(schema):
    data = _minimal_data(
        budget=[
            {
                "kind": "expense",
                "description": "Food",
                "amount": 500,
                "recurrence": "monthly",
                "continuous": True,
                "type": "food",
            }
        ]
    )
    errors = validate_finances_data(data, schema)
    assert errors == []


def test_schema_valid_asset_entry(schema):
    data = _minimal_data(
        assets=[{"kind": "asset", "name": "Home", "value": 500000, "source": "Zillow"}]
    )
    errors = validate_finances_data(data, schema)
    assert errors == []


def test_schema_valid_debt_entry(schema):
    data = _minimal_data(
        assets=[
            {
                "kind": "debt",
                "name": "Mortgage",
                "balance": 300000,
                "interestRate": 0.065,
            }
        ]
    )
    errors = validate_finances_data(data, schema)
    assert errors == []


def test_schema_valid_credit_card(schema):
    data = _minimal_data(
        accounts=[
            {
                "id": 1,
                "name": "Amex",
                "type": "credit_card",
                "limit": 5000,
                "available": 4500,
            }
        ]
    )
    errors = validate_finances_data(data, schema)
    assert errors == []


def test_schema_valid_non_cc_account(schema):
    data = _minimal_data(
        accounts=[
            {
                "id": 1,
                "name": "Checking",
                "type": "checking",
                "balance": 1000,
                "minimum_balance": 100,
            }
        ]
    )
    errors = validate_finances_data(data, schema)
    assert errors == []
