"""Pure, dependency-free helpers for media-type detection and WAV recording
naming. Kept free of Qt/PySide imports so it can be unit-tested headlessly and
reused anywhere (UI, workers, and eventually the pywebview/PWA backend).

NOTE: The extension tuples below must stay in sync with
FolderAccessManager.VIDEO_EXTS / IMAGE_EXTS (vat/utils/fs_access.py). Unifying
them on this module is tracked in the Refactoring/Modularization roadmap (TODO).
"""

import os
from typing import Optional

# Keep in sync with FolderAccessManager (see note above).
VIDEO_EXTS = (".mpg", ".mpeg", ".mp4", ".avi", ".mkv", ".mov")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".heic", ".heif", ".webp")


def media_type(name: str) -> Optional[str]:
    """Return 'video', 'image', or None based on the file's extension."""
    low = os.path.basename(name).lower()
    if low.endswith(VIDEO_EXTS):
        return "video"
    if low.endswith(IMAGE_EXTS):
        return "image"
    return None


def recording_name_for(name: str) -> str:
    """Canonical WAV recording basename for a media file.

    Deliberately reproduces the app's existing per-type convention so the
    short-term "All" tab matches the Videos/Images tabs exactly (a uniform
    "<fullname>.wav" redesign is tracked in the TODO roadmap):

      - video: strip the extension  -> "<stem>.wav"      (clip01.mp4  -> clip01.wav)
      - image: keep the full name   -> "<fullname>.wav"  (photo03.jpg -> photo03.jpg.wav)

    Because videos strip and images keep the extension, a same-stem video+image
    pair map to DISTINCT WAVs (foo.wav vs foo.jpg.wav) with no collision — which
    is what makes canonical-only lookups safe for mixed ("All") queues.

    A file with an unrecognized extension is treated as a video (stem + .wav),
    matching the legacy "a WAV with no embedded media extension belongs to a
    video" convention used when loading pre-refactor work.
    """
    base = os.path.basename(name)
    if media_type(base) == "image":
        return base + ".wav"
    stem = os.path.splitext(base)[0]
    return stem + ".wav"
