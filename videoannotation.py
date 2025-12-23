#!/usr/bin/env python3
# videoannotation.py - PySide6 version
# A simple video annotation tool with audio recording capabilities.
# NOTE: This script works with Python 3.11+

import sys
import os
import cv2
import numpy as np
import shutil
import subprocess
import json
import argparse
import logging
import wave
import threading
from pathlib import Path
from typing import Optional

# Use PyAudio for audio (note: may not work in headless CI)
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except (ImportError, OSError):
    PYAUDIO_AVAILABLE = False
    pyaudio = None

from pydub import AudioSegment

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLabel, QTextEdit, QMessageBox,
    QFileDialog, QComboBox, QTabWidget, QSplitter
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QImage, QPixmap, QKeyEvent

# UI labels for easy translation, with language names in their own language
LABELS_ALL = {
    "English": {
        "language_name": "English",
        "app_title": "Video Annotation Tool",
        "select_folder": "Select Folder",
        "open_ocenaudio": "Open all Recordings in Ocenaudio (To Normalize, Trim, Edit...)",
        "export_wavs": "Export Recorded Data",
        "clear_wavs": "Clear Recorded Data",
        "import_wavs": "Import Recorded Data",
        "join_wavs": "Export as Single Sound File (for SayMore/ELAN)",
        "video_listbox_no_video": "No video selected",
        "play_video": "Play Video",
        "stop_video": "Stop Video",
        "audio_no_annotation": "No audio annotation",
        "play_audio": "Play Audio",
        "stop_audio": "Stop Audio",
        "record_audio": "Record Audio",
        "stop_recording": "Stop Recording",
        "edit_metadata": "Edit Metadata",
        "save_metadata": "Save",
        "audio_label_prefix": "Audio: ",
        "no_folder_selected": "No Folder Selected",
        "no_videos_found": "No video files found in the selected folder:",
        "no_files": "No Files",
        "no_wavs_found": "No WAV files found in the current folder.",
        "overwrite": "Overwrite?",
        "overwrite_audio": "Audio file already exists. Overwrite?",
        "saved": "Saved",
        "metadata_saved": "Metadata saved!",
        "success": "Success",
        "wavs_joined": "All WAV files successfully joined into:",
    },
    "Bahasa Indonesia": {
        "language_name": "Bahasa Indonesia",
        "app_title": "Alat Anotasi Video",
        "select_folder": "Pilih Folder",
        "open_ocenaudio": "Buka semua rekaman di Ocenaudio (Untuk normalisasi, potong, edit...)",
        "export_wavs": "Ekspor Data Rekaman",
        "clear_wavs": "Hapus Data Rekaman",
        "import_wavs": "Impor Data Rekaman",
        "join_wavs": "Ekspor sebagai Satu Berkas Suara (untuk SayMore/ELAN)",
        "video_listbox_no_video": "Tidak ada video yang dipilih",
        "play_video": "Putar Video",
        "stop_video": "Hentikan Video",
        "audio_no_annotation": "Tidak ada anotasi audio",
        "play_audio": "Putar Audio",
        "stop_audio": "Hentikan Audio",
        "record_audio": "Rekam Audio",
        "stop_recording": "Hentikan Rekaman",
        "edit_metadata": "Edit Metadata",
        "save_metadata": "Simpan",
        "audio_label_prefix": "Audio: ",
        "no_folder_selected": "Tidak ada folder yang dipilih",
        "no_videos_found": "Tidak ada berkas video di folder yang dipilih:",
        "no_files": "Tidak Ada Berkas",
        "no_wavs_found": "Tidak ada berkas WAV di folder ini.",
        "overwrite": "Timpa?",
        "overwrite_audio": "Berkas audio sudah ada. Timpa?",
        "saved": "Tersimpan",
        "metadata_saved": "Metadata tersimpan!",
        "success": "Berhasil",
        "wavs_joined": "Semua berkas WAV berhasil digabungkan menjadi:",
    },
    "한국어": {
        "language_name": "한국어",
        "app_title": "비디오 주석 도구",
        "select_folder": "폴더 선택",
        "open_ocenaudio": "모든 녹음을 Ocenaudio에서 열기 (정규화, 자르기, 편집...)",
        "export_wavs": "녹음 데이터 내보내기",
        "clear_wavs": "녹음 데이터 지우기",
        "import_wavs": "녹음 데이터 가져오기",
        "join_wavs": "하나의 오디오 파일로 내보내기 (SayMore/ELAN용)",
        "video_listbox_no_video": "선택된 비디오 없음",
        "play_video": "비디오 재생",
        "stop_video": "비디오 정지",
        "audio_no_annotation": "오디오 주석 없음",
        "play_audio": "오디오 재생",
        "stop_audio": "오디오 정지",
        "record_audio": "오디오 녹음",
        "stop_recording": "녹음 중지",
        "edit_metadata": "메타데이터 편집",
        "save_metadata": "저장",
        "audio_label_prefix": "오디오: ",
        "no_folder_selected": "선택된 폴더 없음",
        "no_videos_found": "선택한 폴더에 비디오 파일이 없습니다:",
        "no_files": "파일 없음",
        "no_wavs_found": "현재 폴더에 WAV 파일이 없습니다.",
        "overwrite": "덮어쓰기?",
        "overwrite_audio": "오디오 파일이 이미 존재합니다. 덮어쓸까요?",
        "saved": "저장됨",
        "metadata_saved": "메타데이터가 저장되었습니다!",
        "success": "성공",
        "wavs_joined": "모든 WAV 파일이 성공적으로 결합되었습니다:",
    },
    "Nederlands": {
        "language_name": "Nederlands",
        "app_title": "Video Annotatie Tool",
        "select_folder": "Selecteer Map",
        "open_ocenaudio": "Open alle opnamen in Ocenaudio (Normaliseren, Knippen, Bewerken...)",
        "export_wavs": "Opgenomen Data Exporteren",
        "clear_wavs": "Opgenomen Data Wissen",
        "import_wavs": "Opgenomen Data Importeren",
        "join_wavs": "Exporteren als Enkel Geluidsbestand (voor SayMore/ELAN)",
        "video_listbox_no_video": "Geen video geselecteerd",
        "play_video": "Video Afspelen",
        "stop_video": "Video Stoppen",
        "audio_no_annotation": "Geen audio annotatie",
        "play_audio": "Audio Afspelen",
        "stop_audio": "Audio Stoppen",
        "record_audio": "Audio Opnemen",
        "stop_recording": "Opname Stoppen",
        "edit_metadata": "Metadata Bewerken",
        "save_metadata": "Opslaan",
        "audio_label_prefix": "Audio: ",
        "no_folder_selected": "Geen map geselecteerd",
        "no_videos_found": "Geen videobestanden gevonden in de geselecteerde map:",
        "no_files": "Geen bestanden",
        "no_wavs_found": "Geen WAV-bestanden gevonden in de huidige map.",
        "overwrite": "Overschrijven?",
        "overwrite_audio": "Audiobestand bestaat al. Overschrijven?",
        "saved": "Opgeslagen",
        "metadata_saved": "Metadata opgeslagen!",
        "success": "Succes",
        "wavs_joined": "Alle WAV-bestanden succesvol samengevoegd tot:",
    },
    "Português (Brasil)": {
        "language_name": "Português (Brasil)",
        "app_title": "Ferramenta de Anotação de Vídeo",
        "select_folder": "Selecionar Pasta",
        "open_ocenaudio": "Abrir todas as gravações no Ocenaudio (Para normalizar, cortar, editar...)",
        "export_wavs": "Exportar Dados Gravados",
        "clear_wavs": "Limpar Dados Gravados",
        "import_wavs": "Importar Dados Gravados",
        "join_wavs": "Exportar como Arquivo Único de Áudio (para SayMore/ELAN)",
        "video_listbox_no_video": "Nenhum vídeo selecionado",
        "play_video": "Reproduzir Vídeo",
        "stop_video": "Parar Vídeo",
        "audio_no_annotation": "Sem anotação de áudio",
        "play_audio": "Reproduzir Áudio",
        "stop_audio": "Parar Áudio",
        "record_audio": "Gravar Áudio",
        "stop_recording": "Parar Gravação",
        "edit_metadata": "Editar Metadados",
        "save_metadata": "Salvar",
        "audio_label_prefix": "Áudio: ",
        "no_folder_selected": "Nenhuma pasta selecionada",
        "no_videos_found": "Nenhum arquivo de vídeo encontrado na pasta selecionada:",
        "no_files": "Nenhum arquivo",
        "no_wavs_found": "Nenhum arquivo WAV encontrado na pasta atual.",
        "overwrite": "Sobrescrever?",
        "overwrite_audio": "O arquivo de áudio já existe. Sobrescrever?",
        "saved": "Salvo",
        "metadata_saved": "Metadados salvos!",
        "success": "Sucesso",
        "wavs_joined": "Todos os arquivos WAV foram unidos com sucesso em:",
    },
    "Español (Latinoamérica)": {
        "language_name": "Español (Latinoamérica)",
        "app_title": "Herramienta de Anotación de Video",
        "select_folder": "Seleccionar Carpeta",
        "open_ocenaudio": "Abrir todas las grabaciones en Ocenaudio (Para normalizar, recortar, editar...)",
        "export_wavs": "Exportar Datos Grabados",
        "clear_wavs": "Borrar Datos Grabados",
        "import_wavs": "Importar Datos Grabados",
        "join_wavs": "Exportar como Archivo Único de Audio (para SayMore/ELAN)",
        "video_listbox_no_video": "No se seleccionó ningún video",
        "play_video": "Reproducir Video",
        "stop_video": "Detener Video",
        "audio_no_annotation": "Sin anotación de audio",
        "play_audio": "Reproducir Audio",
        "stop_audio": "Detener Audio",
        "record_audio": "Grabar Audio",
        "stop_recording": "Detener Grabación",
        "edit_metadata": "Editar Metadatos",
        "save_metadata": "Guardar",
        "audio_label_prefix": "Audio: ",
        "no_folder_selected": "No se seleccionó ninguna carpeta",
        "no_videos_found": "No se encontraron archivos de video en la carpeta seleccionada:",
        "no_files": "Sin archivos",
        "no_wavs_found": "No se encontraron archivos WAV en la carpeta actual.",
        "overwrite": "¿Sobrescribir?",
        "overwrite_audio": "El archivo de audio ya existe. ¿Sobrescribir?",
        "saved": "Guardado",
        "metadata_saved": "¡Metadatos guardados!",
        "success": "Éxito",
        "wavs_joined": "Todos los archivos WAV se unieron exitosamente en:",
    },
    "Afrikaans": {
        "language_name": "Afrikaans",
        "app_title": "Video Annotasie Hulpmiddel",
        "select_folder": "Kies Gids",
        "open_ocenaudio": "Maak alle Opnames in Ocenaudio oop (Vir Normaliseer, Sny, Redigeer...)",
        "export_wavs": "Voer Opname Data Uit",
        "clear_wavs": "Vee Opname Data Uit",
        "import_wavs": "Voer Opname Data In",
        "join_wavs": "Voer uit as Enkel Klanklêer (vir SayMore/ELAN)",
        "video_listbox_no_video": "Geen video gekies nie",
        "play_video": "Speel Video",
        "stop_video": "Stop Video",
        "audio_no_annotation": "Geen klankannotasie nie",
        "play_audio": "Speel Klank",
        "stop_audio": "Stop Klank",
        "record_audio": "Neem Klank op",
        "stop_recording": "Stop Opname",
        "edit_metadata": "Redigeer Metadata",
        "save_metadata": "Stoor",
        "audio_label_prefix": "Klank: ",
        "no_folder_selected": "Geen gids gekies nie",
        "no_videos_found": "Geen videolêers in die gekose gids gevind nie:",
        "no_files": "Geen lêers",
        "no_wavs_found": "Geen WAV-lêers in die huidige gids gevind nie.",
        "overwrite": "Oorskryf?",
        "overwrite_audio": "Klanklêer bestaan reeds. Oorskryf?",
        "saved": "Gestoor",
        "metadata_saved": "Metadata gestoor!",
        "success": "Sukses",
        "wavs_joined": "Alle WAV-lêers suksesvol saamgevoeg tot:",
    },
}


# Helper for PyInstaller runtime resource resolution
def resource_path(relative_path, check_system=True):
    """Get absolute path to resource, works for dev and PyInstaller (onefile/onedir)."""
    # In dev, optionally prefer a system-installed binary if just a filename is provided
    if check_system:
        binary_name = os.path.basename(relative_path)
        system_path = shutil.which(binary_name)
        if system_path:
            return system_path
    # When bundled by PyInstaller, _MEIPASS is set (especially in onefile)
    if hasattr(sys, '_MEIPASS') and sys._MEIPASS:
        return os.path.join(sys._MEIPASS, relative_path)
    # In onedir app bundles, prefer the executable directory (Contents/MacOS) over CWD
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
        return os.path.join(base_dir, relative_path)
    # Fallback to current working directory
    return os.path.join(os.path.abspath("."), relative_path)


# Configure OpenCV FFmpeg DLL path (Windows-specific)
def configure_opencv_ffmpeg():
    dll_name = "opencv_videoio_ffmpeg4120_64.dll"
    opencv_dir = os.path.dirname(cv2.__file__)
    system_dll_path = os.path.join(opencv_dir, dll_name)
    if os.path.exists(system_dll_path):
        os.environ["OPENCV_FFMPEG_DLL_DIR"] = opencv_dir
        os.environ["PATH"] = opencv_dir + os.pathsep + os.environ.get("PATH", "")
    else:
        bundled_dll_path = resource_path(dll_name, check_system=False)
        if os.path.exists(bundled_dll_path):
            os.environ["OPENCV_FFMPEG_DLL_DIR"] = os.path.dirname(bundled_dll_path)
            os.environ["PATH"] = os.path.dirname(bundled_dll_path) + os.pathsep + os.environ.get("PATH", "")


# Configure pydub to use FFmpeg
def configure_pydub_ffmpeg():
    ffmpeg_path = resource_path(os.path.join("ffmpeg", "bin", "ffmpeg"))
    ffprobe_path = resource_path(os.path.join("ffmpeg", "bin", "ffprobe"))
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    if os.path.exists(ffmpeg_dir):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    if os.path.exists(ffmpeg_path):
        os.environ["PYDUB_FFMPEG"] = ffmpeg_path
    if os.path.exists(ffprobe_path):
        os.environ["PYDUB_FFPROBE"] = ffprobe_path


configure_opencv_ffmpeg()
configure_pydub_ffmpeg()


# Audio playback worker (runs in QThread)
class AudioPlaybackWorker(QObject):
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, wav_path):
        super().__init__()
        self.wav_path = wav_path
        self.should_stop = False
    
    def run(self):
        if not PYAUDIO_AVAILABLE:
            self.error.emit("PyAudio is not available")
            self.finished.emit()
            return
            
        try:
            p = pyaudio.PyAudio()
            wf = wave.open(self.wav_path, 'rb')
            stream = p.open(
                format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )
            
            data = wf.readframes(1024)
            while data and not self.should_stop:
                stream.write(data)
                data = wf.readframes(1024)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            wf.close()
        except Exception as e:
            self.error.emit(f"Audio playback failed: {e}")
        finally:
            self.finished.emit()
    
    def stop(self):
        self.should_stop = True


# Audio recording worker (runs in QThread)
class AudioRecordingWorker(QObject):
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, wav_path):
        super().__init__()
        self.wav_path = wav_path
        self.should_stop = False
        self.frames = []
    
    def run(self):
        if not PYAUDIO_AVAILABLE:
            self.error.emit("PyAudio is not available")
            self.finished.emit()
            return
            
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                frames_per_buffer=1024
            )
            
            while not self.should_stop:
                data = stream.read(1024, exception_on_overflow=False)
                self.frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # Save WAV file
            if self.frames:
                wf = wave.open(self.wav_path, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                wf.writeframes(b''.join(self.frames))
                wf.close()
        except Exception as e:
            self.error.emit(f"Recording failed: {e}")
        finally:
            self.finished.emit()
    
    def stop(self):
        self.should_stop = True


# Main application window
class VideoAnnotationApp(QMainWindow):
    ui_info = Signal(str, str)
    ui_warning = Signal(str, str)
    ui_error = Signal(str, str)
    def __init__(self):
        super().__init__()
        self.language = "English"
        self.LABELS = LABELS_ALL[self.language]
        
        self.folder_path = None
        self.video_files = []
        self.current_video = None
        self.ocenaudio_path = None
        self.settings_file = os.path.expanduser("~/.videooralannotation/settings.json")
        
        # Video playback state
        self.playing_video = False
        self.cap = None
        self.video_timer = QTimer()
        self.video_timer.timeout.connect(self.update_video_frame)
        
        # Audio playback state
        self.audio_thread = None
        self.audio_worker = None
        
        # Recording state
        self.is_recording = False
        self.recording_thread = None
        self.recording_worker = None
        
        self.load_settings()
        self.init_ui()
        self.setWindowTitle(self.LABELS["app_title"])
        self.resize(1400, 800)
        self.ui_info.connect(self._show_info)
        self.ui_warning.connect(self._show_warning)
        self.ui_error.connect(self._show_error)

        # If a folder was persisted, reflect it in the UI
        if self.folder_path:
            self.update_folder_display()
            # Enable folder-dependent actions
            self.export_wavs_button.setEnabled(True)
            self.clear_wavs_button.setEnabled(True)
            self.import_wavs_button.setEnabled(True)
            self.join_wavs_button.setEnabled(True)
            self.open_ocenaudio_button.setEnabled(True)
            # Populate list and metadata view
            self.load_video_files()
            self.open_metadata_editor()

    def _show_info(self, title, text):
        QMessageBox.information(self, title, text)

    def _show_warning(self, title, text):
        QMessageBox.warning(self, title, text)

    def _show_error(self, title, text):
        QMessageBox.critical(self, title, text)

    def _show_worker_error(self, msg):
        QMessageBox.critical(self, "Error", msg)
    
    def init_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Language selector at top
        self.language_dropdown = QComboBox()
        self.language_dropdown.addItems([LABELS_ALL[k]["language_name"] for k in LABELS_ALL])
        self.language_dropdown.setCurrentText(self.LABELS["language_name"])
        self.language_dropdown.currentTextChanged.connect(self.change_language)
        main_layout.addWidget(self.language_dropdown)
        
        # Current folder display
        self.folder_display_label = QLabel(self.LABELS["no_folder_selected"])
        self.folder_display_label.setAlignment(Qt.AlignLeft)
        self.folder_display_label.setToolTip("")
        main_layout.addWidget(self.folder_display_label)
        
        # Horizontal splitter for left and right panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel: Video list and buttons
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Action buttons
        self.select_button = QPushButton(self.LABELS["select_folder"])
        self.select_button.clicked.connect(self.select_folder)
        left_layout.addWidget(self.select_button)
        
        self.open_ocenaudio_button = QPushButton(self.LABELS["open_ocenaudio"])
        self.open_ocenaudio_button.clicked.connect(self.open_in_ocenaudio)
        self.open_ocenaudio_button.setEnabled(False)
        left_layout.addWidget(self.open_ocenaudio_button)
        
        self.export_wavs_button = QPushButton(self.LABELS["export_wavs"])
        self.export_wavs_button.clicked.connect(self.export_wavs)
        self.export_wavs_button.setEnabled(False)
        left_layout.addWidget(self.export_wavs_button)
        
        self.clear_wavs_button = QPushButton(self.LABELS["clear_wavs"])
        self.clear_wavs_button.clicked.connect(self.clear_wavs)
        self.clear_wavs_button.setEnabled(False)
        left_layout.addWidget(self.clear_wavs_button)
        
        self.import_wavs_button = QPushButton(self.LABELS["import_wavs"])
        self.import_wavs_button.clicked.connect(self.import_wavs)
        self.import_wavs_button.setEnabled(False)
        left_layout.addWidget(self.import_wavs_button)
        
        self.join_wavs_button = QPushButton(self.LABELS["join_wavs"])
        self.join_wavs_button.clicked.connect(self.join_all_wavs)
        self.join_wavs_button.setEnabled(False)
        left_layout.addWidget(self.join_wavs_button)
        
        # Video list
        self.video_listbox = QListWidget()
        self.video_listbox.currentRowChanged.connect(self.on_video_select)
        left_layout.addWidget(self.video_listbox)
        
        # Metadata editor
        metadata_label = QLabel(self.LABELS["edit_metadata"])
        metadata_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        left_layout.addWidget(metadata_label)
        
        self.metadata_text = QTextEdit()
        self.metadata_text.setMinimumHeight(150)
        left_layout.addWidget(self.metadata_text)
        
        save_metadata_btn = QPushButton(self.LABELS["save_metadata"])
        save_metadata_btn.clicked.connect(self.save_metadata)
        left_layout.addWidget(save_metadata_btn)
        
        splitter.addWidget(left_panel)
        
        # Right panel: Tab widget with Videos tab
        right_panel = QTabWidget()
        
        # Videos tab
        videos_tab = QWidget()
        videos_layout = QVBoxLayout(videos_tab)
        
        # Video display
        self.video_label = QLabel(self.LABELS["video_listbox_no_video"])
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        videos_layout.addWidget(self.video_label)
        
        # Video controls
        video_controls_layout = QHBoxLayout()
        self.play_video_button = QPushButton(self.LABELS["play_video"])
        self.play_video_button.clicked.connect(self.play_video)
        self.play_video_button.setEnabled(False)
        video_controls_layout.addWidget(self.play_video_button)
        
        self.stop_video_button = QPushButton(self.LABELS["stop_video"])
        self.stop_video_button.clicked.connect(self.stop_video)
        self.stop_video_button.setEnabled(False)
        video_controls_layout.addWidget(self.stop_video_button)
        videos_layout.addLayout(video_controls_layout)
        
        # Audio annotation section
        self.audio_label = QLabel(self.LABELS["audio_no_annotation"])
        self.audio_label.setAlignment(Qt.AlignCenter)
        videos_layout.addWidget(self.audio_label)
        
        # Audio controls
        audio_controls_layout = QHBoxLayout()
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
        videos_layout.addLayout(audio_controls_layout)
        
        videos_layout.addStretch()
        
        right_panel.addTab(videos_tab, "Videos")
        splitter.addWidget(right_panel)
        
        # Set splitter sizes (left panel smaller than right)
        splitter.setSizes([400, 1000])
    
    def change_language(self, selected_name):
        for key, labels in LABELS_ALL.items():
            if labels["language_name"] == selected_name:
                self.language = key
                self.LABELS = LABELS_ALL[self.language]
                break
        self.setWindowTitle(self.LABELS["app_title"])
        self.refresh_ui_texts()
    
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
        
        if not self.current_video:
            self.video_label.setText(self.LABELS["video_listbox_no_video"])
            self.audio_label.setText(self.LABELS["audio_no_annotation"])
        
        self.update_folder_display()
    
    def update_folder_display(self):
        if self.folder_path:
            folder_name = os.path.basename(os.path.normpath(self.folder_path)) or self.folder_path
            self.folder_display_label.setText(folder_name)
            self.folder_display_label.setToolTip(self.folder_path)
        else:
            self.folder_display_label.setText(self.LABELS["no_folder_selected"])
            self.folder_display_label.setToolTip("")
    
    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.ocenaudio_path = settings.get('ocenaudio_path')
                    saved_lang = settings.get('language')
                    if saved_lang and saved_lang in LABELS_ALL:
                        self.language = saved_lang
                        self.LABELS = LABELS_ALL[self.language]
                    last_folder = settings.get('last_folder')
                    if last_folder and os.path.isdir(last_folder):
                        self.folder_path = last_folder
        except Exception as e:
            logging.warning(f"Failed to load settings: {e}")
    
    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump({
                    'ocenaudio_path': self.ocenaudio_path,
                    'language': self.language,
                    'last_folder': self.folder_path
                }, f)
        except Exception as e:
            logging.warning(f"Failed to save settings: {e}")
    
    def select_folder(self):
        initial_dir = self.folder_path or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with Video Files", initial_dir)
        if folder:
            self.folder_path = folder
            self.update_folder_display()
            
            # On Windows, delete all files starting with a period
            if sys.platform == "win32":
                hidden_files = [f for f in os.listdir(self.folder_path) if f.startswith('.')]
                errors = []
                for f in hidden_files:
                    try:
                        os.remove(os.path.join(self.folder_path, f))
                    except Exception as e:
                        errors.append(f"Delete {f}: {e}")
                if errors:
                    QMessageBox.warning(self, "Cleanup Errors", "Some hidden files could not be deleted:\n" + "\n".join(errors))
            
            self.load_video_files()
            self.open_metadata_editor()
            self.export_wavs_button.setEnabled(True)
            self.clear_wavs_button.setEnabled(True)
            self.import_wavs_button.setEnabled(True)
            self.join_wavs_button.setEnabled(True)
            self.open_ocenaudio_button.setEnabled(True)
            self.save_settings()
    
    def load_video_files(self):
        self.video_listbox.clear()
        self.video_files = []
        extensions = ('.mpg', '.mpeg', '.mp4', '.avi', '.mkv', '.mov')
        
        if not self.folder_path:
            QMessageBox.information(self, self.LABELS["no_folder_selected"], self.LABELS["no_folder_selected"])
            return
        
        try:
            for filename in os.listdir(self.folder_path):
                full_path = os.path.join(self.folder_path, filename)
                if os.path.isfile(full_path) and filename.lower().endswith(extensions):
                    self.video_files.append(full_path)
            
            self.video_files.sort()
            for video_path in self.video_files:
                self.video_listbox.addItem(os.path.basename(video_path))
            
            if not self.video_files:
                QMessageBox.information(self, self.LABELS["no_videos_found"], f"{self.LABELS['no_videos_found']} {self.folder_path}")
        
        except PermissionError:
            QMessageBox.critical(self, "Permission Denied", f"You do not have permission to access the folder: {self.folder_path}")
        except FileNotFoundError:
            QMessageBox.critical(self, "Folder Not Found", f"The selected folder no longer exists: {self.folder_path}")
        except Exception as e:
            QMessageBox.critical(self, "An Error Occurred", f"An unexpected error occurred: {e}")
        
        self.current_video = None
        self.update_media_controls()
    
    def open_metadata_editor(self):
        metadata_path = os.path.join(self.folder_path, "metadata.txt")
        default_content = (
            "name: \n"
            "date: \n"
            "location: \n"
            "researcher: \n"
            "speaker: \n"
            "permissions for use given by speaker: \n"
        )
        if not os.path.exists(metadata_path):
            with open(metadata_path, "w") as f:
                f.write(default_content)
        with open(metadata_path, "r") as f:
            content = f.read()
        
        self.metadata_text.setPlainText(content)
    
    def save_metadata(self):
        if not self.folder_path:
            return
        metadata_path = os.path.join(self.folder_path, "metadata.txt")
        content = self.metadata_text.toPlainText()
        with open(metadata_path, "w") as f:
            f.write(content)
        QMessageBox.information(self, self.LABELS["saved"], self.LABELS["metadata_saved"])
    
    def on_video_select(self, current_row):
        if current_row < 0:
            return
        self.current_video = self.video_listbox.item(current_row).text()
        self.update_media_controls()
        self.show_first_frame()
    
    def show_first_frame(self):
        if not self.current_video:
            self.video_label.setText("No video selected")
            return
        video_path = os.path.join(self.folder_path, self.current_video)
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (640, 480))
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            self.video_label.setPixmap(pixmap)
        else:
            self.video_label.setText("Cannot read video")
        cap.release()
    
    def update_media_controls(self):
        if self.current_video:
            self.play_video_button.setEnabled(True)
            self.stop_video_button.setEnabled(True)
            self.record_button.setEnabled(True)
            self.record_button.setText(self.LABELS["record_audio"] if not self.is_recording else self.LABELS["stop_recording"])
            
            wav_path = os.path.join(self.folder_path, os.path.splitext(self.current_video)[0] + '.wav')
            if os.path.exists(wav_path):
                self.audio_label.setText(f"{self.LABELS['audio_label_prefix']}{os.path.splitext(self.current_video)[0]}.wav")
                self.play_audio_button.setEnabled(True)
                self.stop_audio_button.setEnabled(True)
            else:
                self.audio_label.setText(self.LABELS["audio_no_annotation"])
                self.play_audio_button.setEnabled(False)
                self.stop_audio_button.setEnabled(False)
        else:
            self.video_label.setText(self.LABELS["video_listbox_no_video"])
            self.play_video_button.setEnabled(False)
            self.stop_video_button.setEnabled(False)
            self.audio_label.setText(self.LABELS["audio_no_annotation"])
            self.play_audio_button.setEnabled(False)
            self.stop_audio_button.setEnabled(False)
            self.record_button.setEnabled(False)
            self.record_button.setText(self.LABELS["record_audio"])
    
    def play_video(self):
        if not self.current_video:
            return
        self.stop_video()
        video_path = os.path.join(self.folder_path, self.current_video)
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Error", "Cannot open video file.")
            return
        self.playing_video = True
        self.video_timer.start(30)  # ~30 FPS
    
    def update_video_frame(self):
        if self.playing_video and self.cap:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (640, 480))
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                self.video_label.setPixmap(pixmap)
            else:
                self.stop_video()
    
    def stop_video(self):
        self.playing_video = False
        self.video_timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.show_first_frame()
    
    def play_audio(self):
        if not self.current_video:
            return
        self.stop_audio()
        wav_path = os.path.join(self.folder_path, os.path.splitext(self.current_video)[0] + '.wav')
        if not os.path.exists(wav_path):
            return
        
        if not PYAUDIO_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyAudio is not available. Cannot play audio.")
            return
        
        self.audio_thread = QThread()
        self.audio_worker = AudioPlaybackWorker(wav_path)
        self.audio_worker.moveToThread(self.audio_thread)
        self.audio_thread.started.connect(self.audio_worker.run)
        self.audio_worker.finished.connect(self.audio_thread.quit)
        self.audio_worker.finished.connect(self.audio_worker.deleteLater)
        self.audio_thread.finished.connect(self.audio_thread.deleteLater)
        self.audio_worker.error.connect(self._show_worker_error)
        self.audio_thread.start()
    
    def stop_audio(self):
        if self.audio_worker:
            self.audio_worker.stop()
        if self.audio_thread:
            self.audio_thread.quit()
            self.audio_thread.wait()
    
    def toggle_recording(self):
        if not self.current_video:
            return
        
        if self.is_recording:
            self.is_recording = False
            if self.recording_worker:
                self.recording_worker.stop()
            if self.recording_thread:
                self.recording_thread.quit()
                self.recording_thread.wait()
            self.update_media_controls()
        else:
            wav_path = os.path.join(self.folder_path, os.path.splitext(self.current_video)[0] + '.wav')
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
            
            self.recording_thread = QThread()
            self.recording_worker = AudioRecordingWorker(wav_path)
            self.recording_worker.moveToThread(self.recording_thread)
            self.recording_thread.started.connect(self.recording_worker.run)
            self.recording_worker.finished.connect(self.recording_thread.quit)
            self.recording_worker.finished.connect(self.recording_worker.deleteLater)
            self.recording_thread.finished.connect(self.recording_thread.deleteLater)
            self.recording_worker.finished.connect(self.update_media_controls)
            self.recording_worker.error.connect(self._show_worker_error)
            self.recording_thread.start()
    
    def open_in_ocenaudio(self):
        if not self.folder_path:
            QMessageBox.critical(self, "Error", "No folder selected.")
            return
        
        wav_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.wav') and not f.startswith('.')]
        if not wav_files:
            QMessageBox.information(self, "No Files", "No WAV files found in the current folder to open.")
            return
        
        wav_files.sort()
        file_paths = [os.path.join(self.folder_path, f) for f in wav_files]
        
        if self.ocenaudio_path and os.path.exists(self.ocenaudio_path):
            command = [self.ocenaudio_path] + file_paths
        else:
            possible_paths = []
            if sys.platform == "darwin":
                possible_paths = ["/Applications/ocenaudio.app/Contents/MacOS/ocenaudio"]
            elif sys.platform == "win32":
                possible_paths = [
                    r"C:\Program Files\ocenaudio\ocenaudio.exe",
                    r"C:\ocenaudio\ocenaudio.exe",
                    r"C:\Program Files (x86)\ocenaudio\ocenaudio.exe",
                    os.path.expandvars(r"%USERPROFILE%\ocenaudio\ocenaudio.exe"),
                    os.path.expandvars(r"%LOCALAPPDATA%\ocenaudio\ocenaudio.exe")
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
                    "Locate Ocenaudio Executable",
                    "",
                    "Executable Files (*.exe);;All Files (*)" if sys.platform == "win32" else "All Files (*)"
                )
                if not ocenaudio_path:
                    QMessageBox.warning(self, "Ocenaudio Not Found", "Ocenaudio not found. Please install it to use this feature.")
                    return
            
            self.ocenaudio_path = ocenaudio_path
            self.save_settings()
            command = [self.ocenaudio_path] + file_paths
        
        try:
            subprocess.Popen(command)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Ocenaudio: {e}")
    
    def export_wavs(self):
        if not self.folder_path:
            QMessageBox.critical(self, "Error", "No folder selected.")
            return
        
        wav_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.wav') and not f.startswith('.')]
        export_dir = QFileDialog.getExistingDirectory(self, "Select Export Folder for WAV Files")
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
                "Overwrite Files?",
                "The following files already exist in the export folder and will be overwritten:\n"
                + "\n".join(overwrite_files)
                + "\n\nDo you want to overwrite them?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                QMessageBox.information(self, "Export Cancelled", "Export was cancelled to avoid overwriting files.")
                return
        
        errors = []
        for wav in wav_files:
            src = os.path.join(self.folder_path, wav)
            dst = os.path.join(export_dir, wav)
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                errors.append(f"{wav}: {e}")
        
        metadata_src = os.path.join(self.folder_path, "metadata.txt")
        try:
            shutil.copy2(metadata_src, metadata_dst)
        except Exception as e:
            errors.append(f"metadata.txt: {e}")
        
        if errors:
            QMessageBox.critical(self, "Export Errors", "Some files could not be exported:\n" + "\n".join(errors))
        else:
            QMessageBox.information(self, "Export Recorded Data", f"Exported {len(wav_files)} WAV files and metadata.txt to {export_dir}.")
    
    def clear_wavs(self):
        if not self.folder_path:
            QMessageBox.critical(self, "Error", "No folder selected.")
            return
        
        wav_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.wav') and not f.startswith('.')]
        if not wav_files:
            QMessageBox.information(self, "Clear Recorded Data", "No WAV files found in the current folder.")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete {len(wav_files)} WAV files from this folder?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return
        
        errors = []
        for wav in wav_files:
            try:
                os.remove(os.path.join(self.folder_path, wav))
            except Exception as e:
                errors.append(f"{wav}: {e}")
        
        metadata_path = os.path.join(self.folder_path, "metadata.txt")
        default_content = (
            "name: \n"
            "date: \n"
            "location: \n"
            "researcher: \n"
            "speaker: \n"
            "permissions for use given by speaker: \n"
        )
        try:
            with open(metadata_path, "w") as f:
                f.write(default_content)
        except Exception as e:
            errors.append(f"metadata.txt reset: {e}")
        
        if errors:
            QMessageBox.critical(self, "Delete Errors", "Some files could not be deleted or metadata.txt could not be reset:\n" + "\n".join(errors))
        else:
            QMessageBox.information(self, "Clear Recorded Data", f"Deleted {len(wav_files)} WAV files and reset metadata.txt.")
        
        self.load_video_files()
        self.open_metadata_editor()
    
    def import_wavs(self):
        if not self.folder_path:
            QMessageBox.critical(self, "Error", "No folder selected.")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            "Importing will delete all current WAV files and reset metadata. Are you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return
        
        # Clear existing WAVs in destination folder
        wav_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.wav') and not f.startswith('.')]
        errors = []
        for wav in wav_files:
            try:
                os.remove(os.path.join(self.folder_path, wav))
            except Exception as e:
                errors.append(f"Delete {wav}: {e}")
        
        # Select import folder
        import_dir = QFileDialog.getExistingDirectory(self, "Select Folder to Import Files From")
        if not import_dir:
            return
        
        # Prepare to import WAV files, excluding macOS hidden files
        import_files = [f for f in os.listdir(import_dir) if f.lower().endswith('.wav') and not f.startswith('.')]
        video_basenames = set(os.path.splitext(os.path.basename(f))[0] for f in self.video_files)
        mismatched_wavs = []
        imported_count = 0
        matched = False
        
        for wav in import_files:
            wav_basename = os.path.splitext(wav)[0]
            if wav_basename in video_basenames:
                matched = True
        
        # Copy metadata.txt only if at least one WAV matches
        metadata_src = os.path.join(import_dir, "metadata.txt")
        metadata_dst = os.path.join(self.folder_path, "metadata.txt")
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
        
        # Check for overwrites
        overwrite_files = []
        for wav in import_files:
            wav_basename = os.path.splitext(wav)[0]
            if wav_basename in video_basenames:
                dst = os.path.join(self.folder_path, wav)
                if os.path.exists(dst):
                    overwrite_files.append(wav)
        
        if os.path.exists(metadata_dst) and os.path.exists(metadata_src):
            overwrite_files.append("metadata.txt")
        
        if overwrite_files:
            reply = QMessageBox.question(
                self,
                "Overwrite Files?",
                "The following files already exist and will be overwritten by import:\n"
                + "\n".join(overwrite_files)
                + "\n\nDo you want to overwrite them?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                QMessageBox.information(self, "Import Cancelled", "Import was cancelled to avoid overwriting files.")
                return
        
        # Import WAV files
        for wav in import_files:
            wav_basename = os.path.splitext(wav)[0]
            if wav_basename in video_basenames:
                src = os.path.join(import_dir, wav)
                dst = os.path.join(self.folder_path, wav)
                try:
                    shutil.copy2(src, dst)
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Import {wav}: {e}")
            else:
                mismatched_wavs.append(wav)
        
        if mismatched_wavs:
            QMessageBox.warning(self, "WAV Filename Mismatch", "The following WAV files do not match any video filenames and were not imported:\n" + "\n".join(mismatched_wavs))
        
        if errors:
            QMessageBox.critical(self, "Import Errors", "Some files could not be imported or deleted:\n" + "\n".join(errors))
        else:
            QMessageBox.information(self, "Import Recorded Data", f"Imported {imported_count} WAV files and metadata.txt.")
        
        self.load_video_files()
        self.open_metadata_editor()
    
    def join_all_wavs(self):
        if not self.folder_path:
            QMessageBox.critical(self, "Error", "No folder selected.")
            return
        
        wav_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.wav') and not f.startswith('.')]
        if not wav_files:
            QMessageBox.information(self, "No Files", "No WAV files found in the current folder.")
            return
        
        ffmpeg_path = resource_path(os.path.join("ffmpeg", "bin", "ffmpeg"))
        if not os.path.exists(ffmpeg_path):
            QMessageBox.critical(self, "Error", "FFmpeg not found. Please ensure FFmpeg is installed or bundled with the executable.")
            return
        
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Save Combined WAV File",
            "",
            "WAV files (*.wav)"
        )
        if not output_file:
            return
        
        # Run in a separate thread to avoid blocking the UI
        def process_and_join():
            try:
                wav_files.sort()
                std_rate = 44100
                std_channels = 1
                std_sample_width = 2
                silence_segment = AudioSegment.silent(duration=500, frame_rate=std_rate)
                click_sound = self.generate_click_sound_pydub(duration_ms=5, freq=2000, rate=std_rate)
                click_segment = silence_segment + click_sound + silence_segment
                combined_audio = AudioSegment.empty()
                combined_audio = combined_audio.set_frame_rate(std_rate).set_channels(std_channels).set_sample_width(std_sample_width)
                
                for i, file in enumerate(wav_files):
                    file_path = os.path.join(self.folder_path, file)
                    audio = AudioSegment.from_file(file_path, format="wav")
                    if audio.frame_rate != std_rate:
                        audio = audio.set_frame_rate(std_rate)
                    if audio.channels != std_channels:
                        audio = audio.set_channels(std_channels)
                    if audio.sample_width != std_sample_width:
                        audio = audio.set_sample_width(std_sample_width)
                    combined_audio += audio
                    if i < len(wav_files) - 1:
                        combined_audio += click_segment
                
                combined_audio.export(output_file, format="wav")
                self.ui_info.emit(self.LABELS["success"], f"{self.LABELS['wavs_joined']}\n{output_file}")
            except Exception as e:
                self.ui_error.emit("Error", f"An error occurred while joining files:\n{e}")
        
        threading.Thread(target=process_and_join, daemon=True).start()
    
    def generate_click_sound_pydub(self, duration_ms, freq, rate):
        """Generates a short, subtle click sound using a high-frequency sine wave with a rapid decay."""
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


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Video Annotation Tool")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--log-file", type=str, help="Log file path")
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    log_handlers = []
    
    if args.log_file:
        log_handlers.append(logging.FileHandler(args.log_file))
    
    if args.debug:
        log_handlers.append(logging.StreamHandler(sys.stdout))
    
    if log_handlers:
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=log_handlers
        )
    
    logging.info("Starting Video Annotation Tool (PySide6 version)")
    
    # Create and run the application
    app = QApplication(sys.argv)
    app.setApplicationName("Video Annotation Tool")
    
    window = VideoAnnotationApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
