"""Status blueprint - shows file selection at root."""

from flask import Blueprint, render_template

from .common import DATA_DIR

status_bp = Blueprint("status", __name__)


@status_bp.route("/")
def status_view():
    """Show file selection page."""
    available_files = (
        sorted(
            f.stem
            for f in DATA_DIR.iterdir()
            if f.is_file() and f.suffix in (".yaml", ".yml")
        )
        if DATA_DIR.exists()
        else []
    )
    return render_template(
        "file_select.html",
        filename="",
        available_files=available_files,
        edit_mode=False,
        n2=None,
        n3=None,
        n6=None,
    )
