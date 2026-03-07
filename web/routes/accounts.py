"""Accounts blueprint - accounts table and CRUD operations."""

from datetime import date

from flask import Blueprint, abort, render_template, request

import finances
from finances.writer import (
    add_account as writer_add_account,
    delete_account as writer_delete_account,
    move_account as writer_move_account,
    update_account as writer_update_account,
)

from .common import (
    account_field_editable,
    drop_separator_rows,
    get_common_context,
    validate_url_filename,
)
from .crud import (
    ACCOUNTS_COERCION,
    coerce_value,
    handle_move,
)

accounts_bp = Blueprint("accounts", __name__, url_prefix="/f")

# Use constants from finances (single source of truth)
ACCOUNT_TYPES = finances.ACCOUNT_TYPES


def _render_tbody(
    path,
    edit_mode=True,
    updated_account_id=None,
    updated_field=None,
    editing_account_id=None,
    editing_field=None,
    editing_value=None,
):
    """Render the full accounts tbody after an update."""
    filename = path.stem
    data = finances.load_finances(path)
    accounts = data.get("accounts") or []
    budget = data.get("budget") or []
    today = date.today()
    n2 = finances.liquid_minus_cc(accounts)
    account_display_by_id = finances._account_display_by_id(accounts)
    headers, rows = finances._build_accounts_table(
        accounts, n2, account_display_by_id=account_display_by_id
    )
    rows = drop_separator_rows(rows)
    funding_by_id = {
        acc["id"]: finances.account_funding_needed(
            acc, accounts, budget, today, default_reserve=0
        )
        for acc in accounts
        if finances._ACCOUNT_TYPE_TO_CALCULATION.get(acc.get("type")) == "liquid"
    }
    rows[-1] += ["-", "-"]
    edit_rows = list(zip(accounts, rows))

    return render_template(
        "partials/accounts_tbody.html",
        filename=filename,
        edit_mode=edit_mode,
        edit_rows=edit_rows,
        rows=rows,
        updated_account_id=updated_account_id,
        updated_field=updated_field,
        account_types=ACCOUNT_TYPES,
        account_display_by_id=account_display_by_id,
        editing_account_id=editing_account_id,
        editing_field=editing_field,
        editing_value=editing_value,
        funding_by_id=funding_by_id,
    )


@accounts_bp.route("/<filename>/accounts")
def accounts_view(filename: str):
    """Accounts table with optional filters and edit mode."""
    path = validate_url_filename(filename)
    edit_mode = request.args.get("edit") == "1"
    ctx = get_common_context(path, edit_mode)
    ctx["active_tab"] = "accounts"
    ctx["sort_col"] = request.args.get("sort_col", "")
    ctx["sort_dir"] = request.args.get("sort_dir", "")
    include_types = (
        request.args.getlist("include_type") or request.args.getlist("type") or []
    )
    accounts = finances.filter_accounts_by_type(ctx["accounts"], include_types or None)
    include_types_set = set(t.lower() for t in include_types)
    n2 = finances.liquid_minus_cc(accounts)
    account_display_by_id = ctx["account_display_by_id"]
    ctx["headers"], ctx["rows"] = finances._build_accounts_table(
        accounts, n2, account_display_by_id=account_display_by_id
    )
    ctx["rows"] = drop_separator_rows(ctx["rows"])
    ctx["include_types"] = [t for t in ACCOUNT_TYPES if t in include_types_set]
    ctx["account_types"] = ACCOUNT_TYPES
    ctx["accounts_raw"] = accounts
    ctx["edit_rows"] = list(zip(accounts, ctx["rows"]))

    # Funding columns: compute per-account dict for liquid accounts
    all_accounts = ctx["accounts"]
    budget = ctx["budget"]
    today = date.today()
    ctx["funding_by_id"] = {
        acc["id"]: finances.account_funding_needed(
            acc, all_accounts, budget, today, default_reserve=0
        )
        for acc in all_accounts
        if finances._ACCOUNT_TYPE_TO_CALCULATION.get(acc.get("type")) == "liquid"
    }
    ctx["headers"] += ["Reserve", "Funding Needed"]
    ctx["rows"][-1] += ["-", "-"]

    return render_template("accounts.html", **ctx)


@accounts_bp.route("/<filename>/accounts/cell/<int:account_id>")
def cell_edit(filename: str, account_id: int):
    """Return tbody with cell in edit mode."""
    field = request.args.get("field", "name")
    path = validate_url_filename(filename)
    data = finances.load_finances(path)
    accounts = data.get("accounts") or []
    acc = next((a for a in accounts if a.get("id") == account_id), None)
    if not acc:
        abort(404)

    if request.args.get("display") == "1":
        return _render_tbody(path, edit_mode=True)

    if not account_field_editable(acc, field):
        return _render_tbody(path, edit_mode=True)

    value = acc.get(field, "")
    if value is None:
        value = ""

    return _render_tbody(
        path,
        edit_mode=True,
        editing_account_id=account_id,
        editing_field=field,
        editing_value=value,
    )


@accounts_bp.route("/<filename>/accounts/update/<int:account_id>", methods=["POST"])
def update(filename: str, account_id: int):
    """Update one account field. Returns full tbody HTML."""
    path = validate_url_filename(filename)
    field = request.form.get("field", "name").strip()
    value_raw = request.form.get("value", "").strip()

    if not field:
        return _render_tbody(path, edit_mode=True), 422

    def _get_account(p):
        data = finances.load_finances(p)
        return next(
            (a for a in (data.get("accounts") or []) if a.get("id") == account_id),
            None,
        )

    acc = _get_account(path)
    if acc is not None and not account_field_editable(acc, field):
        return _render_tbody(
            path,
            edit_mode=True,
            updated_account_id=account_id,
            updated_field=field,
        )

    value, error = coerce_value(field, value_raw, ACCOUNTS_COERCION)
    if error:
        return _render_tbody(path, edit_mode=True), 422

    # Skip write if unchanged
    acc = _get_account(path)
    if acc is not None and acc.get(field) == value:
        return _render_tbody(
            path,
            edit_mode=True,
            updated_account_id=account_id,
            updated_field=field,
        )

    try:
        writer_update_account(path, account_id, {field: value})
    except ValueError:
        return _render_tbody(path, edit_mode=True), 422

    return _render_tbody(
        path,
        edit_mode=True,
        updated_account_id=account_id,
        updated_field=field,
    )


@accounts_bp.route("/<filename>/accounts/add", methods=["POST"])
def add(filename: str):
    """Add account. Returns new row HTML fragment."""
    path = validate_url_filename(filename)
    name = request.form.get("name", "").strip()
    acc_type = request.form.get("type", "checking").strip() or "checking"
    account = {"name": name or "New account", "type": acc_type}
    if acc_type == "credit_card":
        try:
            account["limit"] = float(request.form.get("limit") or 0)
            account["available"] = float(request.form.get("available") or 0)
            for key in ("rewards_balance", "statement_balance"):
                v = request.form.get(key, "").strip()
                if v:
                    account[key] = float(v)
            due_day = request.form.get("statement_due_day_of_month", "").strip()
            if due_day:
                account["statement_due_day_of_month"] = int(due_day)
        except ValueError:
            return "", 422
        pay_ref_raw = request.form.get("paymentAccountRef", "").strip()
        if pay_ref_raw:
            try:
                account["paymentAccountRef"] = int(pay_ref_raw)
            except ValueError:
                pass
    else:
        try:
            account["balance"] = float(request.form.get("balance") or 0)
        except ValueError:
            account["balance"] = 0
    for key in ("institution", "partial_account_number", "asOfDate"):
        v = request.form.get(key, "").strip()
        if v:
            account[key] = v
    try:
        new_id = writer_add_account(path, account)
    except ValueError:
        return "", 422
    data = finances.load_finances(path)
    accounts = data.get("accounts") or []
    acc = next((a for a in accounts if a.get("id") == new_id), None)
    if not acc:
        abort(404)
    n2 = finances.liquid_minus_cc(accounts)
    account_display_by_id = finances._account_display_by_id(accounts)
    _, rows = finances._build_accounts_table(
        accounts, n2, account_display_by_id=account_display_by_id
    )
    idx = next((i for i, a in enumerate(accounts) if a.get("id") == new_id), -1)
    new_row = rows[idx] if 0 <= idx < len(rows) else []
    return render_template(
        "partials/accounts_row_display.html",
        filename=filename,
        account_id=new_id,
        account=acc,
        row_cells=new_row,
        account_types=ACCOUNT_TYPES,
        account_display_by_id=account_display_by_id,
    )


@accounts_bp.route("/<filename>/accounts/delete-btn/<int:account_id>")
def delete_btn(filename: str, account_id: int):
    """Return delete button cell fragment (for No cancel)."""
    return render_template(
        "partials/accounts_delete_btn.html",
        filename=filename,
        account_id=account_id,
    )


@accounts_bp.route("/<filename>/accounts/delete-confirm/<int:account_id>")
def delete_confirm(filename: str, account_id: int):
    """Return delete confirm cell fragment."""
    return render_template(
        "partials/accounts_delete_confirm.html",
        filename=filename,
        account_id=account_id,
    )


@accounts_bp.route("/<filename>/accounts/delete/<int:account_id>", methods=["POST"])
def delete(filename: str, account_id: int):
    """Delete account. Returns empty string so HTMX removes the row."""
    path = validate_url_filename(filename)
    try:
        writer_delete_account(path, account_id)
    except ValueError:
        return "", 422
    return ""


@accounts_bp.route("/<filename>/accounts/move/<int:account_id>", methods=["POST"])
def move(filename: str, account_id: int):
    """Move account up or down."""
    path = validate_url_filename(filename)
    return handle_move(
        lambda p, d: writer_move_account(p, account_id, d),
        path,
    )
