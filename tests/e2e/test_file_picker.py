"""File picker e2e tests — select, duplicate, rename, delete files."""

import pytest

pytestmark = pytest.mark.e2e


def test_file_picker_shows_active_file(page, flask_server):
    """File picker dropdown shows the current active filename."""
    page.goto(f"{flask_server}/f/test_finances/accounts")
    picker = page.locator("[data-file-picker]")
    assert picker.is_visible()
    # Should display a filename (without .yaml extension)
    assert picker.text_content().strip()


def test_file_picker_lists_files(page, flask_server):
    """Opening the file picker shows available files."""
    page.goto(f"{flask_server}/f/test_finances/accounts")
    page.locator("[data-file-picker]").click()
    dropdown = page.locator("[data-file-picker-dropdown]")
    dropdown.wait_for(state="visible")
    # Should list at least the active file with "active" badge
    assert dropdown.locator("span:has-text('active')").count() >= 1


def test_file_picker_create_new_file(page, flask_server):
    """Creating a new file via the picker navigates back to a valid page."""
    page.goto(f"{flask_server}/f/test_finances/accounts")
    page.locator("[data-file-picker]").click()
    page.locator("[data-file-picker-dropdown]").wait_for(state="visible")

    # Click "New file" button
    page.get_by_text("New file").click()

    # Fill in the name and submit
    name_input = page.locator("input[placeholder='filename']")
    name_input.wait_for(state="visible")
    name_input.fill("e2e-test-new")
    page.get_by_text("Create").click()

    # Should end up on a valid page (not blank /files/new)
    page.wait_for_timeout(500)
    assert "/files/" not in page.url
    assert page.locator("header").is_visible()


def test_file_picker_duplicate_file(page, flask_server):
    """Duplicating a file via the picker navigates back to a valid page."""
    page.goto(f"{flask_server}/f/test_finances/accounts")
    page.locator("[data-file-picker]").click()
    page.locator("[data-file-picker-dropdown]").wait_for(state="visible")

    # Click Duplicate button
    page.get_by_role("button", name="Duplicate", exact=True).click()

    # Fill in the name and submit
    name_input = page.locator("input[placeholder='filename']")
    name_input.wait_for(state="visible")
    name_input.fill("e2e-test-copy")
    page.get_by_text("Create").click()

    # Should end up on a valid page (not blank /files/copy)
    page.wait_for_timeout(500)
    assert "/files/" not in page.url
    assert page.locator("header").is_visible()


def test_file_picker_rename_file(page, flask_server):
    """Renaming a file via the picker navigates back to a valid page."""
    # First create a file to rename
    page.goto(f"{flask_server}/f/test_finances/accounts")
    page.locator("[data-file-picker]").click()
    page.locator("[data-file-picker-dropdown]").wait_for(state="visible")
    page.get_by_text("New file").click()
    name_input = page.locator("input[placeholder='filename']")
    name_input.wait_for(state="visible")
    name_input.fill("e2e-rename-source")
    page.get_by_text("Create").click()
    page.wait_for_timeout(500)

    # Now rename it
    page.locator("[data-file-picker]").click()
    page.locator("[data-file-picker-dropdown]").wait_for(state="visible")
    page.get_by_role("button", name="Rename", exact=True).click()
    name_input = page.locator("input[placeholder='filename']")
    name_input.wait_for(state="visible")
    name_input.fill("e2e-rename-dest")
    page.get_by_text("Save").click()

    # Should end up on a valid page (not blank /files/rename)
    page.wait_for_timeout(500)
    assert "/files/" not in page.url
    assert page.locator("header").is_visible()


def test_file_picker_select_file(page, flask_server):
    """Selecting a different file reloads the page with that file's data."""
    # First create a second file so we have something to switch to
    page.goto(f"{flask_server}/f/test_finances/accounts")
    page.locator("[data-file-picker]").click()
    page.locator("[data-file-picker-dropdown]").wait_for(state="visible")
    page.get_by_text("New file").click()
    name_input = page.locator("input[placeholder='filename']")
    name_input.wait_for(state="visible")
    name_input.fill("e2e-select-target")
    page.get_by_text("Create").click()
    page.wait_for_timeout(500)

    # Switch back to the original file
    page.locator("[data-file-picker]").click()
    page.locator("[data-file-picker-dropdown]").wait_for(state="visible")
    # Click the first non-active file (the test_finances file)
    page.locator("[data-file-picker-dropdown] a").first.click()

    # Should end up on a valid page (not blank /files/select)
    page.wait_for_timeout(500)
    assert "/files/" not in page.url
    assert page.locator("header").is_visible()


def test_file_picker_delete_non_active(page, flask_server):
    """Deleting a non-active file stays on a valid page."""
    # First create a file to delete
    page.goto(f"{flask_server}/f/test_finances/accounts")
    page.locator("[data-file-picker]").click()
    page.locator("[data-file-picker-dropdown]").wait_for(state="visible")
    page.get_by_text("New file").click()
    name_input = page.locator("input[placeholder='filename']")
    name_input.wait_for(state="visible")
    name_input.fill("e2e-to-delete")
    page.get_by_text("Create").click()
    page.wait_for_timeout(500)

    # Switch to original file so we can delete the new one
    page.locator("[data-file-picker]").click()
    page.locator("[data-file-picker-dropdown]").wait_for(state="visible")
    page.locator("[data-file-picker-dropdown] a").first.click()
    page.wait_for_timeout(500)

    # Now delete the created file
    page.locator("[data-file-picker]").click()
    page.locator("[data-file-picker-dropdown]").wait_for(state="visible")

    # Accept the confirm dialog
    page.on("dialog", lambda d: d.accept())
    # Click the delete button next to e2e-to-delete
    delete_btn = page.locator("button[title='Delete e2e-to-delete.yaml']")
    delete_btn.click()

    # Should end up on a valid page (not blank /files/delete)
    page.wait_for_timeout(500)
    assert "/files/" not in page.url
    assert page.locator("header").is_visible()
