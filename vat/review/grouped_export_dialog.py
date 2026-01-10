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
    
    def __init__(self, items: List[Tuple[str, str, str]], default_items_per_folder: int = 12, parent=None):
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
        
        self.setWindowTitle("Grouped Export")
        self.setMinimumWidth(400)
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Info label
        info = QLabel(f"Export {len(self.items)} recorded items into organized group folders.")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Mode selection
        mode_group = QButtonGroup(self)
        
        self.items_per_folder_radio = QRadioButton("Items per folder:")
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
        
        self.num_folders_radio = QRadioButton("Number of folders:")
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
        self.copy_mode_check = QCheckBox("Copy files (default, safe)")
        self.copy_mode_check.setChecked(True)
        self.copy_mode_check.setToolTip("Uncheck to move files instead (use with caution)")
        layout.addWidget(self.copy_mode_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        export_btn = QPushButton("Export...")
        export_btn.clicked.connect(self._on_export)
        button_layout.addWidget(export_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _update_preview(self) -> None:
        """Update the preview text."""
        if not self.items:
            self.preview_label.setText("No items to export.")
            return
        
        mode = "items_per_folder" if self.items_per_folder_radio.isChecked() else "number_of_folders"
        value = self.items_per_folder_spin.value() if mode == "items_per_folder" else self.num_folders_spin.value()
        
        groups = GroupedExporter.preview_groups(
            [(m, w) for _, m, w in self.items],
            mode=mode,
            value=value
        )
        
        preview_text = f"Will create {len(groups)} folder(s):\n"
        for i, group in enumerate(groups[:5], start=1):  # Show first 5
            preview_text += f"  Group {i:02d}: {len(group)} items\n"
        
        if len(groups) > 5:
            preview_text += f"  ... and {len(groups) - 5} more folders\n"
        
        if groups and len(groups[-1]) != len(groups[0]):
            preview_text += f"\nNote: Last folder has {len(groups[-1])} items (remainder)."
        
        self.preview_label.setText(preview_text)
    
    def _on_export(self) -> None:
        """Handle export button click."""
        if not self.items:
            QMessageBox.warning(self, "No Items", "No items to export.")
            return
        
        # Select output directory
        output_dir = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if not output_dir:
            return
        
        # Confirm if directory already has Group folders
        existing_groups = [f for f in os.listdir(output_dir) if f.startswith("Group ") and os.path.isdir(os.path.join(output_dir, f))]
        if existing_groups:
            reply = QMessageBox.question(
                self,
                "Confirm Overwrite",
                f"The selected directory already contains {len(existing_groups)} Group folder(s).\n\n"
                "Existing files may be overwritten. Continue?",
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
                "Export Complete",
                f"Successfully exported {self.result_metadata['totalItems']} items "
                f"into {self.result_metadata['totalGroups']} folders."
            )
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export: {e}")
