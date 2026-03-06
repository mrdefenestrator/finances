"""Tests for the files blueprint (web/routes/files.py)."""

import pytest
import yaml

# ---- Fixtures ---------------------------------------------------------------

EMPTY_FINANCES = {
    "accounts": [],
    "budget": [],
    "assets": [],
}


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """Create a temp data/ directory with one default YAML file."""
    d = tmp_path / "data"
    d.mkdir()
    default = d / "finances.yaml"
    with open(default, "w") as f:
        yaml.dump(EMPTY_FINANCES, f, sort_keys=False)

    # Patch DATA_DIR in both common and files (files imports it at module level)
    import web.routes.common as common
    import web.routes.files as files_mod

    monkeypatch.setattr(common, "DATA_DIR", d)
    monkeypatch.setattr(common, "DEFAULT_DATA_FILE", default)
    monkeypatch.setattr(files_mod, "DATA_DIR", d)
    return d


@pytest.fixture()
def client(data_dir):
    """Flask test client with patched data directory."""
    from web.app import app

    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# Mutation routes respond differently based on HX-Request header.
# HTMX requests get HX-Redirect; regular requests get a plain redirect.
HX_HEADERS = {"HX-Request": "true"}


# ---- New --------------------------------------------------------------------


def test_new_file(client, data_dir):
    resp = client.post("/files/new", data={"name": "budget-2026"}, headers=HX_HEADERS)
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect") == "/f/budget-2026/accounts"
    assert (data_dir / "budget-2026.yaml").exists()

    # Verify contents are valid empty skeleton
    with open(data_dir / "budget-2026.yaml") as f:
        data = yaml.safe_load(f)
    assert data == EMPTY_FINANCES


def test_new_file_adds_yaml_extension(client, data_dir):
    resp = client.post("/files/new", data={"name": "test"}, headers=HX_HEADERS)
    assert resp.status_code == 200
    assert (data_dir / "test.yaml").exists()


def test_new_file_already_exists(client, data_dir):
    resp = client.post("/files/new", data={"name": "finances"})
    assert resp.status_code == 409


def test_new_file_invalid_name(client, data_dir):
    resp = client.post("/files/new", data={"name": "   "})
    assert resp.status_code == 400


def test_new_file_path_traversal(client, data_dir):
    resp = client.post("/files/new", data={"name": "../etc/passwd"}, headers=HX_HEADERS)
    # Should sanitize to just "etcpasswd.yaml" (strips path separators)
    assert resp.status_code == 200
    assert not (data_dir.parent / "etc" / "passwd.yaml").exists()


# ---- Copy -------------------------------------------------------------------


def test_copy_file(client, data_dir):
    resp = client.post(
        "/files/copy",
        data={"source": "finances.yaml", "name": "finances-copy"},
        headers=HX_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect") == "/f/finances-copy/accounts"
    assert (data_dir / "finances-copy.yaml").exists()


def test_copy_nonexistent_source(client, data_dir):
    resp = client.post("/files/copy", data={"source": "nope.yaml", "name": "copy"})
    assert resp.status_code == 404


def test_copy_dest_already_exists(client, data_dir):
    resp = client.post(
        "/files/copy", data={"source": "finances.yaml", "name": "finances"}
    )
    assert resp.status_code == 409


# ---- Rename -----------------------------------------------------------------


def test_rename_file(client, data_dir):
    resp = client.post(
        "/files/rename",
        data={"old_name": "finances.yaml", "new_name": "renamed"},
        headers=HX_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect") == "/f/renamed/accounts"
    assert not (data_dir / "finances.yaml").exists()
    assert (data_dir / "renamed.yaml").exists()


def test_rename_nonexistent(client, data_dir):
    resp = client.post(
        "/files/rename",
        data={"old_name": "nope.yaml", "new_name": "renamed"},
    )
    assert resp.status_code == 404


def test_rename_dest_exists(client, data_dir):
    with open(data_dir / "other.yaml", "w") as f:
        yaml.dump(EMPTY_FINANCES, f, sort_keys=False)
    resp = client.post(
        "/files/rename",
        data={"old_name": "finances.yaml", "new_name": "other"},
    )
    assert resp.status_code == 409


# ---- Delete -----------------------------------------------------------------


def test_delete_file(client, data_dir):
    # Create a second file and delete it — should navigate to remaining finances
    with open(data_dir / "deleteme.yaml", "w") as f:
        yaml.dump(EMPTY_FINANCES, f, sort_keys=False)

    resp = client.post(
        "/files/delete", data={"name": "deleteme.yaml"}, headers=HX_HEADERS
    )
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect") == "/f/finances/accounts"
    assert not (data_dir / "deleteme.yaml").exists()


def test_delete_only_file(client, data_dir):
    """Deleting the only file redirects to root file selection page."""
    resp = client.post(
        "/files/delete", data={"name": "finances.yaml"}, headers=HX_HEADERS
    )
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect") == "/"
    assert not (data_dir / "finances.yaml").exists()


def test_delete_nonexistent(client, data_dir):
    resp = client.post("/files/delete", data={"name": "nope.yaml"})
    assert resp.status_code == 404


# ---- Sanitization -----------------------------------------------------------


def test_sanitize_strips_directory_components(client, data_dir):
    resp = client.post("/files/new", data={"name": "foo/bar/baz"}, headers=HX_HEADERS)
    assert resp.status_code == 200
    assert (data_dir / "baz.yaml").exists()
    assert not (data_dir / "foo").exists()
