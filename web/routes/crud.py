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


def handle_update(
    path,
    field: str,
    value_raw: str,
    coercion_map: dict,
    get_entry_fn,
    writer_fn,
    render_tbody_fn,
    entry_id_kwargs: dict,
    editable_check_fn=None,
):
    """Generic update handler for a single field.

    Args:
        path: Path to YAML file
        field: Field name to update
        value_raw: Raw string value from form
        coercion_map: Field->type mapping for coercion
        get_entry_fn: callable(path) -> entry dict or None
        writer_fn: callable(path, updates) -> None
        render_tbody_fn: callable(**kwargs) -> HTML string
        entry_id_kwargs: dict of id params for render_tbody (e.g. updated_account_id=1)
        editable_check_fn: optional callable(entry, field) -> bool
    """
    if not field:
        return render_tbody_fn(path, edit_mode=True), 422

    # Check editability
    entry = get_entry_fn(path)
    if editable_check_fn and entry is not None and not editable_check_fn(entry, field):
        return render_tbody_fn(
            path,
            edit_mode=True,
            **entry_id_kwargs,
        )

    # Coerce value
    value, error = coerce_value(field, value_raw, coercion_map)
    if error:
        return render_tbody_fn(path, edit_mode=True), 422

    # Check if unchanged
    entry = get_entry_fn(path)
    if entry is not None:
        current = entry.get(field)
        if current == value:
            return render_tbody_fn(
                path,
                edit_mode=True,
                **entry_id_kwargs,
            )

    # Write
    updates = {field: value}
    try:
        writer_fn(path, updates)
    except ValueError:
        return render_tbody_fn(path, edit_mode=True), 422

    return render_tbody_fn(
        path,
        edit_mode=True,
        **entry_id_kwargs,
    )


def handle_delete(writer_fn, path):
    """Generic delete handler.

    Args:
        writer_fn: callable(path) -> None, may raise ValueError
        path: Path to YAML file
    """
    try:
        writer_fn(path)
    except ValueError:
        return "", 422
    resp = current_app.make_response("")
    resp.headers["HX-Refresh"] = "true"
    return resp


def handle_move(writer_fn, path):
    """Generic move handler.

    Args:
        writer_fn: callable(path, direction) -> None, may raise ValueError
        path: Path to YAML file
    """
    direction = request.args.get("direction", "up").lower()
    if direction not in ("up", "down"):
        return "", 422
    try:
        writer_fn(path, direction)
    except ValueError:
        return "", 422
    resp = current_app.make_response("")
    resp.headers["HX-Refresh"] = "true"
    return resp
