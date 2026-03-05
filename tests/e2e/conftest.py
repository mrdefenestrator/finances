"""Shared fixtures for e2e Playwright tests."""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_SRC = PROJECT_ROOT / "tests" / "fixtures" / "test_finances.yaml"


def _free_port() -> int:
    """Find a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(port: int, timeout: float = 10.0) -> None:
    """Block until the Flask server is accepting connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"Flask server did not start on port {port}")


@pytest.fixture(scope="session")
def flask_server(tmp_path_factory):
    """Start Flask on a random port with a temp copy of the fixture YAML.

    Yields the base URL (e.g. ``http://127.0.0.1:54321``).
    The server is torn down after the test session.
    """
    port = _free_port()
    data_dir = tmp_path_factory.mktemp("data")
    data_file = data_dir / "test_finances.yaml"
    shutil.copy(FIXTURE_SRC, data_file)

    env = {
        **os.environ,
        "FINANCES_DATA": str(data_file),
        "FLASK_RUN_PORT": str(port),
    }

    proc = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "web" / "app.py")],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        _wait_for_server(port)
    except TimeoutError:
        proc.terminate()
        proc.wait(timeout=5)
        raise

    yield f"http://127.0.0.1:{port}"

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.fixture(scope="session")
def _data_file_path(flask_server, tmp_path_factory):
    """Return path to the data file used by the Flask server."""
    return Path(os.environ.get("FINANCES_DATA", ""))


@pytest.fixture(autouse=True)
def reset_data(flask_server):
    """Reset the test YAML data file before each test.

    This ensures tests are independent - each starts with the original fixture.
    We find the data file path from the environment the server was started with.
    """
    # The data file path was set via FINANCES_DATA env var when starting the server.
    # We need to find the actual tmp path - extract from the server fixture.
    # Since we can't easily get it, we'll use a different approach:
    # store the data file path in a module-level variable during server startup.
    pass


# We need a better way to reset data. Let's use a fixture that knows the path.
@pytest.fixture(scope="session")
def data_file(flask_server, tmp_path_factory):
    """Path to the data YAML file used by the running server."""
    # Reconstruct: the flask_server fixture created the file in a tmp dir.
    # We need to find it. Let's use a class-level approach instead.
    # Actually, let's just search for it in the tmp dirs.
    import glob

    pattern = str(tmp_path_factory.getbasetemp() / "**" / "test_finances.yaml")
    matches = glob.glob(pattern, recursive=True)
    if matches:
        return Path(matches[0])
    raise FileNotFoundError("Could not find test data file")


@pytest.fixture(autouse=True)
def _reset_data(data_file):
    """Reset test data before each test."""
    shutil.copy(FIXTURE_SRC, data_file)
    yield


@pytest.fixture(autouse=True)
def _set_default_timeout(page):
    """Use a short default timeout so test failures are fast."""
    page.set_default_timeout(5000)


def enable_edit_mode(page):
    """Click the global lock button to enter edit mode.

    Waits for the button to change to 'Exit edit mode' (i.e. the full page
    navigation triggered by the edit toggle has completed).
    """
    page.locator("button[title='Enter edit mode']").click()
    page.locator("button[title='Exit edit mode']").wait_for(
        state="visible", timeout=5000
    )
