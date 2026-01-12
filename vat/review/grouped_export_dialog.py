"""Grouped export dialog for Review Tab."""

import os
from typing import List, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QRadioButton, QButtonGroup, QFileDialog, QMessageBox,
    QCheckBox
)
from PySide6.QtCore import Qt

from vat.review.grouped_exporter import GroupedExporter


class GroupedExportDialog(QDialog):
    """Dialog for configuring and executing grouped export."""
    
    def __init__(self, items: List[Tuple[str, str, str]], default_items_per_folder: int = 12, parent=None, labels: dict = None):
        """Initialize the dialog.
        
        Args:
            items: List of (item_id, media_path, wav_path) tuples
            default_items_per_folder: Default value for items per folder
            parent: Parent widget
        """
        super().__init__(parent)
        self.items = items
        self.default_items_per_folder = default_items_per_folder
        self.result_metadata = None
        self.LABELS = labels or {}
        
        self.setWindowTitle(self.LABELS.get("group_export_title", "Grouped Export"))
        self.setMinimumWidth(400)
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Info label
        info = QLabel(self.LABELS.get("group_export_info", "Export {count} recorded items into organized group folders.").format(count=len(self.items)))
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Mode selection
        mode_group = QButtonGroup(self)
        
        self.items_per_folder_radio = QRadioButton(self.LABELS.get("group_export_items_per_folder", "Items per folder:"))
        self.items_per_folder_radio.setChecked(True)
        mode_group.addButton(self.items_per_folder_radio)
        layout.addWidget(self.items_per_folder_radio)
        
        items_layout = QHBoxLayout()
        items_layout.addSpacing(30)
        self.items_per_folder_spin = QSpinBox()
        self.items_per_folder_spin.setRange(1, 100)
        self.items_per_folder_spin.setValue(self.default_items_per_folder)
        items_layout.addWidget(self.items_per_folder_spin)
        items_layout.addStretch()
        layout.addLayout(items_layout)
        
        self.num_folders_radio = QRadioButton(self.LABELS.get("group_export_num_folders", "Number of folders:"))
        mode_group.addButton(self.num_folders_radio)
        layout.addWidget(self.num_folders_radio)
        
        folders_layout = QHBoxLayout()
        folders_layout.addSpacing(30)
        self.num_folders_spin = QSpinBox()
        self.num_folders_spin.setRange(1, len(self.items) if self.items else 1)
        self.num_folders_spin.setValue(min(5, len(self.items) if self.items else 1))
        folders_layout.addWidget(self.num_folders_spin)
        folders_layout.addStretch()
        layout.addLayout(folders_layout)
        
        # Preview
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("color: #666; padding: 8px;")
        self.preview_label.setWordWrap(True)
        layout.addWidget(self.preview_label)
        
        # Connect signals for live preview
        self.items_per_folder_radio.toggled.connect(self._update_preview)
        self.num_folders_radio.toggled.connect(self._update_preview)
        self.items_per_folder_spin.valueChanged.connect(self._update_preview)
        self.num_folders_spin.valueChanged.connect(self._update_preview)
        
        # Initial preview
        self._update_preview()
        
        # Copy/Move option
        self.copy_mode_check = QCheckBox(self.LABELS.get("group_export_copy_mode", "Copy files (default, safe)"))
        self.copy_mode_check.setChecked(True)
        self.copy_mode_check.setToolTip(self.LABELS.get("group_export_copy_mode_tip", "Uncheck to move files instead (use with caution)"))
        layout.addWidget(self.copy_mode_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        export_btn = QPushButton(self.LABELS.get("group_export_export_btn", "Export..."))
        export_btn.clicked.connect(self._on_export)
        button_layout.addWidget(export_btn)
        
        cancel_btn = QPushButton(self.LABELS.get("group_export_cancel_btn", "Cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _update_preview(self) -> None:
        """Update the preview text."""
        if not self.items:
            self.preview_label.setText(self.LABELS.get("group_export_preview_none", "No items to export."))
            return
        
        mode = "items_per_folder" if self.items_per_folder_radio.isChecked() else "number_of_folders"
        value = self.items_per_folder_spin.value() if mode == "items_per_folder" else self.num_folders_spin.value()
        
        groups = GroupedExporter.preview_groups(
            [(m, w) for _, m, w in self.items],
            mode=mode,
            value=value
        )
        
        preview_text = self.LABELS.get("group_export_preview_will_create", "Will create {n} folder(s):\n").format(n=len(groups))
        for i, group in enumerate(groups[:5], start=1):  # Show first 5
            preview_text += self.LABELS.get("group_export_preview_group_line", "  Group {i:02d}: {count} items\n").format(i=i, count=len(group))
        
        if len(groups) > 5:
            preview_text += self.LABELS.get("group_export_preview_more", "  ... and {extra} more folders\n").format(extra=len(groups) - 5)
        
        if groups and len(groups[-1]) != len(groups[0]):
            preview_text += self.LABELS.get("group_export_preview_last_note", "\nNote: Last folder has {count} items (remainder).").format(count=len(groups[-1]))
        
        self.preview_label.setText(preview_text)
    
    def _on_export(self) -> None:
        """Handle export button click."""
        if not self.items:
            QMessageBox.warning(
                self,
                self.LABELS.get("group_export_no_items_title", "No Items"),
                self.LABELS.get("group_export_no_items_msg", "No items to export.")
            )
            return
        
        # Select output directory
        output_dir = QFileDialog.getExistingDirectory(self, self.LABELS.get("group_export_select_dir", "Select Export Directory"))
        if not output_dir:
            return
        
        # Confirm if directory already has Group folders
        existing_groups = [f for f in os.listdir(output_dir) if f.startswith("Group ") and os.path.isdir(os.path.join(output_dir, f))]
        if existing_groups:
            reply = QMessageBox.question(
                self,
                self.LABELS.get("group_export_confirm_overwrite_title", "Confirm Overwrite"),
                self.LABELS.get("group_export_confirm_overwrite_msg", "The selected directory already contains {n} Group folder(s).\n\nExisting files may be overwritten. Continue?").format(n=len(existing_groups)),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Execute export
        mode = "items_per_folder" if self.items_per_folder_radio.isChecked() else "number_of_folders"
        value = self.items_per_folder_spin.value() if mode == "items_per_folder" else self.num_folders_spin.value()
        copy_or_move = "copy" if self.copy_mode_check.isChecked() else "move"
        
        try:
            self.result_metadata = GroupedExporter.export_groups(
                [(m, w) for _, m, w in self.items],
                output_dir,
                mode=mode,
                value=value,
                copy_or_move=copy_or_move,
            )
            
            QMessageBox.information(
                self,
                self.LABELS.get("group_export_complete_title", "Export Complete"),
                self.LABELS.get("group_export_complete_msg", "Successfully exported {items} items into {groups} folders.").format(items=self.result_metadata['totalItems'], groups=self.result_metadata['totalGroups'])
            )
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(
                self,
                self.LABELS.get("group_export_failed_title", "Export Failed"),
                f"{self.LABELS.get('group_export_failed_msg', 'Failed to export:')} {e}"
            )
