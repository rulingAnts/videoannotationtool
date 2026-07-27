"""Characterization tests for recording naming and media listing.

These lock in the CURRENT behavior of the video and image paths — including
the places where they deliberately differ — so the MediaPane refactor can be
proven not to change any of it. Where a test documents a known hazard rather
than desired behavior, it says so explicitly.
"""

import os
import pytest

from vat.utils.media_naming import media_type, recording_name_for
from tests.conftest import make_wav


# --------------------------------------------------------------------------
# Pure naming helpers
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("clip.mp4", "video"), ("clip.MP4", "video"), ("a.mpg", "video"),
    ("a.mov", "video"), ("a.avi", "video"), ("a.mkv", "video"),
    ("p.jpg", "image"), ("p.JPEG", "image"), ("p.png", "image"),
    ("p.tif", "image"), ("p.heic", "image"), ("p.webp", "image"),
    ("x.wav", None), ("README", None),
])
def test_media_type(name, expected):
    assert media_type(name) == expected


def test_recording_name_video_strips_extension():
    assert recording_name_for("clip01.mp4") == "clip01.wav"
    assert recording_name_for("clip01.mpg") == "clip01.wav"


def test_recording_name_image_keeps_extension():
    assert recording_name_for("photo.jpg") == "photo.jpg.wav"
    assert recording_name_for("photo.png") == "photo.png.wav"


def test_recording_name_unknown_extension_treated_as_video():
    """Legacy convention: a WAV with no embedded media extension is a video's."""
    assert recording_name_for("mystery.dat") == "mystery.wav"


def test_same_stem_video_and_image_never_collide():
    assert recording_name_for("bird.mp4") != recording_name_for("bird.jpg")


# --------------------------------------------------------------------------
# FolderAccessManager: the video/image asymmetries the refactor must keep
# --------------------------------------------------------------------------

def test_wav_path_for_video_strips_extension(fs, media_folder):
    assert fs.wav_path_for("bird.mp4") == os.path.join(media_folder, "bird.wav")


def test_wav_path_for_image_keeps_full_name(fs, media_folder):
    got = fs.wav_path_for_image(os.path.join(media_folder, "bird.jpg"))
    assert got == os.path.join(media_folder, "bird.jpg.wav")


def test_recording_path_for_unifies_both_types(fs, media_folder):
    assert fs.recording_path_for(os.path.join(media_folder, "bird.mp4")) == \
        os.path.join(media_folder, "bird.wav")
    assert fs.recording_path_for(os.path.join(media_folder, "bird.jpg")) == \
        os.path.join(media_folder, "bird.jpg.wav")


def test_has_recording_is_canonical_and_same_stem_safe(fs, media_folder):
    """A video's recording must not make its same-stem image look recorded."""
    make_wav(os.path.join(media_folder, "bird.wav"))
    assert fs.has_recording(os.path.join(media_folder, "bird.mp4")) is True
    assert fs.has_recording(os.path.join(media_folder, "bird.jpg")) is False


def test_find_existing_image_audio_stem_fallback_is_a_known_hazard(fs, media_folder):
    """DOCUMENTS A HAZARD, not desired behavior.

    find_existing_image_audio() falls back to '<stem>.wav', so for bird.jpg it
    returns bird.wav — which actually belongs to the video bird.mp4. The All tab
    deliberately avoids this helper. If the refactor tightens this, update this
    test; it exists so the change is a conscious one rather than a silent one.
    """
    make_wav(os.path.join(media_folder, "bird.wav"))  # the VIDEO's recording
    found = fs.find_existing_image_audio(os.path.join(media_folder, "bird.jpg"))
    assert found == os.path.join(media_folder, "bird.wav")


def test_list_videos_and_images_partition_by_extension(fs):
    vids = {os.path.basename(p) for p in fs.list_videos()}
    imgs = {os.path.basename(p) for p in fs.list_images()}
    assert vids == {"bird.mp4", "ant.mp4"}
    assert imgs == {"bird.jpg", "zebra.png"}
    assert vids.isdisjoint(imgs)


def test_list_images_also_scans_images_subfolder(fs, media_folder):
    """Asymmetry to preserve: images are also picked up from images/ ; videos are not."""
    from tests.conftest import make_image, make_video
    sub = os.path.join(media_folder, "images")
    os.makedirs(sub, exist_ok=True)
    make_image(os.path.join(sub, "nested.png"))
    make_video(os.path.join(sub, "nested.mp4"))
    imgs = {os.path.basename(p) for p in fs.list_images()}
    vids = {os.path.basename(p) for p in fs.list_videos()}
    assert "nested.png" in imgs
    assert "nested.mp4" not in vids


def test_list_all_media_is_merged_and_basename_sorted(fs):
    names = [os.path.basename(p) for p in fs.list_all_media()]
    assert names == ["ant.mp4", "bird.jpg", "bird.mp4", "zebra.png"]


def test_recordings_in_variants(fs, media_folder):
    make_wav(os.path.join(media_folder, "bird.wav"))        # video recording
    make_wav(os.path.join(media_folder, "bird.jpg.wav"))    # image recording
    vid = {os.path.basename(p) for p in fs.video_recordings_in()}
    img = {os.path.basename(p) for p in fs.image_recordings_in()}
    assert vid == {"bird.wav"}
    assert img == {"bird.jpg.wav"}
