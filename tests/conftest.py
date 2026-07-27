"""Shared fixtures for the headless test suite.

These tests run the real Qt widgets under the offscreen platform plugin, so
they exercise actual app behavior rather than mocks. Modal dialogs are stubbed
out because an unattended run must never block on a message box.
"""

import os
import sys
import wave
import struct

# Must be set before QApplication is created.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _no_modal_dialogs(monkeypatch):
    """Stub every modal dialog so tests can never hang on one."""
    from PySide6.QtWidgets import QMessageBox, QFileDialog
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: ""))


def make_image(path, size=(64, 48), color=(200, 30, 30)):
    from PIL import Image
    Image.new("RGB", size, color).save(path)
    return path


def make_video(path, frames=5, size=(64, 48), fps=10.0):
    import numpy as np
    import cv2
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(path, fourcc, fps, size)
    for _ in range(frames):
        vw.write(np.zeros((size[1], size[0], 3), np.uint8))
    vw.release()
    return path


def make_wav(path, seconds=0.05, rate=48000, sampwidth=3, channels=1):
    """Write a small silent WAV (defaults match the archival capture format)."""
    n = int(rate * seconds)
    frame = b"\x00" * sampwidth * channels
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        wf.writeframes(frame * n)
    return path


@pytest.fixture
def media_folder(tmp_path):
    """A folder with a same-stem video+image pair plus extra media of each type."""
    d = str(tmp_path)
    make_video(os.path.join(d, "bird.mp4"))
    make_image(os.path.join(d, "bird.jpg"))       # same stem as bird.mp4 on purpose
    make_video(os.path.join(d, "ant.mp4"))
    make_image(os.path.join(d, "zebra.png"))
    return d


@pytest.fixture
def fs(media_folder):
    from vat.utils.fs_access import FolderAccessManager
    m = FolderAccessManager()
    m.set_folder(media_folder)
    return m


@pytest.fixture
def app_window(qapp, media_folder, tmp_path, monkeypatch):
    """A real VideoAnnotationApp pointed at media_folder, with isolated settings."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    os.makedirs(str(tmp_path / "home"), exist_ok=True)
    from vat.ui.app import VideoAnnotationApp
    w = VideoAnnotationApp()
    w.fs.set_folder(media_folder)
    w.load_video_files()
    try:
        w._populate_images_list()
    except Exception:
        pass
    yield w
    try:
        w.close()
    except Exception:
        pass
