"""Headless tests for normalize-on-export.

Covers the two export flows the option plugs into — "Export Recorded Data"
(folder) and "Export as Single Sound File" (join) — plus the drawer checkbox,
the settings dialog, settings persistence and the progress dialog's cancel
guard. FFmpeg-dependent cases are skipped when no ffmpeg is available.
"""

import hashlib
import json
import math
import os
import struct
import threading
import time
import wave

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from tests.test_normalizer import needs_ffmpeg, wav_info, write_tone
from vat.audio import joiner as joiner_mod
from vat.audio.joiner import JoinWavsWorker
from vat.audio.normalizer import DEFAULT_SETTINGS, Normalizer, normalize_settings
from vat.ui.normalize_dialogs import NormalizeProgressDialog, NormalizeSettingsDialog


TAB_INDEX = {"all": 0, "videos": 1, "images": 2, "review": 3}


# --- helpers ----------------------------------------------------------------------

def _wait(qapp, cond, timeout=180):
    t0 = time.time()
    while not cond():
        qapp.processEvents()
        if time.time() - t0 > timeout:
            raise AssertionError("timed out waiting for the background export")
        time.sleep(0.02)


def _settle(qapp, seconds=0.3):
    t0 = time.time()
    while time.time() - t0 < seconds:
        qapp.processEvents()
        time.sleep(0.01)


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _capture_boxes(monkeypatch):
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


def segment_peak_db(path, start_s, end_s):
    """Peak (dBFS) of one time range of a mono WAV, any PCM width."""
    with wave.open(path, "rb") as wf:
        sw, rate = wf.getsampwidth(), wf.getframerate()
        wf.setpos(int(start_s * rate))
        raw = wf.readframes(int((end_s - start_s) * rate))
    full = (1 << (8 * sw - 1)) - 1
    if sw == 2:
        mx = max(abs(v) for (v,) in struct.iter_unpack("<h", raw))
    elif sw == 3:
        mx = max(abs(int.from_bytes(raw[i:i + 3], "little", signed=True)) for i in range(0, len(raw), 3))
    else:
        mx = max(abs(v) for (v,) in struct.iter_unpack("<i", raw))
    return 20 * math.log10(mx / full) if mx else float("-inf")


@pytest.fixture
def quiet_recordings(app_window, media_folder):
    """Three recordings at different (quiet) levels and bit depths."""
    w = app_window
    write_tone(os.path.join(media_folder, "ant.wav"), amp_db=-20, sampwidth=3)        # video, 24-bit
    write_tone(os.path.join(media_folder, "bird.wav"), amp_db=-26, sampwidth=2)       # video, 16-bit
    write_tone(os.path.join(media_folder, "bird.jpg.wav"), amp_db=-14, sampwidth=3)   # image, 24-bit
    w.fs.set_folder(media_folder)
    return w


# --- drawer option + persistence ----------------------------------------------------

def test_option_is_off_by_default_and_exports_stay_plain_copies(quiet_recordings, media_folder, tmp_path, monkeypatch):
    w = quiet_recordings
    assert w.export_normalize_enabled is False
    assert not w.normalize_export_cb.isChecked()
    export_dir = str(tmp_path / "export")
    os.makedirs(export_dir)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: export_dir))
    boxes = _capture_boxes(monkeypatch)
    w.export_wavs()
    assert boxes and boxes[-1][0] == "information"
    for name in ("ant.wav", "bird.wav", "bird.jpg.wav"):
        assert _sha(os.path.join(export_dir, name)) == _sha(os.path.join(media_folder, name))
    assert os.path.exists(os.path.join(export_dir, "metadata.txt"))


def test_checkbox_drives_the_option_and_is_persisted(app_window):
    w = app_window
    w.normalize_export_cb.setChecked(True)
    assert w.export_normalize_enabled is True
    w.export_normalize_settings = normalize_settings({"normMode": "lufs", "autoTrim": True, "targetBitDepth": 16})
    w.save_settings()
    with open(w.settings_file) as f:
        data = json.load(f)
    assert data["export_normalize"]["enabled"] is True
    assert data["export_normalize"]["settings"]["normMode"] == "lufs"
    assert data["export_normalize"]["settings"]["targetBitDepth"] == 16
    # A fresh window (same isolated HOME) restores both.
    from vat.ui.app import VideoAnnotationApp
    w2 = VideoAnnotationApp()
    try:
        assert w2.export_normalize_enabled is True
        assert w2.normalize_export_cb.isChecked()
        assert w2.export_normalize_settings["normMode"] == "lufs"
        assert w2.export_normalize_settings["autoTrim"] is True
        assert w2.export_normalize_settings["targetBitDepth"] == 16
    finally:
        w2.close()


def test_corrupt_saved_settings_fall_back_to_defaults(app_window):
    w = app_window
    os.makedirs(os.path.dirname(w.settings_file), exist_ok=True)
    with open(w.settings_file, "w") as f:
        json.dump({"export_normalize": {"enabled": "yes", "settings": {"normMode": "weird", "peakTargetDb": "loud"}}}, f)
    from vat.ui.app import VideoAnnotationApp
    w2 = VideoAnnotationApp()
    try:
        assert w2.export_normalize_enabled is True
        assert w2.export_normalize_settings == DEFAULT_SETTINGS
    finally:
        w2.close()


def test_settings_button_saves_what_the_dialog_returns(app_window, monkeypatch):
    w = app_window

    def fake_exec(self):
        self.intent_combo.setCurrentIndex(self.intent_combo.findData("lufs"))
        self.lufs_target.setValue(-18.0)
        self.trim_cb.setChecked(True)
        return QDialog.Accepted

    monkeypatch.setattr(NormalizeSettingsDialog, "exec", fake_exec)
    w.open_normalize_settings()
    assert w.export_normalize_settings["normMode"] == "lufs"
    assert w.export_normalize_settings["lufsTarget"] == -18.0
    assert w.export_normalize_settings["autoTrim"] is True
    with open(w.settings_file) as f:
        assert json.load(f)["export_normalize"]["settings"]["lufsTarget"] == -18.0
    # Cancel keeps the previous settings.
    monkeypatch.setattr(NormalizeSettingsDialog, "exec", lambda self: QDialog.Rejected)
    before = dict(w.export_normalize_settings)
    w.open_normalize_settings()
    assert w.export_normalize_settings == before


def test_language_switch_relabels_the_new_controls(app_window):
    from vat.ui.app import LABELS_ALL
    w = app_window
    w.language = "Bahasa Indonesia"
    w.LABELS = LABELS_ALL["Bahasa Indonesia"]
    w.refresh_ui_texts()
    assert w.normalize_export_cb.text() == LABELS_ALL["Bahasa Indonesia"]["normalize_on_export"]
    assert w.normalize_settings_btn.text() == LABELS_ALL["Bahasa Indonesia"]["normalize_settings_btn"]
    assert w.normalize_export_cb.text() != LABELS_ALL["English"]["normalize_on_export"]


# --- settings dialog ---------------------------------------------------------------

def test_settings_dialog_round_trip_sections_and_reset(qapp):
    dlg = NormalizeSettingsDialog({"normMode": "lufs", "lufsTarget": -18, "autoTrim": True, "trimPadMs": 500, "targetBitDepth": 24})
    s = dlg.settings()
    assert s["normMode"] == "lufs" and s["lufsTarget"] == -18.0 and s["autoTrim"] is True
    assert s["trimPadMs"] == 500 and s["targetBitDepth"] == 24
    # The mode sections live inside the collapsed "Advanced" panel, so test
    # their own hidden state rather than visibility through the panel.
    assert not dlg.lufs_group.isHidden() and dlg.peak_group.isHidden()
    assert dlg.trim_group.isEnabled()
    assert dlg.advanced_box.isHidden()
    dlg.advanced_toggle.setChecked(True)
    assert not dlg.advanced_box.isHidden() and dlg.lufs_group.isVisibleTo(dlg) and not dlg.peak_group.isVisibleTo(dlg)
    dlg.intent_combo.setCurrentIndex(dlg.intent_combo.findData("peak"))
    dlg.peak_target.setValue(-6.0)
    dlg.peak_only_boost.setChecked(False)
    dlg.trim_cb.setChecked(False)
    assert not dlg.peak_group.isHidden() and dlg.lufs_group.isHidden()
    assert not dlg.trim_group.isEnabled()
    s = dlg.settings()
    assert s["normMode"] == "peak" and s["peakTargetDb"] == -6.0 and s["peakOnlyBoost"] is False and s["autoTrim"] is False
    dlg.reset_to_defaults()
    assert dlg.settings() == DEFAULT_SETTINGS


def test_progress_dialog_finish_never_cancels_but_the_cancel_button_does(qapp):
    calls = []
    dlg = NormalizeProgressDialog(None, {}, "normalize_progress_title", on_cancel=lambda: calls.append("cancel"))
    dlg.show_normalize_progress(0, 3, "a.wav")
    assert "1 of 3" in dlg.labelText() and "a.wav" in dlg.labelText() and dlg.maximum() == 3
    dlg.show_phase("write", 3, 3, "out.wav")
    assert dlg.maximum() == 0 and "out.wav" in dlg.labelText()
    dlg.finish()
    dlg.finish()
    assert calls == []
    dlg2 = NormalizeProgressDialog(None, {}, "join_progress_title", on_cancel=lambda: calls.append("cancel"))
    dlg2.canceled.emit()   # what the Cancel button (and the close box) emit
    assert calls == ["cancel"] and dlg2.cancel_requested
    dlg2.canceled.emit()
    dlg2.finish()
    assert calls == ["cancel"], "a second cancel, or finishing after one, must not cancel again"
    dlg3 = NormalizeProgressDialog(None, {}, "join_progress_title", on_cancel=lambda: calls.append("esc"))
    dlg3.reject()          # Escape key
    assert calls == ["cancel", "esc"]
    dlg3.finish()


# --- Export Recorded Data (folder) ----------------------------------------------------

@needs_ffmpeg
def test_export_recorded_data_normalizes_every_wav_and_keeps_originals(quiet_recordings, media_folder, tmp_path, monkeypatch, qapp):
    w = quiet_recordings
    export_dir = str(tmp_path / "export")
    os.makedirs(export_dir)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: export_dir))
    boxes = _capture_boxes(monkeypatch)
    names = ("ant.wav", "bird.wav", "bird.jpg.wav")
    before = {n: _sha(os.path.join(media_folder, n)) for n in names}

    w.normalize_export_cb.setChecked(True)
    w.export_wavs()
    _wait(qapp, lambda: bool(boxes))
    _settle(qapp)

    kind, _title, text = boxes[-1]
    assert kind == "information" and "3" in text and export_dir in text, boxes
    for name in names:
        peak, sw, rate, secs = wav_info(os.path.join(export_dir, name))
        assert abs(peak - (-2.0)) < 0.2, (name, peak)
        assert rate == 48000 and abs(secs - 1.0) < 0.01
    assert wav_info(os.path.join(export_dir, "ant.wav"))[1] == 3       # 24-bit kept
    assert wav_info(os.path.join(export_dir, "bird.wav"))[1] == 2      # 16-bit kept
    assert os.path.exists(os.path.join(export_dir, "metadata.txt"))
    assert {n: _sha(os.path.join(media_folder, n)) for n in names} == before, "originals must never change"
    assert w._export_ctx is None


@needs_ffmpeg
def test_export_uses_the_saved_settings(quiet_recordings, media_folder, tmp_path, monkeypatch, qapp):
    w = quiet_recordings
    export_dir = str(tmp_path / "export")
    os.makedirs(export_dir)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: export_dir))
    boxes = _capture_boxes(monkeypatch)
    w.normalize_export_cb.setChecked(True)
    w.export_normalize_settings = normalize_settings({"peakTargetDb": -6.0, "targetBitDepth": 16})
    w.export_wavs()
    _wait(qapp, lambda: bool(boxes))
    _settle(qapp)
    for name in ("ant.wav", "bird.wav", "bird.jpg.wav"):
        peak, sw, _rate, _secs = wav_info(os.path.join(export_dir, name))
        assert abs(peak - (-6.0)) < 0.2 and sw == 2, (name, peak, sw)


@needs_ffmpeg
def test_export_copies_unnormalizable_files_unchanged_and_warns(quiet_recordings, media_folder, tmp_path, monkeypatch, qapp):
    w = quiet_recordings
    broken = os.path.join(media_folder, "broken.wav")
    with open(broken, "wb") as f:
        f.write(b"RIFF....WAVEjunk")
    export_dir = str(tmp_path / "export")
    os.makedirs(export_dir)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: export_dir))
    boxes = _capture_boxes(monkeypatch)
    w.normalize_export_cb.setChecked(True)
    w.export_wavs()
    _wait(qapp, lambda: bool(boxes))
    _settle(qapp)
    kind, _title, text = boxes[-1]
    assert kind == "warning" and "broken.wav" in text, boxes
    assert _sha(os.path.join(export_dir, "broken.wav")) == _sha(broken)
    assert abs(wav_info(os.path.join(export_dir, "ant.wav"))[0] - (-2.0)) < 0.2
    assert os.path.exists(os.path.join(export_dir, "metadata.txt"))


def test_export_with_normalization_but_no_ffmpeg_says_so_and_writes_nothing(quiet_recordings, tmp_path, monkeypatch):
    import vat.audio.normalizer as N
    w = quiet_recordings
    monkeypatch.setattr(N, "resolve_ff_tools", lambda: {"ffmpeg": None, "ffprobe": None})
    export_dir = str(tmp_path / "export")
    os.makedirs(export_dir)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: export_dir))
    boxes = _capture_boxes(monkeypatch)
    w.normalize_export_cb.setChecked(True)
    w.export_wavs()
    assert boxes and boxes[-1][0] == "critical" and "FFmpeg" in boxes[-1][2]
    assert os.listdir(export_dir) == []


@needs_ffmpeg
def test_export_cancel_stops_early_and_reports_what_was_written(quiet_recordings, media_folder, tmp_path, monkeypatch, qapp):
    w = quiet_recordings
    # Long files so the cancel lands mid-batch.
    for name in ("ant.wav", "bird.wav", "bird.jpg.wav"):
        write_tone(os.path.join(media_folder, name), seconds=60.0, amp_db=-20, sampwidth=2)
    export_dir = str(tmp_path / "export")
    os.makedirs(export_dir)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: export_dir))
    boxes = _capture_boxes(monkeypatch)
    w.normalize_export_cb.setChecked(True)
    w.export_normalize_settings = normalize_settings({"normMode": "lufs"})
    w.export_wavs()
    _wait(qapp, lambda: w._export_ctx is not None)
    dlg = w._export_ctx[2]
    QTimer.singleShot(200, dlg.canceled.emit)     # the Cancel button, on the GUI thread
    _wait(qapp, lambda: bool(boxes))
    _settle(qapp)
    kind, title, text = boxes[-1]
    assert kind == "information" and export_dir in text and title == w.LABELS["export_cancelled_title"], boxes
    assert not os.path.exists(os.path.join(export_dir, "metadata.txt"))
    assert len([f for f in os.listdir(export_dir) if f.endswith(".wav")]) < 3


# --- Export as Single Sound File (join) -----------------------------------------------

@needs_ffmpeg
def test_single_file_export_normalizes_each_recording_before_joining(tmp_path, monkeypatch):
    a = write_tone(str(tmp_path / "a.wav"), seconds=1.0, amp_db=-20, sampwidth=3)
    b = write_tone(str(tmp_path / "b.wav"), seconds=0.5, amp_db=-30, sampwidth=2)
    made = []
    real_mkdtemp = joiner_mod.tempfile.mkdtemp
    monkeypatch.setattr(joiner_mod.tempfile, "mkdtemp", lambda *x, **k: made.append(real_mkdtemp(*x, **k)) or made[-1])

    plain = JoinWavsWorker(output_file=str(tmp_path / "plain.wav"), file_paths=[a, b])
    plain.run()
    phases = []
    norm = JoinWavsWorker(output_file=str(tmp_path / "norm.wav"), file_paths=[b, a], normalizer=Normalizer({}))
    norm.progress.connect(lambda ph, i, n, name: phases.append((ph, i, n, name)))
    outcome = []
    norm.success.connect(lambda p: outcome.append("success"))
    norm.error.connect(lambda m: outcome.append(("error", m)))
    norm.run()
    assert outcome == ["success"]

    # Same structure (a, click, b) and length; only the levels differ.
    p_plain = wav_info(str(tmp_path / "plain.wav"))
    p_norm = wav_info(str(tmp_path / "norm.wav"))
    assert p_plain[1] == 4 and p_norm[1] == 4 and p_plain[2] == 48000 == p_norm[2]
    assert abs(p_plain[3] - p_norm[3]) < 0.01
    assert abs(p_norm[3] - (1.0 + 1.005 + 0.5)) < 0.02
    assert abs(segment_peak_db(str(tmp_path / "plain.wav"), 0.0, 1.0) - (-20.0)) < 0.2
    assert abs(segment_peak_db(str(tmp_path / "norm.wav"), 0.0, 1.0) - (-2.0)) < 0.2
    assert abs(segment_peak_db(str(tmp_path / "plain.wav"), 2.05, 2.5) - (-30.0)) < 0.2
    assert abs(segment_peak_db(str(tmp_path / "norm.wav"), 2.05, 2.5) - (-2.0)) < 0.2
    # Normalized in join order (sorted by name), then joined, then written.
    assert phases == [
        ("normalize", 0, 2, "a.wav"), ("normalize", 1, 2, "b.wav"),
        ("join", 0, 2, "0000_a.wav"), ("join", 1, 2, "0001_b.wav"),
        ("write", 2, 2, "norm.wav"),
    ]
    # The temporary folder of normalized copies is gone; originals untouched.
    assert made and not os.path.exists(made[0])
    assert abs(wav_info(a)[0] - (-20.0)) < 0.2 and abs(wav_info(b)[0] - (-30.0)) < 0.2


@needs_ffmpeg
def test_single_file_export_reports_the_file_that_failed_and_writes_nothing(tmp_path):
    a = write_tone(str(tmp_path / "a.wav"), amp_db=-20)
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"RIFF....WAVEjunk")
    out = str(tmp_path / "out.wav")
    worker = JoinWavsWorker(output_file=out, file_paths=[a, str(bad)], normalizer=Normalizer({}))
    errors = []
    worker.error.connect(errors.append)
    worker.run()
    assert errors and "bad.wav" in errors[0], errors
    assert not os.path.exists(out)


@needs_ffmpeg
def test_single_file_export_cancel_writes_no_file(tmp_path):
    srcs = [write_tone(str(tmp_path / f"{i}.wav"), seconds=60.0, amp_db=-20, sampwidth=2) for i in range(3)]
    out = str(tmp_path / "out.wav")
    worker = JoinWavsWorker(output_file=out, file_paths=srcs, normalizer=Normalizer({"normMode": "lufs"}))
    events = []
    worker.canceled.connect(lambda: events.append("canceled"))
    worker.success.connect(lambda p: events.append("success"))
    worker.error.connect(lambda m: events.append(("error", m)))
    worker.progress.connect(lambda ph, i, n, name: threading.Timer(0.2, worker.cancel).start() if (ph, i) == ("normalize", 0) else None)
    worker.run()
    assert events == ["canceled"]
    assert not os.path.exists(out)


@needs_ffmpeg
def test_join_from_the_app_with_normalization_on(quiet_recordings, tmp_path, monkeypatch, qapp):
    w = quiet_recordings
    out = str(tmp_path / "joined.wav")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (out, "WAV files (*.wav)")))
    boxes = _capture_boxes(monkeypatch)
    w.normalize_export_cb.setChecked(True)
    w.right_panel.setCurrentIndex(TAB_INDEX["videos"])     # scope: ant.wav + bird.wav
    assert w._active_tab_key() == "videos"
    w.join_all_wavs()
    _wait(qapp, lambda: bool(boxes))
    _settle(qapp)
    kind, _title, text = boxes[-1]
    assert kind == "information" and out in text, boxes
    peak, sw, rate, secs = wav_info(out)
    assert sw == 4 and rate == 48000
    assert abs(secs - (1.0 + 1.005 + 1.0)) < 0.02
    assert abs(segment_peak_db(out, 0.0, 1.0) - (-2.0)) < 0.2       # ant.wav was -20 dB
    assert abs(segment_peak_db(out, 2.05, 3.0) - (-2.0)) < 0.2      # bird.wav was -26 dB
    assert w._join_progress_dlg is None


def test_join_from_the_app_without_normalization_is_unchanged(quiet_recordings, tmp_path, monkeypatch, qapp):
    w = quiet_recordings
    out = str(tmp_path / "joined.wav")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (out, "WAV files (*.wav)")))
    boxes = _capture_boxes(monkeypatch)
    w.right_panel.setCurrentIndex(TAB_INDEX["videos"])
    w.join_all_wavs()
    _wait(qapp, lambda: bool(boxes))
    _settle(qapp)
    assert boxes[-1][0] == "information" and out in boxes[-1][2], boxes
    assert abs(segment_peak_db(out, 0.0, 1.0) - (-20.0)) < 0.2
