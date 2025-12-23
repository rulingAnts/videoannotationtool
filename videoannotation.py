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
        "videos_tab_title": "Videos",
        "images_tab_title": "Still Images",
        "image_no_selection": "No image selected",
        "image_failed_to_load": "Failed to load",
        "selected_image_label": "Selected Image:",
        "show_filenames": "Show filenames",
        "zoom_label": "Zoom",
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
        "videos_tab_title": "Video",
        "images_tab_title": "Gambar Diam",
        "image_no_selection": "Tidak ada gambar yang dipilih",
        "image_failed_to_load": "Gagal memuat",
        "selected_image_label": "Gambar yang Dipilih:",
        "show_filenames": "Tampilkan nama berkas",
        "zoom_label": "Perbesaran",
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
        "videos_tab_title": "비디오",
        "images_tab_title": "정지 이미지",
        "image_no_selection": "선택된 이미지 없음",
        "image_failed_to_load": "불러오기 실패",
        "selected_image_label": "선택된 이미지:",
        "show_filenames": "파일 이름 표시",
        "zoom_label": "확대/축소",
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
        "videos_tab_title": "Video's",
        "images_tab_title": "Stilstaande Afbeeldingen",
        "image_no_selection": "Geen afbeelding geselecteerd",
        "image_failed_to_load": "Laden mislukt",
        "selected_image_label": "Geselecteerde Afbeelding:",
        "show_filenames": "Bestandsnamen tonen",
        "zoom_label": "Zoom",
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
        "videos_tab_title": "Vídeos",
        "images_tab_title": "Imagens Estáticas",
        "image_no_selection": "Nenhuma imagem selecionada",
        "image_failed_to_load": "Falha ao carregar",
        "selected_image_label": "Imagem Selecionada:",
        "show_filenames": "Mostrar nomes de arquivos",
        "zoom_label": "Zoom",
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
        "videos_tab_title": "Videos",
        "images_tab_title": "Imágenes fijas",
        "image_no_selection": "No se seleccionó ninguna imagen",
        "image_failed_to_load": "Error al cargar",
        "selected_image_label": "Imagen seleccionada:",
        "show_filenames": "Mostrar nombres de archivo",
        "zoom_label": "Zoom",
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
        "videos_tab_title": "Video's",
        "images_tab_title": "Stilstaande Beelde",
        "image_no_selection": "Geen beeld gekies nie",
        "image_failed_to_load": "Kon nie laai nie",
        "selected_image_label": "Gekose Beeld:",
        "show_filenames": "Wys lêernaam",
        "zoom_label": "Zoem",
    },
}


# Simple tooltip helper for Tkinter widgets
class ToolTip:
    def __init__(
        self,
        widget,
        text: str = "",
        delay: int = 500,
        wrap_at_sep: bool = False,
        max_width_ratio: float = 0.5,
        max_width_pixels: int | None = None,
    ):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.wrap_at_sep = wrap_at_sep
        self.max_width_ratio = max_width_ratio
        self.max_width_pixels = max_width_pixels
        self._after_id = None
        self.tipwindow = None
        # Bind events
        self.widget.bind("<Enter>", self._on_enter)
        self.widget.bind("<Leave>", self._on_leave)
        self.widget.bind("<Motion>", self._on_motion)

    def set_text(self, text: str):
        self.text = text or ""

    def _on_enter(self, event=None):
        if not self.text:
            return
        self._schedule(event)

    def _on_leave(self, event=None):
        self._unschedule()
        self._hide()

    def _on_motion(self, event):
        # Reposition tooltip near cursor if it's shown and keep it on-screen
        if self.tipwindow:
            x = event.x_root + 12
            y = event.y_root + 8
            self._place_tooltip(x, y)

    def _schedule(self, event=None):
        self._unschedule()
        self._after_id = self.widget.after(self.delay, lambda e=event: self._show(e))

    def _unschedule(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
                # Update banner filename and rebuild grid to show/hide labels
                if self.current_image:
                    self.image_filename_var.set(self.current_image if self.show_filenames_var.get() else "")
                self.build_image_grid()
            self._after_id = None

    def _show(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = (event.x_root + 12) if event else (self.widget.winfo_rootx() + 12)
        y = (event.y_root + 8) if event else (self.widget.winfo_rooty() + self.widget.winfo_height() + 8)
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        # Determine wrap length based on screen size
        screen_w = self.widget.winfo_screenwidth()
        wrap_len = int(min(self.max_width_pixels or screen_w * self.max_width_ratio, screen_w - 16))
        # Optionally insert line breaks at path separators for readability
        text_to_show = self._format_text(self.text)
        label = tk.Label(
            tw,
            text=text_to_show,
            justify=tk.LEFT,
            relief=tk.SOLID,
            borderwidth=1,
            background="#ffffe0",
            wraplength=wrap_len,
        )
        label.pack(ipadx=4, ipady=2)
        # After layout, adjust to keep on-screen
        tw.update_idletasks()
        self._place_tooltip(x, y)

    def _hide(self):
        if self.tipwindow:
            try:
                self.tipwindow.destroy()
            except Exception:
                pass
            self.tipwindow = None

    def _place_tooltip(self, x: int, y: int):
        if not self.tipwindow:
            return
        screen_w = self.widget.winfo_screenwidth()
        screen_h = self.widget.winfo_screenheight()
        self.tipwindow.update_idletasks()
        w = self.tipwindow.winfo_reqwidth()
        h = self.tipwindow.winfo_reqheight()
        # Clamp within screen bounds with margin
        margin = 8
        x = max(margin, min(x, screen_w - w - margin))
        y = max(margin, min(y, screen_h - h - margin))
        self.tipwindow.wm_geometry(f"+{x}+{y}")

    def _format_text(self, text: str) -> str:
        if not text:
            return ""
        if self.wrap_at_sep:
            # Insert line breaks after path separators for readability.
            # Handle both os.sep and os.altsep (e.g., "/" and "\\" on Windows).
            seps = {os.sep}
            if os.altsep:
                seps.add(os.altsep)
            formatted = text
            for s in seps:
                formatted = formatted.replace(s, s + "\n")
            return formatted
        return text

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

class VideoAnnotationApp:
    def __init__(self, root):
        self.root = root
        self.language = "English"
        self.LABELS = LABELS_ALL[self.language]
        # Upscale caps (can be tuned). Prevents over-blurry fullscreen.
        self.max_image_upscale = 3.0
        self.max_video_upscale = 2.5

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

        # Current folder display (shown under title/language bar)
        self.folder_display_var = tk.StringVar(value=self.LABELS["no_folder_selected"])
        self.folder_display_label = tk.Label(
            root,
            textvariable=self.folder_display_var,
            anchor='w'
        )
        self.folder_display_label.pack(fill=tk.X, padx=10)
        self.folder_display_tooltip = ToolTip(
            self.folder_display_label,
            text="",
            wrap_at_sep=True,
            max_width_ratio=0.5,
        )

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

        # Right frame: Notebook with Videos and Still Images tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        # Videos tab (reuse existing video UI under this frame)
        self.videos_tab = tk.Frame(self.notebook)
        self.notebook.add(self.videos_tab, text=LABELS_ALL.get(self.language, {}).get("videos_tab_title", "Videos"))

        # Images tab (new image UI)
        self.images_tab = tk.Frame(self.notebook)
        self.notebook.add(self.images_tab, text=LABELS_ALL.get(self.language, {}).get("images_tab_title", "Still Images"))

        # For backwards compatibility, keep using media_frame for video widgets
        self.media_frame = tk.Frame(self.videos_tab)
        self.media_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        # Track images state
        self.image_files = []
        self.current_image = None
        self.image_thumbs = {}
        # Image banner (thumbnail + filename + audio controls)
        self.image_banner_frame = tk.Frame(self.images_tab)
        self.image_banner_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        self.image_thumb_label = tk.Label(self.image_banner_frame)
        self.image_thumb_label.pack(side=tk.LEFT, padx=6)
        # Selected image label
        self.image_selected_label = tk.Label(
            self.image_banner_frame,
            text=self.LABELS.get("selected_image_label", "Selected Image:"),
            anchor='w'
        )
        self.image_selected_label.pack(side=tk.LEFT, padx=8)
        self.image_filename_var = tk.StringVar(value=LABELS_ALL.get(self.language, {}).get("image_no_selection", "No image selected"))
        self.image_filename_label = tk.Label(self.image_banner_frame, textvariable=self.image_filename_var, anchor='w')
        self.image_filename_label.pack(side=tk.LEFT, padx=10)
        # Audio controls for selected image
        self.image_controls = tk.Frame(self.image_banner_frame)
        self.image_controls.pack(side=tk.RIGHT)
        # Checkbox to show/hide filenames in grid and banner
        self.show_filenames_var = tk.BooleanVar(value=True)
        self.show_filenames_checkbox = tk.Checkbutton(
            self.image_banner_frame,
            text=self.LABELS.get("show_filenames", "Show filenames"),
            variable=self.show_filenames_var,
            command=self.on_toggle_show_filenames
        )
        self.show_filenames_checkbox.pack(side=tk.RIGHT, padx=8)
        # Apply saved preference if available (loaded in load_settings earlier)
        self.show_filenames_var.set(getattr(self, 'show_filenames_pref', True))
        self.image_play_button = tk.Button(self.image_controls, text=self.LABELS["play_audio"], command=self.play_selected_image_audio, state=tk.DISABLED)
        self.image_play_button.pack(side=tk.LEFT, padx=5)
        self.image_stop_button = tk.Button(self.image_controls, text=self.LABELS["stop_audio"], command=self.stop_audio, state=tk.DISABLED)
        self.image_stop_button.pack(side=tk.LEFT, padx=5)
        self.image_record_button = tk.Button(self.image_controls, text=self.LABELS["record_audio"], command=self.toggle_image_recording, state=tk.DISABLED)
        self.image_record_button.pack(side=tk.LEFT, padx=5)

        # Scrollable image grid
        self.image_canvas = tk.Canvas(self.images_tab, highlightthickness=0)
        self.image_scrollbar = tk.Scrollbar(self.images_tab, orient=tk.VERTICAL, command=self.image_canvas.yview)
        self.image_grid_container = tk.Frame(self.image_canvas)
        self.image_canvas.create_window((0, 0), window=self.image_grid_container, anchor="nw")
        self.image_canvas.configure(yscrollcommand=self.image_scrollbar.set)
        self.image_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.image_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Reflow grid on size changes
        self.image_grid_container.bind("<Configure>", lambda e: self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all")))
        self.images_tab.bind("<Configure>", lambda e: self.build_image_grid())

        # Persist last active tab and update contents on switch
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        # Select last tab if available
        try:
            if getattr(self, 'last_tab', 'videos') == 'images':
                self.notebook.select(self.images_tab)
            else:
                self.notebook.select(self.videos_tab)
        except Exception:
            pass

        # Video player section
        self.video_label = tk.Label(self.media_frame, text=self.LABELS["video_listbox_no_video"])
        self.video_label.pack()
        # Fullscreen on double-click
        self.video_label.bind("<Double-Button-1>", self.on_video_double_click)

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

    def get_active_tab(self) -> str:
        try:
            current = self.notebook.select()
            if current == str(self.images_tab):
                return "images"
        except Exception:
            pass
        return "videos"

    def on_tab_changed(self, event=None):
        # Stop any playback when switching tabs
        self.stop_video()
        self.stop_audio()
        # Save last tab selection to settings
        try:
            self.last_tab = self.get_active_tab()
            self.save_settings()
        except Exception:
            pass
        # Populate media for the active tab
        if self.get_active_tab() == "images":
            self.load_image_files()
            # Hide video list when on images tab
            try:
                self.video_listbox_frame.pack_forget()
            except Exception:
                pass
        else:
            self.load_video_files()
            # Show video list when on videos tab
            try:
                self.video_listbox_frame.pack(fill=tk.BOTH, expand=True)
            except Exception:
                pass

    def get_audio_path_for_media(self, name: str, ext: str | None, media_type: str) -> str:
        base = os.path.join(self.folder_path or "", name)
        if media_type == "image" and ext:
            return base + f".{ext}.wav"
        # videos use plain basename.wav
        return base + ".wav"

    def load_image_files(self):
        # Populate image list based on supported extensions
        self.image_files = []
        if not self.folder_path:
            self.update_folder_display()
            return
        try:
            exts = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif')
            files = [f for f in os.listdir(self.folder_path) if f.lower().endswith(exts) and not f.startswith('.')]
            self.image_files = sorted(files)
            # Build grid view
            self.build_image_grid()
            # Reset banner
            self.current_image = None
            self.image_filename_var.set(LABELS_ALL.get(self.language, {}).get("image_no_selection", "No image selected"))
            self.image_play_button.config(state=tk.DISABLED)
            self.image_stop_button.config(state=tk.DISABLED)
            self.image_record_button.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load images: {e}")

    def build_image_grid(self):
        # Clear existing tiles
        for child in list(self.image_grid_container.children.values()):
            child.destroy()
        if not self.image_files:
            return
        # Determine container width
        container_w = max(self.image_canvas.winfo_width(), 600)
        # Thumbnail target height
        target_h = 240
        row = []
        # Determine orientation for each image (portrait if h > w)
        metas = []
        for fname in self.image_files:
            path = os.path.join(self.folder_path, fname)
            try:
                with Image.open(path) as im:
                    w, h = im.size
                metas.append({"name": fname, "path": path, "portrait": (h >= w)})
            except Exception:
                metas.append({"name": fname, "path": path, "portrait": False, "error": True})
        # Build rows according to rule: 3-wide for all-portrait rows; otherwise 2-wide; if two portraits then landscape next -> stop at 2
        r = 0
        c = 0
        i = 0
        while i < len(metas):
            # Decide row capacity
            cap = 3 if all(m.get("portrait", False) for m in metas[i:i+3]) else 2
            # Special case: first two portraits and third landscape -> cap=2
            if len(metas) - i >= 3:
                if metas[i].get("portrait", False) and metas[i+1].get("portrait", False) and not metas[i+2].get("portrait", False):
                    cap = 2
            # Place up to cap items
            for j in range(cap):
                if i + j >= len(metas):
                    break
                meta = metas[i + j]
                tile_w = int(container_w / cap) - 18
                tile = tk.Frame(self.image_grid_container, bd=3, relief=tk.SOLID)
                tile.grid(row=r, column=j, padx=6, pady=6, sticky="nsew")
                # Thumbnail
                thumb_lbl = tk.Label(tile)
                thumb_lbl.pack(fill=tk.BOTH, expand=True)
                # Filename label (conditional)
                if self.show_filenames_var.get():
                    tk.Label(tile, text=meta["name"], anchor='w').pack(fill=tk.X)
                # Load thumbnail lazily into cache bucket
                try:
                    with Image.open(meta["path"]) as im:
                        im.thumbnail((tile_w, target_h))
                        photo = ImageTk.PhotoImage(im)
                    # Keep reference
                    self.image_thumbs[(meta["path"], tile_w, target_h)] = photo
                    thumb_lbl.configure(image=photo)
                    thumb_lbl.image = photo
                except Exception:
                    thumb_lbl.configure(text=LABELS_ALL.get(self.language, {}).get("image_failed_to_load", "Failed to load"))
                # Bind selection and double-click
                def make_handlers(m=meta, frame_ref=tile):
                    def on_click(_e=None):
                        self.select_image(m, frame_ref)
                    def on_dbl(_e=None):
                        self.on_image_double_click(m)
                    return on_click, on_dbl
                click_h, dbl_h = make_handlers()
                tile.bind("<Button-1>", click_h)
                thumb_lbl.bind("<Button-1>", click_h)
                tile.bind("<Double-Button-1>", dbl_h)
                thumb_lbl.bind("<Double-Button-1>", dbl_h)
            # Next row
            i += cap
            r += 1

    def on_toggle_show_filenames(self):
        # Update banner filename and rebuild grid to show/hide labels
        if self.current_image:
            self.image_filename_var.set(self.current_image if self.show_filenames_var.get() else "")
        self.build_image_grid()

    def select_image(self, meta: dict, frame_ref: tk.Frame | None = None):
        self.current_image = meta["name"]
        # Update banner
        self.image_filename_var.set(meta["name"] if self.show_filenames_var.get() else "")
        # Update thumbnail preview in banner
        try:
            with Image.open(meta["path"]) as im:
                im.thumbnail((96, 96))
                photo = ImageTk.PhotoImage(im)
            self.image_thumb_label.configure(image=photo)
            self.image_thumb_label.image = photo
        except Exception:
            self.image_thumb_label.configure(image="", text=LABELS_ALL.get(self.language, {}).get("image_failed_to_load", "Failed to load"))
        # Enable audio buttons
        self.image_play_button.config(state=tk.NORMAL)
        self.image_stop_button.config(state=tk.NORMAL)
        self.image_record_button.config(state=tk.NORMAL)
        # Highlight selection
        if frame_ref is not None:
            for child in self.image_grid_container.children.values():
                child.configure(bd=3)
            frame_ref.configure(bd=6)

    def on_image_double_click(self, meta: dict):
        # Open fullscreen preview that closes on click or Esc, with zoom control and +/- keys
        win = tk.Toplevel(self.root)
        win.attributes("-fullscreen", True)
        canvas = tk.Canvas(win, background="black", highlightthickness=0)
        control_bar = tk.Frame(win, background="#111")
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        control_bar.pack(side=tk.BOTTOM, fill=tk.X)
        # Zoom slider bound to global fullscreen_scale
        scale_var = tk.DoubleVar(value=getattr(self, 'fullscreen_scale', 1.0))
        zoom_label = tk.Label(control_bar, text=self.LABELS.get("zoom_label", "Zoom"), foreground="#eee", background="#111")
        zoom_label.pack(side=tk.LEFT, padx=8, pady=6)
        zoom_slider = tk.Scale(control_bar, from_=0.5, to=getattr(self, 'max_image_upscale', 3.0), orient=tk.HORIZONTAL, resolution=0.1, variable=scale_var)
        zoom_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=6)
        try:
            with Image.open(meta["path"]) as im_orig:
                # store a copy for re-rendering
                im_base = im_orig.copy()
        except Exception:
            im_base = None
        def render_image():
            canvas.delete("all")
            if im_base is None:
                canvas.create_text(20, 20, anchor='nw', fill="white", text=LABELS_ALL.get(self.language, {}).get("image_failed_to_load", "Failed to load"))
                return
            screen_w = win.winfo_screenwidth()
            screen_h = win.winfo_screenheight()
            w, h = im_base.size
            fill_scale = max(screen_w / max(w, 1), screen_h / max(h, 1))
            user_scale = float(scale_var.get())
            # Apply cap
            scale = min(fill_scale * user_scale, getattr(self, 'max_image_upscale', 3.0))
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            im2 = im_base.resize((new_w, new_h), Image.LANCZOS)
            if new_w >= screen_w and new_h >= screen_h:
                left = (new_w - screen_w) // 2
                top = (new_h - screen_h) // 2
                im_fit = im2.crop((left, top, left + screen_w, top + screen_h))
            else:
                bg = Image.new('RGB', (screen_w, screen_h), color=(0, 0, 0))
                off_x = (screen_w - new_w) // 2
                off_y = (screen_h - new_h) // 2
                bg.paste(im2, (off_x, off_y))
                im_fit = bg
            photo = ImageTk.PhotoImage(im_fit)
            canvas.create_image(0, 0, image=photo, anchor='nw')
            canvas.image = photo
        def close(_e=None):
            win.destroy()
        win.bind("<Button-1>", close)
        win.bind("<Escape>", close)
        def on_scale_change(_v=None):
            try:
                self.fullscreen_scale = float(scale_var.get())
                self.save_settings()
            except Exception:
                pass
            render_image()
        zoom_slider.configure(command=on_scale_change)
        # Keyboard +/- to adjust zoom
        def adjust_zoom(delta):
            val = float(scale_var.get()) + delta
            cap = getattr(self, 'max_image_upscale', 3.0)
            val = max(0.5, min(cap, val))
            scale_var.set(val)
            on_scale_change()
        for ks in ("plus", "equal", "KP_Add"):
            win.bind(f"<KeyPress-{ks}>", lambda e, d=0.1: adjust_zoom(d))
        for ks in ("minus", "underscore", "KP_Subtract"):
            win.bind(f"<KeyPress-{ks}>", lambda e, d=-0.1: adjust_zoom(d))
        render_image()

    def on_video_double_click(self, event=None):
        if not self.current_video or not self.folder_path:
            return
        # Stop inline playback to avoid conflicts
        self.stop_video()
        video_path = os.path.join(self.folder_path, self.current_video)
        win = tk.Toplevel(self.root)
        win.attributes("-fullscreen", True)
        canvas = tk.Canvas(win, background="black", highlightthickness=0)
        control_bar = tk.Frame(win, background="#111")
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        control_bar.pack(side=tk.BOTTOM, fill=tk.X)
        # Zoom slider
        scale_var = tk.DoubleVar(value=getattr(self, 'fullscreen_scale', 1.0))
        zoom_label = tk.Label(control_bar, text=self.LABELS.get("zoom_label", "Zoom"), foreground="#eee", background="#111")
        zoom_label.pack(side=tk.LEFT, padx=8, pady=6)
        zoom_slider = tk.Scale(control_bar, from_=0.5, to=getattr(self, 'max_video_upscale', 2.5), orient=tk.HORIZONTAL, resolution=0.1, variable=scale_var)
        zoom_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=6)
        running = {"val": True}
        cap = cv2.VideoCapture(video_path)
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        def close(_e=None):
            running["val"] = False
            try:
                cap.release()
            except Exception:
                pass
            win.destroy()
        win.bind("<Button-1>", close)
        win.bind("<Escape>", close)
        def on_scale_change(_v=None):
            try:
                self.fullscreen_scale = float(scale_var.get())
                self.save_settings()
            except Exception:
                pass
        zoom_slider.configure(command=on_scale_change)
        def adjust_zoom(delta):
            val = float(scale_var.get()) + delta
            cap = getattr(self, 'max_video_upscale', 2.5)
            val = max(0.5, min(cap, val))
            scale_var.set(val)
            on_scale_change()
        for ks in ("plus", "equal", "KP_Add"):
            win.bind(f"<KeyPress-{ks}>", lambda e, d=0.1: adjust_zoom(d))
        for ks in ("minus", "underscore", "KP_Subtract"):
            win.bind(f"<KeyPress-{ks}>", lambda e, d=-0.1: adjust_zoom(d))
        def loop():
            if not running["val"]:
                return
            ret, frame = cap.read()
            if not ret:
                # Loop video or close
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                if not ret:
                    close()
                    return
            h, w = frame.shape[:2]
            fill_scale = max(screen_w / max(w, 1), screen_h / max(h, 1))
            user_scale = float(scale_var.get())
            scale = min(fill_scale * user_scale, getattr(self, 'max_video_upscale', 2.5))
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            frame_resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            # Convert to RGB for Tk
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            # Crop or letterbox
            if new_w >= screen_w and new_h >= screen_h:
                left = (new_w - screen_w) // 2
                top = (new_h - screen_h) // 2
                img_fit = img.crop((left, top, left + screen_w, top + screen_h))
            else:
                bg = Image.new('RGB', (screen_w, screen_h), color=(0, 0, 0))
                off_x = (screen_w - new_w) // 2
                off_y = (screen_h - new_h) // 2
                bg.paste(img, (off_x, off_y))
                img_fit = bg
            photo = ImageTk.PhotoImage(img_fit)
            canvas.create_image(0, 0, image=photo, anchor='nw')
            canvas.image = photo
            # Schedule next frame respecting ~30fps
            win.after(33, loop)
        loop()

    def play_selected_image_audio(self):
        if not self.folder_path or not self.current_image:
            return
        name, ext = os.path.splitext(self.current_image)
        ext = ext.lstrip('.')
        wav_path = self.get_audio_path_for_media(name, ext, media_type="image")
        if not os.path.exists(wav_path):
            messagebox.showwarning(self.LABELS["no_files"], self.LABELS.get("audio_no_annotation", "No audio annotation"))
            return
        # Reuse audio playback but targeted to image audio
        try:
            segment = AudioSegment.from_wav(wav_path)
            # Simple synchronous playback via pydub/playback would block; keep existing stream approach if available
            from pydub.playback import play
            threading.Thread(target=lambda: play(segment), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play audio: {e}")

    def toggle_image_recording(self):
        if not self.folder_path or not self.current_image:
            return
        name, ext = os.path.splitext(self.current_image)
        ext = ext.lstrip('.')
        wav_path = self.get_audio_path_for_media(name, ext, media_type="image")
        # Confirm overwrite
        if os.path.exists(wav_path):
            if not messagebox.askyesno(self.LABELS.get("overwrite", "Overwrite?"), self.LABELS.get("overwrite_audio", "Audio file already exists. Overwrite?")):
                return
        # Delegate to existing recording thread logic if available; else minimal stub
        try:
            import pyaudio, wave
            pa = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
            frames = []
            self.is_recording = True
            self.image_record_button.config(text=self.LABELS["stop_recording"]) 
            def worker():
                try:
                    while self.is_recording:
                        data = stream.read(1024)
                        frames.append(data)
                finally:
                    stream.stop_stream()
                    stream.close()
                    pa.terminate()
                    wf = wave.open(wav_path, 'wb')
                    wf.setnchannels(1)
                    wf.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(44100)
                    wf.writeframes(b''.join(frames))
                    wf.close()
                    # Restore button label and command after finishing
                    self.root.after(0, lambda: self.image_record_button.config(text=self.LABELS["record_audio"], command=self.toggle_image_recording))
            threading.Thread(target=worker, daemon=True).start()
            # Toggle stop on second press
            def stop_record(_e=None):
                self.is_recording = False
            self.image_record_button.configure(command=stop_record)
        except Exception as e:
            messagebox.showerror("Error", f"Recording failed: {e}")

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
        # Update current folder display text in case no folder is selected (localized)
        if not self.folder_path:
            self.update_folder_display()
        # Update tab titles and image banner controls
        if hasattr(self, "notebook"):
            try:
                self.notebook.tab(self.videos_tab, text=self.LABELS.get("videos_tab_title", "Videos"))
                self.notebook.tab(self.images_tab, text=self.LABELS.get("images_tab_title", "Still Images"))
            except Exception:
                pass
        if hasattr(self, "image_play_button"):
            self.image_play_button.config(text=self.LABELS["play_audio"])
        if hasattr(self, "image_stop_button"):
            self.image_stop_button.config(text=self.LABELS["stop_audio"])
        if hasattr(self, "image_record_button"):
            self.image_record_button.config(text=self.LABELS["record_audio"] if not self.is_recording else self.LABELS["stop_recording"])
        if hasattr(self, "image_filename_var") and not self.current_image:
            self.image_filename_var.set(LABELS_ALL.get(self.language, {}).get("image_no_selection", "No image selected"))
        if hasattr(self, "image_selected_label"):
            self.image_selected_label.config(text=self.LABELS.get("selected_image_label", "Selected Image:"))
        if hasattr(self, "show_filenames_checkbox"):
            self.show_filenames_checkbox.config(text=self.LABELS.get("show_filenames", "Show filenames"))

    def update_folder_display(self):
        if self.folder_path:
            # show only the folder name in the label, full path in tooltip
            folder_name = os.path.basename(os.path.normpath(self.folder_path)) or self.folder_path
            self.folder_display_var.set(folder_name)
            self.folder_display_tooltip.set_text(self.folder_path)
        else:
            self.folder_display_var.set(self.LABELS["no_folder_selected"])
            self.folder_display_tooltip.set_text("")

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.ocenaudio_path = settings.get('ocenaudio_path')
                    self.last_tab = settings.get('last_tab', 'videos')
                    self.show_filenames_pref = settings.get('show_filenames', True)
                    self.fullscreen_scale = float(settings.get('fullscreen_scale', 1.0))
            else:
                self.last_tab = 'videos'
                self.show_filenames_pref = True
                self.fullscreen_scale = 1.0
        except Exception as e:
            messagebox.showwarning("Settings Error", f"Failed to load settings: {e}")

    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            # Merge with existing settings
            settings = {}
            if os.path.exists(self.settings_file):
                try:
                    with open(self.settings_file, 'r') as f:
                        settings = json.load(f)
                except Exception:
                    settings = {}
            settings['ocenaudio_path'] = self.ocenaudio_path
            settings['last_tab'] = getattr(self, 'last_tab', 'videos')
            try:
                settings['show_filenames'] = bool(self.show_filenames_var.get())
            except Exception:
                # If not yet created
                settings['show_filenames'] = settings.get('show_filenames', True)
            settings['fullscreen_scale'] = float(getattr(self, 'fullscreen_scale', 1.0))
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            messagebox.showwarning("Settings Error", f"Failed to save settings: {e}")

    def select_folder(self):
        self.folder_path = filedialog.askdirectory(title="Select Folder with Video Files")
        if self.folder_path:
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
                    messagebox.showwarning("Cleanup Errors", "Some hidden files could not be deleted:\n" + "\n".join(errors))
            # Load media based on active tab
            if self.get_active_tab() == 'images':
                self.load_image_files()
            else:
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
            messagebox.showinfo(self.LABELS["no_folder_selected"], self.LABELS["no_folder_selected"])
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
                messagebox.showinfo(self.LABELS["no_videos_found"], f"{self.LABELS['no_videos_found']} {self.folder_path}")

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

        # Build list based on active tab and visible media order
        wav_files = []
        try:
            active = self.get_active_tab()
        except Exception:
            active = "videos"
        if active == "images" and getattr(self, "image_files", None):
            for img in self.image_files:
                base, ext = os.path.splitext(img)
                ext = ext.lstrip('.')
                candidate = f"{base}.{ext}.wav"
                if os.path.exists(os.path.join(self.folder_path, candidate)):
                    wav_files.append(candidate)
        else:
            for vid in getattr(self, "video_files", []):
                base, _ = os.path.splitext(vid)
                candidate = f"{base}.wav"
                if os.path.exists(os.path.join(self.folder_path, candidate)):
                    wav_files.append(candidate)
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

        # Build list based on active tab and visible media order
        wav_files = []
        try:
            active = self.get_active_tab()
        except Exception:
            active = "videos"
        if active == "images" and getattr(self, "image_files", None):
            for img in self.image_files:
                base, ext = os.path.splitext(img)
                ext = ext.lstrip('.')
                candidate = f"{base}.{ext}.wav"
                if os.path.exists(os.path.join(self.folder_path, candidate)):
                    wav_files.append(candidate)
        else:
            for vid in getattr(self, "video_files", []):
                base, _ = os.path.splitext(vid)
                candidate = f"{base}.wav"
                if os.path.exists(os.path.join(self.folder_path, candidate)):
                    wav_files.append(candidate)
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