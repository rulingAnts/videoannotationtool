import os
import math
import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QFont

class FullscreenVideoViewer(QWidget):
    def __init__(self, video_path: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.video_path = video_path
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.playing = False
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self._current_pixmap = None
        self._auto_fit_done = False
        self._start_video()

    def _start_video(self):
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            self.close()
            return
        fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if fps <= 0.0 or math.isnan(fps) or math.isinf(fps):
            interval_ms = 33
        else:
            interval_ms = int(round(1000.0 / fps))
            interval_ms = max(5, min(1000, interval_ms))
        self.playing = True
        self.timer.start(interval_ms)

    def _update_frame(self):
        if not self.playing or not self.cap:
            return
        ret, frame = self.cap.read()
        if not ret:
            self.playing = False
            self.timer.stop()
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        self._current_pixmap = QPixmap.fromImage(qt_image)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        if self._current_pixmap:
            pw = self._current_pixmap.width()
            ph = self._current_pixmap.height()
            # Auto-fit once to the window, maintaining aspect ratio
            if not self._auto_fit_done and self.width() > 0 and self.height() > 0:
                fit_scale_w = self.width() / float(pw)
                fit_scale_h = self.height() / float(ph)
                self.scale = max(0.1, min(fit_scale_w, fit_scale_h))
                self.offset_x = 0
                self.offset_y = 0
                self._auto_fit_done = True
            sw = int(pw * self.scale)
            sh = int(ph * self.scale)
            x = (self.width() - sw) // 2 + self.offset_x
            y = (self.height() - sh) // 2 + self.offset_y
            painter.drawPixmap(x, y, sw, sh, self._current_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        tip = "+ / -: zoom    arrows: pan    space: play/pause    click/any other key: close"
        font = QFont()
        font.setPointSize(12)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        pad = 12
        text_w = metrics.horizontalAdvance(tip)
        text_h = metrics.height()
        rect_w = text_w + pad * 2
        rect_h = text_h + pad
        painter.setOpacity(0.6)
        painter.fillRect(10, 10, rect_w, rect_h, QColor(0, 0, 0))
        painter.setOpacity(1.0)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(10 + pad, 10 + text_h, tip)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Space:
            self.playing = not self.playing
            if self.playing and not self.timer.isActive():
                fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0)
                if fps <= 0.0 or math.isnan(fps) or math.isinf(fps):
                    interval_ms = 33
                else:
                    interval_ms = int(round(1000.0 / fps))
                    interval_ms = max(5, min(1000, interval_ms))
                self.timer.start(interval_ms)
            elif not self.playing and self.timer.isActive():
                self.timer.stop()
            event.accept()
            return
        if key in (Qt.Key_Plus, Qt.Key_Equal):
            self.scale = min(8.0, self.scale * 1.1)
            self.update()
            event.accept()
            return
        if key == Qt.Key_Minus:
            self.scale = max(0.1, self.scale / 1.1)
            self.update()
            event.accept()
            return
        if key == Qt.Key_Left:
            self.offset_x += 50
            self.update()
            event.accept()
            return
        if key == Qt.Key_Right:
            self.offset_x -= 50
            self.update()
            event.accept()
            return
        if key == Qt.Key_Up:
            self.offset_y += 50
            self.update()
            event.accept()
            return
        if key == Qt.Key_Down:
            self.offset_y -= 50
            self.update()
            event.accept()
            return
        self.close()

    def mousePressEvent(self, event):
        self.close()

    def closeEvent(self, event):
        try:
            if self.timer.isActive():
                self.timer.stop()
        except Exception:
            pass
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
        except Exception:
            pass
        return super().closeEvent(event)
