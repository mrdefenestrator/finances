#!/usr/bin/env python3
"""Flask web application for finances tracker (read-only view + inline edit)."""

import os
from pathlib import Path

from flask import Flask, render_template

# Add project root for finances module
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import finances

# Handle both direct execution (./web/app.py) and module import (from web.app import app)
try:
    from .routes import (
        status_bp,
        accounts_bp,
        budget_bp,
        assets_bp,
        files_bp,
        edit_mode_bp,
    )
except ImportError:
    from routes import (
        status_bp,
        accounts_bp,
        budget_bp,
        assets_bp,
        files_bp,
        edit_mode_bp,
    )

app = Flask(__name__)


def _display_is_negative(value):
    """True if value is a number < 0 or a string that looks like a negative (e.g. ($1.00) or -1)."""
    if isinstance(value, (int, float)):
        return value < 0
    if isinstance(value, str):
        s = value.strip()
        return s.startswith("(") or (s.startswith("-") and len(s) > 1)
    return False


# Jinja filters
app.jinja_env.filters["fmt_money"] = lambda x: (
    finances.fmt_money(x) if x is not None else "-"
)


def _fmt_money_header(x):
    """Format money for the page header: accounting parens for negatives, no trailing spaces."""
    if x is None:
        return ""
    if x == 0:
        return "$0.00"
    if x < 0:
        return f"(${abs(x):,.2f})"
    return f"${x:,.2f}"


app.jinja_env.filters["fmt_money_header"] = _fmt_money_header
app.jinja_env.filters["fmt_qty"] = finances.fmt_qty
app.jinja_env.filters["display_is_negative"] = lambda x: _display_is_negative(x)
app.jinja_env.filters["format_type"] = lambda x: finances.fmt_type_display(x)
app.jinja_env.filters["format_recurrence"] = lambda x: finances.fmt_recurrence_display(
    x
)
app.jinja_env.filters["format_month"] = lambda x: finances.fmt_month_short(x)


# Register blueprints
app.register_blueprint(status_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(budget_bp)
app.register_blueprint(assets_bp)
app.register_blueprint(files_bp)
app.register_blueprint(edit_mode_bp)


@app.errorhandler(404)
def not_found(e):
    """Render 404 with message."""
    return render_template(
        "404.html", message=e.description, n2=None, n3=None, n6=None
    ), 404


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_RUN_PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)
