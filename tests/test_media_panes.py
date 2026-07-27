"""Characterization tests for the video / image / All media panes.

The Videos and Images tabs implement the same media lifecycle twice, and the
All tab is a third variant. These tests pin down the observable behavior of
each — especially where they legitimately differ — so the planned MediaPane
extraction can be shown to preserve every one of those behaviors.
"""

import os
import pytest

from tests.conftest import make_wav


# --------------------------------------------------------------------------
# Tab wiring
# --------------------------------------------------------------------------

def test_tab_order_and_identification(app_window):
    w = app_window
    titles = [w.right_panel.tabText(i) for i in range(w.right_panel.count())]
    assert titles == ["All", "Videos", "Images", "Review"]


def test_active_tab_key_tracks_widget_not_index(app_window):
    w = app_window
    keys = []
    for i in range(w.right_panel.count()):
        w.right_panel.setCurrentIndex(i)
        keys.append(w._active_tab_key())
    assert keys == ["all", "videos", "images", "review"]


def test_drawer_list_enabled_only_for_all_and_videos(app_window):
    w = app_window
    seen = {}
    for i in range(w.right_panel.count()):
        w.right_panel.setCurrentIndex(i)
        seen[w._active_tab_key()] = w.video_listbox.isEnabled()
    assert seen["all"] is True
    assert seen["videos"] is True
    assert seen["images"] is False
    assert seen["review"] is False


# --------------------------------------------------------------------------
# Shared drawer list: contents differ by active tab
# --------------------------------------------------------------------------

def _drawer_names(w):
    return [w.video_listbox.item(i).text() for i in range(w.video_listbox.count())]


def test_drawer_lists_videos_only_on_videos_tab(app_window):
    w = app_window
    w.right_panel.setCurrentIndex(1)  # Videos
    assert set(_drawer_names(w)) == {"ant.mp4", "bird.mp4"}


def test_drawer_lists_videos_and_images_on_all_tab(app_window):
    w = app_window
    w.right_panel.setCurrentIndex(0)  # All
    assert _drawer_names(w) == ["ant.mp4", "bird.jpg", "bird.mp4", "zebra.png"]


def test_all_tab_drawer_items_carry_full_paths(app_window):
    from PySide6.QtCore import Qt
    w = app_window
    w.right_panel.setCurrentIndex(0)
    for i in range(w.video_listbox.count()):
        path = w.video_listbox.item(i).data(Qt.UserRole)
        assert path and os.path.isabs(path) and os.path.exists(path)


# --------------------------------------------------------------------------
# Videos tab control state (update_media_controls)
# --------------------------------------------------------------------------

def test_videos_controls_without_recording(app_window):
    w = app_window
    w.right_panel.setCurrentIndex(1)
    w.current_video = "ant.mp4"
    w.update_media_controls()
    assert w.play_video_button.isEnabled() is True
    assert w.record_button.isEnabled() is True
    assert w.play_audio_button.isEnabled() is False
    assert w.delete_recording_button.isEnabled() is False
    assert w.edit_recording_button.isEnabled() is False


def test_videos_controls_with_recording(app_window, media_folder):
    w = app_window
    w.right_panel.setCurrentIndex(1)
    make_wav(os.path.join(media_folder, "ant.wav"))
    w.current_video = "ant.mp4"
    w.update_media_controls()
    assert w.play_audio_button.isEnabled() is True
    assert w.delete_recording_button.isEnabled() is True
    assert w.edit_recording_button.isEnabled() is True


def test_videos_controls_with_no_selection(app_window):
    w = app_window
    w.right_panel.setCurrentIndex(1)
    w.current_video = None
    w.update_media_controls()
    assert w.play_video_button.isEnabled() is False
    assert w.record_button.isEnabled() is False
    assert w.play_audio_button.isEnabled() is False


def test_convert_to_mp4_disabled_for_mp4_source(app_window):
    """Functional detail to preserve: Convert is offered only for non-MP4."""
    w = app_window
    w.right_panel.setCurrentIndex(1)
    w.current_video = "ant.mp4"
    w.update_media_controls()
    assert w.convert_mp4_button.isEnabled() is False


# --------------------------------------------------------------------------
# All tab control state (per media type)
# --------------------------------------------------------------------------

def _select_in_all(w, basename):
    w.right_panel.setCurrentIndex(0)
    for i, p in enumerate(w.all_tab.queue):
        if os.path.basename(p) == basename:
            w.all_tab.select_index(i)
            return p
    raise AssertionError(f"{basename} not in All queue")


def test_all_tab_video_enables_video_controls(app_window):
    w = app_window
    _select_in_all(w, "ant.mp4")
    assert w.all_tab.play_video_button.isEnabled() is True
    assert w.all_tab.stop_video_button.isEnabled() is True
    assert w.all_tab.record_button.isEnabled() is True


def test_all_tab_image_disables_video_controls(app_window):
    """Stills must not offer video playback, but must still be recordable."""
    w = app_window
    _select_in_all(w, "zebra.png")
    assert w.all_tab.play_video_button.isEnabled() is False
    assert w.all_tab.stop_video_button.isEnabled() is False
    assert w.all_tab.record_button.isEnabled() is True


def test_all_tab_recording_state_per_item(app_window, media_folder):
    w = app_window
    make_wav(os.path.join(media_folder, "bird.jpg.wav"))   # image recording only
    w.all_tab.refresh_queue()
    _select_in_all(w, "bird.jpg")
    assert w.all_tab.play_audio_button.isEnabled() is True
    assert w.all_tab.delete_recording_button.isEnabled() is True
    # The same-stem VIDEO must not be considered recorded.
    _select_in_all(w, "bird.mp4")
    assert w.all_tab.play_audio_button.isEnabled() is False
    assert w.all_tab.delete_recording_button.isEnabled() is False


def test_all_tab_prev_next_walks_mixed_queue(app_window):
    w = app_window
    w.right_panel.setCurrentIndex(0)
    w.all_tab.select_index(0)
    order = [os.path.basename(w.all_tab.current)]
    for _ in range(3):
        w.all_tab.go_next()
        order.append(os.path.basename(w.all_tab.current))
    assert order == ["ant.mp4", "bird.jpg", "bird.mp4", "zebra.png"]
    for _ in range(3):
        w.all_tab.go_prev()
    assert os.path.basename(w.all_tab.current) == "ant.mp4"


def test_all_tab_selection_syncs_drawer_row(app_window):
    w = app_window
    w.right_panel.setCurrentIndex(0)
    w.all_tab.select_index(2)
    assert w.video_listbox.currentRow() == 2


def test_drawer_click_drives_all_tab(app_window):
    w = app_window
    w.right_panel.setCurrentIndex(0)
    w.video_listbox.setCurrentRow(3)   # zebra.png
    assert os.path.basename(w.all_tab.current) == "zebra.png"


def test_all_tab_delete_recording_removes_only_that_file(app_window, media_folder):
    w = app_window
    vid_wav = make_wav(os.path.join(media_folder, "bird.wav"))
    img_wav = make_wav(os.path.join(media_folder, "bird.jpg.wav"))
    w.all_tab.refresh_queue()
    _select_in_all(w, "bird.jpg")
    w.all_tab.delete_recording()
    assert not os.path.exists(img_wav)
    assert os.path.exists(vid_wav), "deleting the image's recording removed the video's"


# --------------------------------------------------------------------------
# Preview behavior
# --------------------------------------------------------------------------

def test_all_tab_shows_pixmap_for_both_media_types(app_window):
    w = app_window
    for name in ("ant.mp4", "zebra.png"):
        _select_in_all(w, name)
        pm = w.all_tab.preview_label.pixmap()
        assert pm is not None and not pm.isNull(), f"no preview rendered for {name}"
