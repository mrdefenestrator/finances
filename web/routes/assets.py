"""Assets blueprint - unified assets/debts table and CRUD operations."""

from flask import Blueprint, abort, current_app, render_template, request

import finances
from finances.writer import (
    add_asset_entry as writer_add_asset_entry,
    delete_asset_entry as writer_delete_asset_entry,
    move_asset_entry as writer_move_asset_entry,
    update_asset_entry as writer_update_asset_entry,
)

from .common import drop_separator_rows, get_common_context, validate_url_filename
from .crud import (
    ASSETS_COERCION,
    coerce_value,
    handle_delete,
    handle_move,
)

assets_bp = Blueprint("assets", __name__, url_prefix="/f")

# Use constants from finances (single source of truth)
ASSETS_KINDS = finances.ASSETS_KINDS


def _render_tbody(
    path,
    edit_mode=True,
    updated_index=None,
    updated_field=None,
    editing_index=None,
    editing_field=None,
    editing_value=None,
):
    """Render the full assets tbody after an update."""
    filename = path.stem
    ctx = get_common_context(path, edit_mode)
    assets = ctx["assets"]

    headers, rows = finances._build_net_worth_table(assets)
    rows = drop_separator_rows(rows)

    data_rows = rows[: len(assets)] if rows else []
    assets_edit_rows = [
        (assets[i].get("kind", "asset"), i, data_rows[i]) for i in range(len(assets))
    ]

    asset_by_id = {
        e["id"]: e
        for e in assets
        if e.get("kind") == "asset" and e.get("id") is not None
    }

    return render_template(
        "partials/assets_tbody.html",
        filename=filename,
        edit_mode=edit_mode,
        assets_edit_rows=assets_edit_rows,
        rows=rows,
        updated_index=updated_index,
        updated_field=updated_field,
        assets_kinds=ASSETS_KINDS,
        asset_by_id=asset_by_id,
        editing_index=editing_index,
        editing_field=editing_field,
        editing_value=editing_value,
    )


@assets_bp.route("/<filename>/assets")
def assets_view(filename: str):
    """Assets and debts table with optional filters."""
    path = validate_url_filename(filename)
    edit_mode = request.args.get("edit") == "1"
    ctx = get_common_context(path, edit_mode)
    ctx["active_tab"] = "assets"
    ctx["sort_col"] = request.args.get("sort_col", "")
    ctx["sort_dir"] = request.args.get("sort_dir", "")
    include_kinds = (
        request.args.getlist("include_kind") or request.args.getlist("kind") or []
    )
    all_assets = ctx["assets"]
    filtered = finances.filter_assets_by_kind(all_assets, include_kinds or None)
    include_kinds_set = set(k.lower() for k in include_kinds)
    ctx["headers"], ctx["rows"] = finances._build_net_worth_table(filtered)
    ctx["rows"] = drop_separator_rows(ctx["rows"])
    # Global indices: map filtered entries back to their positions in all_assets
    global_indices = [all_assets.index(e) for e in filtered] if filtered else []
    data_rows = ctx["rows"][: len(filtered)] if ctx["rows"] else []
    ctx["assets_edit_rows"] = [
        (filtered[i].get("kind", "asset"), global_indices[i], data_rows[i])
        for i in range(len(filtered))
    ]
    ctx["include_kinds"] = [k for k in ASSETS_KINDS if k in include_kinds_set]
    ctx["assets_kinds"] = ASSETS_KINDS
    ctx["assets_list"] = all_assets
    ctx["asset_by_id"] = {
        e["id"]: e
        for e in all_assets
        if e.get("kind") == "asset" and e.get("id") is not None
    }
    return render_template("assets.html", **ctx)


@assets_bp.route("/<filename>/assets/delete-btn/<int:index>")
def delete_btn(filename: str, index: int):
    """Return delete button cell fragment (for cancel)."""
    path = validate_url_filename(filename)
    data = finances.load_finances(path)
    assets = data.get("assets") or []
    if index < 0 or index >= len(assets):
        abort(404)
    kind = assets[index].get("kind", "asset")
    return render_template(
        "partials/assets_delete_icon.html",
        filename=filename,
        kind=kind,
        index=index,
        edit_mode=True,
    )


@assets_bp.route("/<filename>/assets/delete-confirm/<int:index>")
def delete_confirm(filename: str, index: int):
    """Return delete confirm cell fragment."""
    path = validate_url_filename(filename)
    data = finances.load_finances(path)
    assets = data.get("assets") or []
    if index < 0 or index >= len(assets):
        abort(404)
    kind = assets[index].get("kind", "asset")
    return render_template(
        "partials/assets_delete_confirm.html",
        filename=filename,
        kind=kind,
        index=index,
    )


@assets_bp.route("/<filename>/assets/delete/<int:index>", methods=["POST"])
def delete(filename: str, index: int):
    """Delete asset or debt by global index."""
    path = validate_url_filename(filename)
    return handle_delete(lambda p: writer_delete_asset_entry(p, index), path)


@assets_bp.route("/<filename>/assets/move/<int:index>", methods=["POST"])
def move(filename: str, index: int):
    """Move asset or debt up/down by global index."""
    path = validate_url_filename(filename)
    return handle_move(lambda p, d: writer_move_asset_entry(p, index, d), path)


@assets_bp.route("/<filename>/assets/add", methods=["POST"])
def add(filename: str):
    """Add asset or debt. kind comes from form field."""
    path = validate_url_filename(filename)
    kind = request.form.get("kind", "asset").strip()
    if kind not in ("asset", "debt"):
        abort(400)
    if kind == "asset":
        name = request.form.get("name", "").strip() or "New asset"
        value_raw = request.form.get("value", "0").strip()
        try:
            value = float(value_raw) if value_raw else 0.0
        except ValueError:
            value = 0.0
        entry = {"kind": "asset", "name": name, "value": value}
        for key in ("institution", "source"):
            val = request.form.get(key, "").strip()
            if val:
                entry[key] = val
    else:
        name = request.form.get("name", "").strip() or "New debt"
        balance_raw = request.form.get("balance", "0").strip()
        try:
            balance = float(balance_raw) if balance_raw else 0.0
        except ValueError:
            balance = 0.0
        entry = {"kind": "debt", "name": name, "balance": balance}
        for key in ("institution", "assetRef", "interestRate"):
            val = request.form.get(key, "").strip()
            if key == "assetRef" and val:
                try:
                    entry["assetRef"] = int(val)
                except ValueError:
                    pass
            elif key == "interestRate" and val:
                try:
                    entry[key] = float(val)
                except ValueError:
                    pass
            elif val:
                entry[key] = val
    qty_raw = request.form.get("quantity", "").strip()
    if qty_raw:
        try:
            entry["quantity"] = float(qty_raw)
        except ValueError:
            pass
    try:
        writer_add_asset_entry(path, entry)
    except ValueError:
        return "", 422
    resp = current_app.make_response("")
    resp.headers["HX-Refresh"] = "true"
    return resp


@assets_bp.route("/<filename>/assets/cell/<int:index>")
def cell_edit(filename: str, index: int):
    """Return tbody with cell in edit mode."""
    field = request.args.get("field", "name")
    path = validate_url_filename(filename)
    data = finances.load_finances(path)
    entries = data.get("assets") or []
    if index < 0 or index >= len(entries):
        abort(404)
    entry = entries[index]

    if request.args.get("display") == "1":
        return _render_tbody(path, edit_mode=True)

    value = entry.get(field, "")
    if value is None:
        value = ""
    if field == "assetRef" and value != "":
        value = str(value)

    return _render_tbody(
        path,
        edit_mode=True,
        editing_index=index,
        editing_field=field,
        editing_value=value,
    )


@assets_bp.route("/<filename>/assets/update/<int:index>", methods=["POST"])
def update(filename: str, index: int):
    """Update one asset/debt field. Returns full tbody HTML."""
    path = validate_url_filename(filename)
    field = request.form.get("field", "name").strip()
    value_raw = request.form.get("value", "").strip()

    if not field:
        return _render_tbody(path, edit_mode=True), 422

    value, error = coerce_value(field, value_raw, ASSETS_COERCION)
    if error:
        return _render_tbody(path, edit_mode=True), 422

    # Check if unchanged
    data = finances.load_finances(path)
    entries = data.get("assets") or []
    if index < 0 or index >= len(entries):
        abort(404)
    if entries[index].get(field) == value:
        return _render_tbody(
            path,
            edit_mode=True,
            updated_index=index,
            updated_field=field,
        )

    try:
        writer_update_asset_entry(path, index, {field: value})
    except ValueError:
        return _render_tbody(path, edit_mode=True), 422

    return _render_tbody(
        path,
        edit_mode=True,
        updated_index=index,
        updated_field=field,
    )
