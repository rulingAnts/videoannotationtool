"""Thumbnail grid widget for Review Tab."""

import os
import sys
from typing import Optional, List, Tuple
from PySide6.QtWidgets import (
    QWidget, QListWidget, QListWidgetItem, QListView,
    QVBoxLayout, QSizePolicy, QStyle, QStyledItemDelegate,
    QApplication
)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QPoint
from PySide6.QtGui import QIcon, QPixmap, QPen, QColor, QImageReader

from vat.utils.fs_access import FolderAccessManager


class ThumbnailGridWidget(QWidget):
    """Grid widget showing thumbnails of recorded items only.
    
    Features:
    - Icon-mode grid with thumbnails
    - Single-click selection
    - Double-click for preview/fullscreen
    - Right-click, Ctrl/Cmd+Click, or Enter for quick confirm
    - Visual feedback overlays (green check, red X)
    
    Signals:
        selectionChanged(str): Emitted when selection changes (item_id)
        activatedConfirm(str, str): Emitted when user confirms (item_id, method)
        doubleClicked(str): Emitted on double-click for preview (item_id)
    """
    
    selectionChanged = Signal(str)  # item_id
    activatedConfirm = Signal(str, str)  # item_id, method ("mouse", "keyboard")
    doubleClicked = Signal(str)  # item_id
    
    def __init__(self, fs_manager: FolderAccessManager, parent=None):
        super().__init__(parent)
        self.fs = fs_manager
        self._items: List[Tuple[str, str, str]] = []  # (item_id, media_path, wav_path)
        self._feedback_state: dict = {}  # item_id -> "correct" | "wrong"
        self._pixmap_cache: dict = {}
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListView.IconMode)
        self.list_widget.setResizeMode(QListView.Adjust)
        self.list_widget.setFlow(QListView.LeftToRight)
        self.list_widget.setIconSize(QSize(240, 180))
        self.list_widget.setGridSize(QSize(280, 220))
        self.list_widget.setSpacing(6)
        self.list_widget.setMovement(QListView.Static)
        self.list_widget.setWrapping(True)
        self.list_widget.setUniformItemSizes(False)
        self.list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.setSelectionBehavior(QListWidget.SelectItems)
        
        # Install custom delegate for feedback overlays
        self.list_widget.setItemDelegate(ReviewThumbnailDelegate(self))
        
        # Connect signals
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        self.list_widget.itemActivated.connect(self._on_item_activated)
        
        # Install event filter for right-click and modifier+click
        self.list_widget.viewport().installEventFilter(self)
        
        layout.addWidget(self.list_widget)
    
    def populate(self, items: List[Tuple[str, str, str]]) -> None:
        """Populate grid with recorded items.
        
        Args:
            items: List of (item_id, media_path, wav_path) tuples
        """
        self._items = list(items)
        self.list_widget.clear()
        self._feedback_state = {}
        
        icon_size = self.list_widget.iconSize()
        
        for item_id, media_path, wav_path in items:
            name = os.path.basename(media_path)
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, item_id)
            item.setData(Qt.UserRole + 1, media_path)
            item.setData(Qt.UserRole + 2, wav_path)
            
            # Load and cache thumbnail
            try:
                pix = self._load_pixmap(media_path)
                if pix and not pix.isNull():
                    thumb = pix.scaled(icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    item.setIcon(QIcon(thumb))
            except Exception:
                pass
            
            self.list_widget.addItem(item)
        
        if items:
            self.list_widget.setCurrentRow(0)
    
    def _load_pixmap(self, path: str) -> Optional[QPixmap]:
        """Load or retrieve cached pixmap."""
        if path in self._pixmap_cache:
            return self._pixmap_cache[path]
        
        try:
            pix = QPixmap(path)
            if pix.isNull():
                reader = QImageReader(path)
                img = reader.read()
                if img and not img.isNull():
                    pix = QPixmap.fromImage(img)
            
            if pix and not pix.isNull():
                self._pixmap_cache[path] = pix
                return pix
        except Exception:
            pass
        
        return None
    
    def _on_selection_changed(self, current, previous) -> None:
        """Handle selection change."""
        if current:
            item_id = current.data(Qt.UserRole)
            if item_id:
                self.selectionChanged.emit(item_id)
    
    def _on_double_click(self, item: QListWidgetItem) -> None:
        """Handle double-click for preview."""
        item_id = item.data(Qt.UserRole)
        if item_id:
            self.doubleClicked.emit(item_id)
    
    def _on_item_activated(self, item: QListWidgetItem) -> None:
        """Handle Enter key activation."""
        item_id = item.data(Qt.UserRole)
        if item_id:
            self.activatedConfirm.emit(item_id, "keyboard")
    
    def eventFilter(self, obj, event) -> bool:
        """Handle right-click and modifier+click for quick confirm."""
        if obj == self.list_widget.viewport():
            if event.type() == event.Type.MouseButtonPress:
                is_mac = sys.platform == 'darwin'
                
                # Right-click or Ctrl/Cmd+Click
                if (event.button() == Qt.RightButton or
                    (event.button() == Qt.LeftButton and 
                     ((is_mac and event.modifiers() & Qt.MetaModifier) or
                      (not is_mac and event.modifiers() & Qt.ControlModifier)))):
                    
                    item = self.list_widget.itemAt(event.pos())
                    if item:
                        item_id = item.data(Qt.UserRole)
                        if item_id:
                            self.activatedConfirm.emit(item_id, "mouse")
                            return True
        
        return super().eventFilter(obj, event)
    
    def set_feedback(self, item_id: str, state: str) -> None:
        """Set visual feedback for an item.
        
        Args:
            item_id: Item identifier
            state: "correct", "wrong", or empty string to clear
        """
        if state:
            self._feedback_state[item_id] = state
        else:
            self._feedback_state.pop(item_id, None)
        
        # Trigger repaint
        self.list_widget.viewport().update()
    
    def clear_feedback(self) -> None:
        """Clear all feedback overlays."""
        self._feedback_state = {}
        self.list_widget.viewport().update()
    
    def get_item_by_id(self, item_id: str) -> Optional[QListWidgetItem]:
        """Get list item by item_id."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == item_id:
                return item
        return None


class ReviewThumbnailDelegate(QStyledItemDelegate):
    """Custom delegate to draw feedback overlays on thumbnails."""
    
    def __init__(self, grid_widget: ThumbnailGridWidget, parent=None):
        super().__init__(parent)
        self.grid_widget = grid_widget
    
    def paint(self, painter, option, index):
        """Paint item with optional feedback overlay."""
        # Default painting first
        super().paint(painter, option, index)
        
        # Get item_id and check for feedback
        item_id = index.data(Qt.UserRole)
        if not item_id:
            return
        
        feedback = self.grid_widget._feedback_state.get(item_id)
        if not feedback:
            return
        
        try:
            painter.save()
            
            # Determine color and icon
            if feedback == "correct":
                color = QColor("#2ecc71")  # Green
                icon_type = QStyle.SP_DialogApplyButton
            else:  # "wrong"
                color = QColor("#e74c3c")  # Red
                icon_type = QStyle.SP_DialogCancelButton
            
            # Draw border around icon area
            pen = QPen(color)
            pen.setWidth(4)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            r = option.rect
            ds = option.decorationSize
            iw = max(1, ds.width())
            ih = max(1, ds.height())
            x = r.x() + (r.width() - iw) // 2
            y = r.y() + 5
            icon_rect = QRect(x, y, iw, ih)
            painter.drawRect(icon_rect.adjusted(2, 2, -2, -2))
            
            # Draw check/X overlay
            try:
                style = QApplication.style()
                icon = style.standardIcon(icon_type)
                pix = icon.pixmap(32, 32)
                ox = icon_rect.right() - 32 - 6
                oy = icon_rect.top() + 6
                painter.drawPixmap(QPoint(ox, oy), pix)
            except Exception:
                pass
        
        finally:
            painter.restore()
