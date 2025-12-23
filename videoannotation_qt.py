#!/usr/bin/env python3.11
# videoannotation_qt.py
# Qt (PySide6) version of the Video Annotation Tool for improved macOS stability

import sys, os, json, logging, faulthandler, argparse, traceback, threading, shutil, subprocess
import cv2, numpy as np, pyaudio, wave
from pydub import AudioSegment
from PIL import Image
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QTabWidget, QScrollArea, QGridLayout, QCheckBox,
    QFileDialog, QMessageBox, QDialog, QSlider, QFrame, QSplitter, QListWidgetItem)
from PySide6.QtGui import QPixmap, QImage

_DEBUG_FILE_HANDLE = None

def _setup_logging_and_debug(debug=False, log_file=None):
    global _DEBUG_FILE_HANDLE
    root_logger = logging.getLogger()
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s.%(msecs)03d %(levelname)s [%(threadName)s] %(name)s: %(message)s"
    datefmt = "%H:%M:%S"
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    root_logger.addHandler(console)
    root_logger.setLevel(level)
    if log_file:
        try:
            _DEBUG_FILE_HANDLE = open(log_file, "a", buffering=1)
            file_handler = logging.StreamHandler(_DEBUG_FILE_HANDLE)
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
            root_logger.addHandler(file_handler)
            try:
                faulthandler.enable(_DEBUG_FILE_HANDLE)
            except: pass
        except: pass
    else:
        try:
            faulthandler.enable()
        except: pass
    logging.getLogger("videoannotation_qt").debug("Logging initialized. debug=%s, log_file=%s", debug, log_file)

LABELS_ALL = {"English": {"language_name": "English", "app_title": "Video Annotation Tool (Qt)",
    "select_folder": "Select Folder", "open_ocenaudio": "Open all Recordings in Ocenaudio",
    "export_wavs": "Export Recorded Data", "clear_wavs": "Clear Recorded Data",
    "import_wavs": "Import Recorded Data", "join_wavs": "Export as Single Sound File",
    "play_video": "Play Video", "stop_video": "Stop Video", "play_audio": "Play Audio",
    "stop_audio": "Stop Audio", "record_audio": "Record Audio", "stop_recording": "Stop Recording",
    "videos_tab_title": "Videos", "images_tab_title": "Still Images",
    "no_folder_selected": "No Folder Selected", "audio_label_prefix": "Audio: ",
    "audio_no_annotation": "No audio annotation", "selected_image_label": "Selected Image:",
    "show_filenames": "Show filenames", "image_no_selection": "No image selected"}}

def resource_path(relative_path, check_system=True):
    if check_system:
        system_path = shutil.which(os.path.basename(relative_path))
        if system_path: return system_path
    if hasattr(sys, '_MEIPASS') and sys._MEIPASS:
        return os.path.join(sys._MEIPASS, relative_path)
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def configure_opencv_ffmpeg():
    dll_name = "opencv_videoio_ffmpeg4120_64.dll"
    opencv_dir = os.path.dirname(cv2.__file__)
    system_dll_path = os.path.join(opencv_dir, dll_name)
    if os.path.exists(system_dll_path):
        os.environ["OPENCV_FFMPEG_DLL_DIR"] = opencv_dir
        os.environ["PATH"] = opencv_dir + os.pathsep + os.environ.get("PATH", "")

def configure_pydub_ffmpeg():
    ffmpeg_path = resource_path(os.path.join("ffmpeg", "bin", "ffmpeg"))
    ffprobe_path = resource_path(os.path.join("ffmpeg", "bin", "ffprobe"))
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    if os.path.exists(ffmpeg_dir):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    if os.path.exists(ffmpeg_path): os.environ["PYDUB_FFMPEG"] = ffmpeg_path
    if os.path.exists(ffprobe_path): os.environ["PYDUB_FFPROBE"] = ffprobe_path

configure_opencv_ffmpeg()
configure_pydub_ffmpeg()

class VideoAnnotationQt(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("videoannotation_qt")
        self.language = "English"
        self.LABELS = LABELS_ALL[self.language]
        self.settings_file = os.path.expanduser("~/.videooralannotation/settings.json")
        self.folder_path = None
        self.ocenaudio_path = None
        self.last_tab = 'videos'
        self.show_filenames_pref = True
        self.show_advisory = True
        self.fullscreen_scale = 1.0
        self.max_image_upscale = 3.0
        self.max_video_upscale = 2.5
        self.audio_stream = None
        self.recording_thread = None
        self.is_recording = False
        self.video_files = []
        self.current_video = None
        self.cap = None
        self.playing_video = False
        self.video_timer = QTimer()
        self.video_timer.timeout.connect(self._update_video_frame)
        self.image_files = []
        self.current_image = None
        self.load_settings()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(self.LABELS["app_title"])
        self.resize(1400, 800)
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        self.folder_label = QLabel(self.LABELS["no_folder_selected"])
        main_layout.addWidget(self.folder_label)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.videos_tab = self.create_videos_tab()
        self.tab_widget.addTab(self.videos_tab, self.LABELS["videos_tab_title"])
        self.images_tab = self.create_images_tab()
        self.tab_widget.addTab(self.images_tab, self.LABELS["images_tab_title"])
        splitter.addWidget(self.tab_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        if self.last_tab == 'images':
            self.tab_widget.setCurrentWidget(self.images_tab)
        self.logger.info("UI initialized")

    def create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        btn_select = QPushButton(self.LABELS["select_folder"])
        btn_select.clicked.connect(self.select_folder)
        layout.addWidget(btn_select)
        self.btn_ocenaudio = QPushButton(self.LABELS["open_ocenaudio"])
        self.btn_ocenaudio.clicked.connect(self.open_in_ocenaudio)
        self.btn_ocenaudio.setEnabled(False)
        layout.addWidget(self.btn_ocenaudio)
        self.btn_export = QPushButton(self.LABELS["export_wavs"])
        self.btn_export.clicked.connect(self.export_wavs)
        self.btn_export.setEnabled(False)
        layout.addWidget(self.btn_export)
        self.btn_clear = QPushButton(self.LABELS["clear_wavs"])
        self.btn_clear.clicked.connect(self.clear_wavs)
        self.btn_clear.setEnabled(False)
        layout.addWidget(self.btn_clear)
        self.btn_import = QPushButton(self.LABELS["import_wavs"])
        self.btn_import.clicked.connect(self.import_wavs)
        self.btn_import.setEnabled(False)
        layout.addWidget(self.btn_import)
        self.btn_join = QPushButton(self.LABELS["join_wavs"])
        self.btn_join.clicked.connect(self.join_wavs)
        self.btn_join.setEnabled(False)
        layout.addWidget(self.btn_join)
        self.video_list = QListWidget()
        self.video_list.currentItemChanged.connect(self.on_video_select)
        layout.addWidget(self.video_list)
        layout.addStretch()
        return panel

    def create_videos_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.video_container = QFrame()
        self.video_container.setFrameStyle(QFrame.Box)
        self.video_container.setLineWidth(1)
        container_layout = QVBoxLayout(self.video_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: black;")
        container_layout.addWidget(self.video_label)
        self.video_badge = QLabel("✓", self.video_container)
        self.video_badge.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 12px; padding: 4px 8px; font-weight: bold;")
        self.video_badge.hide()
        self.video_badge.adjustSize()
        layout.addWidget(self.video_container)
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        self.btn_play = QPushButton(self.LABELS["play_video"])
        self.btn_play.clicked.connect(self.play_video)
        self.btn_play.setEnabled(False)
        controls_layout.addWidget(self.btn_play)
        self.btn_stop_video = QPushButton(self.LABELS["stop_video"])
        self.btn_stop_video.clicked.connect(self.stop_video)
        self.btn_stop_video.setEnabled(False)
        controls_layout.addWidget(self.btn_stop_video)
        layout.addWidget(controls)
        audio_controls = QWidget()
        audio_layout = QHBoxLayout(audio_controls)
        self.video_audio_label = QLabel(self.LABELS["audio_label_prefix"] + self.LABELS["audio_no_annotation"])
        audio_layout.addWidget(self.video_audio_label)
        self.btn_play_audio = QPushButton(self.LABELS["play_audio"])
        self.btn_play_audio.clicked.connect(self.play_audio)
        self.btn_play_audio.setEnabled(False)
        audio_layout.addWidget(self.btn_play_audio)
        self.btn_stop_audio = QPushButton(self.LABELS["stop_audio"])
        self.btn_stop_audio.clicked.connect(self.stop_audio)
        self.btn_stop_audio.setEnabled(False)
        audio_layout.addWidget(self.btn_stop_audio)
        self.btn_record = QPushButton(self.LABELS["record_audio"])
        self.btn_record.clicked.connect(self.toggle_recording)
        self.btn_record.setEnabled(False)
        audio_layout.addWidget(self.btn_record)
        layout.addWidget(audio_controls)
        return tab

    def create_images_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        banner = QWidget()
        banner_layout = QHBoxLayout(banner)
        self.image_thumb_label = QLabel()
        self.image_thumb_label.setFixedSize(100, 100)
        self.image_thumb_label.setStyleSheet("border: 1px solid #ccc;")
        banner_layout.addWidget(self.image_thumb_label)
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        filename_row = QWidget()
        filename_layout = QHBoxLayout(filename_row)
        filename_layout.addWidget(QLabel(self.LABELS["selected_image_label"]))
        self.image_filename_label = QLabel(self.LABELS["image_no_selection"])
        filename_layout.addWidget(self.image_filename_label)
        filename_layout.addStretch()
        info_layout.addWidget(filename_row)
        self.show_filenames_cb = QCheckBox(self.LABELS["show_filenames"])
        self.show_filenames_cb.setChecked(self.show_filenames_pref)
        self.show_filenames_cb.toggled.connect(self.on_toggle_show_filenames)
        info_layout.addWidget(self.show_filenames_cb)
        banner_layout.addWidget(info_widget)
        audio_controls = QWidget()
        audio_layout = QHBoxLayout(audio_controls)
        self.btn_play_image_audio = QPushButton(self.LABELS["play_audio"])
        self.btn_play_image_audio.clicked.connect(self.play_selected_image_audio)
        self.btn_play_image_audio.setEnabled(False)
        audio_layout.addWidget(self.btn_play_image_audio)
        self.btn_stop_image_audio = QPushButton(self.LABELS["stop_audio"])
        self.btn_stop_image_audio.clicked.connect(self.stop_audio)
        self.btn_stop_image_audio.setEnabled(False)
        audio_layout.addWidget(self.btn_stop_image_audio)
        self.btn_record_image = QPushButton(self.LABELS["record_audio"])
        self.btn_record_image.clicked.connect(self.toggle_image_recording)
        self.btn_record_image.setEnabled(False)
        audio_layout.addWidget(self.btn_record_image)
        banner_layout.addWidget(audio_controls)
        layout.addWidget(banner)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.image_grid_widget = QWidget()
        self.image_grid_layout = QGridLayout(self.image_grid_widget)
        self.image_grid_layout.setSpacing(10)
        scroll.setWidget(self.image_grid_widget)
        layout.addWidget(scroll)
        return tab

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.language = settings.get('language', 'English')
                    if self.language in LABELS_ALL:
                        self.LABELS = LABELS_ALL[self.language]
                    last_folder = settings.get('last_folder')
                    if last_folder and os.path.isdir(last_folder):
                        self.folder_path = last_folder
                    self.ocenaudio_path = settings.get('ocenaudio_path')
                    self.last_tab = settings.get('last_tab', 'videos')
                    self.show_filenames_pref = settings.get('show_filenames', True)
                    self.show_advisory = settings.get('show_advisory', True)
                    self.fullscreen_scale = max(0.5, min(1.0, float(settings.get('fullscreen_scale', 1.0))))
                    self.logger.debug("Settings loaded: folder=%s, tab=%s", self.folder_path, self.last_tab)
        except Exception as e:
            self.logger.warning("Failed to load settings: %s", e)

    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            settings = {}
            if os.path.exists(self.settings_file):
                try:
                    with open(self.settings_file, 'r') as f:
                        settings = json.load(f)
                except: pass
            settings['ocenaudio_path'] = self.ocenaudio_path
            settings['last_tab'] = self.last_tab
            settings['language'] = self.language
            if self.folder_path:
                settings['last_folder'] = self.folder_path
            settings['show_filenames'] = self.show_filenames_pref
            settings['show_advisory'] = self.show_advisory
            settings['fullscreen_scale'] = self.fullscreen_scale
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
            self.logger.debug("Settings saved")
        except Exception as e:
            self.logger.warning("Failed to save settings: %s", e)

    def select_folder(self):
        self.logger.debug("select_folder invoked")
        start_dir = self.folder_path if self.folder_path and os.path.isdir(self.folder_path) else os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, self.LABELS["select_folder"], start_dir)
        if folder:
            self.folder_path = folder
            self.folder_label.setText(folder)
            self.save_settings()
            self.logger.info("Folder selected: %s", folder)
            self.btn_ocenaudio.setEnabled(True)
            self.btn_export.setEnabled(True)
            self.btn_clear.setEnabled(True)
            self.btn_import.setEnabled(True)
            self.btn_join.setEnabled(True)
            if self.tab_widget.currentWidget() == self.videos_tab:
                self.load_video_files()
            else:
                self.load_image_files()

    def load_video_files(self):
        self.logger.debug("load_video_files called. folder=%s", self.folder_path)
        self.video_files = []
        self.video_list.clear()
        if not self.folder_path:
            return
        try:
            exts = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm')
            files = [f for f in os.listdir(self.folder_path) if f.lower().endswith(exts) and not f.startswith('.')]
            self.video_files = sorted(files, key=lambda s: s.lower())
            self.logger.debug("Found %d videos", len(self.video_files))
            for video in self.video_files:
                item = QListWidgetItem(video)
                audio_path = self.get_audio_path_for_media(video, None, "video")
                if os.path.exists(audio_path):
                    item.setText(video + " 🎵")
                self.video_list.addItem(item)
        except Exception as e:
            self.logger.error("Failed to load videos: %s", e)
            QMessageBox.critical(self, "Error", f"Failed to load videos: {e}")

    def load_image_files(self):
        self.logger.debug("load_image_files called. folder=%s", self.folder_path)
        self.image_files = []
        for i in reversed(range(self.image_grid_layout.count())):
            widget = self.image_grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        if not self.folder_path:
            return
        try:
            exts = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif')
            files = [f for f in os.listdir(self.folder_path) if f.lower().endswith(exts) and not f.startswith('.')]
            self.image_files = sorted(files, key=lambda s: s.lower())
            self.logger.debug("Found %d images", len(self.image_files))
            self.build_image_grid()
        except Exception as e:
            self.logger.error("Failed to load images: %s", e)
            QMessageBox.critical(self, "Error", f"Failed to load images: {e}")

    def build_image_grid(self):
        for i in reversed(range(self.image_grid_layout.count())):
            widget = self.image_grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        if not self.image_files:
            return
        row, col = 0, 0
        for fname in self.image_files:
            tile = self.create_image_tile(fname)
            self.image_grid_layout.addWidget(tile, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

    def create_image_tile(self, fname):
        path = os.path.join(self.folder_path, fname)
        container = QFrame()
        container.setFrameStyle(QFrame.Box)
        ext = os.path.splitext(fname)[1].lstrip('.')
        audio_path = self.get_audio_path_for_media(fname, ext, "image")
        has_audio = os.path.exists(audio_path)
        if has_audio:
            container.setStyleSheet("border: 3px solid #4CAF50;")
        else:
            container.setStyleSheet("border: 1px solid #ccc;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        thumb_container = QWidget()
        thumb_container.setFixedSize(220, 220)
        thumb_label = QLabel(thumb_container)
        thumb_label.setAlignment(Qt.AlignCenter)
        thumb_label.setFixedSize(220, 220)
        try:
            pil_img = Image.open(path)
            pil_img.thumbnail((220, 220), Image.LANCZOS)
            img_bytes = pil_img.convert('RGB').tobytes()
            qimg = QImage(img_bytes, pil_img.width, pil_img.height, pil_img.width * 3, QImage.Format_RGB888)
            thumb_label.setPixmap(QPixmap.fromImage(qimg))
        except Exception as e:
            self.logger.warning("Failed to load thumbnail for %s: %s", fname, e)
            thumb_label.setText("Failed to load")
        if has_audio:
            badge = QLabel("✓", thumb_container)
            badge.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 10px; padding: 2px 6px; font-weight: bold;")
            badge.move(200, 5)
            badge.adjustSize()
        thumb_label.mousePressEvent = lambda e, f=fname: self.on_image_select(f)
        layout.addWidget(thumb_container)
        if self.show_filenames_cb.isChecked():
            name_label = QLabel(fname)
            name_label.setWordWrap(True)
            name_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(name_label)
        return container

    def on_video_select(self, current, previous):
        if not current:
            return
        self.logger.debug("Video selected: %s", current.text())
        self.stop_video()
        video_name = current.text().replace(" 🎵", "").strip()
        self.current_video = video_name
        video_path = os.path.join(self.folder_path, video_name)
        try:
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            cap.release()
            if ret:
                self.display_frame(frame)
            else:
                self.video_label.setText("Failed to load video")
        except Exception as e:
            self.logger.error("Failed to load first frame: %s", e)
            self.video_label.setText("Error loading video")
        self.btn_play.setEnabled(True)
        self.btn_record.setEnabled(True)
        audio_path = self.get_audio_path_for_media(video_name, None, "video")
        if os.path.exists(audio_path):
            self.video_audio_label.setText(self.LABELS["audio_label_prefix"] + os.path.basename(audio_path))
            self.btn_play_audio.setEnabled(True)
            self.video_container.setStyleSheet("border: 3px solid #4CAF50;")
            self.video_badge.show()
            self.video_badge.move(self.video_container.width() - self.video_badge.width() - 10, 10)
        else:
            self.video_audio_label.setText(self.LABELS["audio_label_prefix"] + self.LABELS["audio_no_annotation"])
            self.btn_play_audio.setEnabled(False)
            self.video_container.setStyleSheet("border: 1px solid #ccc;")
            self.video_badge.hide()

    def display_frame(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled)

    def play_video(self):
        if self.playing_video or not self.current_video:
            return
        self.logger.debug("Starting video playback: %s", self.current_video)
        video_path = os.path.join(self.folder_path, self.current_video)
        try:
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                raise Exception("Failed to open video")
            self.playing_video = True
            self.btn_play.setEnabled(False)
            self.btn_stop_video.setEnabled(True)
            self.video_timer.start(33)
        except Exception as e:
            self.logger.error("Failed to start video playback: %s", e)
            QMessageBox.critical(self, "Error", f"Failed to play video: {e}")

    def _update_video_frame(self):
        if not self.cap or not self.playing_video:
            self.video_timer.stop()
            return
        ret, frame = self.cap.read()
        if ret:
            self.display_frame(frame)
        else:
            self.stop_video()

    def stop_video(self):
        if not self.playing_video:
            return
        self.logger.debug("Stopping video playback")
        self.playing_video = False
        self.video_timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.btn_play.setEnabled(True)
        self.btn_stop_video.setEnabled(False)
        if self.current_video:
            video_path = os.path.join(self.folder_path, self.current_video)
            try:
                cap = cv2.VideoCapture(video_path)
                ret, frame = cap.read()
                cap.release()
                if ret:
                    self.display_frame(frame)
            except: pass

    def play_audio(self):
        if not self.current_video:
            return
        audio_path = self.get_audio_path_for_media(self.current_video, None, "video")
        self._play_audio_file(audio_path)

    def play_selected_image_audio(self):
        if not self.current_image:
            return
        ext = os.path.splitext(self.current_image)[1].lstrip('.')
        audio_path = self.get_audio_path_for_media(self.current_image, ext, "image")
        self._play_audio_file(audio_path)

    def _play_audio_file(self, audio_path):
        if not os.path.exists(audio_path):
            return
        self.logger.debug("Playing audio: %s", audio_path)
        def play():
            try:
                wf = wave.open(audio_path, 'rb')
                p = pyaudio.PyAudio()
                stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                              channels=wf.getnchannels(), rate=wf.getframerate(), output=True)
                data = wf.readframes(1024)
                while data:
                    stream.write(data)
                    data = wf.readframes(1024)
                stream.stop_stream()
                stream.close()
                p.terminate()
                wf.close()
            except Exception as e:
                self.logger.error("Failed to play audio: %s", e)
        threading.Thread(target=play, daemon=True).start()

    def stop_audio(self):
        pass

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording("video")

    def toggle_image_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording("image")

    def start_recording(self, media_type):
        if media_type == "video" and not self.current_video:
            return
        if media_type == "image" and not self.current_image:
            return
        if media_type == "video":
            media_name = self.current_video
            ext = None
        else:
            media_name = self.current_image
            ext = os.path.splitext(media_name)[1].lstrip('.')
        audio_path = self.get_audio_path_for_media(media_name, ext, media_type)
        if os.path.exists(audio_path):
            reply = QMessageBox.question(self, "Overwrite?", "Audio file already exists. Overwrite?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        self.logger.debug("Starting audio recording: %s", audio_path)
        self.is_recording = True
        if media_type == "video":
            self.btn_record.setText(self.LABELS["stop_recording"])
        else:
            self.btn_record_image.setText(self.LABELS["stop_recording"])
        def record():
            try:
                p = pyaudio.PyAudio()
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100,
                              input=True, frames_per_buffer=1024)
                frames = []
                while self.is_recording:
                    data = stream.read(1024)
                    frames.append(data)
                stream.stop_stream()
                stream.close()
                p.terminate()
                wf = wave.open(audio_path, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(44100)
                wf.writeframes(b''.join(frames))
                wf.close()
                self.logger.info("Recording saved: %s", audio_path)
                if media_type == "video":
                    QTimer.singleShot(0, lambda: self.on_video_select(self.video_list.currentItem(), None))
                else:
                    QTimer.singleShot(0, lambda: self.build_image_grid())
            except Exception as e:
                self.logger.error("Recording failed: %s", e)
        self.recording_thread = threading.Thread(target=record, daemon=True)
        self.recording_thread.start()

    def stop_recording(self):
        if not self.is_recording:
            return
        self.logger.debug("Stopping audio recording")
        self.is_recording = False
        self.btn_record.setText(self.LABELS["record_audio"])
        self.btn_record_image.setText(self.LABELS["record_audio"])

    def on_image_select(self, fname):
        self.logger.debug("Image selected: %s", fname)
        self.current_image = fname
        self.image_filename_label.setText(fname if self.show_filenames_cb.isChecked() else "")
        path = os.path.join(self.folder_path, fname)
        try:
            pil_img = Image.open(path)
            pil_img.thumbnail((100, 100), Image.LANCZOS)
            img_bytes = pil_img.convert('RGB').tobytes()
            qimg = QImage(img_bytes, pil_img.width, pil_img.height, pil_img.width * 3, QImage.Format_RGB888)
            self.image_thumb_label.setPixmap(QPixmap.fromImage(qimg))
        except Exception as e:
            self.logger.warning("Failed to load thumbnail: %s", e)
        self.btn_record_image.setEnabled(True)
        ext = os.path.splitext(fname)[1].lstrip('.')
        audio_path = self.get_audio_path_for_media(fname, ext, "image")
        if os.path.exists(audio_path):
            self.btn_play_image_audio.setEnabled(True)
            self.btn_stop_image_audio.setEnabled(True)
        else:
            self.btn_play_image_audio.setEnabled(False)
            self.btn_stop_image_audio.setEnabled(False)

    def on_toggle_show_filenames(self):
        self.show_filenames_pref = self.show_filenames_cb.isChecked()
        self.save_settings()
        self.build_image_grid()
        if self.current_image:
            self.image_filename_label.setText(self.current_image if self.show_filenames_pref else "")

    def get_audio_path_for_media(self, name, ext, media_type):
        folder = self.folder_path or ""
        base_name, _ = os.path.splitext(name)
        if media_type == "image":
            if not ext:
                ext = os.path.splitext(name)[1].lstrip('.')
            audio_name = f"{base_name}.{ext}.wav"
            return os.path.join(folder, audio_name)
        audio_name = f"{base_name}.wav"
        return os.path.join(folder, audio_name)

    def on_tab_changed(self, index):
        self.logger.debug("Tab changed to index: %d", index)
        self.stop_video()
        if self.tab_widget.widget(index) == self.videos_tab:
            self.last_tab = 'videos'
            self.load_video_files()
        else:
            self.last_tab = 'images'
            self.load_image_files()
        self.save_settings()

    def open_in_ocenaudio(self):
        QMessageBox.information(self, "Info", "Open in Ocenaudio - to be implemented")
    def export_wavs(self):
        QMessageBox.information(self, "Info", "Export WAVs - to be implemented")
    def clear_wavs(self):
        QMessageBox.information(self, "Info", "Clear WAVs - to be implemented")
    def import_wavs(self):
        QMessageBox.information(self, "Info", "Import WAVs - to be implemented")
    def join_wavs(self):
        QMessageBox.information(self, "Info", "Join WAVs - to be implemented")

def main():
    parser = argparse.ArgumentParser(description="Video Annotation Tool (Qt)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--log-file", dest="log_file", default=None, help="Write logs to file")
    args = parser.parse_args()
    _setup_logging_and_debug(debug=args.debug, log_file=args.log_file)
    def exception_hook(exc_type, exc_value, exc_tb):
        logging.getLogger("videoannotation_qt").error("Uncaught exception: %s: %s\n%s",
            exc_type.__name__, exc_value, "".join(traceback.format_tb(exc_tb)))
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = exception_hook
    app = QApplication(sys.argv)
    window = VideoAnnotationQt()
    window.show()
    logging.getLogger("videoannotation_qt").info("Application started. Debug=%s", args.debug)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
