"""Dialogs for the optional normalize-on-export step.

* :class:`NormalizeSettingsDialog` edits the settings dict consumed by
  :mod:`vat.audio.normalizer` (same keys as the Bulk Audio Normalizer).
* :class:`NormalizeProgressDialog` is a progress dialog whose slots are bound
  methods, so background workers can drive it across threads safely, and
  whose Cancel is guarded so closing it after success never cancels anything.

Both take the app's label dictionary and fall back to English for any key a
translation does not carry yet.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QProgressDialog, QPushButton, QSpinBox,
    QToolButton, QVBoxLayout, QWidget,
)

from vat.audio.normalizer import DEFAULT_SETTINGS, normalize_settings


# Keys and English fallbacks shared by the dialog and the drawer controls.
ENGLISH = {
    "normalize_on_export": "Normalize audio when exporting",
    "normalize_on_export_tip": (
        "When checked, 'Export Recorded Data' and 'Export as Single Sound File' normalize "
        "every recording on the way out (the same processing as the Bulk Audio Normalizer). "
        "Your original recordings are never changed."
    ),
    "normalize_settings_btn": "Settings…",
    "normalize_settings_title": "Normalization Settings (Export)",
    "normalize_settings_intro": "Applied to each recording while exporting. Your original recordings are never modified.",
    "normalize_intent": "Normalization intent:",
    "normalize_intent_peak": "Acoustic analysis / language documentation (peak dBFS)",
    "normalize_intent_lufs": "Participatory listening / human ears (LUFS + limiter)",
    "normalize_intent_hint_peak": (
        "Boosts quiet recordings so their loudest point reaches the target peak. No limiter or "
        "compression, so amplitude relationships stay intact (best for Praat and measurement)."
    ),
    "normalize_intent_hint_lufs": (
        "Two-pass EBU R128 loudness normalization followed by a safety limiter, for consistent "
        "perceived loudness when listening."
    ),
    "normalize_bit_depth": "Bit depth:",
    "normalize_bit_depth_original": "Keep each recording's bit depth (recommended)",
    "normalize_bit_depth_16": "16-bit (smaller files, widest compatibility)",
    "normalize_bit_depth_24": "24-bit (16-bit recordings stay 16-bit)",
    "normalize_bit_depth_hint": "Applies to 'Export Recorded Data'. The single sound file is always written as 48 kHz / 32-bit.",
    "normalize_auto_trim": "Auto-trim leading and trailing silence",
    "normalize_advanced": "Advanced…",
    "normalize_peak_target": "Peak target (dBFS):",
    "normalize_peak_only_boost": "Only boost quiet recordings (never turn loud ones down)",
    "normalize_lufs_target": "Loudness target (LUFS):",
    "normalize_tp_target": "True-peak target (dBTP):",
    "normalize_limiter": "Limiter ceiling (0–1, linear):",
    "normalize_fast": "Fast normalize (single pass, less accurate)",
    "normalize_trim_pad": "Keep padding on each side (ms):",
    "normalize_trim_threshold": "Silence threshold (dBFS):",
    "normalize_trim_min_silence": "Minimum silence duration (ms):",
    "normalize_trim_min_file": "Only trim recordings longer than (ms):",
    "normalize_trim_conservative": "Conservative trim (safer for soft voices)",
    "normalize_trim_hpf": "Ignore low rumble when detecting silence (80 Hz high-pass)",
    "normalize_reset_defaults": "Reset to defaults",
    "normalize_progress_title": "Normalizing Recordings",
    "normalize_progress_file": "Normalizing {i} of {n}: {name}",
    "join_progress_title": "Exporting Single Sound File",
    "join_progress_file": "Joining {i} of {n}: {name}",
    "join_progress_write": "Writing {name}…",
    "normalize_export_done": "Exported {count} normalized WAV files and metadata.txt to {dir}.",
    "normalize_export_partial": "{count} recording(s) could not be normalized and were copied unchanged:",
    "normalize_export_cancelled": "Export cancelled. {done} of {total} files were written to {dir}.",
    "join_cancelled": "Export cancelled. No file was written.",
    "ok": "OK",
    "cancel": "Cancel",
}


def label(labels: Optional[Dict[str, str]], key: str) -> str:
    """The translated label, or its English fallback."""
    if labels:
        value = labels.get(key)
        if isinstance(value, str) and value:
            return value
    return ENGLISH.get(key, key)


class NormalizeSettingsDialog(QDialog):
    """Edit normalize-on-export settings; :meth:`settings` returns the result."""

    def __init__(self, settings: Optional[Dict] = None, parent=None, labels: Optional[Dict[str, str]] = None):
        super().__init__(parent)
        self.LABELS = labels or {}
        self._initial = normalize_settings(settings)
        self.setWindowTitle(self._l("normalize_settings_title"))
        self.setMinimumWidth(520)
        self._build()
        self._apply(self._initial)

    # -- helpers -------------------------------------------------------------------

    def _l(self, key: str) -> str:
        return label(self.LABELS, key)

    @staticmethod
    def _hint(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #666; padding: 0 0 6px 0;")
        return lbl

    # -- UI ------------------------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)

        intro = QLabel(self._l("normalize_settings_intro"))
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.intent_combo = QComboBox()
        self.intent_combo.addItem(self._l("normalize_intent_peak"), "peak")
        self.intent_combo.addItem(self._l("normalize_intent_lufs"), "lufs")
        form.addRow(self._l("normalize_intent"), self.intent_combo)
        self.intent_hint = self._hint("")
        form.addRow("", self.intent_hint)

        self.depth_combo = QComboBox()
        self.depth_combo.addItem(self._l("normalize_bit_depth_original"), "original")
        self.depth_combo.addItem(self._l("normalize_bit_depth_16"), 16)
        self.depth_combo.addItem(self._l("normalize_bit_depth_24"), 24)
        form.addRow(self._l("normalize_bit_depth"), self.depth_combo)
        form.addRow("", self._hint(self._l("normalize_bit_depth_hint")))

        self.trim_cb = QCheckBox(self._l("normalize_auto_trim"))
        form.addRow("", self.trim_cb)
        root.addLayout(form)

        # Advanced (collapsed by default)
        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setText(self._l("normalize_advanced"))
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setChecked(False)
        self.advanced_toggle.setArrowType(Qt.RightArrow)
        self.advanced_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.advanced_toggle.setAutoRaise(True)
        root.addWidget(self.advanced_toggle)

        self.advanced_box = QWidget()
        adv = QVBoxLayout(self.advanced_box)
        adv.setContentsMargins(12, 0, 0, 0)

        # Peak section
        self.peak_group = QGroupBox(self._l("normalize_intent_peak"))
        pf = QFormLayout(self.peak_group)
        self.peak_target = QDoubleSpinBox()
        self.peak_target.setRange(-40.0, 0.0)
        self.peak_target.setSingleStep(0.5)
        self.peak_target.setDecimals(1)
        self.peak_target.setSuffix(" dBFS")
        pf.addRow(self._l("normalize_peak_target"), self.peak_target)
        self.peak_only_boost = QCheckBox(self._l("normalize_peak_only_boost"))
        pf.addRow("", self.peak_only_boost)
        adv.addWidget(self.peak_group)

        # LUFS section
        self.lufs_group = QGroupBox(self._l("normalize_intent_lufs"))
        lf = QFormLayout(self.lufs_group)
        self.lufs_target = QDoubleSpinBox()
        self.lufs_target.setRange(-40.0, -5.0)
        self.lufs_target.setSingleStep(0.5)
        self.lufs_target.setDecimals(1)
        self.lufs_target.setSuffix(" LUFS")
        lf.addRow(self._l("normalize_lufs_target"), self.lufs_target)
        self.tp_target = QDoubleSpinBox()
        self.tp_target.setRange(-9.0, 0.0)
        self.tp_target.setSingleStep(0.1)
        self.tp_target.setDecimals(1)
        self.tp_target.setSuffix(" dBTP")
        lf.addRow(self._l("normalize_tp_target"), self.tp_target)
        self.limiter = QDoubleSpinBox()
        self.limiter.setRange(0.5, 1.0)
        self.limiter.setSingleStep(0.01)
        self.limiter.setDecimals(2)
        lf.addRow(self._l("normalize_limiter"), self.limiter)
        self.fast_cb = QCheckBox(self._l("normalize_fast"))
        lf.addRow("", self.fast_cb)
        adv.addWidget(self.lufs_group)

        # Trim section
        self.trim_group = QGroupBox(self._l("normalize_auto_trim"))
        tf = QFormLayout(self.trim_group)
        self.trim_pad = QSpinBox()
        self.trim_pad.setRange(0, 10000)
        self.trim_pad.setSingleStep(100)
        self.trim_pad.setSuffix(" ms")
        tf.addRow(self._l("normalize_trim_pad"), self.trim_pad)
        self.trim_threshold = QSpinBox()
        self.trim_threshold.setRange(-100, -10)
        self.trim_threshold.setSuffix(" dBFS")
        tf.addRow(self._l("normalize_trim_threshold"), self.trim_threshold)
        self.trim_min_silence = QSpinBox()
        self.trim_min_silence.setRange(0, 10000)
        self.trim_min_silence.setSingleStep(50)
        self.trim_min_silence.setSuffix(" ms")
        tf.addRow(self._l("normalize_trim_min_silence"), self.trim_min_silence)
        self.trim_min_file = QSpinBox()
        self.trim_min_file.setRange(0, 600000)
        self.trim_min_file.setSingleStep(100)
        self.trim_min_file.setSuffix(" ms")
        tf.addRow(self._l("normalize_trim_min_file"), self.trim_min_file)
        self.trim_conservative = QCheckBox(self._l("normalize_trim_conservative"))
        tf.addRow("", self.trim_conservative)
        self.trim_hpf = QCheckBox(self._l("normalize_trim_hpf"))
        tf.addRow("", self.trim_hpf)
        adv.addWidget(self.trim_group)

        self.advanced_box.setVisible(False)
        root.addWidget(self.advanced_box)

        # Buttons
        buttons = QHBoxLayout()
        self.reset_btn = QPushButton(self._l("normalize_reset_defaults"))
        self.reset_btn.setAutoDefault(False)
        buttons.addWidget(self.reset_btn)
        buttons.addStretch()
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText(self._l("ok"))
        self.button_box.button(QDialogButtonBox.Cancel).setText(self._l("cancel"))
        buttons.addWidget(self.button_box)
        root.addLayout(buttons)

        # Wiring
        self.advanced_toggle.toggled.connect(self._toggle_advanced)
        self.intent_combo.currentIndexChanged.connect(self._sync_sections)
        self.trim_cb.toggled.connect(self._sync_sections)
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    # -- state ---------------------------------------------------------------------

    def _toggle_advanced(self, shown: bool) -> None:
        self.advanced_toggle.setArrowType(Qt.DownArrow if shown else Qt.RightArrow)
        self.advanced_box.setVisible(shown)
        self.adjustSize()

    def _sync_sections(self, *_) -> None:
        mode = self.intent_combo.currentData()
        self.peak_group.setVisible(mode == "peak")
        self.lufs_group.setVisible(mode == "lufs")
        self.intent_hint.setText(self._l("normalize_intent_hint_lufs" if mode == "lufs" else "normalize_intent_hint_peak"))
        self.trim_group.setEnabled(self.trim_cb.isChecked())

    def _apply(self, s: Dict) -> None:
        s = normalize_settings(s)
        self.intent_combo.setCurrentIndex(max(0, self.intent_combo.findData(s["normMode"])))
        self.depth_combo.setCurrentIndex(max(0, self.depth_combo.findData(s["targetBitDepth"])))
        self.trim_cb.setChecked(bool(s["autoTrim"]))
        self.peak_target.setValue(float(s["peakTargetDb"]))
        self.peak_only_boost.setChecked(bool(s["peakOnlyBoost"]))
        self.lufs_target.setValue(float(s["lufsTarget"]))
        self.tp_target.setValue(float(s["tpMargin"]))
        self.limiter.setValue(float(s["limiterLimit"]))
        self.fast_cb.setChecked(bool(s["fastNormalize"]))
        self.trim_pad.setValue(int(s["trimPadMs"]))
        self.trim_threshold.setValue(int(s["trimThresholdDb"]))
        self.trim_min_silence.setValue(int(s["trimMinDurationMs"]))
        self.trim_min_file.setValue(int(s["trimMinFileMs"]))
        self.trim_conservative.setChecked(bool(s["trimConservative"]))
        self.trim_hpf.setChecked(bool(s["trimHPF"]))
        self._sync_sections()

    def reset_to_defaults(self) -> None:
        self._apply(dict(DEFAULT_SETTINGS))

    def settings(self) -> Dict[str, object]:
        """The settings as currently shown (validated and complete)."""
        base = dict(self._initial)   # keeps keys the dialog does not edit (threads, verbose)
        base.update({
            "normMode": self.intent_combo.currentData(),
            "targetBitDepth": self.depth_combo.currentData(),
            "autoTrim": self.trim_cb.isChecked(),
            "peakTargetDb": self.peak_target.value(),
            "peakOnlyBoost": self.peak_only_boost.isChecked(),
            "lufsTarget": self.lufs_target.value(),
            "tpMargin": self.tp_target.value(),
            "limiterLimit": self.limiter.value(),
            "fastNormalize": self.fast_cb.isChecked(),
            "trimPadMs": self.trim_pad.value(),
            "trimThresholdDb": self.trim_threshold.value(),
            "trimMinDurationMs": self.trim_min_silence.value(),
            "trimMinFileMs": self.trim_min_file.value(),
            "trimConservative": self.trim_conservative.isChecked(),
            "trimHPF": self.trim_hpf.isChecked(),
        })
        return normalize_settings(base)


class NormalizeProgressDialog(QProgressDialog):
    """Progress for a background normalize/join job.

    ``QProgressDialog`` emits ``canceled`` from its close event too, so a
    plain ``close()`` after success would cancel a finished job. ``finish()``
    marks the job done first; the cancel callback then does nothing.
    """

    def __init__(self, parent=None, labels: Optional[Dict[str, str]] = None,
                 title_key: str = "normalize_progress_title",
                 on_cancel: Optional[Callable[[], None]] = None):
        self.LABELS = labels or {}
        super().__init__("", label(self.LABELS, "cancel"), 0, 0, parent)
        self.setWindowTitle(label(self.LABELS, title_key))
        self.setWindowModality(Qt.WindowModal)
        self.setAutoClose(False)
        self.setAutoReset(False)
        self.setMinimumDuration(0)
        self.setMinimumWidth(420)
        self._done = False       # cancel requested or job finished: ignore further cancels
        self._finished = False
        self._on_cancel = on_cancel
        self.canceled.connect(self._cancel_clicked)

    def _cancel_clicked(self) -> None:
        if self._done:
            return
        self._done = True
        if self._on_cancel:
            try:
                self._on_cancel()
            except Exception:
                pass

    @property
    def cancel_requested(self) -> bool:
        return self._done and not self._finished

    @Slot(int, int, str)
    def show_normalize_progress(self, index: int, total: int, name: str) -> None:
        self.show_phase("normalize", index, total, name)

    @Slot(str, int, int, str)
    def show_phase(self, phase: str, index: int, total: int, name: str) -> None:
        if self._done:
            return
        if phase == "write":
            self.setRange(0, 0)
            self.setLabelText(label(self.LABELS, "join_progress_write").format(name=name))
            return
        key = "join_progress_file" if phase == "join" else "normalize_progress_file"
        self.setRange(0, max(1, total))
        self.setValue(min(index, max(1, total)))
        self.setLabelText(label(self.LABELS, key).format(i=index + 1, n=total, name=name))

    @Slot()
    def finish(self) -> None:
        """Close without emitting a cancel; safe to call more than once."""
        if self._finished:
            return
        self._finished = True
        self._done = True
        try:
            self.canceled.disconnect(self._cancel_clicked)
        except (RuntimeError, TypeError):
            pass
        try:
            self.close()
        except RuntimeError:
            pass
        self.deleteLater()


__all__ = ["ENGLISH", "label", "NormalizeSettingsDialog", "NormalizeProgressDialog"]
