#!/usr/bin/env python3.11
# videoannotation.py
# A simple video annotation tool with audio recording capabilities.
#NOTE: This script works with python 3.11, NOT 3.12 (due to opencv and pydub issues) or 3.13
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import cv2
from PIL import Image, ImageTk
import threading
import pyaudio
import wave
import numpy as np
import shutil
from pydub import AudioSegment
import subprocess
import sys
import json

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
    """Get absolute path to resource, works for dev (system PATH) and PyInstaller."""
    if check_system:
        binary_name = os.path.basename(relative_path)
        system_path = shutil.which(binary_name)
        if system_path:
            return system_path
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
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

class VideoAnnotationApp:
    def __init__(self, root):
        self.root = root
        self.language = "English"
        self.LABELS = LABELS_ALL[self.language]

        # Language selection dropdown (shows native names)
        self.language_var = tk.StringVar(value=self.LABELS["language_name"])
        self.language_dropdown = ttk.Combobox(
            root,
            textvariable=self.language_var,
            values=[LABELS_ALL[k]["language_name"] for k in LABELS_ALL],
            state="readonly"
        )
        self.language_dropdown.pack(fill=tk.X, padx=10, pady=5)
        self.language_dropdown.bind("<<ComboboxSelected>>", self.change_language)

        self.folder_path = None
        self.video_files = []
        self.current_video = None
        self.audio_stream = None
        self.recording_thread = None
        self.is_recording = False
        self.ocenaudio_path = None
        self.settings_file = os.path.expanduser("~/.videooralannotation/settings.json")
        self.load_settings()

        # Main container
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left frame: Video list
        self.list_frame = tk.Frame(self.main_frame)
        self.list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Select folder button
        self.select_button = tk.Button(self.list_frame, text=self.LABELS["select_folder"], command=self.select_folder)
        self.select_button.pack(fill=tk.X, pady=5)

        # Button for opening recordings in Ocenaudio
        self.open_ocenaudio_button = tk.Button(self.list_frame, text=self.LABELS["open_ocenaudio"], command=self.open_in_ocenaudio, state=tk.DISABLED)
        self.open_ocenaudio_button.pack(fill=tk.X, pady=5)

        # Export WAVs button
        self.export_wavs_button = tk.Button(self.list_frame, text=self.LABELS["export_wavs"], command=self.export_wavs, state=tk.DISABLED)
        self.export_wavs_button.pack(fill=tk.X, pady=5)

        # Clear WAVs button
        self.clear_wavs_button = tk.Button(self.list_frame, text=self.LABELS["clear_wavs"], command=self.clear_wavs, state=tk.DISABLED)
        self.clear_wavs_button.pack(fill=tk.X, pady=5)

        # Import WAVs button
        self.import_wavs_button = tk.Button(self.list_frame, text=self.LABELS["import_wavs"], command=self.import_wavs, state=tk.DISABLED)
        self.import_wavs_button.pack(fill=tk.X, pady=5)

        # Button for joining WAV files
        self.join_wavs_button = tk.Button(self.list_frame, text=self.LABELS["join_wavs"], command=self.join_all_wavs, state=tk.DISABLED)
        self.join_wavs_button.pack(fill=tk.X, pady=5)

        # Listbox for video files with scrollbar
        self.video_listbox_frame = tk.Frame(self.list_frame)
        self.video_listbox_frame.pack(fill=tk.BOTH, expand=True)
        self.video_listbox = tk.Listbox(self.video_listbox_frame, width=40, height=5)
        self.video_listbox.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        self.video_scrollbar = tk.Scrollbar(self.video_listbox_frame, orient=tk.VERTICAL, command=self.video_listbox.yview)
        self.video_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.video_listbox.config(yscrollcommand=self.video_scrollbar.set)
        self.video_listbox.bind('<<ListboxSelect>>', self.on_video_select)

        # Metadata editor frame placeholder
        self.metadata_editor_frame = None

        # Right frame: Video player and audio controls
        self.media_frame = tk.Frame(self.main_frame)
        self.media_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        # Video player section
        self.video_label = tk.Label(self.media_frame, text=self.LABELS["video_listbox_no_video"])
        self.video_label.pack()

        self.video_controls = tk.Frame(self.media_frame)
        self.video_controls.pack(pady=5)

        self.play_video_button = tk.Button(self.video_controls, text=self.LABELS["play_video"], command=self.play_video, state=tk.DISABLED)
        self.play_video_button.pack(side=tk.LEFT, padx=5)

        self.stop_video_button = tk.Button(self.video_controls, text=self.LABELS["stop_video"], command=self.stop_video, state=tk.DISABLED)
        self.stop_video_button.pack(side=tk.LEFT, padx=5)

        # Audio annotation section
        self.audio_frame = tk.Frame(self.media_frame)
        self.audio_frame.pack(pady=10)

        self.audio_label = tk.Label(self.audio_frame, text=self.LABELS["audio_no_annotation"])
        self.audio_label.pack()

        self.audio_controls = tk.Frame(self.audio_frame)
        self.audio_controls.pack(pady=5)

        self.play_audio_button = tk.Button(self.audio_controls, text=self.LABELS["play_audio"], command=self.play_audio, state=tk.DISABLED)
        self.play_audio_button.pack(side=tk.LEFT, padx=5)

        self.stop_audio_button = tk.Button(self.audio_controls, text=self.LABELS["stop_audio"], command=self.stop_audio, state=tk.DISABLED)
        self.stop_audio_button.pack(side=tk.LEFT, padx=5)

        self.record_button = tk.Button(self.audio_controls, text=self.LABELS["record_audio"], command=self.toggle_recording, state=tk.DISABLED)
        self.record_button.pack(side=tk.LEFT, padx=5)

        # Video playback state
        self.playing_video = False
        self.cap = None

        self.root.title(self.LABELS["app_title"])

    def change_language(self, event=None):
        selected_name = self.language_var.get()
        for key, labels in LABELS_ALL.items():
            if labels["language_name"] == selected_name:
                self.language = key
                self.LABELS = LABELS_ALL[self.language]
                break
        self.root.title(self.LABELS["app_title"])
        self.refresh_ui_texts()

    def refresh_ui_texts(self):
        self.select_button.config(text=self.LABELS["select_folder"])
        self.open_ocenaudio_button.config(text=self.LABELS["open_ocenaudio"])
        self.export_wavs_button.config(text=self.LABELS["export_wavs"])
        self.clear_wavs_button.config(text=self.LABELS["clear_wavs"])
        self.import_wavs_button.config(text=self.LABELS["import_wavs"])
        self.join_wavs_button.config(text=self.LABELS["join_wavs"])
        self.video_label.config(text=self.LABELS["video_listbox_no_video"])
        self.play_video_button.config(text=self.LABELS["play_video"])
        self.stop_video_button.config(text=self.LABELS["stop_video"])
        self.audio_label.config(text=self.LABELS["audio_no_annotation"])
        self.play_audio_button.config(text=self.LABELS["play_audio"])
        self.stop_audio_button.config(text=self.LABELS["stop_audio"])
        self.record_button.config(text=self.LABELS["record_audio"] if not self.is_recording else self.LABELS["stop_recording"])
        if hasattr(self, "metadata_editor_frame") and self.metadata_editor_frame:
            for widget in self.metadata_editor_frame.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.config(text=self.LABELS["edit_metadata"])
                if isinstance(widget, tk.Button):
                    widget.config(text=self.LABELS["save_metadata"])

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.ocenaudio_path = settings.get('ocenaudio_path')
        except Exception as e:
            messagebox.showwarning("Settings Error", f"Failed to load settings: {e}")

    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump({'ocenaudio_path': self.ocenaudio_path}, f)
        except Exception as e:
            messagebox.showwarning("Settings Error", f"Failed to save settings: {e}")

    def select_folder(self):
        self.folder_path = filedialog.askdirectory(title="Select Folder with Video Files")
        if self.folder_path:
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
                    messagebox.showwarning("Cleanup Errors", "Some hidden files could not be deleted:\n" + "\n".join(errors))
            self.load_video_files()
            self.open_metadata_editor()
            self.export_wavs_button.config(state=tk.NORMAL)
            self.clear_wavs_button.config(state=tk.NORMAL)
            self.import_wavs_button.config(state=tk.NORMAL)
            self.join_wavs_button.config(state=tk.NORMAL)
            self.open_ocenaudio_button.config(state=tk.NORMAL)

    def import_wavs(self):
        if not self.folder_path:
            messagebox.showerror("Error", "No folder selected.")
            return
        if not messagebox.askyesno("Confirm Import", "Importing will delete all current WAV files and reset metadata. Are you sure you want to continue?"):
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
        import_dir = filedialog.askdirectory(title="Select Folder to Import Files From")
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
            if not messagebox.askyesno(
                "Overwrite Files?",
                "The following files already exist and will be overwritten by import:\n"
                + "\n".join(overwrite_files)
                + "\n\nDo you want to overwrite them?"
            ):
                messagebox.showinfo("Import Cancelled", "Import was cancelled to avoid overwriting files.")
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
            messagebox.showwarning("WAV Filename Mismatch", "The following WAV files do not match any video filenames and were not imported:\n" + "\n".join(mismatched_wavs))
        if errors:
            messagebox.showerror("Import Errors", "Some files could not be imported or deleted:\n" + "\n".join(errors))
        else:
            messagebox.showinfo("Import Recorded Data", f"Imported {imported_count} WAV files and metadata.txt.")
        self.load_video_files()
        self.open_metadata_editor()

    def load_video_files(self):
        self.video_listbox.delete(0, tk.END)
        self.video_files = []
        extensions = ('.mpg', '.mpeg', '.mp4', '.avi', '.mkv', '.mov')
        
        if not self.folder_path:
            messagebox.showinfo(LABELS_ALL["no_folder_selected"], LABELS_ALL["no_folder_selected"])
            return

        try:
            for filename in os.listdir(self.folder_path):
                full_path = os.path.join(self.folder_path, filename)
                if os.path.isfile(full_path) and filename.lower().endswith(extensions):
                    self.video_files.append(full_path)

            self.video_files.sort()
            for video_path in self.video_files:
                self.video_listbox.insert(tk.END, os.path.basename(video_path))
            
            if not self.video_files:
                messagebox.showinfo(LABELS_ALL["no_videos_found"], f"{LABELS_ALL['no_videos_found']} {self.folder_path}")

        except PermissionError:
            messagebox.showerror("Permission Denied", f"You do not have permission to access the folder: {self.folder_path}")
        except FileNotFoundError:
            messagebox.showerror("Folder Not Found", f"The selected folder no longer exists: {self.folder_path}")
        except Exception as e:
            messagebox.showerror("An Error Occurred", f"An unexpected error occurred: {e}")

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

        if hasattr(self, "metadata_editor_frame") and self.metadata_editor_frame:
            self.metadata_editor_frame.destroy()

        self.metadata_editor_frame = tk.Frame(self.list_frame)
        self.metadata_editor_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        tk.Label(self.metadata_editor_frame, text=self.LABELS["edit_metadata"], font=("Arial", 12, "bold")).pack()
        self.metadata_text = tk.Text(self.metadata_editor_frame, width=40, height=10)
        self.metadata_text.pack(pady=5, fill=tk.BOTH, expand=True)
        self.metadata_text.insert(tk.END, content)

        save_btn = tk.Button(self.metadata_editor_frame, text=self.LABELS["save_metadata"], command=self.save_metadata)
        save_btn.pack(pady=5)

    def save_metadata(self):
        metadata_path = os.path.join(self.folder_path, "metadata.txt")
        content = self.metadata_text.get("1.0", tk.END)
        with open(metadata_path, "w") as f:
            f.write(content)
        messagebox.showinfo(self.LABELS["saved"], self.LABELS["metadata_saved"])

    def on_video_select(self, event):
        selection = self.video_listbox.curselection()
        if not selection:
            return
        self.current_video = self.video_listbox.get(selection[0])
        self.update_media_controls()
        self.show_first_frame()

    def show_first_frame(self):
        if not self.current_video:
            self.video_label.config(image='', text="No video selected")
            return
        video_path = os.path.join(self.folder_path, self.current_video)
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (640, 480))
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk, text="")
        else:
            img = Image.new('RGB', (640, 480), color='black')
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk, text="")
        cap.release()

    def update_media_controls(self):
        if self.current_video:
            self.play_video_button.config(state=tk.NORMAL)
            self.stop_video_button.config(state=tk.NORMAL)
            self.record_button.config(state=tk.NORMAL, text=self.LABELS["record_audio"] if not self.is_recording else self.LABELS["stop_recording"])
            wav_path = os.path.join(self.folder_path, os.path.splitext(self.current_video)[0] + '.wav')
            if os.path.exists(wav_path):
                self.audio_label.config(text=f"{self.LABELS['audio_label_prefix']}{os.path.splitext(self.current_video)[0]}.wav")
                self.play_audio_button.config(state=tk.NORMAL)
                self.stop_audio_button.config(state=tk.NORMAL)
            else:
                self.audio_label.config(text=self.LABELS["audio_no_annotation"])
                self.play_audio_button.config(state=tk.DISABLED)
                self.stop_audio_button.config(state=tk.DISABLED)
        else:
            self.video_label.config(text=self.LABELS["video_listbox_no_video"])
            self.play_video_button.config(state=tk.DISABLED)
            self.stop_video_button.config(state=tk.DISABLED)
            self.audio_label.config(text=self.LABELS["audio_no_annotation"])
            self.play_audio_button.config(state=tk.DISABLED)
            self.stop_audio_button.config(state=tk.DISABLED)
            self.record_button.config(state=tk.DISABLED, text=self.LABELS["record_audio"])

    def open_in_ocenaudio(self):
        if not self.folder_path:
            messagebox.showerror("Error", "No folder selected.")
            return

        wav_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.wav') and not f.startswith('.')]
        if not wav_files:
            messagebox.showinfo("No Files", "No WAV files found in the current folder to open.")
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
                ocenaudio_path = filedialog.askopenfilename(
                    title="Locate Ocenaudio Executable",
                    filetypes=[("Executable Files", "*.exe" if sys.platform == "win32" else "*")]
                )
                if not ocenaudio_path:
                    messagebox.showwarning("Ocenaudio Not Found", "Ocenaudio not found. Please install it to use this feature.")
                    return

            self.ocenaudio_path = ocenaudio_path
            self.save_settings()
            command = [self.ocenaudio_path] + file_paths

        try:
            subprocess.Popen(command)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Ocenaudio: {e}")

    def play_video(self):
        if not self.current_video:
            return
        self.stop_video()
        video_path = os.path.join(self.folder_path, self.current_video)
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Cannot open video file.")
            return
        self.playing_video = True
        self.video_label.config(text="")
        def update_frame():
            if self.playing_video:
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = cv2.resize(frame, (640, 480))
                    img = Image.fromarray(frame)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.video_label.imgtk = imgtk
                    self.video_label.configure(image=imgtk)
                    self.video_label.after(30, update_frame)
                else:
                    self.stop_video()
        update_frame()

    def export_wavs(self):
        if not self.folder_path:
            messagebox.showerror("Error", "No folder selected.")
            return
        wav_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.wav') and not f.startswith('.')]
        export_dir = filedialog.askdirectory(title="Select Export Folder for WAV Files")
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
            if not messagebox.askyesno(
                "Overwrite Files?",
                "The following files already exist in the export folder and will be overwritten:\n"
                + "\n".join(overwrite_files)
                + "\n\nDo you want to overwrite them?"
            ):
                messagebox.showinfo("Export Cancelled", "Export was cancelled to avoid overwriting files.")
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
            messagebox.showerror("Export Errors", "Some files could not be exported:\n" + "\n".join(errors))
        else:
            messagebox.showinfo("Export Recorded Data", f"Exported {len(wav_files)} WAV files and metadata.txt to {export_dir}.")

    def clear_wavs(self):
        if not self.folder_path:
            messagebox.showerror("Error", "No folder selected.")
            return
        wav_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.wav') and not f.startswith('.')]
        if not wav_files:
            messagebox.showinfo("Clear Recorded Data", "No WAV files found in the current folder.")
            return
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {len(wav_files)} WAV files from this folder?"):
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
            messagebox.showerror("Delete Errors", "Some files could not be deleted or metadata.txt could not be reset:\n" + "\n".join(errors))
        else:
            messagebox.showinfo("Clear Recorded Data", f"Deleted {len(wav_files)} WAV files and reset metadata.txt.")
        self.load_video_files()
        self.open_metadata_editor()

    def stop_video(self):
        self.playing_video = False
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

        try:
            p = pyaudio.PyAudio()
            wf = wave.open(wav_path, 'rb')
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)

            def playback():
                try:
                    data = wf.readframes(1024)
                    while data and self.audio_stream == stream:
                        stream.write(data)
                        data = wf.readframes(1024)
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Audio playback failed: {e}"))
                finally:
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    wf.close()

            self.audio_stream = stream
            threading.Thread(target=playback, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play audio: {e}")

    def stop_audio(self):
        self.audio_stream = None

    def toggle_recording(self):
        if not self.current_video:
            return

        if self.is_recording:
            self.is_recording = False
            if self.recording_thread:
                self.recording_thread.join(timeout=1.0)
                self.recording_thread = None
            self.update_media_controls()
        else:
            wav_path = os.path.join(self.folder_path, os.path.splitext(self.current_video)[0] + '.wav')
            if os.path.exists(wav_path):
                if not messagebox.askyesno(self.LABELS["overwrite"], self.LABELS["overwrite_audio"]):
                    return

            try:
                p = pyaudio.PyAudio()
                stream = p.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=44100,
                                input=True,
                                frames_per_buffer=1024)

                frames = []
                self.is_recording = True
                self.record_button.config(text=self.LABELS["stop_recording"])

                def record():
                    try:
                        while self.is_recording:
                            data = stream.read(1024, exception_on_overflow=False)
                            frames.append(data)
                    except Exception as e:
                        self.root.after(0, lambda: messagebox.showerror("Error", f"Recording failed: {e}"))
                    finally:
                        stream.stop_stream()
                        stream.close()
                        p.terminate()
                        if frames and not self.is_recording:
                            wf = wave.open(wav_path, 'wb')
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(44100)
                            wf.writeframes(b''.join(frames))
                            wf.close()
                            self.root.after(0, lambda: messagebox.showinfo(self.LABELS["saved"], self.LABELS["metadata_saved"]))
                        self.root.after(0, self.update_media_controls)

                self.recording_thread = threading.Thread(target=record, daemon=True)
                self.recording_thread.start()
            except Exception as e:
                self.is_recording = False
                self.record_button.config(text=self.LABELS["record_audio"])
                messagebox.showerror("Error", f"Failed to start recording: {e}")

    def join_all_wavs(self):
        if not self.folder_path:
            messagebox.showerror("Error", "No folder selected.")
            return

        wav_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.wav') and not f.startswith('.')]
        if not wav_files:
            messagebox.showinfo("No Files", "No WAV files found in the current folder.")
            return

        ffmpeg_path = resource_path(os.path.join("ffmpeg", "bin", "ffmpeg"))
        if not os.path.exists(ffmpeg_path):
            messagebox.showerror("Error", "FFmpeg not found. Please ensure FFmpeg is installed or bundled with the executable.")
            return

        output_file = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav")],
            title="Save Combined WAV File"
        )
        if not output_file:
            return

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
                self.root.after(0, lambda: messagebox.showinfo(self.LABELS["success"], f"{self.LABELS['wavs_joined']}\n{output_file}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred while joining files:\n{e}"))

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

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoAnnotationApp(root)
    root.geometry("1400x800")
    root.mainloop()