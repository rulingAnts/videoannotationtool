"""A stimulus set is one flat folder: the app warns when the opened folder has subfolders."""
import os
import time

import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox

from conftest import make_image, make_video


def _capture(monkeypatch):
    """Record (kind, title, text) of every message box instead of showing it."""
    calls = []

    def rec(kind):
        def _f(parent, title="", text="", *a, **k):
            calls.append((kind, str(title), str(text)))
            return QMessageBox.Ok
        return staticmethod(_f)

    for kind in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, kind, rec(kind))
    return calls


def _flush(qapp, seconds=0.2):
    """Let the deferred startup checks (QTimer.singleShot(0, ...)) fire."""
    t0 = time.time()
    while time.time() - t0 < seconds:
        qapp.processEvents()
        time.sleep(0.01)


def _warnings(boxes):
    return [b for b in boxes if b[0] == "warning"]


@pytest.fixture
def flat_set(tmp_path):
    """A small flat stimulus folder (one video, one image), nothing else in it."""
    d = str(tmp_path / "set")
    os.makedirs(d)
    make_video(os.path.join(d, "clip01.mp4"))
    make_image(os.path.join(d, "photo02.jpg"))
    return d


def test_list_subfolders_skips_hidden_and_system_folders(fs, flat_set):
    assert fs.list_subfolders(flat_set) == []
    for name in ("images", "Extra", ".git", "$RECYCLE.BIN", "System Volume Information"):
        os.makedirs(os.path.join(flat_set, name))
    open(os.path.join(flat_set, "notes.txt"), "w").close()           # files never count
    assert fs.list_subfolders(flat_set) == ["Extra", "images"]        # sorted, case-insensitive
    assert fs.list_subfolders(os.path.join(flat_set, "images")) == []
    assert fs.list_subfolders(os.path.join(flat_set, "missing")) == []
    fs.set_folder(flat_set)
    assert fs.list_subfolders() == ["Extra", "images"]                # defaults to the current folder


def test_select_folder_warns_about_subfolders_but_still_opens(app_window, flat_set, qapp, monkeypatch):
    w = app_window
    _flush(qapp)
    boxes = _capture(monkeypatch)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: flat_set))

    w.select_folder()
    assert _warnings(boxes) == []                                      # flat folder: silent
    assert w.fs.current_folder == flat_set

    os.makedirs(os.path.join(flat_set, "images"))
    os.makedirs(os.path.join(flat_set, "old session"))
    w.select_folder()
    warnings = _warnings(boxes)
    assert len(warnings) == 1
    _, title, text = warnings[0]
    assert title == w.LABELS["subfolders_warning_title"]
    assert text.startswith(w.LABELS["subfolders_warning_body"])
    assert "images" in text and "old session" in text
    assert w.fs.current_folder == flat_set                             # the folder still opens


def test_startup_checks_warn_for_the_restored_folder(app_window, flat_set, qapp, monkeypatch):
    w = app_window
    _flush(qapp)
    boxes = _capture(monkeypatch)
    w.fs.set_folder(flat_set)
    w._startup_checks()
    assert _warnings(boxes) == []

    os.makedirs(os.path.join(flat_set, "images"))
    w._startup_checks()
    assert [b[1] for b in _warnings(boxes)] == [w.LABELS["subfolders_warning_title"]]


def test_long_listings_are_truncated(app_window, flat_set, qapp, monkeypatch):
    w = app_window
    _flush(qapp)
    boxes = _capture(monkeypatch)
    for i in range(15):
        os.makedirs(os.path.join(flat_set, f"sub{i:02d}"))
    assert w._warn_if_subfolders(flat_set) is True
    text = _warnings(boxes)[-1][2]
    assert "sub11" in text and "sub12" not in text and "(+3)" in text
    assert w._warn_if_subfolders(os.path.join(flat_set, "sub00")) is False


def test_subfolder_labels_exist_in_every_language():
    from vat.i18n.builtin_labels import LABELS_ALL
    for lang, labels in LABELS_ALL.items():
        assert labels["subfolders_warning_title"].strip(), lang
        assert labels["subfolders_warning_body"].strip(), lang
