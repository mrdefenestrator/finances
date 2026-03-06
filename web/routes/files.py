"""File management blueprint — create, copy, rename, delete YAML files."""

import re
import shutil

import yaml
from flask import Blueprint, abort, current_app, redirect, request, url_for

from .common import DATA_DIR

files_bp = Blueprint("files", __name__, url_prefix="/files")

# Minimal valid finances YAML skeleton
EMPTY_FINANCES = {
    "accounts": [],
    "budget": [],
    "assets": [],
}


def _sanitize_name(raw: str) -> str:
    """Return a safe filename (no path separators, always .yaml extension).

    Raises ValueError if the name is empty or invalid after sanitisation.
    """
    # Strip leading/trailing whitespace and any directory components
    name = raw.strip()
    name = name.replace("\\", "/")
    name = name.rsplit("/", 1)[-1]

    # Remove .yaml/.yml extension if provided — we add it back
    name = re.sub(r"\.(yaml|yml)$", "", name, flags=re.IGNORECASE)

    # Only allow alphanumerics, hyphens, underscores, spaces, dots
    name = re.sub(r"[^a-zA-Z0-9 _\-.]", "", name).strip()
    if not name:
        raise ValueError("Invalid filename")

    return name + ".yaml"


def _resolve_path(filename: str):
    """Resolve *filename* under DATA_DIR. Abort 400 if it escapes."""
    path = (DATA_DIR / filename).resolve()
    if not str(path).startswith(str(DATA_DIR.resolve())):
        abort(400, description="Invalid path")
    return path


def _navigate_to_file(stem: str):
    """Navigate browser to /f/<stem>/accounts."""
    target = url_for("accounts.accounts_view", filename=stem)
    if request.headers.get("HX-Request"):
        resp = current_app.make_response("")
        resp.headers["HX-Redirect"] = target
        return resp
    return redirect(target)


def _list_yaml_stems() -> list[str]:
    """Return sorted list of .yaml file stems in data/."""
    if not DATA_DIR.exists():
        return []
    return sorted(
        f.stem
        for f in DATA_DIR.iterdir()
        if f.is_file() and f.suffix in (".yaml", ".yml")
    )


# ---- Routes ----------------------------------------------------------------


@files_bp.route("/new", methods=["POST"])
def new():
    """Create a new empty finances YAML file."""
    raw_name = request.form.get("name", "")
    try:
        filename = _sanitize_name(raw_name)
    except ValueError:
        abort(400, description="Invalid filename")

    path = _resolve_path(filename)
    if path.exists():
        abort(409, description=f"File already exists: {filename}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(EMPTY_FINANCES, f, sort_keys=False, default_flow_style=False)

    stem = path.stem
    return _navigate_to_file(stem)


@files_bp.route("/copy", methods=["POST"])
def copy():
    """Copy an existing file to a new name."""
    source = request.form.get("source", "").strip()
    raw_name = request.form.get("name", "")
    try:
        dest_filename = _sanitize_name(raw_name)
    except ValueError:
        abort(400, description="Invalid filename")

    src_path = _resolve_path(source)
    if not src_path.exists():
        abort(404, description=f"Source file not found: {source}")

    dest_path = _resolve_path(dest_filename)
    if dest_path.exists():
        abort(409, description=f"File already exists: {dest_filename}")

    shutil.copy2(src_path, dest_path)

    stem = dest_path.stem
    return _navigate_to_file(stem)


@files_bp.route("/rename", methods=["POST"])
def rename():
    """Rename a file."""
    old_name = request.form.get("old_name", "").strip()
    raw_new = request.form.get("new_name", "")
    try:
        new_filename = _sanitize_name(raw_new)
    except ValueError:
        abort(400, description="Invalid filename")

    old_path = _resolve_path(old_name)
    if not old_path.exists():
        abort(404, description=f"File not found: {old_name}")

    new_path = _resolve_path(new_filename)
    if new_path.exists():
        abort(409, description=f"File already exists: {new_filename}")

    old_path.rename(new_path)

    stem = new_path.stem
    return _navigate_to_file(stem)


@files_bp.route("/delete", methods=["POST"])
def delete():
    """Delete a file and navigate to the default or first remaining file."""
    name = request.form.get("name", "").strip()
    path = _resolve_path(name)
    if not path.exists():
        abort(404, description=f"File not found: {name}")

    path.unlink()

    remaining_stems = _list_yaml_stems()
    if remaining_stems:
        return _navigate_to_file(remaining_stems[0])

    # No files left — go to root selection page
    target = url_for("status.status_view")
    if request.headers.get("HX-Request"):
        resp = current_app.make_response("")
        resp.headers["HX-Redirect"] = target
        return resp
    return redirect(target)
