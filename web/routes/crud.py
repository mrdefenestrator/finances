"""Shared CRUD helpers for web routes.

Replaces duplicated type coercion, update, delete, and move logic
across accounts, budget, and assets routes.
"""

from flask import current_app, request

# =============================================================================
# Field coercion maps: field name -> coercion type
# =============================================================================

FLOAT_COERCE = "float"
INT_COERCE = "int"

ACCOUNTS_COERCION = {
    "balance": FLOAT_COERCE,
    "limit": FLOAT_COERCE,
    "available": FLOAT_COERCE,
    "rewards_balance": FLOAT_COERCE,
    "statement_balance": FLOAT_COERCE,
    "minimum_balance": FLOAT_COERCE,
    "statement_due_day_of_month": INT_COERCE,
    "paymentAccountRef": INT_COERCE,
}

BUDGET_COERCION = {
    "amount": FLOAT_COERCE,
    "dayOfMonth": INT_COERCE,
    "month": INT_COERCE,
    "dayOfYear": INT_COERCE,
    "autoAccountRef": INT_COERCE,
}

ASSETS_COERCION = {
    "value": FLOAT_COERCE,
    "quantity": FLOAT_COERCE,
    "balance": FLOAT_COERCE,
    "interestRate": FLOAT_COERCE,
    "assetRef": INT_COERCE,
}


def coerce_value(field: str, value_raw: str, coercion_map: dict):
    """Coerce a raw string value to the correct Python type based on field.

    Returns (value, error). If error is not None, coercion failed.
    """
    coerce_type = coercion_map.get(field)
    if coerce_type == FLOAT_COERCE:
        try:
            return (float(value_raw) if value_raw else None), None
        except ValueError:
            return None, f"Invalid number for {field}"
    elif coerce_type == INT_COERCE:
        try:
            return (int(value_raw) if value_raw else None), None
        except ValueError:
            return None, f"Invalid integer for {field}"
    return value_raw, None


def handle_delete(writer_fn, engine):
    """Generic delete handler.

    Args:
        writer_fn: callable(conn) -> None, may raise ValueError
        engine: SQLAlchemy Engine
    """
    try:
        with engine.connect() as conn:
            writer_fn(conn)
    except ValueError:
        return "", 422
    resp = current_app.make_response("")
    resp.headers["HX-Refresh"] = "true"
    return resp


def handle_move(writer_fn, engine):
    """Generic move handler.

    Args:
        writer_fn: callable(conn, direction) -> None, may raise ValueError
        engine: SQLAlchemy Engine
    """
    direction = request.args.get("direction", "up").lower()
    if direction not in ("up", "down"):
        return "", 422
    try:
        with engine.connect() as conn:
            writer_fn(conn, direction)
    except ValueError:
        return "", 422
    resp = current_app.make_response("")
    resp.headers["HX-Refresh"] = "true"
    return resp
