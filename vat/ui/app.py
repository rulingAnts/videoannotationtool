import sys
import os
import cv2
import numpy as np
import shutil
import subprocess
import json
import logging
import math
from pathlib import Path
from pydub import AudioSegment

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QTextEdit, QMessageBox,
    QFileDialog, QComboBox, QTabWidget, QSplitter, QToolButton, QStyle, QSizePolicy,
    QListView, QStyledItemDelegate, QApplication, QCheckBox, QGraphicsDropShadowEffect,
    QMenu, QProgressDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QEvent, QSize, QRect, QPoint, QLocale, QMetaObject, QUrl, QMimeData
import time
from PySide6.QtGui import QImage, QPixmap, QIcon, QShortcut, QKeySequence, QImageReader, QPen, QColor, QGuiApplication, QAction, QCursor
import tempfile
import shlex
import threading
import zipfile

from vat.audio import PYAUDIO_AVAILABLE
from vat.audio.playback import AudioPlaybackWorker
from vat.audio.recording import AudioRecordingWorker
from vat.audio.joiner import JoinWavsWorker
from vat.utils.resources import resource_path
from vat.utils.video_convert import VideoConvertWorker, ConvertSpec, needs_reencode_to_mp4
from vat.ui.fullscreen import FullscreenVideoViewer, FullscreenImageViewer
from vat.utils.fs_access import (
    FolderAccessManager,
    FolderAccessError,
    FolderPermissionError,
    FolderNotFoundError,
)
from vat.review import ReviewTab

# Labels are loaded from the builtin module (vat.i18n.builtin_labels)
# with an optional external YAML/JSON overlay. A minimal English
# fallback is provided below if the builtin import fails.

# Prefer labels from external builtin module; replace embedded dict at runtime
try:
    from vat.i18n.builtin_labels import LABELS_ALL as _EXTERNAL_LABELS_ALL
    if isinstance(_EXTERNAL_LABELS_ALL, dict) and _EXTERNAL_LABELS_ALL:
        # Replace any in-file labels with the builtin set to reduce duplication
        globals()['LABELS_ALL'] = dict(_EXTERNAL_LABELS_ALL)
    else:
        raise ValueError("Empty builtin labels")
except Exception:
    # Minimal English fallback to keep UI running if builtin labels fail to load
    globals()['LABELS_ALL'] = {
        "English": {
            "language_name": "English",
            "app_title": "Visual Stimulus Kit Tool",
            "select_folder": "Select Folder",
            "images_tab_title": "Images",
            "videos_tab_title": "Videos",
            "video_fullscreen_tip": "<b>Tip:</b> Double-click the video to open fullscreen. Use <b>+</b> and <b>-</b> to zoom in/out in fullscreen view.",
            "image_fullscreen_tip": "<b>Tip:</b> Double-click an image to open fullscreen. Use <b>+</b> and <b>-</b> to zoom in/out in fullscreen view.",
            "image_show_filenames": "Show filenames",
            "welcome_dialog_title": "Welcome to the Visual Stimulus Kit Tool",
            "welcome_dialog_body_html": (
                "<p><b>Welcome!</b> This tool helps you collect clear, well-organised "
                "examples of how people speak in minority and under-documented languages.</p>"
            ),
            "review_tab_title": "Review",
            "review_tip_html": "<b>Tip:</b> Single-click selects. Right-click, Ctrl/Cmd+Click, or Enter confirms. Double-click opens preview/fullscreen. Press Space to replay prompt.",
            "time_label_prefix": "Time: ",
            "review_start": "Start Review",
            "review_pause": "Pause",
            "review_resume": "Resume",
            "review_stop": "Stop",
            "review_replay": "Replay",
            "review_set_name_placeholder": "Set name",
            "review_show_settings": "Show settings",
            "review_hide_settings": "Hide settings",
            "review_help_link": "GPA Review Guide",
            "review_scope_label": "Scope:",
            "review_scope_images": "Images",
            "review_scope_videos": "Videos",
            "review_scope_both": "Both",
            "review_play_count_label": "Play Count:",
            "review_time_limit_label": "Time Limit (sec):",
            "review_time_limit_off": "Off",
            "review_limit_mode_label": "Limit Mode:",
            "review_limit_soft": "Soft",
            "review_limit_hard": "Hard",
            "review_sfx_label": "Sound Effects",
            "review_sfx_vol_label": "SFX Vol:",
            "review_sfx_tone_label": "SFX Tone:",
            "review_sfx_tone_default": "Default",
            "review_sfx_tone_gentle": "Gentle",
            "review_time_weight_label": "Time Weight %:",
            "review_ui_overhead_label": "UI Overhead (ms):",
            "review_thumb_size_label": "Thumb Size:",
            "review_items_per_session_label": "Items per Session:",
            "review_sessions_label_initial": "Sessions: --",
            "review_sessions_label_format": "Sessions: {sessions}  |  Items/session: {per}  |  Last: {last_items}",
            "review_reset": "Reset",
            "review_reset_defaults": "Reset to Defaults",
            "review_export_results": "Export Results",
            "review_export_sets": "Export Sets",
            "review_export_format_label": "Format:",
            "review_export_format_folders": "Folders",
            "review_export_format_zip": "Zip files",
            "review_progress_format": "{current}/{total} prompts",
            "review_no_items_title": "No Items",
            "review_no_items_scope": "No recorded items found for the selected scope.",
            "review_no_items_group": "No recorded items to group.",
            "review_no_items_export": "No recorded items to export.",
            "review_no_session_title": "No Session",
            "review_no_session_msg": "No session data to export.",
            "group_export_title": "Grouped Export",
            "group_export_info": "Export {count} recorded items into organized group folders.",
            "group_export_items_per_folder": "Items per folder:",
            "group_export_num_folders": "Number of folders:",
            "group_export_copy_mode": "Copy files (default, safe)",
            "group_export_copy_mode_tip": "Uncheck to move files instead (use with caution)",
            "group_export_export_btn": "Export...",
            "group_export_cancel_btn": "Cancel",
            "group_export_preview_none": "No items to export.",
            "group_export_preview_will_create": "Will create {n} folder(s):\n",
            "group_export_preview_group_line": "  Group {i:02d}: {count} items\n",
            "group_export_preview_more": "  ... and {extra} more folders\n",
            "group_export_preview_last_note": "\nNote: Last folder has {count} items (remainder).",
            "group_export_no_items_title": "No Items",
            "group_export_no_items_msg": "No items to export.",
            "group_export_select_dir": "Select Export Directory",
            "group_export_confirm_overwrite_title": "Confirm Overwrite",
            "group_export_confirm_overwrite_msg": "The selected directory already contains {n} Group folder(s).\n\nExisting files may be overwritten. Continue?",
            "group_export_complete_title": "Export Complete",
            "group_export_complete_msg": "Successfully exported {items} items into {groups} folders.",
            "group_export_failed_title": "Export Failed",
            "group_export_failed_msg": "Failed to export:",
            "drawer_show": "Show drawer",
            "drawer_hide": "Hide drawer",
            "prev_video_tip": "Previous video",
            "next_video_tip": "Next video",
        }
    }

# Optional external labels overlay support (YAML or JSON). This lets us
# keep LABELS_ALL out of the main UI file for easier maintenance.
def _deep_merge_labels(base: dict, overlay: dict) -> dict:
    try:
        for lang, labels in overlay.items():
            if lang not in base or not isinstance(base.get(lang), dict):
                base[lang] = labels
                continue
            b = base[lang]
            if isinstance(labels, dict):
                for k, v in labels.items():
                    b[k] = v
    except Exception:
        pass
    return base

def _load_external_labels_overlay() -> None:
    try:
        import os, json
        try:
            import yaml
        except Exception:
            yaml = None
        from vat.utils.resources import resource_path
        # Prefer YAML, then JSON
        yaml_path = resource_path(os.path.join("i18n", "labels.yaml"), check_system=False)
        json_path = resource_path(os.path.join("i18n", "labels.json"), check_system=False)
        loaded = None
        if yaml and os.path.exists(yaml_path):
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    loaded = yaml.safe_load(f)
            except Exception:
                loaded = None
        elif os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
            except Exception:
                loaded = None
        if isinstance(loaded, dict) and loaded:
            # Deep-merge overlay onto built-ins
            globals()['LABELS_ALL'] = _deep_merge_labels(LABELS_ALL, loaded)
    except Exception:
        # Non-fatal if external labels cannot be loaded
        pass

# Attempt to load external overlay at import-time
_load_external_labels_overlay()

class VideoAnnotationApp(QMainWindow):
    ui_info = Signal(str, str)
    ui_warning = Signal(str, str)
    ui_error = Signal(str, str)
    def __init__(self):
        super().__init__()
        # Default language; may be overridden by settings or system locale
        self.language = "English"
        self.LABELS = LABELS_ALL[self.language]
        # Unified file-system access
        self.fs = FolderAccessManager()
        self.video_files = []
        self.current_video = None
        self.last_video_name = None
        self.ocenaudio_path = None
        self.settings_file = os.path.expanduser("~/.videooralannotation/settings.json")
        self.playing_video = False
        self.cap = None
        self.video_timer = QTimer()
        self.video_timer.timeout.connect(self.update_video_frame)
        # Persistent audio thread used for all playback
        self.audio_thread = QThread(self)
        self.audio_worker = None
        # Unified audio playback state + debounce
        self.is_playing_audio = False
        self._last_play_request_ts = 0.0
        self.is_recording = False
        self.recording_thread = None
        self.recording_worker = None
        self.join_thread = None
        self.join_worker = None
        self._suppress_item_changed = False
        # Pending selection target (used to auto-select a file after folder refresh)
        self._pending_select_video_name = None
        # Cache for full-resolution image pixmaps (used by thumbnails and fullscreen)
        self._image_pixmap_cache = {}
        # Fullscreen viewer state
        self._fullscreen_viewer = None
        self.fullscreen_zoom = None
        self._ui_ready = False
        # Connect FS manager signals
        try:
            self.fs.folderChanged.connect(self._on_folder_changed)
            self.fs.videosUpdated.connect(self._on_videos_updated)
            self.fs.imagesUpdated.connect(self._on_images_updated)
        except Exception:
            pass
        self.load_settings()
        self.init_ui()
        self.setWindowTitle(self.LABELS["app_title"])
        # More compact default window size; adapt to screen width
        try:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            avail = screen.availableGeometry() if screen else None
            if avail:
                # Aim for ~70% of screen width with a hard upper cap
                target_w = max(720, min(int(avail.width() * 0.70), 1200))
                target_h = min(680, avail.height())
                self.resize(target_w, target_h)
                # Prevent initial over-expansion beyond target width
                try:
                    self.setMaximumWidth(target_w)
                    self.setFixedWidth(target_w)
                except Exception:
                    pass
                # Adjust splitter sizes proportionally to target width
                try:
                    if hasattr(self, 'main_splitter'):
                        sizes = self.main_splitter.sizes()
                        # Respect collapsed default: only adjust if left is visible
                        if sizes and sizes[0] > 0:
                            left = max(160, int(target_w * 0.26))
                            right = max(1, target_w - left)
                            self.main_splitter.setSizes([left, right])
                            self._splitter_prev_sizes = [left, right]
                except Exception:
                    pass
                try:
                    logging.info(f"UI.window: screen_w={avail.width()}, target_w={target_w}, final_w={self.size().width()}, splitter_sizes={getattr(self, 'main_splitter').sizes() if hasattr(self, 'main_splitter') else 'n/a'}")
                except Exception:
                    pass
                # Enforce width cap again after initial layout to avoid expansion
                try:
                    QTimer.singleShot(0, self._enforce_window_width_cap)
                except Exception:
                    pass
            else:
                # Fallback if screen info unavailable
                self.resize(840, 680)
                try:
                    logging.info(f"UI.window: no screen info; final_w={self.size().width()}")
                except Exception:
                    pass
        except Exception:
            self.resize(840, 680)
            try:
                logging.info(f"UI.window: sizing exception; final_w={self.size().width()}")
            except Exception:
                pass
        # Global shortcuts: work regardless of focus
        try:
            self._shortcut_log_ctrl = QShortcut(QKeySequence("Ctrl+Shift+L"), self)
            self._shortcut_log_ctrl.activated.connect(self._show_log_viewer)
            self._shortcut_log_meta = QShortcut(QKeySequence("Meta+Shift+L"), self)
            self._shortcut_log_meta.activated.connect(self._show_log_viewer)
            self._shortcut_ff_ctrl = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
            self._shortcut_ff_ctrl.activated.connect(self._show_ffmpeg_diagnostics)
            self._shortcut_ff_meta = QShortcut(QKeySequence("Meta+Shift+F"), self)
            self._shortcut_ff_meta.activated.connect(self._show_ffmpeg_diagnostics)
            # Drawer toggle shortcut: Ctrl+D and Cmd+D (Meta+D on macOS)
            self._shortcut_drawer_ctrl = QShortcut(QKeySequence("Ctrl+D"), self)
            self._shortcut_drawer_ctrl.activated.connect(self._toggle_drawer)
            self._shortcut_drawer_meta = QShortcut(QKeySequence("Meta+D"), self)
            self._shortcut_drawer_meta.activated.connect(self._toggle_drawer)
        except Exception:
            pass

    def _is_dark_mode(self) -> bool:
        """Detect whether the OS/app is currently using a dark color scheme."""
        try:
            from PySide6.QtGui import QGuiApplication, QPalette
            hints = QGuiApplication.styleHints()
            # Qt 6+ provides a color scheme hint
            if hasattr(hints, 'colorScheme'):
                return hints.colorScheme() == Qt.ColorScheme.Dark
            # Fallback: infer from window color lightness
            pal = QGuiApplication.palette()
            base = pal.color(QPalette.Window)
            return base.lightness() < 128
        except Exception:
            return False

    def _apply_theme_styles(self) -> None:
        """Apply theme-aware styles to overlay drawer and scrim."""
        try:
            dark = self._is_dark_mode()
            # Drawer background and border adapt to theme
            if getattr(self, 'drawer_layer', None) is not None:
                bg = 'rgba(32,32,32,0.92)' if dark else 'rgba(248,248,248,0.95)'
                border = '#555' if dark else '#ccc'
                self.drawer_layer.setStyleSheet(f"#drawer_layer {{ background-color: {bg}; border-right: 1px solid {border}; }}")
            # Scrim: slightly stronger in dark mode
            if getattr(self, 'drawer_scrim', None) is not None:
                alpha = 0.25 if dark else 0.15
                self.drawer_scrim.setStyleSheet(f"background-color: rgba(0,0,0,{alpha});")
            # Icons should adapt to theme as well
            self._apply_theme_icons()
        except Exception:
            pass

    def changeEvent(self, event):
        """React to palette/theme changes (e.g., macOS auto dark mode)."""
        try:
            if event.type() in (QEvent.PaletteChange, QEvent.ApplicationPaletteChange, QEvent.StyleChange):
                self._apply_theme_styles()
        except Exception:
            pass
        return super().changeEvent(event)

    def _apply_theme_icons(self) -> None:
        """Update button icons to ensure sufficient contrast in current theme."""
        try:
            # Drawer: regenerate hamburger icon with palette-derived color
            if getattr(self, 'drawer_toggle_btn', None) is not None:
                self.drawer_toggle_btn.setIcon(self._hamburger_icon())
            # Prev/Next: re-fetch standard icons so the style supplies theme-appropriate glyphs
            if getattr(self, 'prev_button', None) is not None:
                try:
                    self.prev_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
                except Exception:
                    pass
            if getattr(self, 'next_button', None) is not None:
                try:
                    self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
                except Exception:
                    pass
        except Exception:
            pass
        # Start persistent audio thread
        try:
            if self.audio_thread and not self.audio_thread.isRunning():
                self.audio_thread.start()
                logging.info("UI.audio: persistent audio thread started")
        except Exception:
            pass

        def _enforce_window_width_cap(self):
            """Enforce a hard maximum width after layouts settle.

            Prevents child widgets with Expanding policies from widening the
            main window beyond our desired cap.
            """
            try:
                from PySide6.QtGui import QGuiApplication
                screen = QGuiApplication.primaryScreen()
                avail = screen.availableGeometry() if screen else None
                if avail:
                    # Cap aligned with target: ~70% of screen, max 1200px
                    cap_w = max(720, min(int(avail.width() * 0.70), 1200))
                else:
                    cap_w = 840
                # Apply cap
                try:
                    self.setMaximumWidth(cap_w)
                    # Also set a fixed width to prevent Expanding children widening the window
                    self.setFixedWidth(cap_w)
                except Exception:
                    pass
                if self.width() > cap_w:
                    self.resize(cap_w, self.height())
                # Keep splitter aligned only if left panel is visible
                try:
                    if hasattr(self, 'main_splitter'):
                        sizes = self.main_splitter.sizes()
                        if sizes and sizes[0] > 0:
                            left = max(180, int(cap_w * 0.26))
                            right = max(1, cap_w - left)
                            self.main_splitter.setSizes([left, right])
                except Exception:
                    pass
                try:
                    logging.info(f"UI.window.cap: applied cap_w={cap_w}, final_w={self.size().width()}")
                except Exception:
                    pass
            except Exception:
                # Best effort only; avoid crashing UI
                pass

        def showEvent(self, event):
            try:
                super().showEvent(event)
            except Exception:
                pass
            # Enforce width immediately on show
            try:
                self._enforce_window_width_cap()
            except Exception:
                pass
            # Ensure drawer starts collapsed
            try:
                if hasattr(self, 'main_splitter'):
                    sizes = self.main_splitter.sizes()
                    total = sum(sizes) if sizes else self.width()
                    self.main_splitter.setSizes([0, max(1, total)])
                    self.drawer_toggle_btn.setToolTip(self.LABELS.get("drawer_show", "Show drawer"))
            except Exception:
                pass

        def resizeEvent(self, event):
            try:
                super().resizeEvent(event)
            except Exception:
                pass
            # Clamp width on any resize to avoid expansion (e.g., due to content policies)
            try:
                self._enforce_window_width_cap()
            except Exception:
                pass
            # Keep drawer and scrim geometry in sync on resize
            try:
                if getattr(self, 'drawer_layer', None) is not None and self.drawer_layer.isVisible():
                    self._position_drawer()
            except Exception:
                pass
        self.ui_info.connect(self._show_info)
        self.ui_warning.connect(self._show_warning)
        self.ui_error.connect(self._show_error)
        if self.fs.current_folder:
            self.update_folder_display()
            self.export_wavs_button.setEnabled(True)
            self.clear_wavs_button.setEnabled(True)
            self.import_wavs_button.setEnabled(True)
            self.join_wavs_button.setEnabled(True)
            self.open_ocenaudio_button.setEnabled(True)
            if getattr(self, 'edit_metadata_btn', None):
                self.edit_metadata_btn.setEnabled(True)
            # Populate via signal with current FS folder
            try:
                self._on_folder_changed(self.fs.current_folder)
                self._on_videos_updated(self.fs.list_videos())
            except Exception:
                self.load_video_files()
            # Do not auto-open metadata; use the button
    def _show_info(self, title, text):
        QMessageBox.information(self, title, text)
    def _show_warning(self, title, text):
        QMessageBox.warning(self, title, text)
    def _show_error(self, title, text):
        QMessageBox.critical(self, title, text)
    def _show_worker_error(self, msg):
        QMessageBox.critical(self, "Error", msg)
    def _on_join_success(self, output_file: str):
        self.ui_info.emit(self.LABELS["success"], f"{self.LABELS['wavs_joined']}\n{output_file}")
    def _on_join_error(self, msg: str):
        self.ui_error.emit(self.LABELS["error_title"], f"An error occurred while joining files:\n{msg}")
    def _on_folder_changed(self, path: str):
        try:
            if getattr(self, '_ui_ready', False):
                logging.info(f"UI._on_folder_changed: path={path}")
                self.update_folder_display()
                # Populate images directly from the active FS folder to ensure sync
                try:
                    active = self.fs.current_folder or ""
                    imgs = self.fs.list_images(active)
                    logging.info(f"UI._on_folder_changed: active={active}; images_count={len(imgs)}; sample={[os.path.basename(f) for f in imgs[:3]]}")
                    self._populate_images_list(imgs)
                except Exception as e:
                    logging.warning(f"UI._on_folder_changed: failed to list/populate images: {e}")
        except Exception:
            pass
    def _on_videos_updated(self, files: list):
        # Populate listbox and internal state from FS manager update
        try:
            try:
                logging.info(f"UI._on_videos_updated: received {len(files)} files; pending_select={self._pending_select_video_name}; last={self.last_video_name}")
            except Exception:
                pass
            self.video_files = list(files)
            if not getattr(self, '_ui_ready', False) or getattr(self, 'video_listbox', None) is None:
                return
            self.video_listbox.clear()
            basenames = [os.path.basename(vp) for vp in self.video_files]
            for name in basenames:
                item = QListWidgetItem(name)
                wav_exists = os.path.exists(self.fs.wav_path_for(name))
                item.setIcon(self._check_icon if wav_exists else self._empty_icon)
                self.video_listbox.addItem(item)
            # If there's a pending selection target, prefer that
            if self._pending_select_video_name and self._pending_select_video_name in basenames:
                try:
                    logging.info(f"UI._on_videos_updated: selecting pending {self._pending_select_video_name}")
                except Exception:
                    pass
                idx = basenames.index(self._pending_select_video_name)
                self.video_listbox.setCurrentRow(idx)
                try:
                    self.current_video = self._pending_select_video_name
                    self.last_video_name = self._pending_select_video_name
                except Exception:
                    pass
                self._pending_select_video_name = None
            elif self.last_video_name and self.last_video_name in basenames:
                try:
                    logging.info(f"UI._on_videos_updated: reselecting last {self.last_video_name}")
                except Exception:
                    pass
                idx = basenames.index(self.last_video_name)
                self.video_listbox.setCurrentRow(idx)
            elif basenames:
                try:
                    logging.info("UI._on_videos_updated: selecting first item by default")
                except Exception:
                    pass
                # Auto-select the first video on folder change
                self.video_listbox.setCurrentRow(0)
            if not self.video_files:
                QMessageBox.information(self, self.LABELS["no_videos_found"], f"{self.LABELS['no_videos_found']} {self.fs.current_folder}")
        except Exception as e:
            logging.warning(f"Failed to refresh videos from FS manager: {e}")
        self.update_media_controls()
        self.update_video_file_checks()
    def _reload_folder_and_select(self, target_name: str, retries: int = 6, delay_ms: int = 250):
        """Force a folder reload and try to select target_name after refresh. Retries with a short delay if needed."""
        try:
            try:
                logging.info(f"UI._reload_folder_and_select: target={target_name}, retries={retries}, delay={delay_ms}ms")
            except Exception:
                pass
            if not target_name:
                return
            self._pending_select_video_name = target_name
            cur = self.fs.current_folder
            if cur:
                try:
                    logging.info(f"UI._reload_folder_and_select: calling fs.set_folder({cur})")
                except Exception:
                    pass
                self.fs.set_folder(cur)
            # After a short delay, verify selection; retry if not applied yet
            def _verify_or_retry():
                try:
                    basenames = [os.path.basename(vp) for vp in self.video_files]
                    logging.info(f"UI._reload_folder_and_select.verify: have {len(basenames)} items; looking for {target_name}")
                    if target_name in basenames:
                        idx = basenames.index(target_name)
                        if getattr(self, 'video_listbox', None):
                            self.video_listbox.setCurrentRow(idx)
                        self.current_video = target_name
                        self.last_video_name = target_name
                        self.show_first_frame()
                        self.update_media_controls()
                        try:
                            self.statusBar().showMessage(self.LABELS.get("selected_converted", "Converted video selected"), 2000)
                        except Exception:
                            pass
                        return
                except Exception:
                    pass
                if retries > 0:
                    try:
                        logging.info(f"UI._reload_folder_and_select.verify: target not found yet; retrying ({retries-1} left)")
                    except Exception:
                        pass
                    QTimer.singleShot(delay_ms, lambda: self._reload_folder_and_select(target_name, retries - 1, delay_ms))
                else:
                    try:
                        logging.warning("UI._reload_folder_and_select.verify: selection failed after retries")
                    except Exception:
                        pass
                    try:
                        resp = QMessageBox.question(
                            self,
                            self.LABELS.get("selection_failed_title", "Selection failed"),
                            self.LABELS.get("selection_failed_msg", "Could not select the converted video yet. Retry?"),
                            QMessageBox.Retry | QMessageBox.Cancel,
                            QMessageBox.Retry,
                        )
                        if resp == QMessageBox.Retry:
                            self._reload_folder_and_select(target_name, retries=6, delay_ms=250)
                    except Exception:
                        pass
            QTimer.singleShot(delay_ms, _verify_or_retry)
        except Exception:
            pass
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        # Keep layout tight but ensure a small top margin
        try:
            main_layout.setSpacing(0)
            # Increase top margin to prevent overlap under titlebar
            main_layout.setContentsMargins(8, 14, 8, 6)
        except Exception:
            pass
        try:
            self._check_icon = self.style().standardIcon(QStyle.SP_DialogApplyButton)
        except Exception:
            self._check_icon = QIcon()
        try:
            placeholder = QPixmap(16, 16)
            placeholder.fill(Qt.transparent)
            self._empty_icon = QIcon(placeholder)
        except Exception:
            self._empty_icon = QIcon()
        self.language_dropdown = QComboBox()
        self.language_dropdown.addItems([LABELS_ALL[k]["language_name"] for k in LABELS_ALL])
        self.language_dropdown.setCurrentText(self.LABELS["language_name"])
        self.language_dropdown.currentTextChanged.connect(self.change_language)
        # Remove extra margins/padding in the header controls
        try:
            self.language_dropdown.setStyleSheet("margin:0px; padding:0px;")
            self.language_dropdown.setFixedHeight(28)
            # Ensure the dropdown popup list has an opaque background so
            # language names are readable even if parent widgets use
            # transparent backgrounds or custom stylesheets.
            try:
                view = self.language_dropdown.view()
                view.setStyleSheet("background-color: palette(base); color: palette(text);")
            except Exception:
                # If anything goes wrong here, we still want the app to start.
                pass
        except Exception:
            pass
        # Language dropdown will be placed in the header row next to the folder label
        # Folder label + drawer toggle row
        self.folder_display_label = QLabel(self.LABELS["no_folder_selected"])
        self.folder_display_label.setAlignment(Qt.AlignLeft)
        self.folder_display_label.setToolTip("")
        try:
            self.folder_display_label.setMargin(0)
            self.folder_display_label.setStyleSheet("margin:0px; padding:0px;")
            self.folder_display_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        except Exception:
            pass
        header_row = QHBoxLayout()
        # Drawer toggle button (top-left)
        self.drawer_toggle_btn = QToolButton()
        try:
            self.drawer_toggle_btn.setToolTip(self.LABELS.get("drawer_show", "Show drawer"))
            # Use a custom hamburger icon (three horizontal lines)
            try:
                self.drawer_toggle_btn.setIcon(self._hamburger_icon())
            except Exception:
                self.drawer_toggle_btn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMenuButton))
            self.drawer_toggle_btn.setFixedSize(28, 28)
            self.drawer_toggle_btn.setAutoRaise(True)
            self.drawer_toggle_btn.clicked.connect(self._toggle_drawer)
        except Exception:
            pass
        header_row.addWidget(self.drawer_toggle_btn)
        # Small spacing between hamburger and folder name
        try:
            header_row.addSpacing(8)
        except Exception:
            pass
        # Folder label follows the drawer button on the left
        header_row.addWidget(self.folder_display_label)

        # Push the language dropdown to the right edge on the same line
        try:
            header_row.addStretch(1)
        except Exception:
            pass
        header_row.addWidget(self.language_dropdown)
        main_layout.addLayout(header_row)
        splitter = QSplitter(Qt.Horizontal)
        try:
            splitter.setContentsMargins(0, 0, 0, 0)
        except Exception:
            pass
        self.main_splitter = splitter
        self._splitter_prev_sizes = [240, 600]
        main_layout.addWidget(splitter)
        # Build left panel content (will live inside an overlay drawer)
        left_panel = QWidget()
        self.left_panel = left_panel
        left_layout = QVBoxLayout(left_panel)
        try:
            left_layout.setContentsMargins(8, 8, 8, 8)
            left_layout.setSpacing(8)
        except Exception:
            pass
        self.select_button = QPushButton(self.LABELS["select_folder"])
        self.select_button.clicked.connect(self.select_folder)
        try:
            self.select_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.select_button.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.select_button)
        self.open_ocenaudio_button = QPushButton(self.LABELS["open_ocenaudio"])
        self.open_ocenaudio_button.clicked.connect(self.open_in_ocenaudio)
        self.open_ocenaudio_button.setEnabled(False)
        try:
            self.open_ocenaudio_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.open_ocenaudio_button.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.open_ocenaudio_button)
        self.export_wavs_button = QPushButton(self.LABELS["export_wavs"])
        self.export_wavs_button.clicked.connect(self.export_wavs)
        self.export_wavs_button.setEnabled(False)
        try:
            self.export_wavs_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.export_wavs_button.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.export_wavs_button)
        self.clear_wavs_button = QPushButton(self.LABELS["clear_wavs"])
        self.clear_wavs_button.clicked.connect(self.clear_wavs)
        self.clear_wavs_button.setEnabled(False)
        try:
            self.clear_wavs_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.clear_wavs_button.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.clear_wavs_button)
        self.import_wavs_button = QPushButton(self.LABELS["import_wavs"])
        self.import_wavs_button.clicked.connect(self.import_wavs)
        self.import_wavs_button.setEnabled(False)
        try:
            self.import_wavs_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.import_wavs_button.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.import_wavs_button)
        self.join_wavs_button = QPushButton(self.LABELS["join_wavs"])
        self.join_wavs_button.clicked.connect(self.join_all_wavs)
        self.join_wavs_button.setEnabled(False)
        try:
            self.join_wavs_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.join_wavs_button.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.join_wavs_button)
        self.video_listbox = QListWidget()
        try:
            self.video_listbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        except Exception:
            pass
        # Videos context menu and Ctrl+C to copy video file URL
        try:
            self.video_listbox.setContextMenuPolicy(Qt.CustomContextMenu)
            self.video_listbox.customContextMenuRequested.connect(self._on_videos_context_menu)
            self.copy_video_shortcut = QShortcut(QKeySequence.Copy, self.video_listbox)
            self.copy_video_shortcut.activated.connect(self._copy_current_video_to_clipboard)
        except Exception:
            pass
        self.video_listbox.currentRowChanged.connect(self.on_video_select)
        left_layout.addWidget(self.video_listbox)
        # Replace inline metadata editor with a single button
        self.edit_metadata_btn = QPushButton(self.LABELS["edit_metadata"])
        self.edit_metadata_btn.clicked.connect(self.open_metadata_dialog)
        self.edit_metadata_btn.setEnabled(False)
        try:
            self.edit_metadata_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.edit_metadata_btn.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.edit_metadata_btn)
        # Drawer overlay (appears over UI instead of resizing splitter)
        try:
            self.drawer_layer = QWidget(central_widget)
            self.drawer_layer.setVisible(False)
            self.drawer_layer.setAttribute(Qt.WA_StyledBackground, True)
            # Targeted style on the drawer container only to avoid affecting child controls
            self.drawer_layer.setObjectName("drawer_layer")
            # Initial style; will be updated by _apply_theme_styles()
            self._apply_theme_styles()
            dl = QVBoxLayout(self.drawer_layer)
            dl.setContentsMargins(8, 8, 8, 8)
            dl.setSpacing(6)
            dl.addWidget(left_panel)
            # Ensure child buttons use native style (clear any inherited QSS side-effects)
            try:
                for btn in (
                    self.select_button,
                    self.open_ocenaudio_button,
                    self.export_wavs_button,
                    self.clear_wavs_button,
                    self.import_wavs_button,
                    self.join_wavs_button,
                    self.edit_metadata_btn,
                ):
                    btn.setStyleSheet("")
                    btn.setAutoDefault(False)
            except Exception:
                pass
            # Subtle shadow for visual depth
            try:
                shadow = QGraphicsDropShadowEffect(self.drawer_layer)
                shadow.setBlurRadius(16)
                shadow.setOffset(0, 0)
                shadow.setColor(QColor(0, 0, 0, 80))
                self.drawer_layer.setGraphicsEffect(shadow)
            except Exception:
                pass
            # Background scrim to dim UI and capture clicks to close
            self.drawer_scrim = QWidget(central_widget)
            self.drawer_scrim.setVisible(False)
            self.drawer_scrim.setAttribute(Qt.WA_StyledBackground, True)
            # Initial style; will be updated by _apply_theme_styles()
            self._apply_theme_styles()
            self.drawer_scrim.installEventFilter(self)
        except Exception:
            self.drawer_layer = None
            self.drawer_scrim = None
        # Placeholder on the splitter's left, to keep API stable
        self._drawer_placeholder = QWidget()
        try:
            self._drawer_placeholder.setMinimumWidth(0)
        except Exception:
            pass
        splitter.addWidget(self._drawer_placeholder)
        right_panel = QTabWidget()
        self.right_panel = right_panel
        videos_tab = QWidget()
        videos_layout = QVBoxLayout(videos_tab)
        # Tip for fullscreen video
        self.video_fullscreen_tip = QLabel(
            self.LABELS.get(
                "video_fullscreen_tip",
                LABELS_ALL["English"]["video_fullscreen_tip"],
            )
        )
        self.video_fullscreen_tip.setStyleSheet("color: black; font-size: 13px; margin-bottom: 4px;")
        self.video_fullscreen_tip.setWordWrap(True)
        videos_layout.addWidget(self.video_fullscreen_tip)
        self.video_label = QLabel(self.LABELS["video_listbox_no_video"])
        self.video_label.setAlignment(Qt.AlignCenter)
        # More compact default size for smaller screens; allow expanding
        self.video_label.setMinimumSize(480, 360)
        # Avoid cropping: do not auto-stretch, we will scale pixmaps ourselves
        try:
            self.video_label.setScaledContents(False)
        except Exception:
            pass
        try:
            self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
        self.video_label.setStyleSheet("background-color: black; color: white; border: 1px solid #333;")
        videos_layout.addWidget(self.video_label)
        self.badge_label = QLabel(self.video_label)
        self.badge_label.setText("✓")
        self.badge_label.setAlignment(Qt.AlignCenter)
        self.badge_label.setFixedSize(22, 22)
        self.badge_label.setStyleSheet("background-color: #2ecc71; color: white; border-radius: 11px;")
        self.badge_label.setVisible(False)
        # Note: format badge removed per UX decision.
        self.video_label.installEventFilter(self)
        video_controls_layout = QHBoxLayout()
        self.prev_button = QToolButton()
        try:
            self.prev_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        except Exception:
            self.prev_button.setText("◀")
        self.prev_button.setToolTip(self.LABELS.get("prev_video_tip", "Previous video"))
        self.prev_button.clicked.connect(self.go_prev)
        video_controls_layout.addWidget(self.prev_button)
        self.play_video_button = QPushButton(self.LABELS["play_video"])
        self.play_video_button.clicked.connect(self.play_video)
        self.play_video_button.setEnabled(False)
        video_controls_layout.addWidget(self.play_video_button)
        self.stop_video_button = QPushButton(self.LABELS["stop_video"])
        self.stop_video_button.clicked.connect(self.stop_video)
        self.stop_video_button.setEnabled(False)
        video_controls_layout.addWidget(self.stop_video_button)
        # Convert to MP4 button (in-place)
        self.convert_mp4_button = QPushButton(self.LABELS.get("convert_to_mp4", "Convert to MP4"))
        self.convert_mp4_button.clicked.connect(self._convert_current_video_in_place)
        self.convert_mp4_button.setEnabled(False)
        video_controls_layout.addWidget(self.convert_mp4_button)
        self.next_button = QToolButton()
        try:
            self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        except Exception:
            self.next_button.setText("▶")
        self.next_button.setToolTip(self.LABELS.get("next_video_tip", "Next video"))
        self.next_button.clicked.connect(self.go_next)
        video_controls_layout.addWidget(self.next_button)
        videos_layout.addLayout(video_controls_layout)
        audio_controls_layout = QHBoxLayout()
        try:
            audio_controls_layout.setSpacing(8)
        except Exception:
            pass
        audio_controls_layout.addStretch(1)
        self.play_audio_button = QPushButton(self.LABELS["play_audio"])
        self.play_audio_button.clicked.connect(self.play_audio)
        self.play_audio_button.setEnabled(False)
        audio_controls_layout.addWidget(self.play_audio_button)
        self.stop_audio_button = QPushButton(self.LABELS["stop_audio"])
        self.stop_audio_button.clicked.connect(self.stop_audio)
        self.stop_audio_button.setEnabled(False)
        audio_controls_layout.addWidget(self.stop_audio_button)
        self.record_button = QPushButton(self.LABELS["record_audio"])
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setEnabled(False)
        audio_controls_layout.addWidget(self.record_button)
        # Add audio dropdown (From file / Paste from clipboard)
        self.add_audio_button = QToolButton()
        self.add_audio_button.setText(self.LABELS.get("add_existing_audio", "Add audio…"))
        try:
            self.add_audio_button.setPopupMode(QToolButton.InstantPopup)
        except Exception:
            pass
        self.add_audio_button.setEnabled(False)
        add_menu = QMenu(self)
        act_file = QAction(self.LABELS.get("add_audio_from_file", "From file…"), self)
        act_file.triggered.connect(self._handle_add_existing_audio_video)
        add_menu.addAction(act_file)
        act_clip = QAction(self.LABELS.get("add_audio_paste_clipboard", "Paste from clipboard"), self)
        act_clip.triggered.connect(self._handle_paste_audio_video)
        add_menu.addAction(act_clip)
        self.add_audio_button.setMenu(add_menu)
        audio_controls_layout.addWidget(self.add_audio_button)
        self.recording_status_label = QLabel("")
        self.recording_status_label.setStyleSheet("color: red; font-weight: bold;")
        audio_controls_layout.addWidget(self.recording_status_label)
        audio_controls_layout.addStretch(1)
        videos_layout.addLayout(audio_controls_layout)
        videos_layout.addStretch()
        right_panel.addTab(videos_tab, self.LABELS["videos_tab_title"])
        # Images tab
        images_tab = QWidget()
        images_layout = QVBoxLayout(images_tab)
        try:
            images_layout.setContentsMargins(0, 0, 0, 0)
            images_layout.setSpacing(6)
        except Exception:
            pass
        try:
            logging.info("UI.init_ui: creating Images tab")
        except Exception:
            pass
        # Banner: two columns, left = preview, right = controls+tip
        image_banner = QHBoxLayout()
        try:
            image_banner.setSpacing(8)
            image_banner.setContentsMargins(0, 0, 0, 0)
        except Exception:
            pass
        self.image_thumb = QLabel()
        try:
            self.image_thumb.setFixedSize(96, 72)
            self.image_thumb.setStyleSheet("background-color: black; color: white; border: 1px solid #333;")
        except Exception:
            pass
        image_banner.addWidget(self.image_thumb)
        # Right cell: controls and tip stacked vertically
        # (QVBoxLayout, QHBoxLayout, QCheckBox are already imported at the top)
        controls_and_tip = QVBoxLayout()
        controls_row = QHBoxLayout()
        # Always show Show filenames toggle above controls
        self.show_image_labels = False
        self.image_labels_toggle = QCheckBox(
            self.LABELS.get(
                "image_show_filenames",
                LABELS_ALL["English"]["image_show_filenames"],
            )
        )
        self.image_labels_toggle.setChecked(self.show_image_labels)
        self.image_labels_toggle.toggled.connect(self._toggle_image_labels)
        controls_and_tip.addWidget(self.image_labels_toggle)
        # Controls row (audio/record buttons)
        self.play_image_audio_button = QPushButton(self.LABELS.get("play_audio", "Play Audio"))
        self.play_image_audio_button.clicked.connect(self._handle_play_image_audio)
        self.play_image_audio_button.setEnabled(False)
        controls_row.addWidget(self.play_image_audio_button)
        self.stop_image_audio_button = QPushButton(self.LABELS.get("stop_audio", "Stop Audio"))
        self.stop_image_audio_button.clicked.connect(self._handle_stop_image_audio)
        self.stop_image_audio_button.setEnabled(False)
        controls_row.addWidget(self.stop_image_audio_button)
        self.record_image_button = QPushButton(self.LABELS.get("record_audio", "Record Audio"))
        self.record_image_button.clicked.connect(self._handle_record_image)
        self.record_image_button.setEnabled(False)
        controls_row.addWidget(self.record_image_button)
        # Add Image dropdown (From file / Paste from clipboard)
        self.add_image_button = QToolButton()
        self.add_image_button.setText(self.LABELS.get("add_image", "Add image…"))
        try:
            self.add_image_button.setPopupMode(QToolButton.InstantPopup)
        except Exception:
            pass
        self.add_image_button.setEnabled(True)
        add_img_src_menu = QMenu(self)
        act_img_src_file = QAction(self.LABELS.get("add_image_from_file", "From file…"), self)
        act_img_src_file.triggered.connect(self._handle_add_existing_image)
        add_img_src_menu.addAction(act_img_src_file)
        act_img_src_clip = QAction(self.LABELS.get("add_image_paste_clipboard", "Paste from clipboard"), self)
        act_img_src_clip.triggered.connect(self._handle_paste_image)
        add_img_src_menu.addAction(act_img_src_clip)
        self.add_image_button.setMenu(add_img_src_menu)
        controls_row.addWidget(self.add_image_button)
        # Add audio dropdown (From file / Paste from clipboard)
        self.add_image_audio_button = QToolButton()
        self.add_image_audio_button.setText(self.LABELS.get("add_existing_audio", "Add audio…"))
        try:
            self.add_image_audio_button.setPopupMode(QToolButton.InstantPopup)
        except Exception:
            pass
        self.add_image_audio_button.setEnabled(False)
        add_img_menu = QMenu(self)
        act_img_file = QAction(self.LABELS.get("add_audio_from_file", "From file…"), self)
        act_img_file.triggered.connect(self._handle_add_existing_audio_image)
        add_img_menu.addAction(act_img_file)
        act_img_clip = QAction(self.LABELS.get("add_audio_paste_clipboard", "Paste from clipboard"), self)
        act_img_clip.triggered.connect(self._handle_paste_audio_image)
        add_img_menu.addAction(act_img_clip)
        self.add_image_audio_button.setMenu(add_img_menu)
        controls_row.addWidget(self.add_image_audio_button)
        self.stop_image_record_button = QPushButton(self.LABELS.get("stop_recording", "Stop Recording"))
        self.stop_image_record_button.clicked.connect(self._handle_stop_image_record)
        self.stop_image_record_button.setEnabled(False)
        controls_row.addWidget(self.stop_image_record_button)
        controls_row.addStretch(1)
        controls_and_tip.addLayout(controls_row)
        # Tip below controls
        self.image_fullscreen_tip = QLabel(
            self.LABELS.get(
                "image_fullscreen_tip",
                LABELS_ALL["English"]["image_fullscreen_tip"],
            )
        )
        self.image_fullscreen_tip.setStyleSheet("color: black; font-size: 13px; margin: 4px 0 8px 0;")
        self.image_fullscreen_tip.setWordWrap(True)
        controls_and_tip.addWidget(self.image_fullscreen_tip)
        image_banner.addLayout(controls_and_tip)
        images_layout.addLayout(image_banner)
        # Thumbnail size slider
        try:
            thumb_row = QHBoxLayout()
            thumb_row.addWidget(QLabel("Thumb Size:"))
            self.images_thumb_slider = QSlider(Qt.Horizontal)
            self.images_thumb_slider.setRange(60, 180)  # percent
            self.images_thumb_slider.setValue(100)
            self.images_thumb_slider.setMaximumWidth(140)
            thumb_row.addWidget(self.images_thumb_slider)
            thumb_row.addStretch(1)
            images_layout.addLayout(thumb_row)
            self.images_thumb_scale = 1.0
            self.images_thumb_slider.valueChanged.connect(self._on_images_thumb_scale_changed)
        except Exception:
            self.images_thumb_scale = 1.0
        # Grid of thumbnails
        self.images_list = QListWidget()
        try:
            self.images_list.setViewMode(QListView.IconMode)
            # Ensure Adjust mode is set from QListView enum
            self.images_list.setResizeMode(QListView.Adjust)
            # Fill rows left-to-right to avoid a single tall column
            self.images_list.setFlow(QListView.LeftToRight)
            # Initial placeholder sizes; smaller defaults for compact UI (recomputed adaptively)
            self.images_list.setIconSize(QSize(240, 180))
            self.images_list.setGridSize(QSize(260, 190))
            self.images_list.setSpacing(6)
            self.images_list.setMovement(QListView.Static)
            self.images_list.setWrapping(True)
            # Let items compute size per grid cell for better wrapping
            self.images_list.setUniformItemSizes(False)
            self.images_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.images_list.setSelectionMode(QListWidget.SingleSelection)
            self.images_list.setSelectionBehavior(QListWidget.SelectItems)
            logging.info("UI.init_ui: images_list ready (IconMode)")
        except Exception:
            pass
        # Context menu and Ctrl+C to copy image to clipboard
        try:
            self.images_list.setContextMenuPolicy(Qt.CustomContextMenu)
            self.images_list.customContextMenuRequested.connect(self._on_images_context_menu)
            self.copy_image_shortcut = QShortcut(QKeySequence.Copy, self.images_list)
            self.copy_image_shortcut.activated.connect(self._copy_current_image_to_clipboard)
        except Exception:
            pass
        # Install custom delegate to draw green border and check overlay for recorded images
        try:
            self.images_list.setItemDelegate(ImageGridDelegate(self.fs))
        except Exception:
            pass
        # Selection syncing: rely on current-item changes to avoid duplicate triggers
        try:
            self.images_list.currentItemChanged.connect(lambda *args: self._handle_image_selection())
        except Exception:
            pass
        self.images_list.itemDoubleClicked.connect(self._handle_open_fullscreen_image)
        # Warm the image cache for items that become visible as the user
        # scrolls the grid, so fullscreen opens don't pay a cold-start
        # decoding cost.
        try:
            vsb = self.images_list.verticalScrollBar()
            if vsb is not None:
                vsb.valueChanged.connect(lambda *_: self._preload_visible_images())
        except Exception:
            pass
        images_layout.addWidget(self.images_list)
        right_panel.addTab(images_tab, self.LABELS.get("images_tab_title", "Images"))
        
        # Review tab
        try:
            from vat import VERSION
            app_version = VERSION
        except Exception:
            app_version = "2.0.3"
        
        self.review_tab = ReviewTab(self.fs, app_version, self, labels=self.LABELS)
        right_panel.addTab(self.review_tab, self.LABELS.get("review_tab_title", "Review"))
        
        splitter.addWidget(right_panel)
        # Start with drawer collapsed; remember previous sizes for temporary expand
        splitter.setSizes([0, 600])
        self._splitter_prev_sizes = [240, 600]
        # Connect tab change to enable/disable video_listbox
        def _on_tab_changed(idx):
            # 0 = Videos, 1 = Images, 2 = Review (assume order)
            try:
                self.video_listbox.setEnabled(idx == 0)
            except Exception:
                pass
            # Keep drawer overlay position in sync
            try:
                self._position_drawer()
            except Exception:
                pass
        self.right_panel.currentChanged.connect(_on_tab_changed)
        # Set initial state
        _on_tab_changed(self.right_panel.currentIndex())
        # Keep images grid sizing in sync and defer initial compute
        try:
            self.images_list.installEventFilter(self)
            QTimer.singleShot(0, self._recompute_image_grid_sizes)
        except Exception:
            pass
        # Compute adaptive two-column sizing after layout
        try:
            self._recompute_image_grid_sizes()
        except Exception:
            pass
        # Mark UI as ready for FS signal handlers
        self._ui_ready = True
        # Populate images initially if a folder is already set
        if self.fs.current_folder:
            try:
                imgs = self.fs.list_images()
                self._on_images_updated(self.fs.current_folder, imgs)
            except Exception:
                pass
            # Also populate the videos list to avoid empty state on startup
            try:
                vids = self.fs.list_videos()
                self._on_videos_updated(vids)
            except Exception:
                try:
                    self.load_video_files()
                except Exception:
                    pass
        # Show a short welcome/best-practices message once on startup
        try:
            QTimer.singleShot(0, self._show_welcome_dialog)
        except Exception:
            pass
        # After the first population/layout pass, warm the cache for the
        # thumbnails that are actually visible.
        try:
            QTimer.singleShot(0, self._preload_visible_images)
        except Exception:
            pass

        # Collapse drawer on outside click
        try:
            central_widget.installEventFilter(self)
            self._central_widget = central_widget
        except Exception:
            pass
    def change_language(self, selected_name):
        for key, labels in LABELS_ALL.items():
            if labels["language_name"] == selected_name:
                self.language = key
                self.LABELS = LABELS_ALL[self.language]
                break
        self.setWindowTitle(self.LABELS["app_title"])
        # Update tab titles
        try:
            if getattr(self, 'right_panel', None) is not None:
                self.right_panel.setTabText(0, self.LABELS.get("videos_tab_title", "Videos"))
                self.right_panel.setTabText(1, self.LABELS.get("images_tab_title", "Images"))
                self.right_panel.setTabText(2, self.LABELS.get("review_tab_title", "Review"))
        except Exception:
            pass
        # Retranslate Review tab
        try:
            if getattr(self, 'review_tab', None) is not None:
                self.review_tab.retranslate(self.LABELS)
        except Exception:
            pass
        # Refresh other UI texts
        self.refresh_ui_texts()
        # Update dropdown/menu labels where created earlier
        try:
            if getattr(self, 'add_audio_button', None) is not None and self.add_audio_button.menu():
                self.add_audio_button.setText(self.LABELS.get("add_existing_audio", "Add audio…"))
                acts = self.add_audio_button.menu().actions()
                if len(acts) >= 2:
                    acts[0].setText(self.LABELS.get("add_audio_from_file", "From file…"))
                    acts[1].setText(self.LABELS.get("add_audio_paste_clipboard", "Paste from clipboard"))
        except Exception:
            pass
        self.save_settings()

    def _toggle_drawer(self):
        """Toggle the left drawer overlay visibility."""
        try:
            if getattr(self, 'drawer_layer', None) is None:
                return
            vis = self.drawer_layer.isVisible()
            if vis:
                self.drawer_layer.hide()
                try:
                    if getattr(self, 'drawer_scrim', None) is not None:
                        self.drawer_scrim.hide()
                except Exception:
                    pass
                try:
                    self.drawer_toggle_btn.setToolTip(self.LABELS.get("drawer_show", "Show drawer"))
                except Exception:
                    pass
            else:
                self._position_drawer()
                # Show scrim behind drawer
                try:
                    if getattr(self, 'drawer_scrim', None) is not None:
                        self.drawer_scrim.show()
                        self.drawer_scrim.raise_()
                except Exception:
                    pass
                self.drawer_layer.show()
                self.drawer_layer.raise_()
                try:
                    self.drawer_toggle_btn.setToolTip(self.LABELS.get("drawer_hide", "Hide drawer"))
                except Exception:
                    pass
        except Exception:
            pass

    def _hamburger_icon(self):
        """Create a simple hamburger icon (three stacked lines)."""
        try:
            size = 24
            pm = QPixmap(size, size)
            pm.fill(Qt.transparent)
            from PySide6.QtGui import QPainter
            painter = QPainter(pm)
            try:
                painter.setRenderHint(QPainter.Antialiasing, True)
                # Derive stroke color from current palette for good contrast
                from PySide6.QtGui import QGuiApplication, QPalette
                pal = QGuiApplication.palette()
                stroke = pal.color(QPalette.ButtonText)
                pen = QPen(stroke)
                pen.setWidth(2)
                painter.setPen(pen)
                # Draw three lines
                y_positions = [6, 12, 18]
                for y in y_positions:
                    painter.drawLine(5, y, size - 5, y)
            finally:
                painter.end()
            return QIcon(pm)
        except Exception:
            return QIcon()

    def _position_drawer(self):
        """Position the drawer overlay anchored to the left inside the central widget."""
        try:
            if getattr(self, 'drawer_layer', None) is None:
                return
            cw = getattr(self, '_central_widget', None)
            if cw is None:
                return
            # Default drawer width: proportional to window, with sensible bounds
            dw = min(max(400, int(cw.width() * 0.40)), 600)
            # Compute top offset based on header row metrics
            try:
                # Use the lower edge of the highest header element
                lbl = getattr(self, 'folder_display_label', None)
                dd = getattr(self, 'language_dropdown', None)
                btn = getattr(self, 'drawer_toggle_btn', None)
                candidates = []
                for w in (lbl, dd, btn):
                    if w is not None:
                        p = w.mapTo(cw, QPoint(0, 0))
                        candidates.append(p.y() + w.height())
                header_bottom = max(candidates) if candidates else 50
                top_margin = header_bottom + 6
            except Exception:
                top_margin = 50
            h = cw.height() - top_margin
            h = max(200, h)
            self.drawer_layer.setGeometry(8, top_margin, dw, h)
            # Keep scrim covering the central widget
            try:
                if getattr(self, 'drawer_scrim', None) is not None:
                    # Leave header/hamburger clickable: scrim starts below header
                    self.drawer_scrim.setGeometry(0, top_margin, cw.width(), cw.height() - top_margin)
            except Exception:
                pass
        except Exception:
            pass

    def _on_images_thumb_scale_changed(self, value: int):
        try:
            self.images_thumb_scale = max(0.5, min(1.8, value / 100.0))
            self._recompute_image_grid_sizes()
            self.save_settings()
        except Exception:
            pass

    def eventFilter(self, obj, event):
        # Collapse drawer when clicking outside the drawer overlay
        try:
            target_central = getattr(self, '_central_widget', None)
            target_scrim = getattr(self, 'drawer_scrim', None)
            if obj is target_central or obj is target_scrim:
                if event.type() == QEvent.MouseButtonPress:
                    dl = getattr(self, 'drawer_layer', None)
                    if dl is not None and dl.isVisible():
                        # Map drawer geometry to the coordinate space of the clicked widget
                        top_left_in_obj = dl.mapTo(obj, QPoint(0, 0))
                        rect = QRect(top_left_in_obj, dl.size())
                        pos = event.position() if hasattr(event, 'position') else event.pos()
                        p = QPoint(int(pos.x()), int(pos.y()))
                        if not rect.contains(p):
                            dl.hide()
                            try:
                                if target_scrim is not None:
                                    target_scrim.hide()
                            except Exception:
                                pass
                            try:
                                self.drawer_toggle_btn.setToolTip("Show drawer")
                            except Exception:
                                pass
                            return True
        except Exception:
            pass
        # Keep video badges anchored on video label show/resize
        try:
            if obj is getattr(self, 'video_label', None):
                et = event.type()
                if et in (QEvent.Show, QEvent.Resize, QEvent.Paint, QEvent.LayoutRequest):
                    # Reposition synchronously during paint/resize/show to avoid visible drift
                    try:
                        self._position_badge()
                    except Exception:
                        pass
                    # Format badge removed; no additional positioning needed
        except Exception:
            pass
        try:
            return super().eventFilter(obj, event)
        except Exception:
            return False
    def refresh_ui_texts(self):
        self.select_button.setText(self.LABELS["select_folder"])
        self.open_ocenaudio_button.setText(self.LABELS["open_ocenaudio"])
        self.export_wavs_button.setText(self.LABELS["export_wavs"])
        self.clear_wavs_button.setText(self.LABELS["clear_wavs"])
        self.import_wavs_button.setText(self.LABELS["import_wavs"])
        self.join_wavs_button.setText(self.LABELS["join_wavs"])
        self.play_video_button.setText(self.LABELS["play_video"])
        self.stop_video_button.setText(self.LABELS["stop_video"])
        self.play_audio_button.setText(self.LABELS["play_audio"])
        self.stop_audio_button.setText(self.LABELS["stop_audio"])
        self.record_button.setText(self.LABELS["record_audio"] if not self.is_recording else self.LABELS["stop_recording"])
        if getattr(self, 'edit_metadata_btn', None):
            self.edit_metadata_btn.setText(self.LABELS["edit_metadata"])
        if not self.current_video:
            self.video_label.setText(self.LABELS["video_listbox_no_video"])
        # Localized tips and checkbox labels
        try:
            if getattr(self, "video_fullscreen_tip", None) is not None:
                self.video_fullscreen_tip.setText(
                    self.LABELS.get(
                        "video_fullscreen_tip",
                        LABELS_ALL["English"]["video_fullscreen_tip"],
                    )
                )
        except Exception:
            pass
        try:
            if getattr(self, "image_fullscreen_tip", None) is not None:
                self.image_fullscreen_tip.setText(
                    self.LABELS.get(
                        "image_fullscreen_tip",
                        LABELS_ALL["English"]["image_fullscreen_tip"],
                    )
                )
        except Exception:
            pass
        try:
            if getattr(self, "image_labels_toggle", None) is not None:
                self.image_labels_toggle.setText(
                    self.LABELS.get(
                        "image_show_filenames",
                        LABELS_ALL["English"]["image_show_filenames"],
                    )
                )
        except Exception:
            pass
        self.update_folder_display()
    def update_folder_display(self):
        if getattr(self, 'folder_display_label', None) is None:
            return
        folder = self.fs.current_folder
        if folder:
            base = os.path.basename(folder.rstrip(os.sep)) or folder
            self.folder_display_label.setText(base)
            self.folder_display_label.setToolTip(folder)
        else:
            self.folder_display_label.setText(self.LABELS["no_folder_selected"])
            self.folder_display_label.setToolTip("")
    def load_settings(self):
        try:
            settings = None
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
            if isinstance(settings, dict):
                self.ocenaudio_path = settings.get('ocenaudio_path')
                saved_lang = settings.get('language')
                if saved_lang and saved_lang in LABELS_ALL:
                    # Respect explicit user choice
                    self.language = saved_lang
                    self.LABELS = LABELS_ALL[self.language]
                last_folder = settings.get('last_folder')
                if last_folder and os.path.isdir(last_folder):
                    try:
                        self.fs.set_folder(last_folder)
                    except Exception:
                        pass
                last_video = settings.get('last_video')
                if last_video:
                    self.last_video_name = last_video
                # Persistent fullscreen zoom
                zoom = settings.get('fullscreen_zoom')
                if isinstance(zoom, (int, float)) and zoom > 0:
                    self.fullscreen_zoom = float(zoom)
                
                # Load review settings if review tab exists
                if hasattr(self, 'review_tab') and settings:
                    try:
                        self.review_tab.state.load_from_json(settings)
                        self.review_tab._sync_ui_from_state()
                    except Exception:
                        pass
                # Images thumbnail scale (persisted)
                try:
                    img_scale = settings.get('images_thumb_scale')
                    if isinstance(img_scale, (int, float)):
                        self.images_thumb_scale = max(0.5, min(1.8, float(img_scale)))
                        if hasattr(self, 'images_thumb_slider'):
                            self.images_thumb_slider.setValue(int(self.images_thumb_scale * 100))
                        self._recompute_image_grid_sizes()
                except Exception:
                    pass
            else:
                # No saved language preference: try to match system UI language
                try:
                    locale = QLocale.system()
                    # Prefer explicit language codes; fall back to language name
                    lang_name = locale.languageToString(locale.language())
                    lang_name = (lang_name or "").strip()
                    candidates = []
                    if lang_name:
                        candidates.append(lang_name)
                    ui_name = locale.name()  # e.g. "en_US"
                    if ui_name:
                        candidates.append(ui_name)
                    # Map common Qt language names / codes to our LABELS_ALL keys
                    def _match_language():
                        # Direct match on language_name
                        for key, labels in LABELS_ALL.items():
                            if labels.get("language_name") in candidates:
                                return key
                        # Simple heuristics for common locales
                        for c in candidates:
                            c_lower = c.lower()
                            if c_lower.startswith("en"):
                                return "English"
                            if c_lower.startswith("id") or "bahasa" in c_lower:
                                return "Bahasa Indonesia"
                            if c_lower.startswith("ko"):
                                return "한국어"
                            if c_lower.startswith("nl"):
                                return "Nederlands"
                            if c_lower.startswith("pt"):
                                return "Português (Brasil)"
                            if c_lower.startswith("es"):
                                return "Español (Latinoamérica)"
                            if c_lower.startswith("af"):
                                return "Afrikaans"
                        return None
                    matched = _match_language()
                    if matched and matched in LABELS_ALL:
                        self.language = matched
                        self.LABELS = LABELS_ALL[self.language]
                except Exception:
                    # On any failure, keep English defaults
                    pass
        except Exception as e:
            logging.warning(f"Failed to load settings: {e}")
    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            settings = {
                'ocenaudio_path': self.ocenaudio_path,
                'language': self.language,
                'last_folder': self.fs.current_folder,
                'last_video': self.current_video,
                # Persist the last used fullscreen zoom if set
                'fullscreen_zoom': self.fullscreen_zoom if isinstance(self.fullscreen_zoom, (int, float)) else None,
                'images_thumb_scale': getattr(self, 'images_thumb_scale', 1.0),
            }
            
            # Save review settings if review tab exists
            if hasattr(self, 'review_tab'):
                try:
                    self.review_tab._sync_state_from_ui()
                    settings = self.review_tab.state.save_to_json(settings)
                except Exception:
                    pass
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2, sort_keys=True)
        except Exception as e:
            logging.warning(f"Failed to save settings: {e}")
    def select_folder(self):
        initial_dir = self.fs.current_folder or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, self.LABELS["select_folder_dialog"], initial_dir)
        if folder:
            # Set via FS manager for unified state and signal refresh
            if not self.fs.set_folder(folder):
                QMessageBox.critical(self, self.LABELS["error_title"], self.LABELS["permission_denied_title"])
                return
            try:
                errors = self.fs.cleanup_hidden_files()
                if errors:
                    QMessageBox.warning(self, self.LABELS["cleanup_errors_title"], "Some hidden files could not be deleted:\n" + "\n".join(errors))
            except Exception:
                pass
            self.export_wavs_button.setEnabled(True)
            self.clear_wavs_button.setEnabled(True)
            self.import_wavs_button.setEnabled(True)
            self.join_wavs_button.setEnabled(True)
            self.open_ocenaudio_button.setEnabled(True)
            if getattr(self, 'edit_metadata_btn', None):
                self.edit_metadata_btn.setEnabled(True)
            self.save_settings()
            # Rely on FS signals (_on_folder_changed -> list_images -> imagesUpdated)
            try:
                logging.info(f"UI.select_folder: path={folder}")
            except Exception:
                pass
            # Populate immediately to prevent transient empty state
            try:
                self._on_folder_changed(folder)
            except Exception:
                pass
    def load_video_files(self):
        # Manual refresh using FS manager (in case signals are not available)
        self.video_listbox.clear()
        self.video_files = []
        if not self.fs.current_folder:
            QMessageBox.information(self, self.LABELS["no_folder_selected"], self.LABELS["no_folder_selected"])
            return
        try:
            self.video_files = self.fs.list_videos()
            self.video_files.sort()
            basenames = [os.path.basename(vp) for vp in self.video_files]
            for name in basenames:
                item = QListWidgetItem(name)
                wav_exists = os.path.exists(self.fs.wav_path_for(name))
                item.setIcon(self._check_icon if wav_exists else self._empty_icon)
                self.video_listbox.addItem(item)
            if self.last_video_name and self.last_video_name in basenames:
                idx = basenames.index(self.last_video_name)
                self.video_listbox.setCurrentRow(idx)
            elif basenames:
                # Auto-select first video to ensure player loads
                self.video_listbox.setCurrentRow(0)
            if not self.video_files:
                QMessageBox.information(self, self.LABELS["no_videos_found"], f"{self.LABELS['no_videos_found']} {self.fs.current_folder}")
        except FolderPermissionError:
            QMessageBox.critical(self, self.LABELS["permission_denied_title"], f"You do not have permission to access the folder: {self.fs.current_folder}")
        except FolderNotFoundError:
            QMessageBox.critical(self, self.LABELS["folder_not_found_title"], f"The selected folder no longer exists: {self.fs.current_folder}")
        except FolderAccessError as e:
            QMessageBox.critical(self, self.LABELS["unexpected_error_title"], f"An unexpected error occurred: {e}")
        except Exception as e:
            QMessageBox.critical(self, self.LABELS["unexpected_error_title"], f"An unexpected error occurred: {e}")
        if not self.video_files:
            self.current_video = None
        self.update_media_controls()
        self.update_video_file_checks()
    def open_metadata_dialog(self):
        if not self.fs.current_folder:
            return
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
        except Exception:
            QMessageBox.critical(self, self.LABELS["error_title"], "Unable to open metadata editor.")
            return
        default_content = (
            "name: \n"
            "date: \n"
            "location: \n"
            "researcher: \n"
            "speaker: \n"
            "permissions for use given by speaker: \n"
        )
        try:
            content = self.fs.ensure_and_read_metadata(self.fs.current_folder, default_content)
        except FolderAccessError as e:
            QMessageBox.critical(self, self.LABELS["error_title"], f"Failed to load metadata: {e}")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(self.LABELS["edit_metadata"])
        layout = QVBoxLayout(dlg)
        editor = QTextEdit(dlg)
        editor.setPlainText(content)
        layout.addWidget(editor)
        btns = QHBoxLayout()
        save_btn = QPushButton(self.LABELS["save_metadata"], dlg)
        cancel_btn = QPushButton("Cancel", dlg)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        def _save_and_close():
            try:
                self.fs.write_metadata(editor.toPlainText())
                QMessageBox.information(dlg, self.LABELS["saved"], self.LABELS["metadata_saved"])
                dlg.accept()
            except Exception as e:
                QMessageBox.critical(dlg, self.LABELS["error_title"], f"Failed to save metadata: {e}")
        save_btn.clicked.connect(_save_and_close)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.resize(600, 400)
        dlg.exec()
    def on_video_select(self, current_row):
        if current_row < 0:
            return
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
                self.update_recording_indicator()
        except Exception:
            pass
        self.current_video = self.video_listbox.item(current_row).text()
        self.last_video_name = self.current_video
        self.save_settings()
        self.update_media_controls()
        self.show_first_frame()
        try:
            self._position_badge()
        except Exception:
            pass
    def _resolve_current_video_path(self) -> str:
        """Return full path for `self.current_video` by matching against `self.video_files`.
        Fallback to FS join if not found.
        """
        try:
            if self.current_video:
                for vp in self.video_files:
                    if os.path.basename(vp) == self.current_video:
                        return vp
                if self.fs.current_folder:
                    return os.path.join(self.fs.current_folder, self.current_video)
        except Exception:
            pass
        return ""
    def show_first_frame(self):
        if not self.current_video:
            self.video_label.setText(self.LABELS["video_listbox_no_video"])
            return
        video_path = self._resolve_current_video_path()
        if not (video_path and os.path.exists(video_path)):
            logging.warning(f"Cannot open video (path missing or inaccessible): {video_path}")
            self.video_label.setText("Loading preview…")
            return
        cap = None
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logging.warning(f"Cannot open video (cv2 open failed): {video_path}")
                self.video_label.setText("Loading preview…")
                return
            ret, frame = cap.read()
            if not ret:
                logging.warning(f"Cannot open video (first frame read failed): {video_path}")
                self.video_label.setText("Loading preview…")
                return
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(qt_image)
            # Scale pixmap to fit the label while preserving aspect ratio
            try:
                target = self.video_label.contentsRect().size()
                if target.width() > 0 and target.height() > 0:
                    pixmap = pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            except Exception:
                pass
            self.video_label.setPixmap(pixmap)
            try:
                self._position_badge()
            except Exception:
                pass
            # Ensure format badge is shown/hidden correctly after geometry is ready
            # Format badge removed
        except Exception as e:
            logging.error(f"Failed to load first frame for {video_path}: {e}")
            # Silent UI update; avoid popup on auto-selection
            self.video_label.setText("Loading preview…")
        finally:
            if cap is not None:
                cap.release()
    def update_media_controls(self):
        if self.current_video:
            self.play_video_button.setEnabled(True)
            self.stop_video_button.setEnabled(True)
            # Enable Convert to MP4 only when current selection is not already MP4
            if getattr(self, 'convert_mp4_button', None):
                vp_for_convert = self._resolve_current_video_path()
                ext_for_convert = os.path.splitext(vp_for_convert)[1].lower() if vp_for_convert else ""
                self.convert_mp4_button.setEnabled(bool(vp_for_convert) and ext_for_convert != ".mp4")
            self.record_button.setEnabled(True)
            self.record_button.setText(self.LABELS["record_audio"] if not self.is_recording else self.LABELS["stop_recording"])
            self.update_recording_indicator()
            # Enable import button when a video is selected and not recording
            if getattr(self, 'add_audio_button', None):
                self.add_audio_button.setEnabled(not self.is_recording)
            wav_path = self.fs.wav_path_for(self.current_video)
            if os.path.exists(wav_path):
                # Disable Play while audio is actively playing
                self.play_audio_button.setEnabled(not self.is_playing_audio)
                self.stop_audio_button.setEnabled(True)
                self.video_label.setStyleSheet("background-color: black; color: white; border: 3px solid #2ecc71;")
                if getattr(self, 'badge_label', None):
                    try:
                        self._position_badge()
                    except Exception:
                        pass
                    self.badge_label.setVisible(True)
            else:
                self.play_audio_button.setEnabled(False)
                self.stop_audio_button.setEnabled(False)
                self.video_label.setStyleSheet("background-color: black; color: white; border: 1px solid #333;")
                if getattr(self, 'badge_label', None):
                    self.badge_label.setVisible(False)
            # Format badge removed
        else:
            self.video_label.setText(self.LABELS["video_listbox_no_video"])
            self.play_video_button.setEnabled(False)
            self.stop_video_button.setEnabled(False)
            if getattr(self, 'convert_mp4_button', None):
                self.convert_mp4_button.setEnabled(False)
            self.play_audio_button.setEnabled(False)
            self.stop_audio_button.setEnabled(False)
            self.record_button.setEnabled(False)
            self.record_button.setText(self.LABELS["record_audio"])
            if getattr(self, 'add_audio_button', None):
                self.add_audio_button.setEnabled(False)
            self.update_recording_indicator()
            self.video_label.setStyleSheet("background-color: black; color: white; border: 1px solid #333;")
            if getattr(self, 'badge_label', None):
                self.badge_label.setVisible(False)
            # Format badge removed
        self.update_video_file_checks()
    def update_recording_indicator(self):
        if getattr(self, 'recording_status_label', None) is None:
            return
        if self.is_recording:
            self.recording_status_label.setText(self.LABELS.get("recording_indicator", "● Recording"))
        else:
            self.recording_status_label.setText("")
    def play_video(self):
        if not self.current_video:
            return
        self.stop_video()
        video_path = self._resolve_current_video_path()
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
            QMessageBox.critical(self, self.LABELS["error_title"], self.LABELS["cannot_open_video"])
            return
        self.playing_video = True
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if fps is None:
            fps = 0.0
        fps_val = float(fps)
        fps_valid = isinstance(fps, (float, int)) and not math.isnan(fps_val) and fps_val > 0.0 and not math.isinf(fps_val)
        if fps_valid:
            interval_ms = int(round(1000.0 / fps_val))
        else:
            interval_ms = 33
        interval_ms = max(5, min(1000, interval_ms))
        width = 0
        height = 0
        codec = ""
        try:
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            fourcc_val = int(self.cap.get(cv2.CAP_PROP_FOURCC) or 0)
            if fourcc_val:
                codec_chars = [
                    chr((fourcc_val >> 0) & 0xFF),
                    chr((fourcc_val >> 8) & 0xFF),
                    chr((fourcc_val >> 16) & 0xFF),
                    chr((fourcc_val >> 24) & 0xFF),
                ]
                codec = "".join(codec_chars).strip()
        except Exception:
            pass
        try:
            logging.info(
                f"Playing '{os.path.basename(video_path)}' at {fps_val:.2f} FPS, timer interval {interval_ms} ms, "
                f"resolution {width}x{height}, codec {codec or fourcc_val}"
            )
            if not fps_valid:
                logging.info(
                    f"FPS invalid or unavailable for '{os.path.basename(video_path)}'; using fallback interval {interval_ms} ms"
                )
        except Exception:
            pass
        self.video_timer.start(interval_ms)
    def update_video_frame(self):
        try:
            if self.playing_video and self.cap:
                if not self.cap.isOpened():
                    self.stop_video()
                    self.video_label.setText(self.LABELS.get("cannot_open_video", "Cannot open video file."))
                    return
                ret, frame = self.cap.read()
                if not ret:
                    self.stop_video()
                    self.video_label.setText(self.LABELS.get("cannot_open_video", "Cannot open video file."))
                    return
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
                pixmap = QPixmap.fromImage(qt_image)
                # Scale pixmap to fit the label while preserving aspect ratio
                try:
                    target = self.video_label.contentsRect().size()
                    if target.width() > 0 and target.height() > 0:
                        pixmap = pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                except Exception:
                    pass
                self.video_label.setPixmap(pixmap)
        except Exception as e:
            logging.error(f"Video frame update failed: {e}")
            self.stop_video()
            self.video_label.setText(self.LABELS.get("cannot_open_video", "Cannot open video file."))
        # Format badge removed
    def stop_video(self):
        self.playing_video = False
        self.video_timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.show_first_frame()
        try:
            self._position_badge()
        except Exception:
            pass
    def _release_video_handle(self):
        """Release any active video capture without refreshing preview."""
        try:
            self.playing_video = False
        except Exception:
            pass
        try:
            self.video_timer.stop()
        except Exception:
            pass
        if getattr(self, 'cap', None):
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
    def play_audio(self):
        if not self.current_video:
            return
        # Debounce rapid clicks
        now = time.time()
        if (now - self._last_play_request_ts) < 0.2:
            return
        self._last_play_request_ts = now
        # Re-entrancy guard: ignore if already playing
        if self.is_playing_audio:
            return
        wav_path = self.fs.wav_path_for(self.current_video)
        if not os.path.exists(wav_path):
            return
        if not PYAUDIO_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyAudio is not available. Cannot play audio.")
            return
        # Mark playing and update UI (busy indicator)
        try:
            self.is_playing_audio = True
            self.play_audio_button.setText("Playing…")
            self.play_audio_button.setEnabled(False)
            logging.info(f"UI.audio: start video audio path={os.path.basename(wav_path)}")
        except Exception:
            pass
        # Use persistent audio thread
        try:
            self.audio_worker = AudioPlaybackWorker(wav_path)
            self.audio_worker.moveToThread(self.audio_thread)
            QMetaObject.invokeMethod(self.audio_worker, "run", Qt.QueuedConnection)
            # Re-enable controls when playback finishes
            self.audio_worker.finished.connect(self._on_any_audio_finished)
            self.audio_worker.error.connect(self._show_worker_error)
        except Exception:
            # Fallback: start thread if not running
            try:
                if self.audio_thread and not self.audio_thread.isRunning():
                    self.audio_thread.start()
                self.audio_thread.started.connect(self.audio_worker.run)
            except Exception:
                pass
    def stop_audio(self):
        logging.info("UI.audio: stop requested")
        if self.audio_worker:
            try:
                self.audio_worker.stop()
            except RuntimeError:
                pass
        # Do not quit persistent thread here; just clear UI state
        self.is_playing_audio = False
        try:
            # Restore button text
            self.play_audio_button.setText(self.LABELS.get("play_audio", "Play Audio"))
        except Exception:
            pass
        try:
            self.update_media_controls()
        except Exception:
            pass
        try:
            self._update_image_record_controls()
        except Exception:
            pass
        # Clear playing state and re-enable Play buttons
        self.is_playing_audio = False
        try:
            self.update_media_controls()
        except Exception:
            pass
        try:
            self._update_image_record_controls()
        except Exception:
            pass
    def _on_audio_thread_finished(self):
        self.audio_thread = None
        self.audio_worker = None
        # Ensure UI reflects that playback has ended
        self.is_playing_audio = False
        try:
            self.update_media_controls()
        except Exception:
            pass
        try:
            self._update_image_record_controls()
        except Exception:
            pass
    def _handle_play_image_audio(self):
        try:
            return self.play_image_audio()
        except Exception:
            pass
    def _handle_stop_image_audio(self):
        try:
            return self.stop_image_audio()
        except Exception:
            pass
    def _on_images_context_menu(self, pos: QPoint):
        try:
            # Select the item under the cursor if present
            item = self.images_list.itemAt(pos)
            if item is not None:
                self.images_list.setCurrentItem(item)
            menu = QMenu(self)
            copy_act = QAction(self.LABELS.get("copy_image", "Copy Image"), self)
            copy_act.triggered.connect(self._copy_current_image_to_clipboard)
            menu.addAction(copy_act)
            save_act = QAction(self.LABELS.get("save_image_as", "Save Image as…"), self)
            save_act.triggered.connect(self._save_current_image_as)
            menu.addAction(save_act)
            # Add Reveal action (third), with platform-specific label
            try:
                label = self._platform_reveal_label()
            except Exception:
                label = "Reveal in File Manager"
            reveal_act = QAction(label, self)
            reveal_act.triggered.connect(lambda: self._reveal_in_file_manager(self._current_image_path()))
            menu.addAction(reveal_act)
            try:
                global_pos = self.images_list.mapToGlobal(pos)
            except Exception:
                global_pos = None
            if global_pos:
                menu.exec(global_pos)
            else:
                menu.exec(QCursor.pos())
        except Exception:
            pass
    def _current_image_path(self) -> str:
        """Resolve full path of the currently selected image thumbnail."""
        try:
            sel = getattr(self, 'images_list', None).currentItem() if getattr(self, 'images_list', None) else None
            if sel is None:
                return ""
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            if path and os.path.exists(path):
                return path
        except Exception:
            pass
        return ""
    def _copy_current_image_to_clipboard(self):
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            if not path or not os.path.exists(path):
                return
            reader = QImageReader(path)
            img = reader.read()
            if img.isNull():
                # Fallback: try via QPixmap
                try:
                    pix = QPixmap(path)
                    if not pix.isNull():
                        QGuiApplication.clipboard().setPixmap(pix)
                        return
                except Exception:
                    pass
                return
            QGuiApplication.clipboard().setImage(img)
            try:
                self.statusBar().showMessage(self.LABELS.get("copied_image", "Image copied to clipboard"), 2000)
            except Exception:
                pass
        except Exception:
            pass
    def _on_videos_context_menu(self, pos: QPoint):
        try:
            item = self.video_listbox.itemAt(pos)
            if item is not None:
                self.video_listbox.setCurrentItem(item)
            menu = QMenu(self)
            copy_act = QAction(self.LABELS.get("copy_video", "Copy Video"), self)
            copy_act.triggered.connect(self._copy_current_video_to_clipboard)
            menu.addAction(copy_act)
            save_act = QAction(self.LABELS.get("save_video_as", "Save Video as…"), self)
            save_act.triggered.connect(self._save_current_video_as)
            menu.addAction(save_act)
            try:
                global_pos = self.video_listbox.mapToGlobal(pos)
            except Exception:
                global_pos = None
            if global_pos:
                menu.exec(global_pos)
            else:
                menu.exec(QCursor.pos())
        except Exception:
            pass
    def _copy_current_video_to_clipboard(self):
        try:
            if not self.current_video:
                return
            video_path = self._resolve_current_video_path()
            if not (video_path and os.path.exists(video_path)):
                return
            # Convert if needed (extension/codec/pix_fmt/audio) for WhatsApp compatibility
            if needs_reencode_to_mp4(video_path):
                self._convert_video_to_mp4_and_copy(video_path)
                return
            # Already MP4: copy the file URL directly
            mime = QMimeData()
            try:
                mime.setUrls([QUrl.fromLocalFile(video_path)])
            except Exception:
                pass
            try:
                mime.setText(video_path)
            except Exception:
                pass
            QGuiApplication.clipboard().setMimeData(mime)
            try:
                self.statusBar().showMessage(self.LABELS.get("copied_video", "Video copied to clipboard"), 2000)
            except Exception:
                pass
        except Exception:
            pass

    def _convert_video_to_mp4_and_copy(self, src_path: str):
        """Convert the given video to MP4 using worker+progress, then copy the result."""
        try:
            if not (src_path and os.path.exists(src_path)):
                return
            base = os.path.splitext(os.path.basename(src_path))[0]
            tmp_dir = tempfile.mkdtemp(prefix="vat_convert_")
            dst_path = os.path.join(tmp_dir, base + ".mp4")
            try:
                logging.info(f"UI.copy_convert: starting worker: src={src_path}, dst={dst_path}")
            except Exception:
                pass
            worker = VideoConvertWorker(ConvertSpec(src_path, dst_path))
            self._convert_worker = worker
            dlg = QProgressDialog(self.LABELS.get("converting_video", "Converting…"), self.LABELS.get("cancel", "Cancel"), 0, 100, self)
            dlg.setWindowTitle(self.LABELS.get("converting_title", "Converting"))
            dlg.setWindowModality(Qt.WindowModal)
            dlg.setAutoClose(True)
            dlg.setAutoReset(True)
            # Guard so closing dialog after success doesn't trigger cancel
            done = {"value": False}
            def _mark_done():
                done["value"] = True
            def do_cancel():
                if not done["value"]:
                    worker.cancel()
            dlg.canceled.connect(do_cancel)
            worker.progress.connect(dlg.setValue)
            def on_finished(out_path: str):
                try:
                    logging.info(f"UI.copy_convert: finished: out={out_path}")
                except Exception:
                    pass
                try:
                    mime = QMimeData()
                    mime.setUrls([QUrl.fromLocalFile(out_path)])
                    mime.setText(out_path)
                    QGuiApplication.clipboard().setMimeData(mime)
                    self.statusBar().showMessage(self.LABELS.get("copied_video", "Video copied to clipboard"), 2000)
                except Exception:
                    pass
                try:
                    # prevent canceled signal from firing a cancel after success
                    try:
                        dlg.canceled.disconnect(do_cancel)
                    except Exception:
                        pass
                    _mark_done()
                    dlg.close()
                except Exception:
                    pass
            def on_error(msg: str):
                try:
                    logging.error(f"UI.copy_convert: error: {msg}")
                except Exception:
                    pass
                try:
                    dlg.close()
                except Exception:
                    pass
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), f"{self.LABELS.get('conversion_failed', 'Conversion failed')}: {msg}")
            def on_canceled():
                try:
                    logging.info("UI.copy_convert: canceled")
                except Exception:
                    pass
                try:
                    dlg.close()
                except Exception:
                    pass
                # Cleanup temp dir on cancel/error
                try:
                    if os.path.isdir(tmp_dir):
                        shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass
            def _cleanup_refs(*args, **kwargs):
                try:
                    self._convert_worker = None
                except Exception:
                    pass
            worker.finished.connect(_cleanup_refs)
            worker.error.connect(_cleanup_refs)
            worker.canceled.connect(_cleanup_refs)
            worker.finished.connect(on_finished)
            worker.error.connect(on_error)
            worker.canceled.connect(on_canceled)
            # Fallback: also handle base QThread finished() if custom signal is not delivered
            def _fallback_on_thread_finished():
                try:
                    if done["value"]:
                        return
                    # Use worker state to decide
                    out = getattr(worker, "output_path", None)
                    if getattr(worker, "succeeded", False) and out and os.path.exists(out):
                        logging.info("UI.copy_convert: fallback via QThread.finished; invoking on_finished")
                        on_finished(out)
                        # on_finished marks done
                except Exception:
                    pass
            try:
                worker.finished.connect(lambda *_: _mark_done())
            except Exception:
                pass
            try:
                super(VideoConvertWorker, worker).finished.connect(_fallback_on_thread_finished)  # type: ignore
            except Exception:
                # PySide may not allow super() signal access; try attribute on instance
                try:
                    worker.finished.connect(_fallback_on_thread_finished)  # best-effort
                except Exception:
                    pass
            # Timer-based fallback: poll for output existence briefly
            attempts = {"n": 25}  # ~5s @200ms
            def _poll_fallback():
                try:
                    if done["value"]:
                        return
                    # Only consider fallback when the worker reports success or the thread finished
                    out = getattr(worker, "output_path", None) or dst_path
                    if (getattr(worker, "succeeded", False) or worker.isFinished()) and out and os.path.exists(out):
                        logging.info("UI.copy_convert: timer fallback detected completion; invoking on_finished")
                        on_finished(out)
                        return
                    if attempts["n"] > 0:
                        attempts["n"] -= 1
                        QTimer.singleShot(200, _poll_fallback)
                except Exception:
                    pass
            QTimer.singleShot(300, _poll_fallback)
            # Extra debug hooks
            try:
                worker.finished.connect(lambda *_: logging.info("UI.copy_convert: finished signal received"))
                worker.canceled.connect(lambda *_: logging.info("UI.copy_convert: canceled signal received"))
            except Exception:
                pass
            worker.start()
            dlg.show()
        except Exception:
            pass
    def _save_current_video_as(self):
        try:
            if not self.current_video:
                return
            src = self._resolve_current_video_path()
            if not (src and os.path.exists(src)):
                return
            name = os.path.basename(src)
            dst, _ = QFileDialog.getSaveFileName(
                self,
                self.LABELS.get("save_video_as_dialog_title", "Save Video as…"),
                name,
                "Video files (*.mpg *.mpeg *.mp4 *.avi *.mkv *.mov);;All files (*)",
            )
            if not dst:
                return
            try:
                shutil.copyfile(src, dst)
            except Exception as e:
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), f"Failed to save video: {e}")
                return
        except Exception:
            pass

    def _convert_current_video_in_place(self):
        """Convert the current video to MP4 next to original, delete original on success, update UI."""
        try:
            if not self.current_video:
                return
            src_path = self._resolve_current_video_path()
            if not (src_path and os.path.exists(src_path)):
                return
            folder = os.path.dirname(src_path)
            base = os.path.splitext(os.path.basename(src_path))[0]
            dst_path = os.path.join(folder, base + ".mp4")
            try:
                logging.info(f"UI.convert_in_place: begin: src={src_path}, dst={dst_path}")
                self.statusBar().showMessage(self.LABELS.get("converting_video", "Converting…"), 2000)
            except Exception:
                pass
            if os.path.exists(dst_path):
                resp = QMessageBox.question(
                    self,
                    self.LABELS.get("overwrite_title", "Overwrite?"),
                    self.LABELS.get("mp4_exists_overwrite", "MP4 already exists. Overwrite?"),
                )
                if resp != QMessageBox.Yes:
                    return
                try:
                    os.remove(dst_path)
                except Exception:
                    pass
            worker = VideoConvertWorker(ConvertSpec(src_path, dst_path))
            self._convert_worker = worker
            dlg = QProgressDialog(self.LABELS.get("converting_video", "Converting…"), self.LABELS.get("cancel", "Cancel"), 0, 100, self)
            dlg.setWindowTitle(self.LABELS.get("converting_title", "Converting"))
            dlg.setWindowModality(Qt.WindowModal)
            dlg.setAutoClose(True)
            dlg.setAutoReset(True)
            done2 = {"value": False}
            def _mark_done2():
                done2["value"] = True
            def _cancel2():
                if not done2["value"]:
                    worker.cancel()
            dlg.canceled.connect(_cancel2)
            worker.progress.connect(dlg.setValue)
            def on_finished(out_path: str):
                try:
                    logging.info(f"UI.convert_in_place: finished ffmpeg: src={src_path}, out={out_path}")
                except Exception:
                    pass
                # 1) Release any active handle on the original without reloading preview
                try:
                    logging.info("UI.convert_in_place: releasing video handle")
                except Exception:
                    pass
                self._release_video_handle()
                new_name = os.path.basename(out_path)
                # 2) Zip the original file into filename.ext.bak.zip (with original filename inside) and delete original
                try:
                    logging.info("UI.convert_in_place: creating zip backup of original")
                    if os.path.exists(src_path):
                        zip_path = src_path + ".bak.zip"
                        # Ensure unique zip name if exists
                        if os.path.exists(zip_path):
                            i = 2
                            while True:
                                alt = f"{src_path}.bak{i}.zip"
                                if not os.path.exists(alt):
                                    zip_path = alt
                                    break
                                i += 1
                        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                            zf.write(src_path, arcname=os.path.basename(src_path))
                        try:
                            os.remove(src_path)
                        except Exception:
                            pass
                        try:
                            logging.info(f"UI.convert_in_place: backup created at {zip_path} and original removed")
                        except Exception:
                            pass
                except Exception as e:
                    try:
                        QMessageBox.warning(self, self.LABELS.get("error_title", "Error"), f"{self.LABELS.get('backup_failed', 'Backup failed')}: {e}")
                    except Exception:
                        pass
                # 3) Reload the current folder and reselect the new MP4 after refresh (pending selection with retry)
                try:
                    logging.info("UI.convert_in_place: reloading folder and selecting new mp4 (extended retries)")
                    self._reload_folder_and_select(new_name, retries=6, delay_ms=250)
                except Exception:
                    pass
                try:
                    self.statusBar().showMessage(self.LABELS.get("conversion_done", "Conversion complete"), 2000)
                    try:
                        dlg.canceled.disconnect(_cancel2)
                    except Exception:
                        pass
                    _mark_done2()
                    dlg.close()
                except Exception:
                    pass
            def on_error(msg: str):
                try:
                    logging.error(f"UI.convert_in_place: error: {msg}")
                except Exception:
                    pass
                try:
                    dlg.close()
                except Exception:
                    pass
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), f"{self.LABELS.get('conversion_failed', 'Conversion failed')}: {msg}")
            def on_canceled():
                try:
                    logging.info("UI.convert_in_place: canceled")
                except Exception:
                    pass
                try:
                    dlg.close()
                except Exception:
                    pass
            def _cleanup_refs2(*args, **kwargs):
                try:
                    self._convert_worker = None
                except Exception:
                    pass
            worker.finished.connect(_cleanup_refs2)
            worker.error.connect(_cleanup_refs2)
            worker.canceled.connect(_cleanup_refs2)
            worker.finished.connect(on_finished)
            worker.error.connect(on_error)
            worker.canceled.connect(on_canceled)
            # Fallback: handle base QThread finished() in case custom signal is not delivered
            def _fallback_on_thread_finished2():
                try:
                    if done2["value"]:
                        return
                    out = getattr(worker, "output_path", None)
                    if getattr(worker, "succeeded", False) and out and os.path.exists(out):
                        logging.info("UI.convert_in_place: fallback via QThread.finished; invoking on_finished")
                        on_finished(out)
                        # on_finished marks done
                except Exception:
                    pass
            try:
                worker.finished.connect(lambda *_: _mark_done2())
            except Exception:
                pass
            try:
                super(VideoConvertWorker, worker).finished.connect(_fallback_on_thread_finished2)  # type: ignore
            except Exception:
                try:
                    worker.finished.connect(_fallback_on_thread_finished2)  # best-effort
                except Exception:
                    pass
            # Timer-based fallback: poll for output existence briefly
            attempts2 = {"n": 25}  # ~5s @200ms
            def _poll_fallback2():
                try:
                    if done2["value"]:
                        return
                    out = getattr(worker, "output_path", None) or dst_path
                    if (getattr(worker, "succeeded", False) or worker.isFinished()) and out and os.path.exists(out):
                        logging.info("UI.convert_in_place: timer fallback detected completion; invoking on_finished")
                        on_finished(out)
                        return
                    if attempts2["n"] > 0:
                        attempts2["n"] -= 1
                        QTimer.singleShot(200, _poll_fallback2)
                except Exception:
                    pass
            QTimer.singleShot(300, _poll_fallback2)
            # Extra debug hooks
            try:
                worker.finished.connect(lambda *_: logging.info("UI.convert_in_place: finished signal received"))
                worker.canceled.connect(lambda *_: logging.info("UI.convert_in_place: canceled signal received"))
            except Exception:
                pass
            worker.start()
            dlg.show()
        except Exception:
            pass
    def _save_current_image_as(self):
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            if not path or not os.path.exists(path):
                return
            name = os.path.basename(path)
            dst, _ = QFileDialog.getSaveFileName(
                self,
                self.LABELS.get("save_image_as_dialog_title", "Save Image as…"),
                name,
                "Image files (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.gif);;All files (*)",
            )
            if not dst:
                return
            try:
                shutil.copyfile(path, dst)
            except Exception as e:
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), f"Failed to save image: {e}")
                return
        except Exception:
            pass
    def _handle_add_existing_audio_video(self):
        """Import an existing audio file for the currently selected video and convert to 16-bit WAV."""
        try:
            if not self.current_video or not self.fs.current_folder:
                return
            target_wav = self.fs.wav_path_for(self.current_video)
            if os.path.exists(target_wav):
                reply = QMessageBox.question(
                    self,
                    self.LABELS.get("overwrite", "Overwrite?"),
                    self.LABELS.get("overwrite_audio", "Audio file already exists. Overwrite?"),
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return
            # Choose source audio file
            src_path, _ = QFileDialog.getOpenFileName(
                self,
                self.LABELS.get("import_select_file_dialog", "Select Audio File"),
                self.fs.current_folder or "",
                "Audio files (*.wav *.mp3 *.ogg *.m4a *.aac *.flac *.opus *.aif *.aiff);;All files (*)",
            )
            if not src_path:
                return
            try:
                seg = AudioSegment.from_file(src_path)
                seg = seg.set_channels(1).set_frame_rate(44100).set_sample_width(2)
                seg.export(target_wav, format="wav")
            except Exception as e:
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), f"Failed to import audio: {e}")
                return
            try:
                self.statusBar().showMessage(self.LABELS.get("metadata_saved", "Metadata saved!"))
            except Exception:
                pass
            # Refresh controls and badges
            self.update_media_controls()
        except Exception:
            pass
    def _convert_audio_to_wav(self, src_path: str, target_wav: str) -> None:
        seg = AudioSegment.from_file(src_path)
        seg = seg.set_channels(1).set_frame_rate(44100).set_sample_width(2)
        seg.export(target_wav, format="wav")
    def _clipboard_audio_to_tempfile(self, mime) -> str | None:
        try:
            # Prefer file URLs on the clipboard
            if mime.hasUrls():
                for url in mime.urls():
                    try:
                        if isinstance(url, QUrl) and url.isLocalFile():
                            p = url.toLocalFile()
                            if p and os.path.exists(p):
                                return p
                    except Exception:
                        continue
            # Next, check for plain-text paths or file:// URLs
            if mime.hasText():
                txt = (mime.text() or "").strip()
                if txt:
                    if os.path.exists(txt):
                        return txt
                    try:
                        u = QUrl(txt)
                        if u.isLocalFile():
                            p = u.toLocalFile()
                            if p and os.path.exists(p):
                                return p
                    except Exception:
                        pass
            # Finally, handle raw audio bytes for known MIME types
            format_map = {
                "audio/wav": ".wav",
                "audio/x-wav": ".wav",
                "audio/mpeg": ".mp3",
                "audio/mp3": ".mp3",
                "audio/ogg": ".ogg",
                "application/ogg": ".ogg",
                "audio/aac": ".aac",
                "audio/flac": ".flac",
                "audio/opus": ".opus",
                "audio/webm": ".webm",
                "audio/aiff": ".aiff",
                "audio/x-aiff": ".aif",
            }
            for fmt, ext in format_map.items():
                try:
                    if fmt in mime.formats():
                        data = mime.data(fmt)
                        if data and len(data) > 0:
                            import tempfile
                            fd, tmp = tempfile.mkstemp(suffix=ext)
                            os.write(fd, bytes(data))
                            os.close(fd)
                            return tmp
                except Exception:
                    continue
        except Exception:
            pass
        return None
    def _clipboard_image_to_tempfile(self, mime) -> str | None:
        """Extract an image from the system clipboard into a temporary file, safely.
        Order of attempts (safer first): URLs -> raw image bytes -> HTML data URLs -> text paths -> direct image() last.
        """
        # 1) File URLs on the clipboard
        try:
            if mime and mime.hasUrls():
                for url in mime.urls():
                    try:
                        if isinstance(url, QUrl) and url.isLocalFile():
                            p = url.toLocalFile()
                            if p and os.path.exists(p):
                                return p
                    except Exception:
                        continue
        except Exception:
            pass
        # 2) Raw image bytes in known formats
        try:
            if mime:
                fmt_map = {
                    "image/png": ".png",
                    "image/jpeg": ".jpg",
                    "image/jpg": ".jpg",
                    "image/gif": ".gif",
                    "image/bmp": ".bmp",
                    "image/tiff": ".tiff",
                }
                available = set(mime.formats() or [])
                for fmt, ext in fmt_map.items():
                    if fmt in available:
                        data = mime.data(fmt)
                        if data and len(data) > 0:
                            import tempfile
                            fd, tmp_path = tempfile.mkstemp(suffix=ext)
                            try:
                                os.write(fd, bytes(data))
                            finally:
                                os.close(fd)
                            if os.path.exists(tmp_path):
                                return tmp_path
        except Exception:
            pass
        # 3) HTML with data URL image
        try:
            if mime and mime.hasHtml():
                html = mime.html() or ""
                import re, base64, tempfile
                m = re.search(r"data:(image/[^;]+);base64,([A-Za-z0-9+/=]+)", html)
                if m:
                    mime_type = m.group(1)
                    b64 = m.group(2)
                    ext = ".png" if mime_type == "image/png" else ".jpg"
                    raw = base64.b64decode(b64)
                    fd, tmp_path = tempfile.mkstemp(suffix=ext)
                    try:
                        os.write(fd, raw)
                    finally:
                        os.close(fd)
                    if os.path.exists(tmp_path):
                        return tmp_path
        except Exception:
            pass
        # 4) Plain text path or file:// URL
        try:
            if mime and mime.hasText():
                txt = (mime.text() or "").strip()
                if txt:
                    if txt.startswith("file://"):
                        try:
                            from urllib.parse import urlparse
                            p = urlparse(txt)
                            if p.scheme == "file":
                                loc = p.path
                                if loc and os.path.exists(loc):
                                    return loc
                        except Exception:
                            pass
                    if os.path.exists(txt):
                        return txt
        except Exception:
            pass
        # 5) Do not call QClipboard.image() (can be unstable on some macOS setups)
        return None

    def _handle_paste_image(self):
        try:
            if not self.fs.current_folder:
                QMessageBox.information(self, self.LABELS.get("no_folder_selected", "No folder selected"), self.LABELS.get("no_folder_selected", "No folder selected"))
                return
            try:
                mime = QGuiApplication.clipboard().mimeData()
            except Exception as e:
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), self.LABELS.get("clipboard_access_failed", "Failed to access clipboard."))
                return
            src = None
            try:
                src = self._clipboard_image_to_tempfile(mime)
            except Exception as e:
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), self.LABELS.get("clipboard_parse_failed", "Clipboard content could not be parsed as an image."))
                return
            if not src:
                QMessageBox.warning(self, self.LABELS.get("error_title", "Error"), self.LABELS.get("clipboard_no_image", "No image found on clipboard"))
                return
            self._import_image_with_prompt(src)
        except Exception as e:
            QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), self.LABELS.get("paste_failed_generic", "Paste failed unexpectedly."))

    def _import_image_with_prompt(self, src_path: str):
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, QLineEdit, QCheckBox, QPushButton
        except Exception:
            QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), "Unable to open import options dialog.")
            return
        try:
            folder = self.fs.current_folder or ""
            base_name = os.path.basename(src_path)
            src_ext = os.path.splitext(base_name)[1].lower()
            dlg = QDialog(self)
            dlg.setWindowTitle(self.LABELS.get("add_image_options", "Import Image"))
            layout = QVBoxLayout(dlg)
            tip = QLabel(self.LABELS.get("add_image_tip", "Images are shown in filename order. Consider putting numbers first (e.g., 001_name.jpg) to control sort order."))
            tip.setWordWrap(True)
            layout.addWidget(tip)
            rb_auto = QRadioButton(self.LABELS.get("name_auto_number", "Autonumber: vat_0000"))
            rb_orig = QRadioButton(self.LABELS.get("name_original", "Original filename & format"))
            rb_custom = QRadioButton(self.LABELS.get("name_custom", "Custom filename"))
            rb_auto.setChecked(True)
            layout.addWidget(rb_auto)
            layout.addWidget(rb_orig)
            layout.addWidget(rb_custom)
            custom_row = QHBoxLayout()
            custom_row.addWidget(QLabel(self.LABELS.get("custom_filename_label", "Filename:")))
            le_custom = QLineEdit()
            le_custom.setPlaceholderText(self.LABELS.get("custom_filename_placeholder", "e.g., 001_scene.jpg"))
            le_custom.setEnabled(False)
            custom_row.addWidget(le_custom)
            layout.addLayout(custom_row)
            def _toggle_custom():
                le_custom.setEnabled(rb_custom.isChecked())
            rb_custom.toggled.connect(_toggle_custom)
            cb_jpg = QCheckBox(self.LABELS.get("convert_to_jpg", "Convert to JPG"))
            cb_jpg.setChecked(True)
            layout.addWidget(cb_jpg)
            btns = QHBoxLayout()
            ok_btn = QPushButton(self.LABELS.get("ok", "OK"))
            cancel_btn = QPushButton(self.LABELS.get("cancel", "Cancel"))
            btns.addWidget(ok_btn)
            btns.addWidget(cancel_btn)
            layout.addLayout(btns)
            cancel_btn.clicked.connect(dlg.reject)
            ok_btn.clicked.connect(dlg.accept)
            dlg.resize(520, 240)
            if dlg.exec() != QDialog.Accepted:
                return
            to_jpg = cb_jpg.isChecked()
            ext_out = ".jpg" if to_jpg else (src_ext or ".jpg")
            def _next_vat_name():
                i = 0
                while True:
                    name = f"vat_{i:04d}{ext_out}"
                    cand = os.path.join(folder, name)
                    if not os.path.exists(cand):
                        return cand
                    i += 1
            if rb_auto.isChecked():
                dst_path = _next_vat_name()
            elif rb_orig.isChecked():
                base_no_ext = os.path.splitext(base_name)[0]
                dst_path = os.path.join(folder, base_no_ext + ext_out)
                if os.path.exists(dst_path):
                    reply = QMessageBox.question(self, self.LABELS.get("overwrite_title", "Overwrite?"), self.LABELS.get("file_exists_overwrite", "File already exists. Overwrite?"))
                    if reply != QMessageBox.Yes:
                        return
            else:
                name_in = (le_custom.text() or "").strip()
                if not name_in:
                    QMessageBox.warning(self, self.LABELS.get("error_title", "Error"), self.LABELS.get("custom_name_required", "Please enter a filename."))
                    return
                root, ext_in = os.path.splitext(name_in)
                if not ext_in:
                    name_in = root + ext_out
                elif to_jpg and ext_in.lower() != ".jpg":
                    name_in = root + ext_out
                dst_path = os.path.join(folder, name_in)
                if os.path.exists(dst_path):
                    reply = QMessageBox.question(self, self.LABELS.get("overwrite_title", "Overwrite?"), self.LABELS.get("file_exists_overwrite", "File already exists. Overwrite?"))
                    if reply != QMessageBox.Yes:
                        return
            try:
                if to_jpg:
                    # Prefer Qt path to avoid native codec crashes
                    try:
                        from PySide6.QtGui import QImage
                        qimg = QImage(src_path)
                        if not qimg.isNull():
                            # Ensure no alpha for JPEG
                            if qimg.hasAlphaChannel():
                                qimg = qimg.convertToFormat(QImage.Format_RGB888)
                            if qimg.save(dst_path, "JPG"):
                                pass
                            else:
                                raise RuntimeError("QImage save to JPG failed")
                        else:
                            raise RuntimeError("QImage failed to load")
                    except Exception:
                        # Fallback to OpenCV conversion
                        import cv2
                        img = cv2.imread(src_path, cv2.IMREAD_UNCHANGED)
                        if img is None:
                            QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), self.LABELS.get("import_failed", "Failed to read image for conversion."))
                            return
                        if len(img.shape) == 3 and img.shape[2] == 4:
                            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                        quality = 92
                        ok = cv2.imwrite(dst_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                        if not ok:
                            QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), self.LABELS.get("import_failed", "Failed to write JPG."))
                            return
                else:
                    shutil.copyfile(src_path, dst_path)
            except Exception as e:
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), f"Failed to import image: {e}")
                return
            imgs = self.fs.list_images()
            self._on_images_updated(self.fs.current_folder, imgs)
            basename = os.path.basename(dst_path)
            for i in range(self.images_list.count()):
                it = self.images_list.item(i)
                if it and it.text() == basename:
                    self.images_list.setCurrentRow(i)
                    break
            self.statusBar().showMessage(self.LABELS.get("image_imported", "Image imported"), 2000)
        except Exception:
            pass

    def _handle_add_existing_image(self):
        try:
            if not self.fs.current_folder:
                QMessageBox.information(self, self.LABELS.get("no_folder_selected", "No folder selected"), self.LABELS.get("no_folder_selected", "No folder selected"))
                return
            src_path, _ = QFileDialog.getOpenFileName(
                self,
                self.LABELS.get("select_image_file_dialog", "Select Image File"),
                self.fs.current_folder or "",
                "Image files (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.gif);;All files (*)",
            )
            if not src_path:
                return
            self._import_image_with_prompt(src_path)
        except Exception:
            pass

    def _handle_paste_audio_video(self):
        try:
            if not self.current_video or not self.fs.current_folder:
                return
            target_wav = self.fs.wav_path_for(self.current_video)
            if os.path.exists(target_wav):
                reply = QMessageBox.question(
                    self,
                    self.LABELS.get("overwrite", "Overwrite?"),
                    self.LABELS.get("overwrite_audio", "Audio file already exists. Overwrite?"),
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return
            cb = QGuiApplication.clipboard()
            mime = cb.mimeData()
            src = self._clipboard_audio_to_tempfile(mime)
            if not src:
                QMessageBox.warning(self, self.LABELS.get("error_title", "Error"), self.LABELS.get("paste_audio_failed", "Clipboard does not contain audio or an audio file path."))
                return
            try:
                self._convert_audio_to_wav(src, target_wav)
            finally:
                # Clean temp file if we created one
                try:
                    if src and os.path.basename(src).startswith("tmp") and not os.path.isdir(src):
                        pass
                except Exception:
                    pass
            self.update_media_controls()
        except Exception:
            pass
    def _handle_paste_audio_image(self):
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            if not path:
                return
            existing = self.fs.find_existing_image_audio(path)
            target_wav = self.fs.wav_path_for_image(path)
            if existing and os.path.exists(existing):
                reply = QMessageBox.question(
                    self,
                    self.LABELS.get("overwrite", "Overwrite?"),
                    self.LABELS.get("overwrite_audio", "Audio file already exists. Overwrite?"),
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return
            cb = QGuiApplication.clipboard()
            mime = cb.mimeData()
            src = self._clipboard_audio_to_tempfile(mime)
            if not src:
                QMessageBox.warning(self, self.LABELS.get("error_title", "Error"), self.LABELS.get("paste_audio_failed", "Clipboard does not contain audio or an audio file path."))
                return
            try:
                self._convert_audio_to_wav(src, target_wav)
            finally:
                try:
                    if src and os.path.basename(src).startswith("tmp") and not os.path.isdir(src):
                        pass
                except Exception:
                    pass
            try:
                self._update_image_record_controls(path)
            except Exception:
                pass
            self.update_video_file_checks()
        except Exception:
            pass
    def _handle_add_existing_audio_image(self):
        """Import an existing audio file for the selected image and convert to 16-bit WAV."""
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            if not path:
                return
            existing = self.fs.find_existing_image_audio(path)
            target_wav = self.fs.wav_path_for_image(path)
            if existing and os.path.exists(existing):
                reply = QMessageBox.question(
                    self,
                    self.LABELS.get("overwrite", "Overwrite?"),
                    self.LABELS.get("overwrite_audio", "Audio file already exists. Overwrite?"),
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return
            # Choose source audio file
            src_path, _ = QFileDialog.getOpenFileName(
                self,
                self.LABELS.get("import_select_file_dialog", "Select Audio File"),
                os.path.dirname(path) or (self.fs.current_folder or ""),
                "Audio files (*.wav *.mp3 *.ogg *.m4a *.aac *.flac *.opus *.aif *.aiff);;All files (*)",
            )
            if not src_path:
                return
            try:
                seg = AudioSegment.from_file(src_path)
                seg = seg.set_channels(1).set_frame_rate(44100).set_sample_width(2)
                seg.export(target_wav, format="wav")
            except Exception as e:
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), f"Failed to import audio: {e}")
                return
            try:
                self.statusBar().showMessage(self.LABELS.get("metadata_saved", "Metadata saved!"))
            except Exception:
                pass
            # Refresh controls and visuals
            try:
                self._update_image_record_controls(path)
            except Exception:
                pass
            self.update_video_file_checks()
        except Exception:
            pass
    def _handle_record_image(self):
        try:
            return self.toggle_image_recording()
        except Exception:
            pass
    def _handle_stop_image_record(self):
        try:
            return self.stop_image_recording()
        except Exception:
            pass
    def _handle_image_selection(self):
        try:
            logging.debug("UI._handle_image_selection invoked")
            return self.on_image_select()
        except Exception:
            pass
    def _handle_open_fullscreen_image(self, item):
        try:
            return self._open_fullscreen_image(item)
        except Exception:
            pass
    def toggle_recording(self):
        if not self.current_video:
            return
        if self.is_recording:
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
            self.update_media_controls()
            try:
                self.statusBar().showMessage(self.LABELS.get("recording_stopped", "Recording stopped"), 2000)
            except Exception:
                pass
            self.update_video_file_checks()
        else:
            wav_path = self.fs.wav_path_for(self.current_video)
            if os.path.exists(wav_path):
                reply = QMessageBox.question(self, self.LABELS["overwrite"], 
                                            self.LABELS["overwrite_audio"],
                                            QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    return
            if not PYAUDIO_AVAILABLE:
                QMessageBox.warning(self, "Error", "PyAudio is not available. Cannot record audio.")
                return
            self.is_recording = True
            self.record_button.setText(self.LABELS["stop_recording"])
            self.update_recording_indicator()
            try:
                self.statusBar().showMessage(self.LABELS.get("recording_started", "Recording started"), 2000)
            except Exception:
                pass
            self.recording_thread = QThread()
            self.recording_worker = AudioRecordingWorker(wav_path)
            self.recording_worker.moveToThread(self.recording_thread)
            self.recording_thread.started.connect(self.recording_worker.run)
            self.recording_worker.finished.connect(self.recording_thread.quit)
            self.recording_worker.finished.connect(self.recording_worker.deleteLater)
            self.recording_thread.finished.connect(self.recording_thread.deleteLater)
            self.recording_worker.finished.connect(self.update_media_controls)
            self.recording_thread.finished.connect(self._on_recording_thread_finished)
            self.recording_worker.error.connect(self._show_worker_error)
            self.recording_thread.start()
    def _on_recording_thread_finished(self):
        self.recording_thread = None
        self.recording_worker = None
        # Ensure recording state resets on thread finish (videos and images)
        try:
            self.is_recording = False
        except Exception:
            pass
        # Update UI controls accordingly
        try:
            self.update_media_controls()
        except Exception:
            pass
        try:
            self._update_image_record_controls()
        except Exception:
            pass
        try:
            # Ensure grid overlays update when recording stops
            self.images_list.viewport().update()
        except Exception:
            pass
    def closeEvent(self, event):
        try:
            # Ensure Review tab threads stop before main window closes
            try:
                review_tab = getattr(self, 'review_tab', None)
                if review_tab and hasattr(review_tab, 'cleanup'):
                    review_tab.cleanup()
            except Exception:
                pass
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
                    self.update_recording_indicator()
            except Exception:
                pass
            # Ensure persistent audio thread stops on app close
            try:
                if self.audio_thread and self.audio_thread.isRunning():
                    self.audio_thread.quit()
                    self.audio_thread.wait()
                    logging.info("UI.audio: persistent audio thread stopped on close")
            except Exception:
                pass
            try:
                if hasattr(self, 'join_thread') and self.join_thread and self.join_thread.isRunning():
                    self.join_thread.wait()
            except Exception:
                pass
        finally:
            super().closeEvent(event)
    def open_in_ocenaudio(self):
        if not self.fs.current_folder:
            QMessageBox.critical(self, self.LABELS["error_title"], self.LABELS["no_folder_selected"]) 
            return
        # Tab-aware: open recordings for the active tab
        try:
            active_index = self.right_panel.currentIndex() if getattr(self, 'right_panel', None) else 0
        except Exception:
            active_index = 0
        
        # Determine which recordings to open based on active tab
        if active_index == 1:  # Images tab
            file_paths = self.fs.image_recordings_in()
        elif active_index == 2:  # Review tab
            # Get recordings from Review tab's filtered scope
            try:
                review_tab = getattr(self, 'review_tab', None)
                if review_tab:
                    items = review_tab._get_recorded_items()
                    file_paths = [wav_path for _, _, wav_path in items]
                else:
                    file_paths = self.fs.recordings_in()
            except Exception:
                file_paths = self.fs.recordings_in()
        else:  # Videos tab (default)
            file_paths = self.fs.video_recordings_in()
        
        if not file_paths:
            QMessageBox.information(self, self.LABELS["no_files"], self.LABELS["no_wavs_found"]) 
            return
        file_paths.sort()
        if self.ocenaudio_path and os.path.exists(self.ocenaudio_path):
            command = [self.ocenaudio_path] + file_paths
        else:
            possible_paths = []
            if sys.platform == "darwin":
                possible_paths = ["/Applications/ocenaudio.app/Contents/MacOS/ocenaudio"]
            elif sys.platform == "win32":
                possible_paths = [
                    r"C:\\Program Files\\ocenaudio\\ocenaudio.exe",
                    r"C:\\ocenaudio\\ocenaudio.exe",
                    r"C:\\Program Files (x86)\\ocenaudio\\ocenaudio.exe",
                    os.path.expandvars(r"%USERPROFILE%\\ocenaudio\\ocenaudio.exe"),
                    os.path.expandvars(r"%LOCALAPPDATA%\\ocenaudio\\ocenaudio.exe")
                ]
            else:
                possible_paths = [shutil.which("ocenaudio")]
            ocenaudio_path = None
            for path in possible_paths:
                if path and os.path.exists(path):
                    ocenaudio_path = path
                    break
            if not ocenaudio_path:
                ocenaudio_path, _ = QFileDialog.getOpenFileName(
                    self,
                    self.LABELS["ocenaudio_locate_title"],
                    "",
                    "Executable Files (*.exe);;All Files (*)" if sys.platform == "win32" else "All Files (*)"
                )
                if not ocenaudio_path:
                    QMessageBox.warning(
                        self,
                        self.LABELS["ocenaudio_not_found_title"],
                        self.LABELS.get(
                            "ocenaudio_not_found_body",
                            LABELS_ALL["English"]["ocenaudio_not_found_body"],
                        ),
                    )
                    return
            self.ocenaudio_path = ocenaudio_path
            self.save_settings()
            command = [self.ocenaudio_path] + file_paths
        try:
            subprocess.Popen(command)
        except Exception as e:
            QMessageBox.critical(self, self.LABELS["error_title"], f"{self.LABELS['ocenaudio_open_fail_prefix']}{e}")
    def export_wavs(self):
        if not self.fs.current_folder:
            QMessageBox.critical(self, "Error", "No folder selected.")
            return
        wav_paths = self.fs.recordings_in()
        wav_files = [os.path.basename(p) for p in wav_paths]
        export_dir = QFileDialog.getExistingDirectory(self, self.LABELS["export_select_folder_dialog"]) 
        if not export_dir:
            return
        overwrite_files = []
        for wav in wav_files:
            dst = os.path.join(export_dir, wav)
            if os.path.exists(dst):
                overwrite_files.append(wav)
        metadata_dst = os.path.join(export_dir, "metadata.txt")
        if os.path.exists(metadata_dst):
            overwrite_files.append("metadata.txt")
        if overwrite_files:
            reply = QMessageBox.question(
                self,
                self.LABELS["overwrite_files_title"],
                self.LABELS["overwrite_export_body_prefix"] + "\n".join(overwrite_files) + self.LABELS["overwrite_question_suffix"],
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                QMessageBox.information(self, self.LABELS["export_cancelled_title"], self.LABELS["export_cancelled_msg"]) 
                return
        errors = []
        for wav in wav_files:
            src = os.path.join(self.fs.current_folder, wav)
            dst = os.path.join(export_dir, wav)
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                errors.append(f"{wav}: {e}")
        try:
            content = self.fs.ensure_and_read_metadata(self.fs.current_folder, "")
            with open(metadata_dst, "w") as f:
                f.write(content if isinstance(content, str) else "")
        except Exception as e:
            errors.append(f"metadata.txt: {e}")
        if errors:
            QMessageBox.critical(self, self.LABELS["error_title"], "Some files could not be exported:\n" + "\n".join(errors))
        else:
            QMessageBox.information(self, self.LABELS["export_wavs"], f"Exported {len(wav_files)} WAV files and metadata.txt to {export_dir}.")
    def clear_wavs(self):
        if not self.fs.current_folder:
            QMessageBox.critical(self, "Error", "No folder selected.")
            return
        wav_paths = self.fs.recordings_in()
        wav_files = [os.path.basename(p) for p in wav_paths]
        if not wav_files:
            QMessageBox.information(self, self.LABELS["clear_wavs"], self.LABELS["no_wavs_found"]) 
            return
        reply = QMessageBox.question(
            self,
            self.LABELS["confirm_delete_title"],
            f"Are you sure you want to delete {len(wav_files)} WAV files from this folder?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return
        errors = []
        for wav in wav_files:
            try:
                os.remove(os.path.join(self.fs.current_folder, wav))
            except Exception as e:
                errors.append(f"{wav}: {e}")
        default_content = (
            "name: \n"
            "date: \n"
            "location: \n"
            "researcher: \n"
            "speaker: \n"
            "permissions for use given by speaker: \n"
        )
        try:
            self.fs.write_metadata(default_content)
        except Exception as e:
            errors.append(f"metadata.txt reset: {e}")
        if errors:
            QMessageBox.critical(self, self.LABELS["delete_errors_title"], self.LABELS["delete_errors_msg_prefix"] + "\n".join(errors))
        else:
            QMessageBox.information(self, self.LABELS["clear_wavs"], self.LABELS["clear_success_msg_prefix"].format(count=len(wav_files)))
        self.load_video_files()
        self.update_video_file_checks()
    def import_wavs(self):
        if not self.fs.current_folder:
            QMessageBox.critical(self, "Error", "No folder selected.")
            return
        reply = QMessageBox.question(
            self,
            self.LABELS["confirm_import_title"],
            "Importing will delete all current WAV files and reset metadata. Are you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return
        wav_paths_existing = self.fs.recordings_in()
        wav_files = [os.path.basename(p) for p in wav_paths_existing]
        errors = []
        for wav in wav_files:
            try:
                os.remove(os.path.join(self.fs.current_folder, wav))
            except Exception as e:
                errors.append(f"Delete {wav}: {e}")
        import_dir = QFileDialog.getExistingDirectory(self, self.LABELS["import_select_folder_dialog"]) 
        if not import_dir:
            return
        try:
            import_paths = self.fs.recordings_in(import_dir)
            import_files = [os.path.basename(p) for p in import_paths]
        except Exception:
            import_files = [f for f in os.listdir(import_dir) if f.lower().endswith('.wav') and not f.startswith('.')]
        video_basenames = set(os.path.splitext(os.path.basename(f))[0] for f in self.video_files)
        mismatched_wavs = []
        imported_count = 0
        matched = False
        for wav in import_files:
            wav_basename = os.path.splitext(wav)[0]
            if wav_basename in video_basenames:
                matched = True
        metadata_src = os.path.join(import_dir, "metadata.txt")
        metadata_dst = os.path.join(self.fs.current_folder, "metadata.txt")
        if matched and os.path.exists(metadata_src):
            try:
                shutil.copy2(metadata_src, metadata_dst)
            except Exception as e:
                errors.append(f"metadata.txt import: {e}")
        else:
            default_content = (
                "name: \n"
                "date: \n"
                "location: \n"
                "researcher: \n"
                "speaker: \n"
                "permissions for use given by speaker: \n"
            )
            try:
                with open(metadata_dst, "w") as f:
                    f.write(default_content)
            except Exception as e:
                errors.append(f"metadata.txt create: {e}")
        overwrite_files = []
        for wav in import_files:
            wav_basename = os.path.splitext(wav)[0]
            if wav_basename in video_basenames:
                dst = os.path.join(self.fs.current_folder, wav)
                if os.path.exists(dst):
                    overwrite_files.append(wav)
        if os.path.exists(metadata_dst) and os.path.exists(metadata_src):
            overwrite_files.append("metadata.txt")
        if overwrite_files:
            reply = QMessageBox.question(
                self,
                self.LABELS["overwrite_files_title"],
                self.LABELS["overwrite_import_body_prefix"] + "\n".join(overwrite_files) + self.LABELS["overwrite_question_suffix"],
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                QMessageBox.information(self, self.LABELS["saved"], "Import was cancelled to avoid overwriting files.")
                return
        for wav in import_files:
            wav_basename = os.path.splitext(wav)[0]
            if wav_basename in video_basenames:
                src = os.path.join(import_dir, wav)
                dst = os.path.join(self.fs.current_folder, wav)
                try:
                    shutil.copy2(src, dst)
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Import {wav}: {e}")
            else:
                mismatched_wavs.append(wav)
        if mismatched_wavs:
            QMessageBox.warning(self, self.LABELS["wav_mismatch_title"], self.LABELS["wav_mismatch_msg_prefix"] + "\n".join(mismatched_wavs))
        if errors:
            QMessageBox.critical(self, self.LABELS["import_errors_title"], self.LABELS["import_errors_msg_prefix"] + "\n".join(errors))
        else:
            QMessageBox.information(self, self.LABELS["import_wavs"], self.LABELS["import_success_msg_prefix"].format(count=imported_count))
        self.load_video_files()
        self.update_video_file_checks()
    def join_all_wavs(self):
        if not self.fs.current_folder:
            QMessageBox.critical(self, self.LABELS["error_title"], self.LABELS["no_folder_selected"]) 
            return
        # Tab-aware: join recordings for the active tab
        try:
            active_index = self.right_panel.currentIndex() if getattr(self, 'right_panel', None) else 0
        except Exception:
            active_index = 0
        
        # Determine which recordings to join based on active tab
        if active_index == 1:  # Images tab
            wav_paths = self.fs.image_recordings_in()
        elif active_index == 2:  # Review tab
            # Get recordings from Review tab's filtered scope
            try:
                review_tab = getattr(self, 'review_tab', None)
                if review_tab:
                    items = review_tab._get_recorded_items()
                    wav_paths = [wav_path for _, _, wav_path in items]
                else:
                    wav_paths = self.fs.recordings_in()
            except Exception:
                wav_paths = self.fs.recordings_in()
        else:  # Videos tab (default)
            wav_paths = self.fs.video_recordings_in()
        if not wav_paths:
            QMessageBox.information(self, self.LABELS["no_files"], self.LABELS["no_wavs_found"]) 
            return
        ffmpeg_path = resource_path(os.path.join("ffmpeg", "bin", "ffmpeg"))
        if not os.path.exists(ffmpeg_path):
            QMessageBox.critical(self, self.LABELS["error_title"], self.LABELS["ffmpeg_not_found_msg"]) 
            return
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            self.LABELS["save_combined_wav_dialog_title"],
            "",
            "WAV files (*.wav)"
        )
        if not output_file:
            return
        self.join_thread = QThread()
        self.join_worker = JoinWavsWorker(output_file=output_file, fs=self.fs, file_paths=wav_paths)
        self.join_worker.moveToThread(self.join_thread)
        self.join_thread.started.connect(self.join_worker.run)
        self.join_worker.finished.connect(self.join_thread.quit)
        self.join_worker.finished.connect(self.join_worker.deleteLater)
        self.join_thread.finished.connect(self.join_thread.deleteLater)
        self.join_worker.success.connect(self._on_join_success)
        self.join_worker.error.connect(self._on_join_error)
        self.join_thread.start()
        self.update_video_file_checks()
    def generate_click_sound_pydub(self, duration_ms, freq, rate):
        t = np.linspace(0, duration_ms / 1000, int(rate * duration_ms / 1000), endpoint=False)
        sine_wave = np.sin(2 * np.pi * freq * t)
        decay = np.linspace(1, 0, len(sine_wave))
        click_data = sine_wave * decay
        click_data = (click_data * 0.5 * (2**15 - 1)).astype(np.int16).tobytes()
        return AudioSegment(
            data=click_data,
            sample_width=2,
            frame_rate=rate,
            channels=1
        )
    def update_video_file_checks(self):
        if not self.fs.current_folder:
            return
        for i in range(self.video_listbox.count()):
            item = self.video_listbox.item(i)
            name = item.text()
            wav_exists = os.path.exists(self.fs.wav_path_for(name))
            desired_icon = self._check_icon if wav_exists else self._empty_icon
            item.setIcon(desired_icon)
        # Update image badges
        try:
            # Just trigger repaint; delegate will render overlays based on wav existence
            if getattr(self, 'images_list', None):
                self.images_list.viewport().update()
        except Exception:
            pass
    def go_prev(self):
        if self.video_listbox.count() == 0:
            return
        row = self.video_listbox.currentRow()
        if row > 0:
            self.video_listbox.setCurrentRow(row - 1)
    def go_next(self):
        if self.video_listbox.count() == 0:
            return
        row = self.video_listbox.currentRow()
        if row < self.video_listbox.count() - 1:
            self.video_listbox.setCurrentRow(row + 1)
    def keyPressEvent(self, event):
        try:
            key = event.key()
        except Exception:
            return super().keyPressEvent(event)
        try:
            mods = event.modifiers()
            is_mac = sys.platform == 'darwin'
            # Secret: Cmd+Shift+L (mac) or Ctrl+Shift+L (others) opens log viewer
            if key == Qt.Key_L and (mods & Qt.ShiftModifier) and ((is_mac and (mods & Qt.MetaModifier)) or ((not is_mac) and (mods & Qt.ControlModifier))):
                self._show_log_viewer()
                event.accept()
                return
            # Secret: Cmd+Shift+F (mac) or Ctrl+Shift+F (others) shows ffmpeg/ffprobe diagnostics
            if key == Qt.Key_F and (mods & Qt.ShiftModifier) and ((is_mac and (mods & Qt.MetaModifier)) or ((not is_mac) and (mods & Qt.ControlModifier))):
                self._show_ffmpeg_diagnostics()
                event.accept()
                return
        except Exception:
            pass
        if key == Qt.Key_Right:
            self.go_next()
            event.accept()
            return
        if key == Qt.Key_Left:
            self.go_prev()
            event.accept()
            return
        return super().keyPressEvent(event)
    def resizeEvent(self, event):
        try:
            # Reduce listbox vertical size to ~75% of the left panel
            if getattr(self, 'left_panel', None) is not None and getattr(self, 'video_listbox', None) is not None:
                left_h = max(0, self.left_panel.height())
                # Reduce another ~10%: target ~65% of left panel height
                target_h = int(left_h * 0.65)
                min_h = 200
                self.video_listbox.setMaximumHeight(max(min_h, target_h))
        except Exception:
            pass
        # Recompute images grid sizes to maintain true two-column layout
        try:
            self._recompute_image_grid_sizes()
        except Exception:
            pass
        try:
            return super().resizeEvent(event)
        except Exception:
            pass
    def _show_log_viewer(self):
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
            dlg = QDialog(self)
            dlg.setWindowTitle("Debug Log")
            layout = QVBoxLayout(dlg)
            text = QTextEdit(dlg)
            text.setReadOnly(True)
            content = ""
            log_path = getattr(self, 'log_file_path', None)
            if log_path and os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        # Show last ~200 lines
                        lines = f.readlines()
                        content = ''.join(lines[-200:])
                except Exception as e:
                    content = f"Failed to read log: {e}"
            else:
                content = "No log file configured. Run with --debug --log-file <path>."
            text.setPlainText(content)
            layout.addWidget(text)
            close_btn = QPushButton("Close", dlg)
            close_btn.clicked.connect(dlg.accept)
            layout.addWidget(close_btn)
            dlg.resize(800, 500)
            dlg.exec()
        except Exception:
            QMessageBox.information(self, "Debug Log", "Unable to display log.")
    def _show_ffmpeg_diagnostics(self):
        try:
            from vat.utils.resources import resolve_ff_tools
            info = resolve_ff_tools()
            ffm = info.get('ffmpeg') or 'none'
            ffp = info.get('ffprobe') or 'none'
            srcm = info.get('ffmpeg_origin')
            srcp = info.get('ffprobe_origin')
            msg = (
                f"FFmpeg: {ffm}\n"
                f"  origin: {srcm}\n"
                f"FFprobe: {ffp}\n"
                f"  origin: {srcp}\n"
            )
            QMessageBox.information(self, "FF Tools Diagnostics", msg)
        except Exception as e:
            QMessageBox.information(self, "FF Tools Diagnostics", f"Error: {e}")
    def eventFilter(self, obj, event):
        if obj is self.video_label:
            try:
                if event.type() == QEvent.MouseButtonDblClick and self.current_video and self.fs.current_folder:
                    self._open_fullscreen_video()
                    return True
                # Right-click context menu on video frame
                if event.type() == QEvent.MouseButtonPress:
                    try:
                        from PySide6.QtGui import QMouseEvent
                    except Exception:
                        QMouseEvent = None
                    try:
                        btn = event.button() if hasattr(event, 'button') else None
                    except Exception:
                        btn = None
                    if btn == Qt.RightButton:
                        try:
                            global_pos = event.globalPos() if hasattr(event, 'globalPos') else None
                        except Exception:
                            global_pos = None
                        try:
                            self._on_video_frame_context_menu(global_pos)
                        except Exception:
                            pass
                        return True
            except Exception:
                pass
            try:
                self._position_badge()
            except Exception:
                pass
        # Keep images grid sizing in sync with show/resize events
        try:
            if obj is getattr(self, 'images_list', None):
                if event.type() in (QEvent.Show, QEvent.Resize):
                    self._recompute_image_grid_sizes()
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _on_video_frame_context_menu(self, global_pos: QPoint | None):
        """Show Copy/Save As/Reveal menu for the current video on the frame."""
        try:
            # Build menu with required ordering
            menu = QMenu(self)
            copy_act = QAction(self.LABELS.get("copy_video", "Copy Video"), self)
            copy_act.triggered.connect(self._copy_current_video_to_clipboard)
            menu.addAction(copy_act)
            save_act = QAction(self.LABELS.get("save_video_as", "Save Video as…"), self)
            save_act.triggered.connect(self._save_current_video_as)
            menu.addAction(save_act)
            # Platform-specific label for Reveal
            label = self._platform_reveal_label()
            reveal_act = QAction(label, self)
            reveal_act.triggered.connect(self._reveal_current_video_with_warning)
            menu.addAction(reveal_act)
            # Position
            if global_pos:
                menu.exec(global_pos)
            else:
                try:
                    menu.exec(QCursor.pos())
                except Exception:
                    pass
        except Exception:
            pass

    def _platform_reveal_label(self) -> str:
        """Return OS-appropriate label for reveal action."""
        try:
            import sys
            if sys.platform.startswith("darwin"):
                return self.LABELS.get("reveal_in_finder", "Reveal in Finder")
            if sys.platform.startswith("win"):
                return self.LABELS.get("reveal_in_explorer", "Reveal in Explorer")
            return self.LABELS.get("reveal_in_file_manager", "Reveal in File Manager")
        except Exception:
            return "Reveal in File Manager"

    def _reveal_current_video_with_warning(self):
        """Warn if the current video is not MP4, then reveal if confirmed."""
        try:
            path = self._resolve_current_video_path()
            if not (path and os.path.exists(path)):
                return
            ext = os.path.splitext(path)[1].lower()
            if ext and ext != ".mp4":
                title = self.LABELS.get("non_mp4_reveal_warn_title", "Not an MP4")
                reveal_lbl = self._platform_reveal_label()
                msg = (
                    self.LABELS.get(
                        "non_mp4_reveal_warn_msg_simple",
                        "This video is not in MP4 format.\n\nWhatsApp and many other common apps can only play MP4 videos. Please Cancel now, click 'Convert to MP4', then try again.\n\n{action} anyway?",
                    )
                )
                try:
                    msg_fmt = msg.format(action=reveal_lbl)
                except Exception:
                    msg_fmt = msg
                resp = QMessageBox.question(
                    self,
                    title,
                    msg_fmt,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if resp != QMessageBox.Yes:
                    return
            self._reveal_in_file_manager(path)
        except Exception:
            pass

    def _reveal_in_file_manager(self, path: str | None):
        """Reveal the given file in the OS file manager (select/highlight if supported)."""
        try:
            if not path:
                return
            if not os.path.exists(path):
                return
            import sys
            if sys.platform.startswith("darwin"):
                try:
                    subprocess.run(["open", "-R", path], check=False)
                    return
                except Exception:
                    pass
            elif sys.platform.startswith("win"):
                try:
                    subprocess.run(["explorer", f"/select,", path], check=False)
                    return
                except Exception:
                    pass
            else:
                try:
                    # Reveal containing folder; selection not universally supported
                    folder = os.path.dirname(path)
                    if folder:
                        subprocess.run(["xdg-open", folder], check=False)
                        return
                except Exception:
                    pass
            # Fallback: try opening the folder via desktop services if available
            try:
                from PySide6.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
            except Exception:
                pass
        except Exception:
            pass

    def _show_welcome_dialog(self):
        """Display a brief purpose + best-practices message on startup."""
        try:
            title = self.LABELS.get(
                "welcome_dialog_title",
                LABELS_ALL["English"]["welcome_dialog_title"],
            )
            body = self.LABELS.get(
                "welcome_dialog_body_html",
                LABELS_ALL["English"]["welcome_dialog_body_html"],
            )
            try:
                from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
                from PySide6.QtCore import Qt
            except Exception:
                # Fallback if widgets cannot be imported for some reason
                QMessageBox.information(self, title, body)
                return

            dlg = QDialog(self)
            dlg.setWindowTitle(title)
            layout = QVBoxLayout(dlg)
            try:
                layout.setContentsMargins(16, 10, 16, 10)
                layout.setSpacing(8)
            except Exception:
                pass

            label = QLabel(dlg)
            label.setTextFormat(Qt.RichText)
            label.setWordWrap(True)
            try:
                label.setOpenExternalLinks(True)
            except Exception:
                pass
            label.setText(body)
            layout.addWidget(label)

            btn_row = QHBoxLayout()
            btn_row.addStretch(1)
            ok_btn = QPushButton("OK", dlg)
            ok_btn.clicked.connect(dlg.accept)
            btn_row.addWidget(ok_btn)
            layout.addLayout(btn_row)

            # Make the dialog wider but slightly shorter to reduce empty space
            try:
                current_size = dlg.sizeHint()
                # Target ~1.25x typical width, with a reasonable minimum
                new_w = max(720, int(current_size.width() * 1.25))
                # Reduce minimum height to trim top/bottom whitespace
                new_h = max(440, current_size.height())
                dlg.resize(new_w, new_h)
            except Exception:
                dlg.resize(720, 460)

            dlg.exec()
        except Exception:
            pass

    def _open_docs_site(self, _link: str = "internal:docs#default"):
        """Open the bundled documentation site in a pywebview window."""
        try:
            import subprocess, sys
            from vat.utils.resources import resource_path
            # Resolve bundled docs path (PyInstaller-aware)
            index_path = resource_path(os.path.join("docs", "gpa", "index.html"), check_system=False)
            # Support internal anchors like internal:docs#section
            frag = None
            try:
                if isinstance(_link, str) and "#" in _link:
                    frag = _link.split("#", 1)[1]
            except Exception:
                frag = None
            if not os.path.exists(index_path):
                # Fallback: bundled full docs
                index_path = resource_path(os.path.join("docs", "index.html"), check_system=False)
            # Launch a separate process to avoid interfering with the Qt event loop
            if frag:
                cmd = [sys.executable, "-m", "vat.ui.docs_webview", index_path, frag]
            else:
                cmd = [sys.executable, "-m", "vat.ui.docs_webview", index_path]
            subprocess.Popen(cmd)
        except Exception as e:
            try:
                QMessageBox.information(self, "Documentation", f"Unable to open documentation window: {e}")
            except Exception:
                pass

    # --- Images tab helpers (moved back into VideoAnnotationApp) ---
    def _open_fullscreen_video(self):
        try:
            if not self.current_video or not self.fs.current_folder:
                return
            if getattr(self, '_fullscreen_viewer', None) is not None:
                try:
                    if self._fullscreen_viewer.isVisible():
                        self._fullscreen_viewer.raise_()
                        self._fullscreen_viewer.activateWindow()
                        self._fullscreen_viewer.setFocus()
                        return
                except Exception:
                    pass
            video_path = self._resolve_current_video_path()
            viewer = FullscreenVideoViewer(video_path)
            self._fullscreen_viewer = viewer
            viewer.showFullScreen()
            try:
                viewer.raise_()
                viewer.activateWindow()
                viewer.setFocus()
            except Exception:
                pass
            try:
                viewer.scale_changed.connect(self._on_fullscreen_scale_changed)
                viewer.destroyed.connect(self._on_fullscreen_closed)
            except Exception:
                pass
        except Exception as e:
            logging.error(f"Failed to open fullscreen viewer: {e}")

    def _open_fullscreen_image(self, item=None):
        try:
            if getattr(self, 'images_list', None) is None:
                return
            # Reuse existing fullscreen viewer if still visible
            try:
                if getattr(self, '_fullscreen_viewer', None) is not None and self._fullscreen_viewer.isVisible():
                    self._fullscreen_viewer.raise_()
                    self._fullscreen_viewer.activateWindow()
                    self._fullscreen_viewer.setFocus()
                    return
            except Exception:
                pass
            if item is None:
                sel = self.images_list.currentItem()
                if sel is None:
                    return
            else:
                sel = item
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                if not (self.fs.current_folder and name):
                    return
                path = os.path.join(self.fs.current_folder, name)

            # Use any cached pixmap if available so the fullscreen viewer
            # can display immediately on first open.
            cached_pix = None
            try:
                cache = getattr(self, "_image_pixmap_cache", None)
                if cache:
                    cached_pix = cache.get(path)
            except Exception:
                cached_pix = None

            # Always attempt to open the fullscreen viewer; any image-loading
            # issues are handled defensively inside FullscreenImageViewer.
            viewer = FullscreenImageViewer(path, pixmap=cached_pix)
            self._fullscreen_viewer = viewer
            viewer.showFullScreen()
            try:
                viewer.raise_()
                viewer.activateWindow()
                viewer.setFocus()
            except Exception:
                pass
            try:
                viewer.scale_changed.connect(self._on_fullscreen_scale_changed)
                viewer.destroyed.connect(self._on_fullscreen_closed)
            except Exception:
                pass
        except Exception as e:
            logging.error(f"Failed to open fullscreen image viewer: {e}")

    def _toggle_image_labels(self, checked: bool):
        try:
            self.show_image_labels = bool(checked)
            files = []
            for i in range(self.images_list.count()):
                it = self.images_list.item(i)
                fp = it.data(Qt.UserRole)
                if fp:
                    files.append(fp)
            if not files:
                files = self.fs.list_images()
            self._populate_images_list(files)
            try:
                self._recompute_image_grid_sizes()
            except Exception:
                pass
        except Exception:
            pass

    def _load_image_pixmap(self, path: str | None):
        """Load or retrieve a cached full-resolution pixmap for an image.

        Uses QImageReader first for robustness, then falls back to
        QPixmap. Successful loads are stored in self._image_pixmap_cache
        so later fullscreen opens do not pay a first-decode penalty.
        """
        if not path:
            return None
        try:
            cache = getattr(self, "_image_pixmap_cache", None)
            if cache is None:
                self._image_pixmap_cache = {}
                cache = self._image_pixmap_cache
        except Exception:
            return None
        pix = cache.get(path)
        if pix is not None and not pix.isNull():
            return pix
        try:
            pix = QPixmap(path)
            if pix.isNull():
                try:
                    reader = QImageReader(path)
                    img = reader.read()
                    if img and not img.isNull():
                        pix = QPixmap.fromImage(img)
                except Exception:
                    pass
            if pix is None or pix.isNull():
                return None
            cache[path] = pix
            return pix
        except Exception:
            return None

    def _preload_visible_images(self):
        """Warm the pixmap cache for all items currently visible in the grid."""
        try:
            if getattr(self, 'images_list', None) is None:
                return
            viewport = self.images_list.viewport()
            if viewport is None:
                return
            vp_rect = viewport.rect()
            for i in range(self.images_list.count()):
                item = self.images_list.item(i)
                if item is None:
                    continue
                rect = self.images_list.visualItemRect(item)
                if (not rect.isValid()) or (not rect.intersects(vp_rect)):
                    continue
                path = None
                try:
                    path = item.data(Qt.UserRole)
                except Exception:
                    path = None
                if not path:
                    name = item.text()
                    if self.fs.current_folder and name:
                        path = os.path.join(self.fs.current_folder, name)
                if path:
                    self._load_image_pixmap(path)
        except Exception:
            pass

    def _populate_images_list(self, files: list):
        try:
            if getattr(self, 'images_list', None) is None:
                return
            self.images_list.clear()
            try:
                self._recompute_image_grid_sizes()
            except Exception:
                pass
            icon_size = self.images_list.iconSize()
            count = 0
            for full in files:
                name = os.path.basename(full)
                item_text = name if getattr(self, 'show_image_labels', False) else ""
                item = QListWidgetItem(item_text)
                try:
                    item.setData(Qt.UserRole, full)
                except Exception:
                    pass
                try:
                    pix = self._load_image_pixmap(full)
                    if pix is not None and not pix.isNull():
                        thumb = pix.scaled(icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        item.setIcon(QIcon(thumb))
                    else:
                        item.setIcon(self._empty_icon)
                except Exception:
                    item.setIcon(self._empty_icon)
                self.images_list.addItem(item)
                count += 1
            if count > 0:
                self.images_list.setCurrentRow(0)
            # Delegate repaint checks; selection change will trigger banner update
            self.update_video_file_checks()
            try:
                logging.info(f"Images tab populated: count={count}; sample={[os.path.basename(f) for f in files[:3]]}")
            except Exception:
                pass
            # Avoid manual select handlers here; currentItemChanged will fire
        except Exception as e:
            logging.warning(f"Failed to refresh images from FS manager: {e}")
        # Warm the cache for the thumbnails that are currently visible.
        try:
            self._preload_visible_images()
        except Exception:
            pass

    def _recompute_image_grid_sizes(self):
        if getattr(self, 'images_list', None) is None:
            return
        try:
            vp = self.images_list.viewport()
            vpw = vp.width() if vp is not None else self.images_list.width()
            try:
                fw = int(getattr(self.images_list, 'frameWidth', lambda: 0)())
            except Exception:
                fw = 0
            vpw = max(50, vpw - (fw * 2))
            try:
                sbw = int(self.images_list.verticalScrollBar().width())
                if sbw <= 0:
                    sbw = 12
            except Exception:
                sbw = 12
            vpw = max(100, vpw - sbw)
            try:
                spacing = int(self.images_list.spacing())
            except Exception:
                spacing = 8
            # Auto-adjust columns based on available width and user scale
            usable = max(120, vpw - spacing * 3)
            min_col_w = int(160 * max(0.5, min(1.8, getattr(self, 'images_thumb_scale', 1.0))))
            cols = max(1, usable // max(120, min_col_w))
            total_spacing = spacing * (cols + 1)
            usable = max(120, vpw - total_spacing)
            col_w = max(min_col_w, usable // max(1, cols))
            icon_w = int(col_w * 0.90)
            icon_h = int(icon_w * 3 / 4)
            label_h = 18 if getattr(self, 'show_image_labels', False) else 0
            grid_w = max(100, col_w)
            grid_h = icon_h + label_h + 10
            self.images_list.setIconSize(QSize(icon_w, icon_h))
            self.images_list.setGridSize(QSize(grid_w, grid_h))
            try:
                logging.debug(f"UI._recompute_image_grid_sizes: vpw={vpw}, fw={fw}, sbw={sbw}, usable={usable}, col_w={col_w}, icon=({icon_w}x{icon_h}), grid=({grid_w}x{grid_h}), spacing={spacing}")
            except Exception:
                pass
        except Exception:
            pass

    def _on_images_updated(self, *args):
        # Support both legacy (files) and new (folder, files) signal forms
        if len(args) == 2:
            folder, files = args
        elif len(args) == 1:
            folder, files = "", args[0]
        else:
            return
        try:
            active = self.fs.current_folder or ""
            if folder and os.path.normpath(folder) != os.path.normpath(active):
                try:
                    logging.warning(f"UI._on_images_updated: ignoring update for folder={folder}; active={active}")
                except Exception:
                    pass
                return
        except Exception:
            pass
        self._populate_images_list(files)

    def on_image_select(self):
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                try:
                    self.image_thumb.clear()
                except Exception:
                    pass
                self.play_image_audio_button.setEnabled(False)
                self.stop_image_audio_button.setEnabled(False)
                self.record_image_button.setEnabled(False)
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            try:
                logging.debug(f"UI.on_image_select: path={path}")
            except Exception:
                pass
            try:
                pix = self._load_image_pixmap(path)
                if pix is not None and not pix.isNull():
                    self.image_thumb.setPixmap(pix.scaled(self.image_thumb.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    self.image_thumb.clear()
            except Exception:
                pass
            # Update image-related controls (play/stop and record/stop-record)
            try:
                self._update_image_record_controls(path)
            except Exception:
                pass
            try:
                logging.debug(f"UI.on_image_select: selected='{os.path.basename(path)}', wav_exists={exists}")
            except Exception:
                pass
        except Exception:
            pass

    def _update_image_record_controls(self, path: str | None = None):
        try:
            # Resolve current selection path if not provided
            if not path:
                sel = self.images_list.currentItem()
                if sel is not None:
                    try:
                        path = sel.data(Qt.UserRole) or os.path.join(self.fs.current_folder or "", sel.text())
                    except Exception:
                        path = None
            # Resolve existing audio with compatibility (legacy basename.wav, root folder)
            resolved = self.fs.find_existing_image_audio(path or "")
            wav_path = resolved or self.fs.wav_path_for_image(path or "")
            exists = bool(resolved)
            # Play/Stop audio reflect wav existence, but disable Play while actively playing
            self.play_image_audio_button.setEnabled(exists and not self.is_playing_audio)
            self.stop_image_audio_button.setEnabled(exists)
            # Record/Stop-Record reflect recording state
            if self.is_recording:
                self.record_image_button.setEnabled(False)
                self.stop_image_record_button.setEnabled(True)
                if getattr(self, 'add_image_audio_button', None):
                    self.add_image_audio_button.setEnabled(False)
            else:
                self.record_image_button.setEnabled(True)
                self.stop_image_record_button.setEnabled(False)
                if getattr(self, 'add_image_audio_button', None):
                    # Enable import when an image is selected
                    self.add_image_audio_button.setEnabled(bool(path))
            try:
                logging.debug(f"UI._update_image_record_controls: wav_path={wav_path}, exists={exists}, is_recording={self.is_recording}")
            except Exception:
                pass
            # Trigger repaint so delegate overlays reflect current state
            try:
                self.images_list.viewport().update()
            except Exception:
                pass
        except Exception:
            pass

    def play_image_audio(self):
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            # Resolve existing audio; play if found
            wav_path = self.fs.find_existing_image_audio(path) or self.fs.wav_path_for_image(path)
            if not (wav_path and os.path.exists(wav_path)):
                return
            # Re-entrancy guard: ignore if already playing
            if self.is_playing_audio:
                return
            if not PYAUDIO_AVAILABLE:
                QMessageBox.warning(self, "Error", "PyAudio is not available. Cannot play audio.")
                return
            # Mark playing and update UI (disable Play, enable Stop)
            self.is_playing_audio = True
            try:
                self.play_image_audio_button.setEnabled(False)
                self.stop_image_audio_button.setEnabled(True)
            except Exception:
                pass
            try:
                # Also disable videos tab Play if present
                if getattr(self, 'play_audio_button', None):
                    self.play_audio_button.setEnabled(False)
            except Exception:
                pass
            # Use persistent audio thread (created in __init__) for playback
            self.audio_worker = AudioPlaybackWorker(wav_path)
            self.audio_worker.moveToThread(self.audio_thread)
            try:
                from PySide6.QtCore import QMetaObject
                QMetaObject.invokeMethod(self.audio_worker, "run", Qt.QueuedConnection)
            except Exception:
                # Fallback: start thread if not already running and connect
                try:
                    if self.audio_thread and not self.audio_thread.isRunning():
                        self.audio_thread.start()
                    self.audio_thread.started.connect(self.audio_worker.run)
                except Exception:
                    pass
            # Re-enable controls when playback finishes
            self.audio_worker.finished.connect(self._on_any_audio_finished)
            self.audio_worker.error.connect(self._show_worker_error)
        except Exception:
            pass

    def _on_any_audio_finished(self):
        """Shared handler to re-enable Play buttons after audio playback completes."""
        try:
            logging.info("UI.audio: finished")
        except Exception:
            pass
        self.is_playing_audio = False
        # Restore Play button texts
        try:
            if getattr(self, 'play_audio_button', None):
                self.play_audio_button.setText(self.LABELS.get("play_audio", "Play Audio"))
        except Exception:
            pass
        try:
            if getattr(self, 'play_image_audio_button', None):
                self.play_image_audio_button.setText(self.LABELS.get("play_audio", "Play Audio"))
        except Exception:
            pass
        try:
            self.update_media_controls()
        except Exception:
            pass
        try:
            self._update_image_record_controls()
        except Exception:
            pass

    def stop_image_audio(self):
        self.stop_audio()

    def toggle_image_recording(self):
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            # If any existing audio (including legacy paths) exists, confirm overwrite
            existing = self.fs.find_existing_image_audio(path)
            wav_path = self.fs.wav_path_for_image(path)
            if existing and os.path.exists(existing):
                reply = QMessageBox.question(self, self.LABELS["overwrite"], 
                                            self.LABELS["overwrite_audio"],
                                            QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    return
            if not PYAUDIO_AVAILABLE:
                QMessageBox.warning(self, "Error", "PyAudio is not available. Cannot record audio.")
                return
            self.is_recording = True
            try:
                self.statusBar().showMessage(self.LABELS.get("recording_started", "Recording started"), 2000)
            except Exception:
                pass
            # Update controls: disable Record, enable Stop Recording
            try:
                self._update_image_record_controls(path)
            except Exception:
                pass
            self.recording_thread = QThread()
            self.recording_worker = AudioRecordingWorker(wav_path)
            self.recording_worker.moveToThread(self.recording_thread)
            self.recording_thread.started.connect(self.recording_worker.run)
            self.recording_worker.finished.connect(self.recording_thread.quit)
            self.recording_worker.finished.connect(self.recording_worker.deleteLater)
            self.recording_thread.finished.connect(self.recording_thread.deleteLater)
            self.recording_worker.finished.connect(self.update_video_file_checks)
            self.recording_thread.finished.connect(self._on_recording_thread_finished)
            self.recording_worker.error.connect(self._show_worker_error)
            self.recording_thread.start()
        except Exception:
            pass

    def stop_image_recording(self):
        try:
            if not self.is_recording:
                return
            # Request worker stop
            if self.recording_worker:
                try:
                    self.recording_worker.stop()
                except RuntimeError:
                    pass
            # Quit and wait for thread
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
            self.is_recording = False
            # Update controls after stop
            try:
                self._update_image_record_controls()
            except Exception:
                pass
            try:
                self.statusBar().showMessage(self.LABELS.get("recording_stopped", "Recording stopped"), 2000)
            except Exception:
                pass
            self.update_video_file_checks()
            try:
                # Update the images grid visuals
                self.images_list.viewport().update()
            except Exception:
                pass
        except Exception:
            pass

    def _on_fullscreen_scale_changed(self, scale: float):
        try:
            if isinstance(scale, (int, float)) and scale > 0:
                self.fullscreen_zoom = float(scale)
        except Exception:
            pass

    def _on_fullscreen_closed(self, *args):
        try:
            self._fullscreen_viewer = None
            self.save_settings()
        except Exception:
            pass

    def _position_badge(self):
        if not getattr(self, 'badge_label', None):
            return
        w = self.video_label.width()
        if not w or w <= 0:
            try:
                w = max(0, int(self.video_label.minimumWidth()))
            except Exception:
                w = 480
        h = self.video_label.height()
        bw = self.badge_label.width()
        x = max(0, w - bw - 8)
        y = 8
        self.badge_label.move(x, y)
        try:
            self.badge_label.raise_()
        except Exception:
            pass

    # _position_format_badge removed with format badge


class ImageGridDelegate(QStyledItemDelegate):
    def __init__(self, fs_manager: FolderAccessManager, parent=None):
        super().__init__(parent)
        self.fs = fs_manager

    def paint(self, painter, option, index):
        # Default painting first (thumbnail + optional text)
        super().paint(painter, option, index)
        try:
            path = index.data(Qt.UserRole)
            if not path:
                name = index.data(Qt.DisplayRole) or ""
                parent_folder = getattr(getattr(self.parent(), 'fs', None), 'current_folder', None)
                if parent_folder and name:
                    path = os.path.join(parent_folder, name)
            wav_path = self.fs.wav_path_for_image(path or "")
            has_wav = bool(wav_path and os.path.exists(wav_path))
        except Exception:
            has_wav = False
        if not has_wav:
            return
        try:
            painter.save()
            # Green border around icon area
            pen = QPen(QColor("#2ecc71"))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            r = option.rect
            ds = getattr(option, 'decorationSize', QSize(0, 0))
            iw = max(1, ds.width())
            ih = max(1, ds.height())
            x = r.x() + (r.width() - iw) // 2
            y = r.y() + 5
            icon_rect = QRect(x, y, iw, ih)
            painter.drawRect(icon_rect.adjusted(1, 1, -1, -1))
            # Small check overlay in the top-right of the icon
            try:
                chk = QApplication.style().standardIcon(QStyle.SP_DialogApplyButton).pixmap(18, 18)
                ox = icon_rect.right() - 18 - 4
                oy = icon_rect.top() + 4
                painter.drawPixmap(QPoint(ox, oy), chk)
            except Exception:
                pass
        finally:
            try:
                painter.restore()
            except Exception:
                pass
