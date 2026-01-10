"""Review Tab widget for quiz-based review sessions."""

"""
- [ ] Visually distinguish video thumbnails from still image thumbnails somehow in Review tab.
- [ ] Consider adding a "Reset to Defaults" button in the Review settings UI to restore default settings easily.
- [ ] Fix full-screen play/preview functionality in Review tab for videos.
- [ ] Add ability to export current media into multiple separate folders in order to reduce it to manageable lessons (like if the user has too many in one folder).
"""

import logging

import os
import uuid
import tempfile
import numpy as np
from typing import Optional, List, Tuple
from pydub import AudioSegment
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QSlider, QCheckBox,
    QProgressBar, QMessageBox, QFileDialog, QGroupBox, QRadioButton
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QShortcut, QKeySequence

from vat.utils.fs_access import FolderAccessManager
from vat.review.session_state import ReviewSessionState
from vat.review.queue import ReviewQueue
from vat.review.stats import ReviewStats
from vat.review.yaml_exporter import YAMLExporter
from vat.review.grouped_exporter import GroupedExporter
from vat.review.thumbnail_grid import ThumbnailGridWidget
from vat.audio import PYAUDIO_AVAILABLE
from vat.audio.playback import AudioPlaybackWorker


class ReviewTab(QWidget):
    """Main Review Tab widget.
    
    Provides:
    - Recorded-only thumbnail grid
    - Session controls and settings
    - Progress tracking and timing
    - YAML export and grouped export
    """
    
    def __init__(self, fs_manager: FolderAccessManager, app_version: str, parent=None):
        super().__init__(parent)
        self.fs = fs_manager
        self.app_version = app_version
        
        # State and logic components
        self.state = ReviewSessionState()
        self.queue = ReviewQueue(self)
        self.stats = ReviewStats()
        
        # Session tracking
        self.current_item_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timer_tick)
        self.elapsed_time: float = 0.0
        self.current_wav_path: Optional[str] = None
        self.waiting_for_prompt_audio: bool = False
        
        # Audio playback
        # Persistent audio thread to avoid destruction while running
        self.audio_thread: Optional[QThread] = QThread(self)
        self.audio_worker: Optional[AudioPlaybackWorker] = None
        self.audio_kind: Optional[str] = None  # 'prompt', 'prompt_replay', 'sfx'
        
        self._init_ui()
        self._connect_signals()
        # Start persistent audio thread
        try:
            if self.audio_thread and not self.audio_thread.isRunning():
                self.audio_thread.start()
        except Exception:
            pass
    
    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Header controls
        header = self._create_header_controls()
        layout.addWidget(header)
        
        # Tip
        tip = QLabel(
            "<b>Tip:</b> Single-click selects. Right-click, Ctrl/Cmd+Click, or Enter confirms. "
            "Double-click opens preview/fullscreen. Press Space to replay prompt."
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #555; font-size: 12px; padding: 4px;")
        layout.addWidget(tip)
        
        # Progress bar and timer
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar, 1)
        
        self.timer_label = QLabel("Time: --")
        self.timer_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        progress_layout.addWidget(self.timer_label)
        
        layout.addLayout(progress_layout)
        
        # Thumbnail grid
        self.grid = ThumbnailGridWidget(self.fs, self)
        layout.addWidget(self.grid, 1)
    
    def _create_header_controls(self) -> QWidget:
        """Create header controls."""
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Row 1: Scope, Play Count, Time Limit
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("Scope:"))
        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["Images", "Videos", "Both"])
        self.scope_combo.setCurrentText("Both")
        row1.addWidget(self.scope_combo)
        
        row1.addWidget(QLabel("Play Count:"))
        self.play_count_spin = QSpinBox()
        self.play_count_spin.setRange(1, 10)
        self.play_count_spin.setValue(1)
        row1.addWidget(self.play_count_spin)
        
        row1.addWidget(QLabel("Time Limit (sec):"))
        self.time_limit_spin = QDoubleSpinBox()
        self.time_limit_spin.setRange(0, 60)
        self.time_limit_spin.setValue(0)
        self.time_limit_spin.setSpecialValueText("Off")
        row1.addWidget(self.time_limit_spin)
        
        row1.addWidget(QLabel("Limit Mode:"))
        self.limit_mode_combo = QComboBox()
        self.limit_mode_combo.addItems(["Soft", "Hard"])
        row1.addWidget(self.limit_mode_combo)
        
        row1.addStretch()
        layout.addLayout(row1)
        
        # Row 2: SFX, Time Weighting, UI Overhead
        row2 = QHBoxLayout()
        
        self.sfx_check = QCheckBox("Sound Effects")
        self.sfx_check.setChecked(True)
        row2.addWidget(self.sfx_check)
        
        row2.addWidget(QLabel("SFX Vol:"))
        self.sfx_volume_slider = QSlider(Qt.Horizontal)
        self.sfx_volume_slider.setRange(0, 100)
        self.sfx_volume_slider.setValue(70)
        self.sfx_volume_slider.setMaximumWidth(100)
        row2.addWidget(self.sfx_volume_slider)
        
        row2.addWidget(QLabel("SFX Tone:"))
        self.sfx_tone_combo = QComboBox()
        self.sfx_tone_combo.addItems(["Default", "Gentle"])
        row2.addWidget(self.sfx_tone_combo)
        
        row2.addWidget(QLabel("Time Weight %:"))
        self.time_weight_spin = QSpinBox()
        self.time_weight_spin.setRange(0, 100)
        self.time_weight_spin.setValue(30)
        row2.addWidget(self.time_weight_spin)
        
        row2.addWidget(QLabel("UI Overhead (ms):"))
        self.ui_overhead_spin = QSpinBox()
        self.ui_overhead_spin.setRange(0, 5000)
        self.ui_overhead_spin.setValue(2000)
        row2.addWidget(self.ui_overhead_spin)
        
        row2.addStretch()
        layout.addLayout(row2)
        
        # Row 3: Session controls
        row3 = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Review")
        self.start_btn.clicked.connect(self._on_start)
        row3.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self._on_pause_resume)
        self.pause_btn.setEnabled(False)
        row3.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        row3.addWidget(self.stop_btn)
        
        self.replay_btn = QPushButton("Replay Prompt")
        self.replay_btn.clicked.connect(self._on_replay_clicked)
        self.replay_btn.setEnabled(False)
        row3.addWidget(self.replay_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._on_reset)
        row3.addWidget(self.reset_btn)
        
        self.reset_defaults_btn = QPushButton("Reset to Defaults")
        self.reset_defaults_btn.clicked.connect(self._on_reset_defaults)
        row3.addWidget(self.reset_defaults_btn)
        
        row3.addStretch()
        
        self.export_yaml_btn = QPushButton("Export YAML Report")
        self.export_yaml_btn.clicked.connect(self._on_export_yaml)
        row3.addWidget(self.export_yaml_btn)
        
        self.grouped_export_btn = QPushButton("Grouped Export")
        self.grouped_export_btn.clicked.connect(self._on_grouped_export)
        row3.addWidget(self.grouped_export_btn)
        
        layout.addLayout(row3)
        
        return header
    
    def _connect_signals(self) -> None:
        """Connect signals."""
        self.grid.activatedConfirm.connect(self._on_confirm)
        self.grid.doubleClicked.connect(self._on_preview)
        self.queue.promptReady.connect(self._on_prompt_ready)
        self.queue.queueFinished.connect(self._on_queue_finished)
        # Auto-refresh the grid when scope changes or folder contents update
        try:
            self.scope_combo.currentTextChanged.connect(lambda _t: self._refresh_grid())
        except Exception:
            pass
        try:
            self.fs.folderChanged.connect(lambda _p: self._refresh_grid())
        except Exception:
            pass
        try:
            self.fs.imagesUpdated.connect(lambda *_args: self._refresh_grid())
        except Exception:
            pass
        try:
            self.fs.videosUpdated.connect(lambda *_args: self._refresh_grid())
        except Exception:
            pass

        # Also refresh thumbnails when other UI settings change (visual feedback)
        for w in (
            self.play_count_spin,
            self.time_limit_spin,
            self.limit_mode_combo,
            self.sfx_check,
            self.sfx_volume_slider,
            self.sfx_tone_combo,
            self.time_weight_spin,
            self.ui_overhead_spin,
        ):
            try:
                # Lightweight repaint; does not rebuild items
                signal = getattr(w, 'valueChanged', None) or getattr(w, 'currentTextChanged', None) or getattr(w, 'toggled', None)
                if signal:
                    signal.connect(lambda *_: self.grid.list_widget.viewport().update())
            except Exception:
                pass

        # Initial population
        self._refresh_grid()

        # Ensure the tab can receive key events for shortcuts
        try:
            self.setFocusPolicy(Qt.StrongFocus)
        except Exception:
            pass

        # Add keyboard shortcuts that work when any child has focus
        try:
            self.shortcut_space = QShortcut(QKeySequence(Qt.Key_Space), self)
            self.shortcut_space.setContext(Qt.WidgetWithChildrenShortcut)
            self.shortcut_space.activated.connect(self._on_replay_clicked)

            self.shortcut_r = QShortcut(QKeySequence("R"), self)
            self.shortcut_r.setContext(Qt.WidgetWithChildrenShortcut)
            self.shortcut_r.activated.connect(self._on_replay_clicked)
        except Exception:
            pass

    def _refresh_grid(self) -> None:
        """Populate the thumbnail grid with recorded items for current scope."""
        try:
            items = self._get_recorded_items()
            self.grid.populate(items)
            self.grid.clear_feedback()
            try:
                logging.info(f"Review._refresh_grid: items={len(items)}; sample={[os.path.basename(p) for _, p, _ in items[:3]]}")
            except Exception:
                pass
            # Reset progress display outside sessions
            if not self.state.sessionActive:
                self.progress_bar.setMaximum(max(1, len(items)))
                self.progress_bar.setValue(0)
                self.progress_bar.setFormat(f"0/{len(items)} prompts")
        except Exception:
            pass
    
    def _on_start(self) -> None:
        """Start a review session."""
        # Build item list based on scope
        items = self._get_recorded_items()
        if not items:
            QMessageBox.information(self, "No Items", "No recorded items found for the selected scope.")
            return
        
        # Update state from UI
        self._sync_state_from_ui()
        
        # Build queue
        self.queue.build_queue(items, self.state.playCountPerItem)
        
        # Initialize stats
        self.stats.start_session()
        for item_id, media_path, wav_path in items:
            media_type = "video" if media_path.lower().endswith(self.fs.VIDEO_EXTS) else "image"
            self.stats.add_item(item_id, media_type, media_path, wav_path)
        
        # Populate grid (already populated by _refresh_grid; refresh to ensure order matches queue)
        self.grid.populate(items)
        self.grid.clear_feedback()
        
        # Update UI
        self.state.sessionActive = True
        self.state.paused = False
        self.session_id = str(uuid.uuid4())
        self._update_controls_state()
        
        # Start first prompt
        self.queue.emit_next_prompt()
    
    def _on_pause_resume(self) -> None:
        """Pause or resume the session."""
        if self.state.paused:
            self.state.paused = False
            self.pause_btn.setText("Pause")
            self.stats.resume_timer()
        else:
            self.state.paused = True
            self.pause_btn.setText("Resume")
            self.stats.pause_timer()
    
    def _on_stop(self) -> None:
        """Stop the session."""
        # Ensure any audio playback is stopped
        self._stop_audio()
        self.state.reset_session()
        self.timer.stop()
        self.current_item_id = None
        self.grid.clear_feedback()
        self._update_controls_state()
        self._update_progress()
    
    def _on_reset(self) -> None:
        """Reset the session."""
        self._stop_audio()
        self._on_stop()
        self.queue.reset()
        self.stats = ReviewStats()
        self.grid.clear_feedback()
    
    def _on_reset_defaults(self) -> None:
        """Reset all settings to defaults."""
        self.state.reset_to_defaults()
        self._sync_ui_from_state()
    
    def _on_prompt_ready(self, item_id: str, wav_path: str) -> None:
        """Handle a new prompt."""
        # Clear any lingering feedback from previous prompt
        try:
            self.grid.clear_feedback()
        except Exception:
            pass
        self.current_item_id = item_id
        self.elapsed_time = 0.0
        self.current_wav_path = wav_path
        self.waiting_for_prompt_audio = True
        
        # Play audio; timing will start when playback finishes
        self._play_audio(wav_path, kind='prompt')
        
        # Update progress
        self._update_progress()
    
    def _on_confirm(self, item_id: str, method: str) -> None:
        """Handle user confirmation."""
        if not self.state.sessionActive or self.state.paused:
            return
        
        try:
            logging.info(f"Review.confirm: method={method}; current_item={self.current_item_id}; audio_kind={self.audio_kind}")
        except Exception:
            pass

        # Stop any ongoing prompt/replay audio immediately
        self._stop_audio()

        correct = (item_id == self.current_item_id)
        
        # Record response
        overtime = False
        if self.state.perItemTimeLimitSec > 0 and self.elapsed_time > self.state.perItemTimeLimitSec:
            overtime = True
        
        self.stats.record_response(self.current_item_id, correct, method, overtime=overtime)
        
        # Show feedback
        self.grid.set_feedback(item_id, "correct" if correct else "wrong")
        
        # Play sound effect
        if self.state.sfxEnabled:
            self._play_sfx("correct" if correct else "wrong")
        
        if correct:
            # Remove any previous red 'wrong' marks once the correct item is chosen
            try:
                self.grid.clear_wrong_feedback()
            except Exception:
                pass
            # Move to next prompt
            self.timer.stop()
            QTimer.singleShot(500, self._advance_prompt)
        # If wrong, continue with same prompt
    
    def _on_preview(self, item_id: str) -> None:
        """Handle preview/fullscreen request."""
        # Pause timer during preview
        if self.state.sessionActive and not self.state.paused:
            self.stats.pause_timer()
        
        # Get item details
        item = self.grid.get_item_by_id(item_id)
        if not item:
            return
        
        media_path = item.data(Qt.UserRole + 1)
        if not media_path or not os.path.exists(media_path):
            return
        
        # Determine media type and show appropriate viewer
        try:
            if media_path.lower().endswith(self.fs.VIDEO_EXTS):
                from vat.ui.fullscreen import FullscreenVideoViewer
                viewer = FullscreenVideoViewer(media_path)
                
                # Connect to playingChanged signal for timer pause/resume
                try:
                    viewer.playingChanged.connect(self._on_fullscreen_playing_changed)
                except Exception:
                    pass
                
                viewer.showFullScreen()
                viewer.destroyed.connect(self._on_fullscreen_closed)
            else:
                from vat.ui.fullscreen import FullscreenImageViewer
                viewer = FullscreenImageViewer(media_path)
                viewer.showFullScreen()
                viewer.destroyed.connect(self._on_fullscreen_closed)
        except Exception:
            # Resume timer if preview fails
            if self.state.sessionActive and not self.state.paused:
                self.stats.resume_timer()
    
    def _on_fullscreen_playing_changed(self, is_playing: bool) -> None:
        """Handle fullscreen video playing state change."""
        if not self.state.sessionActive or self.state.paused:
            return
        
        if is_playing:
            self.stats.pause_timer()
        else:
            self.stats.resume_timer()
    
    def _on_fullscreen_closed(self) -> None:
        """Handle fullscreen viewer closed."""
        # Resume timer when fullscreen closes
        if self.state.sessionActive and not self.state.paused:
            self.stats.resume_timer()
    
    def _on_queue_finished(self) -> None:
        """Handle queue completion."""
        self._stop_audio()
        self.timer.stop()
        self.state.sessionActive = False
        self._update_controls_state()
        
        # Show summary
        overall = self.stats.get_overall_stats(
            time_weighting=self.state.timeWeightingPercent / 100.0,
            ui_overhead_sec=self.state.uiOverheadMs / 1000.0,
        )
        
        msg = (
            f"Review session complete!\n\n"
            f"Grade: {overall['grade']}\n"
            f"Accuracy: {overall['accuracyPercent']}%\n"
            f"Average Time: {overall['averageTimeSec']}s\n"
            f"Composite Score: {overall['compositeScore']}\n"
        )
        QMessageBox.information(self, "Session Complete", msg)
    
    def _on_timer_tick(self) -> None:
        """Update timer display."""
        self.elapsed_time += 0.1
        self.timer_label.setText(f"Time: {self.elapsed_time:.1f}s")
        
        # Check hard limit
        if (self.state.limitMode == "hard" and 
            self.state.perItemTimeLimitSec > 0 and 
            self.elapsed_time >= self.state.perItemTimeLimitSec):
            
            # Auto-mark wrong (timeout)
            self.stats.record_response(self.current_item_id, False, "timeout", timeout=True)
            self.grid.set_feedback(self.current_item_id, "wrong")
            
            if self.state.sfxEnabled:
                self._play_sfx("wrong")
            
            self.timer.stop()
            QTimer.singleShot(500, self._advance_prompt)
    
    def _advance_prompt(self) -> None:
        """Advance to next prompt."""
        self.grid.set_feedback(self.current_item_id, "")
        self.queue.emit_next_prompt()
    
    def _on_export_yaml(self) -> None:
        """Export YAML report."""
        if not self.session_id:
            QMessageBox.warning(self, "No Session", "No session data to export.")
            return
        
        output_dir = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if not output_dir:
            return
        
        try:
            filepath = YAMLExporter.export_session(
                self.stats,
                self.state,
                self.queue,
                self.session_id,
                "en",  # TODO: Get from app
                self.app_version,
                output_dir,
            )
            QMessageBox.information(self, "Export Complete", f"YAML report saved to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export YAML: {e}")
    
    def _on_grouped_export(self) -> None:
        """Open grouped export dialog."""
        items = self._get_recorded_items()
        if not items:
            QMessageBox.information(self, "No Items", "No recorded items to export.")
            return
        
        from vat.review.grouped_export_dialog import GroupedExportDialog
        dialog = GroupedExportDialog(items, self.state.groupedDefaultItemsPerFolder, self)
        if dialog.exec() == dialog.Accepted and dialog.result_metadata:
            # Optionally save the metadata for the YAML export
            pass
    
    def _get_recorded_items(self) -> List[Tuple[str, str, str]]:
        """Get list of recorded items based on scope."""
        items = []
        scope = self.scope_combo.currentText().lower()
        
        if scope in ("images", "both"):
            images = self.fs.list_images()
            for img_path in images:
                # Use compatibility resolver to find existing audio for image
                wav_path = self.fs.find_existing_image_audio(img_path) or self.fs.wav_path_for_image(img_path)
                if wav_path and os.path.exists(wav_path):
                    item_id = f"img_{os.path.basename(img_path)}"
                    items.append((item_id, img_path, wav_path))
        
        if scope in ("videos", "both"):
            videos = self.fs.list_videos()
            for vid_path in videos:
                name = os.path.basename(vid_path)
                wav_path = self.fs.wav_path_for(name)
                if os.path.exists(wav_path):
                    item_id = f"vid_{name}"
                    items.append((item_id, vid_path, wav_path))
        
        return items
    
    def _play_audio(self, wav_path: str, kind: str = 'prompt') -> None:
        """Play audio file with kind control ('prompt', 'prompt_replay', 'sfx')."""
        if not PYAUDIO_AVAILABLE:
            return
        
        # Stop any existing playback (do not quit persistent thread)
        if self.audio_worker:
            try:
                logging.info("Review.audio: pre-stop existing playback before starting new")
            except Exception:
                pass
            try:
                self.audio_worker.stop()
            except RuntimeError:
                pass
        
        # Set current audio kind
        self.audio_kind = kind
        try:
            logging.info(f"Review.audio: start kind={kind}; path={os.path.basename(wav_path)}")
        except Exception:
            pass
        
        # If replaying prompt, pause timer during playback
        if kind == 'prompt_replay' and self.state.sessionActive and not self.state.paused:
            try:
                self.stats.pause_timer()
            except Exception:
                pass
        
        # Start new playback on persistent thread
        self.audio_worker = AudioPlaybackWorker(wav_path)
        self.audio_worker.moveToThread(self.audio_thread)
        # Run worker in the thread via queued connection
        try:
            from PySide6.QtCore import QMetaObject
            QMetaObject.invokeMethod(self.audio_worker, "run", Qt.QueuedConnection)
        except Exception:
            # Fallback: start thread if needed
            if self.audio_thread and not self.audio_thread.isRunning():
                self.audio_thread.start()
            self.audio_thread.started.connect(self.audio_worker.run)
        # Notify when finished
        self.audio_worker.finished.connect(self._on_audio_finished)
        try:
            # Log errors from worker
            self.audio_worker.error.connect(lambda msg: logging.error(f"Review.audio: worker error: {msg}"))
        except Exception:
            pass
    
    def _on_audio_finished(self) -> None:
        """Handle audio playback finished."""
        # Resume or start timer based on audio kind
        if self.state.sessionActive and not self.state.paused:
            try:
                if self.audio_kind == 'prompt' and self.waiting_for_prompt_audio and self.current_item_id:
                    # Start timing only after initial prompt audio finishes
                    self.waiting_for_prompt_audio = False
                    self.stats.start_prompt(self.current_item_id)
                    self.timer.start(100)
                elif self.audio_kind == 'prompt_replay':
                    # Resume timing after replay finishes
                    self.stats.resume_timer()
            except Exception:
                pass
        try:
            logging.info(f"Review.audio: finished kind={self.audio_kind}; waiting_for_prompt_audio={self.waiting_for_prompt_audio}")
        except Exception:
            pass
        
        self.audio_worker = None
        self.audio_kind = None

    def _stop_audio(self) -> None:
        """Stop any ongoing audio playback immediately."""
        try:
            logging.info("Review.audio: stop requested")
            # Signal the worker to stop reading/writing audio data
            if self.audio_worker:
                try:
                    self.audio_worker.stop()
                except RuntimeError:
                    pass
            # We keep a persistent thread; do not quit/destroy it here
        finally:
            # Only clear references if the thread has actually stopped
            if not (self.audio_thread and self.audio_thread.isRunning()):
                self.audio_worker = None
                self.audio_kind = None
    
    def _play_sfx(self, effect: str) -> None:
        """Play sound effect."""
        if not self.state.sfxEnabled or not PYAUDIO_AVAILABLE:
            return
        
        try:
            # Generate sound effect based on tone and effect type
            if effect == "correct":
                if self.state.sfxTone == "gentle":
                    freq = 600  # Gentler, lower tone
                else:
                    freq = 800  # Default higher tone
                duration_ms = 150
            else:  # "wrong"
                if self.state.sfxTone == "gentle":
                    freq = 300  # Gentler, lower buzz
                else:
                    freq = 200  # Default lower buzz
                duration_ms = 200
            
            # Generate sound with pydub
            rate = 44100
            t = np.linspace(0, duration_ms / 1000, int(rate * duration_ms / 1000), endpoint=False)
            
            if effect == "correct":
                # Pleasant ding with envelope
                sine_wave = np.sin(2 * np.pi * freq * t)
                decay = np.linspace(1, 0, len(sine_wave))
                click_data = sine_wave * decay
            else:
                # Buzzer with slight vibrato
                vibrato = 1 + 0.1 * np.sin(2 * np.pi * 5 * t)
                sine_wave = np.sin(2 * np.pi * freq * vibrato * t)
                click_data = sine_wave
            
            # Apply volume
            volume = self.state.sfxVolumePercent / 100.0
            click_data = (click_data * volume * 0.5 * (2**15 - 1)).astype(np.int16).tobytes()
            
            audio_segment = AudioSegment(
                data=click_data,
                sample_width=2,
                frame_rate=rate,
                channels=1
            )
            
            # Save to temp file and play
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name
                audio_segment.export(tmp_path, format='wav')
            
            # Play the temp file as SFX
            self._play_audio(tmp_path, kind='sfx')
            
            # Clean up temp file after a delay
            QTimer.singleShot(1000, lambda: self._cleanup_temp_file(tmp_path))
        
        except Exception:
            # Silently fail on sound effect errors
            pass
    
    def _cleanup_temp_file(self, path: str) -> None:
        """Clean up temporary audio file."""
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
    
    def _sync_state_from_ui(self) -> None:
        """Update state from UI controls."""
        self.state.scope = self.scope_combo.currentText().lower()
        self.state.playCountPerItem = self.play_count_spin.value()
        self.state.perItemTimeLimitSec = self.time_limit_spin.value()
        self.state.limitMode = self.limit_mode_combo.currentText().lower()
        self.state.sfxEnabled = self.sfx_check.isChecked()
        self.state.sfxVolumePercent = self.sfx_volume_slider.value()
        self.state.sfxTone = self.sfx_tone_combo.currentText().lower()
        self.state.timeWeightingPercent = self.time_weight_spin.value()
        self.state.uiOverheadMs = self.ui_overhead_spin.value()
    
    def _sync_ui_from_state(self) -> None:
        """Update UI controls from state."""
        scope_map = {"images": "Images", "videos": "Videos", "both": "Both"}
        self.scope_combo.setCurrentText(scope_map.get(self.state.scope, "Both"))
        self.play_count_spin.setValue(self.state.playCountPerItem)
        self.time_limit_spin.setValue(self.state.perItemTimeLimitSec)
        
        limit_map = {"soft": "Soft", "hard": "Hard"}
        self.limit_mode_combo.setCurrentText(limit_map.get(self.state.limitMode, "Soft"))
        
        self.sfx_check.setChecked(self.state.sfxEnabled)
        self.sfx_volume_slider.setValue(self.state.sfxVolumePercent)
        
        tone_map = {"default": "Default", "gentle": "Gentle"}
        self.sfx_tone_combo.setCurrentText(tone_map.get(self.state.sfxTone, "Default"))
        
        self.time_weight_spin.setValue(self.state.timeWeightingPercent)
        self.ui_overhead_spin.setValue(self.state.uiOverheadMs)
    
    def _update_controls_state(self) -> None:
        """Update enabled state of controls."""
        in_session = self.state.sessionActive
        
        self.start_btn.setEnabled(not in_session)
        self.pause_btn.setEnabled(in_session)
        self.stop_btn.setEnabled(in_session)
        self.replay_btn.setEnabled(in_session)
        
        # Disable settings during session
        self.scope_combo.setEnabled(not in_session)
        self.play_count_spin.setEnabled(not in_session)
        self.time_limit_spin.setEnabled(not in_session)
        self.limit_mode_combo.setEnabled(not in_session)
    
    def _update_progress(self) -> None:
        """Update progress bar."""
        current, total = self.queue.get_progress()
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current}/{total} prompts")

    def _on_replay_clicked(self) -> None:
        """Replay the current prompt audio and pause timer during playback."""
        if not self.current_wav_path:
            return
        try:
            logging.info("Review.replay: requested; stopping current audio and replaying prompt")
        except Exception:
            pass
        self._stop_audio()
        self._play_audio(self.current_wav_path, kind='prompt_replay')

    def keyPressEvent(self, event) -> None:
        """Handle keyboard shortcuts for the review tab."""
        try:
            if event.key() in (Qt.Key_Space, Qt.Key_R):
                # Replay prompt on Space (preferred) or 'R'
                self._on_replay_clicked()
                return
        except Exception:
            pass
        super().keyPressEvent(event)
