"""Regression tests for tab-scoped export/join/Ocenaudio actions.

Background: `join_all_wavs` selected its recording set with HARDCODED tab
indices. Inserting the All tab at index 0 shifted every index, so the join
scope was wrong on all four tabs (All joined only videos; Videos joined the
IMAGE recordings; Images used the Review scope). Scope is now derived from
`_active_tab_key()` (widget identity), and these tests pin that down so
reordering tabs can never silently change it again.
"""

import os
import pytest

from tests.conftest import make_wav, make_image


TAB_INDEX = {"all": 0, "videos": 1, "images": 2, "review": 3}


@pytest.fixture
def recorded(app_window, media_folder):
    """Give every media item a recording so each scope is non-empty."""
    w = app_window
    make_wav(os.path.join(media_folder, "ant.wav"))        # video
    make_wav(os.path.join(media_folder, "bird.wav"))       # video
    make_wav(os.path.join(media_folder, "bird.jpg.wav"))   # image
    make_wav(os.path.join(media_folder, "zebra.png.wav"))  # image
    w.fs.set_folder(media_folder)
    w.all_tab.refresh_queue()
    return w


def _scope_used(w, monkeypatch, method):
    """Call `method` on the window and report which fs source it consulted.

    Everything downstream of the scope decision is stubbed: we are testing which
    set of recordings the action selects, not ffmpeg or the Ocenaudio launcher
    (the real launcher probes the filesystem and prompts, which blocks headless).
    """
    calls = []
    monkeypatch.setattr(w, "_launch_ocenaudio", lambda *a, **k: None, raising=False)

    def rec(name, result):
        def _f(*a, **k):
            calls.append(name)
            return list(result)
        return _f

    monkeypatch.setattr(w.fs, "video_recordings_in", rec("video", ["/v.wav"]))
    monkeypatch.setattr(w.fs, "image_recordings_in", rec("image", ["/i.wav"]))
    monkeypatch.setattr(w.fs, "all_recordings_in", rec("all", ["/a.wav"]))
    monkeypatch.setattr(w.fs, "recordings_in", rec("folder", ["/f.wav"]))
    try:
        method()
    except Exception:
        pass  # bails later (no ffmpeg/Ocenaudio here); the scope choice already happened
    return calls


@pytest.mark.parametrize("tab,expected", [
    ("all", "all"),
    ("videos", "video"),
    ("images", "image"),
])
def test_join_uses_the_scope_of_the_active_tab(recorded, monkeypatch, tab, expected):
    w = recorded
    w.right_panel.setCurrentIndex(TAB_INDEX[tab])
    assert w._active_tab_key() == tab
    calls = _scope_used(w, monkeypatch, w.join_all_wavs)
    assert calls and calls[0] == expected, \
        f"{tab} tab joined the '{calls[0] if calls else None}' scope, expected '{expected}'"


@pytest.mark.parametrize("tab,expected", [
    ("all", "all"),
    ("videos", "video"),
    ("images", "image"),
])
def test_ocenaudio_uses_the_scope_of_the_active_tab(recorded, monkeypatch, tab, expected):
    w = recorded
    w.right_panel.setCurrentIndex(TAB_INDEX[tab])
    calls = _scope_used(w, monkeypatch, w.open_in_ocenaudio)
    assert calls and calls[0] == expected


def test_all_scope_contains_both_video_and_image_recordings(recorded, media_folder):
    names = {os.path.basename(p) for p in recorded.fs.all_recordings_in()}
    assert names == {"ant.wav", "bird.wav", "bird.jpg.wav", "zebra.png.wav"}, \
        "the All scope must cover videos AND images"


def test_all_scope_includes_recordings_for_images_in_subfolder(recorded, media_folder):
    """images/ subfolder recordings are missed by the top-level-only recordings_in()."""
    sub = os.path.join(media_folder, "images")
    os.makedirs(sub, exist_ok=True)
    make_image(os.path.join(sub, "nested.png"))
    make_wav(os.path.join(sub, "nested.png.wav"))
    names = {os.path.basename(p) for p in recorded.fs.all_recordings_in()}
    assert "nested.png.wav" in names
    # and the flat helper genuinely does not find it (documents why all_recordings_in exists)
    flat = {os.path.basename(p) for p in recorded.fs.recordings_in()}
    assert "nested.png.wav" not in flat


def test_export_and_clear_are_folder_wide_not_tab_scoped(recorded):
    """Export/Clear recorded data are deliberately folder-wide on every tab."""
    import inspect
    for fn in (recorded.export_wavs, recorded.clear_wavs):
        src = inspect.getsource(fn)
        assert "recordings_in()" in src
        assert "_active_tab_key" not in src, f"{fn.__name__} unexpectedly became tab-scoped"
