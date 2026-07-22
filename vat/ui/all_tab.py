"""Self-contained "All" tab: a single queue of videos + still images, previewed
one at a time in the same container as the Videos tab, with per-item record.

Design (short-term, low-risk): this is an ADDITIVE component that owns its own
widgets, preview, and playback/recording workers so it does not touch or
destabilize the existing Videos/Images tabs. The duplication it introduces is
intentional and temporary — the Refactoring/Modularization roadmap (TODO) will
later collapse Videos/Images/All into one shared MediaPane. It uses the
canonical, same-stem-safe recording lookups on FolderAccessManager
(recording_path_for / has_recording) so a same-stem video+image pair never map
to the same WAV.

Wiring: constructed with (fs, labels, host) where `host` is the MainWindow,
used only for shared services (_launch_ocenaudio, status bar). Not yet added to
the tab widget — see app.py integration step.

RESUME STATUS (for interrupted sessions):
  [x] UI skeleton (queue list + preview + controls)
  [x] queue load / selection / prev-next navigation
  [x] preview: video first-frame + image static
  [x] video playback (cv2 + QTimer), disabled for stills
  [x] audio playback (AudioPlaybackWorker on a fresh QThread)
  [x] record / stop (AudioRecordingWorker), canonical WAV naming
  [x] delete recording, edit-in-Ocenaudio (via host)
  [ ] NOT YET: wired into app.py right_panel + tab-index fixups
  [ ] NOT YET: GUI click-test (PySide6/cv2 unavailable headless — syntax-checked only)
"""

from __future__ import annotations

import os
import math
import logging
from typing import List, Optional

from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton,
    QListWidget, QListWidgetItem, QMessageBox, QStyle, QSizePolicy,
)

try:
    import cv2  # type: ignore
    CV2_AVAILABLE = True
except Exception:  # pragma: no cover - cv2 optional at import time
    cv2 = None  # type: ignore
    CV2_AVAILABLE = False

from vat.audio import PYAUDIO_AVAILABLE
from vat.audio.recording import AudioRecordingWorker
from vat.audio.playback import AudioPlaybackWorker

_NORMAL_BORDER = "background-color: black; color: white; border: 1px solid #333;"
_RECORDED_BORDER = "background-color: black; color: white; border: 3px solid #2ecc71;"


class AllMediaTab(QWidget):
    """One-at-a-time preview/record over a merged video+image queue."""

    def __init__(self, fs, labels: Optional[dict] = None, host=None, parent=None):
        super().__init__(parent)
        self.fs = fs
        self.labels = labels or {}
        self.host = host

        # Queue state
        self.queue: List[str] = []
        self.index: int = -1
        self.current: Optional[str] = None

        # Video playback state
        self.cap = None
        self.playing_video = False
        self.video_timer = QTimer(self)
        self.video_timer.timeout.connect(self._update_video_frame)

        # Audio playback state
        self.audio_thread: Optional[QThread] = None
        self.audio_worker: Optional[AudioPlaybackWorker] = None
        self.is_playing_audio = False

        # Recording state
        self.recording_thread: Optional[QThread] = None
        self.recording_worker: Optional[AudioRecordingWorker] = None
        self.is_recording = False

        self._build_ui()
        self.refresh_queue()

    # ---- labels helper -------------------------------------------------
    def _L(self, key: str, default: str) -> str:
        try:
            return self.labels.get(key, default)
        except Exception:
            return default

    # ---- UI construction ----------------------------------------------
    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)

        # Left: the merged queue list
        self.list_widget = QListWidget()
        self.list_widget.setMaximumWidth(240)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.currentRowChanged.connect(self.select_index)
        outer.addWidget(self.list_widget)

        # Right: preview + controls
        right = QVBoxLayout()
        self.preview_label = QLabel(self._L("video_listbox_no_video", "No media selected"))
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(480, 360)
        try:
            self.preview_label.setScaledContents(False)
            self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
        self.preview_label.setStyleSheet(_NORMAL_BORDER)
        right.addWidget(self.preview_label)

        # Navigation + video controls
        nav = QHBoxLayout()
        self.prev_button = QToolButton()
        try:
            self.prev_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        except Exception:
            self.prev_button.setText("◀")
        self.prev_button.setToolTip(self._L("prev_video_tip", "Previous"))
        self.prev_button.clicked.connect(self.go_prev)
        nav.addWidget(self.prev_button)

        self.play_video_button = QPushButton(self._L("play_video", "Play Video"))
        self.play_video_button.clicked.connect(self.play_video)
        self.play_video_button.setEnabled(False)
        nav.addWidget(self.play_video_button)

        self.stop_video_button = QPushButton(self._L("stop_video", "Stop Video"))
        self.stop_video_button.clicked.connect(self.stop_video)
        self.stop_video_button.setEnabled(False)
        nav.addWidget(self.stop_video_button)

        self.next_button = QToolButton()
        try:
            self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        except Exception:
            self.next_button.setText("▶")
        self.next_button.setToolTip(self._L("next_video_tip", "Next"))
        self.next_button.clicked.connect(self.go_next)
        nav.addWidget(self.next_button)
        right.addLayout(nav)

        # Audio controls
        audio = QHBoxLayout()
        audio.addStretch(1)
        self.play_audio_button = QPushButton(self._L("play_audio", "Play Audio"))
        self.play_audio_button.clicked.connect(self.play_audio)
        self.play_audio_button.setEnabled(False)
        audio.addWidget(self.play_audio_button)

        self.stop_audio_button = QPushButton(self._L("stop_audio", "Stop Audio"))
        self.stop_audio_button.clicked.connect(self.stop_audio)
        self.stop_audio_button.setEnabled(False)
        audio.addWidget(self.stop_audio_button)

        self.record_button = QPushButton(self._L("record_audio", "Record Audio"))
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setEnabled(False)
        audio.addWidget(self.record_button)

        self.delete_recording_button = QPushButton(self._L("delete_recording", "Delete Recording"))
        self.delete_recording_button.clicked.connect(self.delete_recording)
        self.delete_recording_button.setEnabled(False)
        audio.addWidget(self.delete_recording_button)

        self.edit_recording_button = QPushButton(self._L("edit_recording_ocenaudio", "Edit in Ocenaudio"))
        self.edit_recording_button.clicked.connect(self.edit_recording_ocenaudio)
        self.edit_recording_button.setEnabled(False)
        audio.addWidget(self.edit_recording_button)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        audio.addWidget(self.status_label)
        audio.addStretch(1)
        right.addLayout(audio)
        right.addStretch()

        outer.addLayout(right, 1)

    # ---- queue / selection --------------------------------------------
    def refresh_queue(self, select_name: Optional[str] = None) -> None:
        """Reload the merged media queue, preserving selection when possible."""
        prev = select_name or self.current
        try:
            self.queue = list(self.fs.list_all_media())
        except Exception as e:
            logging.error(f"AllMediaTab.refresh_queue failed: {e}")
            self.queue = []
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for p in self.queue:
            item = QListWidgetItem(os.path.basename(p))
            item.setData(Qt.UserRole, p)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)

        if not self.queue:
            self.index = -1
            self.current = None
            self.preview_label.setText(self._L("video_listbox_no_video", "No media selected"))
            self.preview_label.setStyleSheet(_NORMAL_BORDER)
            self._update_controls()
            return
        target = 0
        if prev:
            for i, p in enumerate(self.queue):
                if os.path.basename(p) == os.path.basename(prev):
                    target = i
                    break
        self.select_index(target)

    def select_index(self, i: int) -> None:
        if i is None or i < 0 or i >= len(self.queue):
            return
        self._stop_all_for_switch()
        self.index = i
        self.current = self.queue[i]
        if self.list_widget.currentRow() != i:
            self.list_widget.blockSignals(True)
            self.list_widget.setCurrentRow(i)
            self.list_widget.blockSignals(False)
        self._show_preview()
        self._update_controls()

    def go_prev(self) -> None:
        if self.queue and self.index > 0:
            self.select_index(self.index - 1)

    def go_next(self) -> None:
        if self.queue and self.index < len(self.queue) - 1:
            self.select_index(self.index + 1)

    def _current_kind(self) -> Optional[str]:
        if not self.current:
            return None
        try:
            return self.fs.media_type_of(self.current)
        except Exception:
            return None

    # ---- preview -------------------------------------------------------
    def _show_preview(self) -> None:
        if not self.current or not os.path.exists(self.current):
            self.preview_label.setText(self._L("video_listbox_no_video", "No media selected"))
            return
        kind = self._current_kind()
        if kind == "image":
            self._show_image_preview()
        else:
            self._show_video_first_frame()

    def _show_image_preview(self) -> None:
        try:
            pixmap = QPixmap(self.current)
            if pixmap.isNull():
                self.preview_label.setText("Loading preview…")
                return
            self.preview_label.setPixmap(self._scaled(pixmap))
        except Exception as e:
            logging.error(f"AllMediaTab image preview failed: {e}")
            self.preview_label.setText("Loading preview…")

    def _show_video_first_frame(self) -> None:
        if not CV2_AVAILABLE:
            self.preview_label.setText("Loading preview…")
            return
        cap = None
        try:
            cap = cv2.VideoCapture(self.current)
            if not cap.isOpened():
                self.preview_label.setText("Loading preview…")
                return
            ret, frame = cap.read()
            if not ret:
                self.preview_label.setText("Loading preview…")
                return
            self.preview_label.setPixmap(self._frame_to_pixmap(frame))
        except Exception as e:
            logging.error(f"AllMediaTab video first-frame failed: {e}")
            self.preview_label.setText("Loading preview…")
        finally:
            if cap is not None:
                cap.release()

    def _frame_to_pixmap(self, frame) -> QPixmap:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        qt_image = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888).copy()
        return self._scaled(QPixmap.fromImage(qt_image))

    def _scaled(self, pixmap: QPixmap) -> QPixmap:
        try:
            target = self.preview_label.contentsRect().size()
            if target.width() > 0 and target.height() > 0:
                return pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception:
            pass
        return pixmap

    # ---- video playback ------------------------------------------------
    def play_video(self) -> None:
        if not self.current or self._current_kind() != "video":
            return
        self.stop_video()
        if not CV2_AVAILABLE:
            return
        self.cap = cv2.VideoCapture(self.current)
        if not self.cap.isOpened():
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
            QMessageBox.critical(self, self._L("error_title", "Error"),
                                 self._L("cannot_open_video", "Cannot open video file."))
            return
        self.playing_video = True
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        fps_val = float(fps) if fps else 0.0
        fps_valid = fps_val > 0.0 and not math.isnan(fps_val) and not math.isinf(fps_val)
        interval_ms = int(round(1000.0 / fps_val)) if fps_valid else 33
        interval_ms = max(5, min(1000, interval_ms))
        self.video_timer.start(interval_ms)

    def _update_video_frame(self) -> None:
        try:
            if self.playing_video and self.cap:
                if not self.cap.isOpened():
                    self.stop_video()
                    return
                ret, frame = self.cap.read()
                if not ret:
                    self.stop_video()
                    return
                self.preview_label.setPixmap(self._frame_to_pixmap(frame))
        except Exception as e:
            logging.error(f"AllMediaTab frame update failed: {e}")
            self.stop_video()

    def stop_video(self) -> None:
        self.playing_video = False
        try:
            self.video_timer.stop()
        except Exception:
            pass
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        # Restore the still first-frame/image
        if self.current and self._current_kind() == "video":
            self._show_video_first_frame()

    # ---- audio playback ------------------------------------------------
    def play_audio(self) -> None:
        if not self.current or self.is_playing_audio:
            return
        wav_path = self.fs.recording_path_for(self.current)
        if not os.path.exists(wav_path):
            return
        if not PYAUDIO_AVAILABLE:
            QMessageBox.warning(self, self._L("error_title", "Error"),
                                "PyAudio is not available. Cannot play audio.")
            return
        self.is_playing_audio = True
        try:
            self.play_audio_button.setText(self._L("playing", "Playing…"))
            self.play_audio_button.setEnabled(False)
        except Exception:
            pass
        self.audio_thread = QThread()
        self.audio_worker = AudioPlaybackWorker(wav_path)
        self.audio_worker.moveToThread(self.audio_thread)
        self.audio_thread.started.connect(self.audio_worker.run)
        self.audio_worker.finished.connect(self.audio_thread.quit)
        self.audio_worker.finished.connect(self.audio_worker.deleteLater)
        self.audio_thread.finished.connect(self.audio_thread.deleteLater)
        self.audio_thread.finished.connect(self._on_audio_finished)
        self.audio_worker.error.connect(self._on_worker_error)
        self.audio_thread.start()

    def stop_audio(self) -> None:
        if self.audio_worker:
            try:
                self.audio_worker.stop()
            except RuntimeError:
                pass
        self.is_playing_audio = False
        try:
            self.play_audio_button.setText(self._L("play_audio", "Play Audio"))
        except Exception:
            pass
        self._update_controls()

    def _on_audio_finished(self) -> None:
        self.audio_thread = None
        self.audio_worker = None
        self.is_playing_audio = False
        try:
            self.play_audio_button.setText(self._L("play_audio", "Play Audio"))
        except Exception:
            pass
        self._update_controls()

    # ---- recording -----------------------------------------------------
    def toggle_recording(self) -> None:
        if not self.current:
            return
        if self.is_recording:
            self._stop_recording()
            return
        wav_path = self.fs.recording_path_for(self.current)
        if os.path.exists(wav_path):
            reply = QMessageBox.question(
                self, self._L("overwrite", "Overwrite?"),
                self._L("overwrite_audio", "Audio file already exists. Overwrite?"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return
        if not PYAUDIO_AVAILABLE:
            QMessageBox.warning(self, self._L("error_title", "Error"),
                                "PyAudio is not available. Cannot record audio.")
            return
        self.is_recording = True
        self.record_button.setText(self._L("stop_recording", "Stop Recording"))
        self._update_recording_indicator()
        self.recording_thread = QThread()
        self.recording_worker = AudioRecordingWorker(wav_path)
        self.recording_worker.moveToThread(self.recording_thread)
        self.recording_thread.started.connect(self.recording_worker.run)
        self.recording_worker.finished.connect(self.recording_thread.quit)
        self.recording_worker.finished.connect(self.recording_worker.deleteLater)
        self.recording_thread.finished.connect(self.recording_thread.deleteLater)
        self.recording_thread.finished.connect(self._on_recording_finished)
        self.recording_worker.error.connect(self._on_worker_error)
        self.recording_thread.start()

    def _stop_recording(self) -> None:
        self.is_recording = False
        if self.recording_worker:
            try:
                self.recording_worker.stop()
            except RuntimeError:
                pass
        if self.recording_thread:
            try:
                if self.recording_thread.isRunning():
                    self.recording_thread.quit()
                    self.recording_thread.wait()
            except RuntimeError:
                pass
            finally:
                self.recording_thread = None
                self.recording_worker = None
        self._update_recording_indicator()
        self._update_controls()

    def _on_recording_finished(self) -> None:
        self.recording_thread = None
        self.recording_worker = None
        self.is_recording = False
        self._update_recording_indicator()
        self._update_controls()

    def _update_recording_indicator(self) -> None:
        try:
            self.status_label.setText(
                self._L("recording_indicator", "● Recording") if self.is_recording else ""
            )
        except Exception:
            pass

    # ---- recording management -----------------------------------------
    def delete_recording(self) -> None:
        if not self.current:
            return
        wav_path = self.fs.recording_path_for(self.current)
        if not os.path.exists(wav_path):
            return
        filename = os.path.basename(wav_path)
        body = self._L("delete_recording_confirm_body", "Delete {filename}?")
        try:
            body = body.format(filename=filename)
        except Exception:
            body = f"Delete {filename}?"
        reply = QMessageBox.question(
            self, self._L("delete_recording_confirm_title", "Delete recording?"),
            body, QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            os.remove(wav_path)
        except Exception as e:
            QMessageBox.critical(self, self._L("error_title", "Error"), str(e))
            return
        self._update_controls()

    def edit_recording_ocenaudio(self) -> None:
        if not self.current:
            return
        wav_path = self.fs.recording_path_for(self.current)
        if not os.path.exists(wav_path):
            return
        # Reuse the host's Ocenaudio launcher to avoid duplicating that logic.
        launcher = getattr(self.host, "_launch_ocenaudio", None)
        if callable(launcher):
            launcher([wav_path])
        else:
            QMessageBox.information(self, self._L("error_title", "Error"),
                                    "Ocenaudio launcher unavailable.")

    # ---- control state / cleanup --------------------------------------
    def _stop_all_for_switch(self) -> None:
        try:
            self.stop_audio()
        except Exception:
            pass
        try:
            if self.playing_video:
                self.stop_video()
        except Exception:
            pass
        try:
            if self.is_recording:
                self._stop_recording()
        except Exception:
            pass

    def _update_controls(self) -> None:
        has_current = bool(self.current)
        kind = self._current_kind()
        is_video = kind == "video"
        # Video controls only for videos
        self.play_video_button.setEnabled(has_current and is_video and not self.is_recording)
        self.stop_video_button.setEnabled(has_current and is_video)
        # Recording available for any media item
        self.record_button.setEnabled(has_current)
        self.record_button.setText(
            self._L("stop_recording", "Stop Recording") if self.is_recording
            else self._L("record_audio", "Record Audio")
        )
        wav_exists = bool(has_current) and self.fs.has_recording(self.current)
        self.play_audio_button.setEnabled(wav_exists and not self.is_playing_audio and not self.is_recording)
        self.stop_audio_button.setEnabled(wav_exists)
        self.delete_recording_button.setEnabled(wav_exists and not self.is_recording)
        self.edit_recording_button.setEnabled(wav_exists and not self.is_recording)
        # Green border when a recording exists (mirrors the Videos tab)
        self.preview_label.setStyleSheet(_RECORDED_BORDER if wav_exists else _NORMAL_BORDER)

    def _on_worker_error(self, msg: str) -> None:
        handler = getattr(self.host, "_show_worker_error", None)
        if callable(handler):
            handler(msg)
            return
        logging.error(f"AllMediaTab worker error: {msg}")
        try:
            QMessageBox.critical(self, self._L("error_title", "Error"), str(msg))
        except Exception:
            pass

    def cleanup(self) -> None:
        """Stop any active playback/recording (call on app close)."""
        self._stop_all_for_switch()
