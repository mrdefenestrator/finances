"""Status blueprint - redirects root to accounts."""

from flask import Blueprint, redirect, url_for

from .common import get_default_filename

status_bp = Blueprint("status", __name__)


@status_bp.route("/")
def status_view():
    """Redirect root to accounts."""
    return redirect(url_for("accounts.accounts_view", filename=get_default_filename()))
