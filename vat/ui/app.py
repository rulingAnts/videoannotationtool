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
    QFileDialog, QComboBox, QTabWidget, QSplitter, QToolButton, QStyle, QDialog, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QEvent
from PySide6.QtGui import QImage, QPixmap, QIcon, QShortcut, QKeySequence

from vat.audio import PYAUDIO_AVAILABLE
from vat.audio.playback import AudioPlaybackWorker
from vat.audio.recording import AudioRecordingWorker
from vat.audio.joiner import JoinWavsWorker
from vat.utils.resources import resource_path
from vat.ui.fullscreen import FullscreenVideoViewer
from vat.utils.fs_access import (
    FolderAccessManager,
    FolderAccessError,
    FolderPermissionError,
    FolderNotFoundError,
)

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
        "select_folder_dialog": "Select Folder with Video Files",
        "cleanup_errors_title": "Cleanup Errors",
        "permission_denied_title": "Permission Denied",
        "folder_not_found_title": "Folder Not Found",
        "unexpected_error_title": "An Error Occurred",
        "error_title": "Error",
        "cannot_open_video": "Cannot open video file.",
        "ocenaudio_locate_title": "Locate Ocenaudio Executable",
        "ocenaudio_not_found_title": "Ocenaudio Not Found",
        "ocenaudio_open_fail_prefix": "Failed to open Ocenaudio: ",
        "export_select_folder_dialog": "Select Export Folder for WAV Files",
        "overwrite_files_title": "Overwrite Files?",
        "overwrite_export_body_prefix": "The following files already exist in the export folder and will be overwritten:\n",
        "overwrite_import_body_prefix": "The following files already exist and will be overwritten by import:\n",
        "overwrite_question_suffix": "\n\nDo you want to overwrite them?",
        "export_cancelled_title": "Export Cancelled",
        "export_cancelled_msg": "Export was cancelled to avoid overwriting files.",
        "delete_errors_title": "Delete Errors",
        "delete_errors_msg_prefix": "Some files could not be deleted or metadata.txt could not be reset:\n",
        "clear_success_msg_prefix": "Deleted {count} WAV files and reset metadata.txt.",
        "import_select_folder_dialog": "Select Folder to Import Files From",
        "confirm_delete_title": "Confirm Delete",
        "confirm_import_title": "Confirm Import",
        "import_errors_title": "Import Errors",
        "import_errors_msg_prefix": "Some files could not be imported or deleted:\n",
        "import_success_msg_prefix": "Imported {count} WAV files and metadata.txt.",
        "wav_mismatch_title": "WAV Filename Mismatch",
        "wav_mismatch_msg_prefix": "The following WAV files do not match any video filenames and were not imported:\n",
        "ffmpeg_not_found_msg": "FFmpeg not found. Please ensure FFmpeg is installed or bundled with the executable.",
        "save_combined_wav_dialog_title": "Save Combined WAV File",
        "recording_indicator": "● Recording",
        "recording_started": "Recording started",
        "recording_stopped": "Recording stopped",
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
        "select_folder_dialog": "Pilih Folder dengan Berkas Video",
        "cleanup_errors_title": "Kesalahan Pembersihan",
        "permission_denied_title": "Izin Ditolak",
        "folder_not_found_title": "Folder Tidak Ditemukan",
        "unexpected_error_title": "Terjadi Kesalahan",
        "error_title": "Kesalahan",
        "cannot_open_video": "Tidak dapat membuka berkas video.",
        "ocenaudio_locate_title": "Temukan Eksekutabel Ocenaudio",
        "ocenaudio_not_found_title": "Ocenaudio Tidak Ditemukan",
        "ocenaudio_open_fail_prefix": "Gagal membuka Ocenaudio: ",
        "export_select_folder_dialog": "Pilih Folder Ekspor untuk Berkas WAV",
        "overwrite_files_title": "Timpa Berkas?",
        "overwrite_export_body_prefix": "Berkas berikut sudah ada di folder ekspor dan akan ditimpa:\n",
        "overwrite_import_body_prefix": "Berkas berikut sudah ada dan akan ditimpa oleh impor:\n",
        "overwrite_question_suffix": "\n\nApakah Anda ingin menimpanya?",
        "export_cancelled_title": "Ekspor Dibatalkan",
        "export_cancelled_msg": "Ekspor dibatalkan untuk menghindari penimpaan berkas.",
        "delete_errors_title": "Kesalahan Penghapusan",
        "delete_errors_msg_prefix": "Beberapa berkas tidak dapat dihapus atau metadata.txt tidak dapat diatur ulang:\n",
        "clear_success_msg_prefix": "Menghapus {count} berkas WAV dan mengatur ulang metadata.txt.",
        "import_select_folder_dialog": "Pilih Folder untuk Mengimpor Berkas",
        "confirm_delete_title": "Konfirmasi Hapus",
        "confirm_import_title": "Konfirmasi Impor",
        "import_errors_title": "Kesalahan Impor",
        "import_errors_msg_prefix": "Beberapa berkas tidak dapat diimpor atau dihapus:\n",
        "import_success_msg_prefix": "Mengimpor {count} berkas WAV dan metadata.txt.",
        "wav_mismatch_title": "Nama Berkas WAV Tidak Cocok",
        "wav_mismatch_msg_prefix": "Berkas WAV berikut tidak cocok dengan nama berkas video manapun dan tidak diimpor:\n",
        "ffmpeg_not_found_msg": "FFmpeg tidak ditemukan. Pastikan FFmpeg terpasang atau dibundel dengan eksekutabel.",
        "save_combined_wav_dialog_title": "Simpan Berkas WAV Gabungan",
        "recording_indicator": "● Merekam",
        "recording_started": "Perekaman dimulai",
        "recording_stopped": "Perekaman dihentikan",
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
        "select_folder_dialog": "비디오 파일이 있는 폴더 선택",
        "cleanup_errors_title": "정리 오류",
        "permission_denied_title": "권한 거부",
        "folder_not_found_title": "폴더를 찾을 수 없음",
        "unexpected_error_title": "오류가 발생했습니다",
        "error_title": "오류",
        "cannot_open_video": "비디오 파일을 열 수 없습니다.",
        "ocenaudio_locate_title": "Ocenaudio 실행 파일 찾기",
        "ocenaudio_not_found_title": "Ocenaudio를 찾을 수 없음",
        "ocenaudio_open_fail_prefix": "Ocenaudio를 열지 못했습니다: ",
        "export_select_folder_dialog": "WAV 파일 내보낼 폴더 선택",
        "overwrite_files_title": "파일 덮어쓰기?",
        "overwrite_export_body_prefix": "다음 파일은 내보내기 폴더에 이미 존재하며 덮어쓰게 됩니다:\n",
        "overwrite_import_body_prefix": "다음 파일은 이미 존재하며 가져오기에 의해 덮어쓰게 됩니다:\n",
        "overwrite_question_suffix": "\n\n덮어쓰시겠습니까?",
        "export_cancelled_title": "내보내기 취소됨",
        "export_cancelled_msg": "파일 덮어쓰기를 피하기 위해 내보내기가 취소되었습니다.",
        "delete_errors_title": "삭제 오류",
        "delete_errors_msg_prefix": "일부 파일을 삭제할 수 없거나 metadata.txt를 재설정할 수 없습니다:\n",
        "clear_success_msg_prefix": "{count}개의 WAV 파일을 삭제하고 metadata.txt를 재설정했습니다.",
        "import_select_folder_dialog": "가져올 폴더 선택",
        "confirm_delete_title": "삭제 확인",
        "confirm_import_title": "가져오기 확인",
        "import_errors_title": "가져오기 오류",
        "import_errors_msg_prefix": "일부 파일을 가져오거나 삭제할 수 없습니다:\n",
        "import_success_msg_prefix": "{count}개의 WAV 파일과 metadata.txt를 가져왔습니다.",
        "wav_mismatch_title": "WAV 파일명 불일치",
        "wav_mismatch_msg_prefix": "다음 WAV 파일은 어떤 비디오 파일명과도 일치하지 않아 가져오지 않았습니다:\n",
        "ffmpeg_not_found_msg": "FFmpeg를 찾을 수 없습니다. FFmpeg가 설치되어 있거나 실행 파일과 함께 제공되는지 확인하세요.",
        "save_combined_wav_dialog_title": "결합된 WAV 파일 저장",
        "recording_indicator": "● 녹음 중",
        "recording_started": "녹음이 시작되었습니다",
        "recording_stopped": "녹음이 종료되었습니다",
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
        "select_folder_dialog": "Selecteer map met videobestanden",
        "cleanup_errors_title": "Opschoningsfouten",
        "permission_denied_title": "Toegang geweigerd",
        "folder_not_found_title": "Map niet gevonden",
        "unexpected_error_title": "Er is een fout opgetreden",
        "error_title": "Fout",
        "cannot_open_video": "Kan videobestand niet openen.",
        "ocenaudio_locate_title": "Ocenaudio-programma zoeken",
        "ocenaudio_not_found_title": "Ocenaudio niet gevonden",
        "ocenaudio_open_fail_prefix": "Ocenaudio openen mislukt: ",
        "export_select_folder_dialog": "Selecteer exportmap voor WAV-bestanden",
        "overwrite_files_title": "Bestanden overschrijven?",
        "overwrite_export_body_prefix": "De volgende bestanden bestaan al in de exportmap en zullen worden overschreven:\n",
        "overwrite_import_body_prefix": "De volgende bestanden bestaan al en zullen door import worden overschreven:\n",
        "overwrite_question_suffix": "\n\nWilt u ze overschrijven?",
        "export_cancelled_title": "Export geannuleerd",
        "export_cancelled_msg": "Export is geannuleerd om overschrijven te voorkomen.",
        "delete_errors_title": "Verwijderfouten",
        "delete_errors_msg_prefix": "Sommige bestanden konden niet worden verwijderd of metadata.txt kon niet worden teruggezet:\n",
        "clear_success_msg_prefix": "{count} WAV-bestanden verwijderd en metadata.txt teruggezet.",
        "import_select_folder_dialog": "Selecteer map om bestanden uit te importeren",
        "confirm_delete_title": "Verwijderen bevestigen",
        "confirm_import_title": "Import bevestigen",
        "import_errors_title": "Importfouten",
        "import_errors_msg_prefix": "Sommige bestanden konden niet worden geïmporteerd of verwijderd:\n",
        "import_success_msg_prefix": "{count} WAV-bestanden en metadata.txt geïmporteerd.",
        "wav_mismatch_title": "WAV-bestandsnamen komen niet overeen",
        "wav_mismatch_msg_prefix": "De volgende WAV-bestanden komen met geen enkele videobestandsnaam overeen en zijn niet geïmporteerd:\n",
        "ffmpeg_not_found_msg": "FFmpeg niet gevonden. Zorg dat FFmpeg is geïnstalleerd of is meegeleverd met de executable.",
        "save_combined_wav_dialog_title": "Gecombineerd WAV-bestand opslaan",
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
        "select_folder_dialog": "Selecionar pasta com arquivos de vídeo",
        "cleanup_errors_title": "Erros de limpeza",
        "permission_denied_title": "Permissão negada",
        "folder_not_found_title": "Pasta não encontrada",
        "unexpected_error_title": "Ocorreu um erro",
        "error_title": "Erro",
        "cannot_open_video": "Não é possível abrir o arquivo de vídeo.",
        "ocenaudio_locate_title": "Localizar executável do Ocenaudio",
        "ocenaudio_not_found_title": "Ocenaudio não encontrado",
        "ocenaudio_open_fail_prefix": "Falha ao abrir Ocenaudio: ",
        "export_select_folder_dialog": "Selecionar pasta de exportação para arquivos WAV",
        "overwrite_files_title": "Sobrescrever arquivos?",
        "overwrite_export_body_prefix": "Os seguintes arquivos já existem na pasta de exportação e serão sobrescritos:\n",
        "overwrite_import_body_prefix": "Os seguintes arquivos já existem e serão sobrescritos pela importação:\n",
        "overwrite_question_suffix": "\n\nDeseja sobrescrevê-los?",
        "export_cancelled_title": "Exportação cancelada",
        "export_cancelled_msg": "A exportação foi cancelada para evitar sobrescrições.",
        "delete_errors_title": "Erros ao excluir",
        "delete_errors_msg_prefix": "Alguns arquivos não puderam ser excluídos ou metadata.txt não pôde ser redefinido:\n",
        "clear_success_msg_prefix": "{count} arquivos WAV excluídos e metadata.txt redefinido.",
        "import_select_folder_dialog": "Selecionar pasta de onde importar arquivos",
        "confirm_delete_title": "Confirmar exclusão",
        "confirm_import_title": "Confirmar importação",
        "import_errors_title": "Erros na importação",
        "import_errors_msg_prefix": "Alguns arquivos não puderam ser importados ou excluídos:\n",
        "import_success_msg_prefix": "{count} arquivos WAV e metadata.txt importados.",
        "wav_mismatch_title": "Incompatibilidade de nomes de arquivos WAV",
        "wav_mismatch_msg_prefix": "Os seguintes arquivos WAV não correspondem a nenhum nome de arquivo de vídeo e não foram importados:\n",
        "ffmpeg_not_found_msg": "FFmpeg não encontrado. Certifique-se de que o FFmpeg esteja instalado ou incluído no executável.",
        "save_combined_wav_dialog_title": "Salvar arquivo WAV combinado",
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
        "select_folder_dialog": "Seleccionar carpeta con archivos de video",
        "cleanup_errors_title": "Errores de limpieza",
        "permission_denied_title": "Permiso denegado",
        "folder_not_found_title": "Carpeta no encontrada",
        "unexpected_error_title": "Ocurrió un error",
        "error_title": "Error",
        "cannot_open_video": "No se puede abrir el archivo de video.",
        "ocenaudio_locate_title": "Ubicar ejecutable de Ocenaudio",
        "ocenaudio_not_found_title": "Ocenaudio no encontrado",
        "ocenaudio_open_fail_prefix": "Error al abrir Ocenaudio: ",
        "export_select_folder_dialog": "Seleccionar carpeta de exportación para archivos WAV",
        "overwrite_files_title": "¿Sobrescribir archivos?",
        "overwrite_export_body_prefix": "Los siguientes archivos ya existen en la carpeta de exportación y serán sobrescritos:\n",
        "overwrite_import_body_prefix": "Los siguientes archivos ya existen y serán sobrescritos al importar:\n",
        "overwrite_question_suffix": "\n\n¿Desea sobrescribirlos?",
        "export_cancelled_title": "Exportación cancelada",
        "export_cancelled_msg": "Se canceló la exportación para evitar sobrescrituras.",
        "delete_errors_title": "Errores al eliminar",
        "delete_errors_msg_prefix": "Algunos archivos no se pudieron eliminar o metadata.txt no se pudo restablecer:\n",
        "clear_success_msg_prefix": "Se eliminaron {count} archivos WAV y se restableció metadata.txt.",
        "import_select_folder_dialog": "Seleccionar carpeta desde la cual importar archivos",
        "confirm_delete_title": "Confirmar eliminación",
        "confirm_import_title": "Confirmar importación",
        "import_errors_title": "Errores de importación",
        "import_errors_msg_prefix": "Algunos archivos no se pudieron importar o eliminar:\n",
        "import_success_msg_prefix": "Se importaron {count} archivos WAV y metadata.txt.",
        "wav_mismatch_title": "Incompatibilidad en nombres de archivos WAV",
        "wav_mismatch_msg_prefix": "Los siguientes archivos WAV no coinciden con ningún nombre de archivo de video y no se importaron:\n",
        "ffmpeg_not_found_msg": "FFmpeg no encontrado. Asegúrate de que FFmpeg esté instalado o incluido con el ejecutable.",
        "save_combined_wav_dialog_title": "Guardar archivo WAV combinado",
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
        "select_folder_dialog": "Kies gids met videolêers",
        "cleanup_errors_title": "Opruimfoute",
        "permission_denied_title": "Toegang geweier",
        "folder_not_found_title": "Gids nie gevind nie",
        "unexpected_error_title": "'n Fout het plaasgevind",
        "error_title": "Fout",
        "cannot_open_video": "Kan videolêer nie oopmaak nie.",
        "ocenaudio_locate_title": "Skep Ocenaudio uitvoerbare",
        "ocenaudio_not_found_title": "Ocenaudio nie gevind nie",
        "ocenaudio_open_fail_prefix": "Kon Ocenaudio nie oopmaak nie: ",
        "export_select_folder_dialog": "Kies uitvoergids vir WAV-lêers",
        "overwrite_files_title": "Oorskryf lêers?",
        "overwrite_export_body_prefix": "Die volgende lêers bestaan reeds in die uitvoergids en sal oorskryf word:\n",
        "overwrite_import_body_prefix": "Die volgende lêers bestaan reeds en sal deur invoer oorskryf word:\n",
        "overwrite_question_suffix": "\n\nWil u dit oorskryf?",
        "export_cancelled_title": "Uitvoer gekanselleer",
        "export_cancelled_msg": "Uitvoer is gekanselleer om oorskrywing te vermy.",
        "delete_errors_title": "Skrapfoute",
        "delete_errors_msg_prefix": "Sommige lêers kon nie geskrap word nie of metadata.txt kon nie teruggestel word nie:\n",
        "clear_success_msg_prefix": "{count} WAV-lêers geskrap en metadata.txt teruggestel.",
        "import_select_folder_dialog": "Kies gids om vanaf te invoer",
        "confirm_delete_title": "Bevestig skrap",
        "confirm_import_title": "Bevestig invoer",
        "import_errors_title": "Invoerfoute",
        "import_errors_msg_prefix": "Sommige lêers kon nie ingevoer of geskrap word nie:\n",
        "import_success_msg_prefix": "{count} WAV-lêers en metadata.txt ingevoer.",
        "wav_mismatch_title": "WAV-lêernaam stem nie ooreen nie",
        "wav_mismatch_msg_prefix": "Die volgende WAV-lêers stem met geen videolêernaam ooreen nie en is nie ingevoer nie:\n",
        "ffmpeg_not_found_msg": "FFmpeg nie gevind nie. Maak seker FFmpeg is geïnstalleer of saam met die uitvoerbare gebundel.",
        "save_combined_wav_dialog_title": "Stoor saamgevoegde WAV-lêer",
    },
}

class VideoAnnotationApp(QMainWindow):
    ui_info = Signal(str, str)
    ui_warning = Signal(str, str)
    ui_error = Signal(str, str)
    def __init__(self):
        super().__init__()
        self.language = "English"
        self.LABELS = LABELS_ALL[self.language]
        self.folder_path = None
        self._pending_inaccessible_folder = None
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
        self.audio_thread = None
        self.audio_worker = None
        self.is_recording = False
        self.recording_thread = None
        self.recording_worker = None
        self.join_thread = None
        self.join_worker = None
        self._suppress_item_changed = False
        # Fullscreen viewer state
        self._fullscreen_viewer = None
        self.fullscreen_zoom = None
        self.load_settings()
        self.init_ui()
        self.setWindowTitle(self.LABELS["app_title"])
        self.resize(1400, 800)
        # Wire FolderAccessManager signals to keep UI in sync
        try:
            self.fs.folderChanged.connect(self._on_folder_changed)
            self.fs.videosUpdated.connect(self._on_videos_updated)
            self.fs.metadataChanged.connect(self._on_metadata_changed)
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
            self._shortcut_diag_ctrl = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
            self._shortcut_diag_ctrl.activated.connect(self._show_folder_access_diagnostics)
            self._shortcut_diag_meta = QShortcut(QKeySequence("Meta+Shift+D"), self)
            self._shortcut_diag_meta.activated.connect(self._show_folder_access_diagnostics)
        except Exception:
            pass
        self.ui_info.connect(self._show_info)
        self.ui_warning.connect(self._show_warning)
        self.ui_error.connect(self._show_error)
        # If a saved folder exists but is not accessible, prompt the user
        if self.fs.current_folder and not self._is_folder_accessible(self.fs.current_folder):
            self._handle_inaccessible_last_folder(self.fs.current_folder)
        elif getattr(self, '_pending_inaccessible_folder', None):
            self._handle_inaccessible_last_folder(self._pending_inaccessible_folder)
        # Sync UI state with current folder
        if self.fs.current_folder:
            self._on_folder_changed(self.fs.current_folder)
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
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        try:
            # Make header-to-content gap minimal
            main_layout.setContentsMargins(4, 2, 4, 2)
            main_layout.setSpacing(0)
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
        main_layout.addWidget(self.language_dropdown)
        self.folder_display_label = QLabel(self.LABELS["no_folder_selected"])
        self.folder_display_label.setAlignment(Qt.AlignLeft)
        self.folder_display_label.setToolTip("")
        try:
            # Prevent the folder label from expanding vertically
            self.folder_display_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        except Exception:
            pass
        main_layout.addWidget(self.folder_display_label)
        splitter = QSplitter(Qt.Horizontal)
        try:
            splitter.setHandleWidth(2)
        except Exception:
            pass
        main_layout.addWidget(splitter)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        try:
            # Make the left panel as compact as possible
            left_layout.setContentsMargins(0, 0, 0, 0)
            left_layout.setSpacing(0)
            # Reduce default padding on controls in the left panel
            left_panel.setStyleSheet(
                "QPushButton{margin:0; padding:2px 6px;}\n"
                "QListWidget{margin:0; padding:0;}"
            )
        except Exception:
            pass
        self.select_button = QPushButton(self.LABELS["select_folder"])
        try:
            self.select_button.setFixedHeight(28)
        except Exception:
            pass
        self.select_button.clicked.connect(self.select_folder)
        left_layout.addWidget(self.select_button)
        self.open_ocenaudio_button = QPushButton(self.LABELS["open_ocenaudio"])
        try:
            self.open_ocenaudio_button.setFixedHeight(28)
        except Exception:
            pass
        self.open_ocenaudio_button.clicked.connect(self.open_in_ocenaudio)
        self.open_ocenaudio_button.setEnabled(False)
        left_layout.addWidget(self.open_ocenaudio_button)
        self.export_wavs_button = QPushButton(self.LABELS["export_wavs"])
        try:
            self.export_wavs_button.setFixedHeight(28)
        except Exception:
            pass
        self.export_wavs_button.clicked.connect(self.export_wavs)
        self.export_wavs_button.setEnabled(False)
        left_layout.addWidget(self.export_wavs_button)
        self.clear_wavs_button = QPushButton(self.LABELS["clear_wavs"])
        try:
            self.clear_wavs_button.setFixedHeight(28)
        except Exception:
            pass
        self.clear_wavs_button.clicked.connect(self.clear_wavs)
        self.clear_wavs_button.setEnabled(False)
        left_layout.addWidget(self.clear_wavs_button)
        self.import_wavs_button = QPushButton(self.LABELS["import_wavs"])
        try:
            self.import_wavs_button.setFixedHeight(28)
        except Exception:
            pass
        self.import_wavs_button.clicked.connect(self.import_wavs)
        self.import_wavs_button.setEnabled(False)
        left_layout.addWidget(self.import_wavs_button)
        self.join_wavs_button = QPushButton(self.LABELS["join_wavs"])
        try:
            self.join_wavs_button.setFixedHeight(28)
        except Exception:
            pass
        self.join_wavs_button.clicked.connect(self.join_all_wavs)
        self.join_wavs_button.setEnabled(False)
        left_layout.addWidget(self.join_wavs_button)
        self.video_listbox = QListWidget()
        # Make the list a bit shorter by capping its height
        try:
            self.video_listbox.setMaximumHeight(300)
        except Exception:
            pass
        self.video_listbox.currentRowChanged.connect(self.on_video_select)
        # Let the list occupy ~75% of the extra vertical space
        left_layout.addWidget(self.video_listbox, 3)
        # Replace inline metadata editor with a button that opens a dialog
        self.edit_metadata_button = QPushButton(self.LABELS["edit_metadata"])
        try:
            self.edit_metadata_button.setFixedHeight(28)
        except Exception:
            pass
        self.edit_metadata_button.clicked.connect(self.open_metadata_editor)
        self.edit_metadata_button.setEnabled(False)
        left_layout.addWidget(self.edit_metadata_button)
        splitter.addWidget(left_panel)
        right_panel = QTabWidget()
        videos_tab = QWidget()
        videos_layout = QVBoxLayout(videos_tab)
        try:
            videos_layout.setContentsMargins(4, 4, 4, 4)
            videos_layout.setSpacing(4)
        except Exception:
            pass
        self.video_label = QLabel(self.LABELS["video_listbox_no_video"])
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: black; color: white; border: 1px solid #333;")
        videos_layout.addWidget(self.video_label)
        self.badge_label = QLabel(self.video_label)
        self.badge_label.setText("✓")
        self.badge_label.setAlignment(Qt.AlignCenter)
        self.badge_label.setFixedSize(22, 22)
        self.badge_label.setStyleSheet("background-color: #2ecc71; color: white; border-radius: 11px;")
        self.badge_label.setVisible(False)
        self.video_label.installEventFilter(self)
        video_controls_layout = QHBoxLayout()
        try:
            video_controls_layout.setSpacing(4)
        except Exception:
            pass
        self.prev_button = QToolButton()
        try:
            self.prev_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        except Exception:
            self.prev_button.setText("◀")
        self.prev_button.setToolTip("Previous video")
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
        self.next_button = QToolButton()
        try:
            self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        except Exception:
            self.next_button.setText("▶")
        self.next_button.setToolTip("Next video")
        self.next_button.clicked.connect(self.go_next)
        video_controls_layout.addWidget(self.next_button)
        videos_layout.addLayout(video_controls_layout)
        audio_controls_layout = QHBoxLayout()
        try:
            audio_controls_layout.setSpacing(4)
        except Exception:
            pass
        # Center the audio controls horizontally within their area
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
        self.recording_status_label = QLabel("")
        self.recording_status_label.setStyleSheet("color: red; font-weight: bold;")
        audio_controls_layout.addWidget(self.recording_status_label)
        audio_controls_layout.addStretch(1)
        videos_layout.addLayout(audio_controls_layout)
        videos_layout.addStretch()
        right_panel.addTab(videos_tab, self.LABELS["videos_tab_title"])
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 1000])
    def change_language(self, selected_name):
        for key, labels in LABELS_ALL.items():
            if labels["language_name"] == selected_name:
                self.language = key
                self.LABELS = LABELS_ALL[self.language]
                break
        self.setWindowTitle(self.LABELS["app_title"])
        self.refresh_ui_texts()
        self.save_settings()
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
        # Update the metadata editor button label
        self.edit_metadata_button.setText(self.LABELS["edit_metadata"])
        if not self.current_video:
            self.video_label.setText(self.LABELS["video_listbox_no_video"])
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
                        if not self.fs.set_folder(last_folder):
                            # Defer prompt until UI is ready
                            self._pending_inaccessible_folder = last_folder
                    last_video = settings.get('last_video')
                    if last_video:
                        self.last_video_name = last_video
                    # Persistent fullscreen zoom
                    zoom = settings.get('fullscreen_zoom')
                    if isinstance(zoom, (int, float)) and zoom > 0:
                        self.fullscreen_zoom = float(zoom)
        except Exception as e:
            logging.warning(f"Failed to load settings: {e}")
    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump({
                    'ocenaudio_path': self.ocenaudio_path,
                    'language': self.language,
                    'last_folder': self.fs.current_folder,
                    'last_video': self.current_video,
                    # Persist the last used fullscreen zoom if set
                    'fullscreen_zoom': self.fullscreen_zoom if isinstance(self.fullscreen_zoom, (int, float)) else None,
                }, f)
        except Exception as e:
            logging.warning(f"Failed to save settings: {e}")
    def _is_folder_accessible(self, path: str) -> bool:
        try:
            return self.fs.is_accessible(path)
        except Exception:
            return False
    def _handle_inaccessible_last_folder(self, path: str):
        try:
            QMessageBox.warning(
                self,
                self.LABELS.get("permission_denied_title", "Permission Denied"),
                f"You do not have permission to access the folder:\n{path}\n\nPlease select a different folder."
            )
        except Exception:
            pass
        try:
            self.fs.clear_folder()
        except Exception:
            pass
        self._pending_inaccessible_folder = None
        self.update_folder_display()
        try:
            self.export_wavs_button.setEnabled(False)
            self.clear_wavs_button.setEnabled(False)
            self.import_wavs_button.setEnabled(False)
            self.join_wavs_button.setEnabled(False)
            self.open_ocenaudio_button.setEnabled(False)
            self.edit_metadata_button.setEnabled(False)
        except Exception:
            pass
    def select_folder(self):
        initial_dir = self.fs.current_folder or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, self.LABELS["select_folder_dialog"], initial_dir)
        if folder:
            if not self.fs.set_folder(folder):
                QMessageBox.critical(
                    self,
                    self.LABELS.get("permission_denied_title", "Permission Denied"),
                    f"Cannot access folder: {folder}\n\nPlease select a different folder."
                )
                return
            # Reset current selection to avoid attempting to open a video from the previous folder
            self.current_video = None
            self.update_folder_display()
            if sys.platform == "win32":
                hidden_files = [f for f in os.listdir(self.fs.current_folder) if f.startswith('.')]
                errors = []
                for f in hidden_files:
                    try:
                        os.remove(os.path.join(self.fs.current_folder, f))
                    except Exception as e:
                        errors.append(f"Delete {f}: {e}")
                if errors:
                    QMessageBox.warning(self, self.LABELS["cleanup_errors_title"], "Some hidden files could not be deleted:\n" + "\n".join(errors))
            self.load_video_files()
            self.export_wavs_button.setEnabled(True)
            self.clear_wavs_button.setEnabled(True)
            self.import_wavs_button.setEnabled(True)
            self.join_wavs_button.setEnabled(True)
            self.open_ocenaudio_button.setEnabled(True)
            self.edit_metadata_button.setEnabled(True)
            self.save_settings()
    def load_video_files(self):
        self.video_listbox.clear()
        self.video_files = []
        if not self.fs.current_folder:
            QMessageBox.information(self, self.LABELS["no_folder_selected"], self.LABELS["no_folder_selected"])
            return
        try:
            # Prefer centralized listing
            self.video_files = self.fs.list_videos(self.fs.current_folder)
            self.video_files.sort()
            basenames = [os.path.basename(vp) for vp in self.video_files]
            for name in basenames:
                item = QListWidgetItem(name)
                wav_exists = os.path.exists(self.fs.wav_path_for(name))
                item.setIcon(self._check_icon if wav_exists else self._empty_icon)
                self.video_listbox.addItem(item)
            # Auto-select: prefer last selected name if present, otherwise the first video
            if basenames:
                if self.last_video_name and self.last_video_name in basenames:
                    idx = basenames.index(self.last_video_name)
                else:
                    idx = 0
                # Setting the current row triggers on_video_select, which updates current_video and preview
                self.video_listbox.setCurrentRow(idx)
            if not self.video_files:
                QMessageBox.information(self, self.LABELS["no_videos_found"], f"{self.LABELS['no_videos_found']} {self.fs.current_folder}")
        except PermissionError:
            QMessageBox.critical(self, self.LABELS["permission_denied_title"], f"You do not have permission to access the folder: {self.fs.current_folder}")
        except FileNotFoundError:
            QMessageBox.critical(self, self.LABELS["folder_not_found_title"], f"The selected folder no longer exists: {self.fs.current_folder}")
        except Exception as e:
            QMessageBox.critical(self, self.LABELS["unexpected_error_title"], f"An unexpected error occurred: {e}")
        if not self.video_files:
            self.current_video = None
        self.update_media_controls()
        self.update_video_file_checks()
    def open_metadata_editor(self):
        if not self.fs.current_folder:
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
            # Build a simple modal dialog for metadata editing
            dlg = QDialog(self)
            dlg.setWindowTitle(self.LABELS.get("metadata_editor_title", self.LABELS.get("edit_metadata", "Edit Metadata")))
            vbox = QVBoxLayout(dlg)
            editor = QTextEdit()
            editor.setPlainText(content)
            editor.setMinimumHeight(200)
            vbox.addWidget(editor)
            btn_box = QHBoxLayout()
            save_btn = QPushButton(self.LABELS.get("update_metadata", "Save and Close"))
            cancel_btn = QPushButton(self.LABELS.get("cancel", "Cancel"))
            btn_box.addWidget(save_btn)
            btn_box.addWidget(cancel_btn)
            vbox.addLayout(btn_box)

            def _save_and_close():
                new_content = editor.toPlainText()
                try:
                    self.fs.write_metadata(new_content)
                    QMessageBox.information(self, self.LABELS.get("saved", "Saved"), self.LABELS.get("metadata_saved", "Metadata saved!"))
                    dlg.accept()
                except FolderPermissionError:
                    QMessageBox.critical(self, self.LABELS.get("permission_denied_title", "Permission Denied"), f"You do not have permission to write metadata in: {self.fs.current_folder}")
                except FolderNotFoundError:
                    QMessageBox.critical(self, self.LABELS.get("folder_not_found_title", "Folder Not Found"), f"The selected folder no longer exists: {self.fs.current_folder}")
                except FolderAccessError as e:
                    QMessageBox.critical(self, self.LABELS.get("unexpected_error_title", "Unexpected Error"), f"An unexpected error occurred: {e}")

            save_btn.clicked.connect(_save_and_close)
            cancel_btn.clicked.connect(dlg.reject)
            dlg.exec()
        except FolderPermissionError:
            QMessageBox.critical(self, self.LABELS["permission_denied_title"], f"You do not have permission to access the folder: {self.fs.current_folder}")
        except FolderNotFoundError:
            QMessageBox.critical(self, self.LABELS["folder_not_found_title"], f"The selected folder no longer exists: {self.fs.current_folder}")
        except FolderAccessError as e:
            QMessageBox.critical(self, self.LABELS["unexpected_error_title"], f"An unexpected error occurred: {e}")
    def save_metadata(self):
        if not self.fs.current_folder:
            return
        content = self.metadata_text.toPlainText()
        try:
            self.fs.write_metadata(content)
            QMessageBox.information(self, self.LABELS["saved"], self.LABELS["metadata_saved"])
        except FolderPermissionError:
            QMessageBox.critical(self, self.LABELS["permission_denied_title"], f"You do not have permission to write metadata in: {self.fs.current_folder}")
        except FolderNotFoundError:
            QMessageBox.critical(self, self.LABELS["folder_not_found_title"], f"The selected folder no longer exists: {self.fs.current_folder}")
        except FolderAccessError as e:
            QMessageBox.critical(self, self.LABELS["unexpected_error_title"], f"An unexpected error occurred: {e}")
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
    def show_first_frame(self):
        if not self.current_video:
            self.video_label.setText(self.LABELS["video_listbox_no_video"])
            return
        video_path = os.path.join(self.fs.current_folder or "", self.current_video)
        if not os.path.exists(video_path):
            # Avoid noisy popup during folder transitions; just update the label
            logging.info(f"Video path does not exist for preview: {video_path}")
            self.video_label.setText(self.LABELS["video_listbox_no_video"])
            return
        cap = None
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                # Suppress popup here; selection handler will display valid content shortly
                logging.warning(f"Failed to open video for preview: {video_path}")
                self.video_label.setText(self.LABELS["video_listbox_no_video"])
                return
            ret, frame = cap.read()
            if not ret:
                logging.warning(f"Failed to read first frame: {video_path}")
                self.video_label.setText(self.LABELS["video_listbox_no_video"])
                return
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(qt_image)
            # Scale to fill the label without black bars, cropping as needed
            target = self.video_label.size()
            if target.width() > 0 and target.height() > 0:
                pixmap = pixmap.scaled(target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.video_label.setPixmap(pixmap)
        except Exception as e:
            logging.error(f"Failed to load first frame for {video_path}: {e}")
            QMessageBox.critical(self, self.LABELS["error_title"], f"{self.LABELS['unexpected_error_title']}: {e}")
            self.video_label.setText(self.LABELS["cannot_open_video"])
        finally:
            if cap is not None:
                cap.release()
    def update_media_controls(self):
        if self.current_video:
            self.play_video_button.setEnabled(True)
            self.stop_video_button.setEnabled(True)
            self.record_button.setEnabled(True)
            self.record_button.setText(self.LABELS["record_audio"] if not self.is_recording else self.LABELS["stop_recording"])
            self.update_recording_indicator()
            wav_path = self.fs.wav_path_for(self.current_video)
            if os.path.exists(wav_path):
                # Audio file exists: enable audio controls and show badge
                self.play_audio_button.setEnabled(True)
                self.stop_audio_button.setEnabled(True)
                self.video_label.setStyleSheet("background-color: black; color: white; border: 3px solid #2ecc71;")
                if getattr(self, 'badge_label', None):
                    self.badge_label.setVisible(True)
            else:
                # No audio: disable audio controls and hide badge
                self.play_audio_button.setEnabled(False)
                self.stop_audio_button.setEnabled(False)
                self.video_label.setStyleSheet("background-color: black; color: white; border: 1px solid #333;")
                if getattr(self, 'badge_label', None):
                    self.badge_label.setVisible(False)
        else:
            self.video_label.setText(self.LABELS["video_listbox_no_video"])
            self.play_video_button.setEnabled(False)
            self.stop_video_button.setEnabled(False)
            self.play_audio_button.setEnabled(False)
            self.stop_audio_button.setEnabled(False)
            self.record_button.setEnabled(False)
            self.record_button.setText(self.LABELS["record_audio"])
            self.update_recording_indicator()
            self.video_label.setStyleSheet("background-color: black; color: white; border: 1px solid #333;")
            if getattr(self, 'badge_label', None):
                self.badge_label.setVisible(False)
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
        video_path = os.path.join(self.fs.current_folder or "", self.current_video)
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
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
                target = self.video_label.size()
                if target.width() > 0 and target.height() > 0:
                    pixmap = pixmap.scaled(target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.video_label.setPixmap(pixmap)
        except Exception as e:
            logging.error(f"Video frame update failed: {e}")
            self.stop_video()
            self.video_label.setText(self.LABELS.get("cannot_open_video", "Cannot open video file."))
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
    def play_audio(self):
        if not self.current_video:
            return
        self.stop_audio()
        wav_path = self.fs.wav_path_for(self.current_video)
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
        self.audio_thread.finished.connect(self._on_audio_thread_finished)
        self.audio_worker.error.connect(self._show_worker_error)
        self.audio_thread.start()
    def stop_audio(self):
        if self.audio_worker:
            try:
                self.audio_worker.stop()
            except RuntimeError:
                pass
        if self.audio_thread:
            try:
                if self.audio_thread.isRunning():
                    self.audio_thread.quit()
                    self.audio_thread.wait()
            except RuntimeError:
                pass
            finally:
                self.audio_thread = None
                self.audio_worker = None
    def _on_audio_thread_finished(self):
        self.audio_thread = None
        self.audio_worker = None
    def toggle_recording(self):
        logging.debug("toggle_recording invoked: current_video=%s, is_recording=%s", self.current_video, self.is_recording)
        if not self.current_video:
            logging.debug("toggle_recording: no current_video, ignoring")
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
            logging.debug("toggle_recording: starting, wav_path=%s, pyaudio_available=%s", wav_path, PYAUDIO_AVAILABLE)
            if os.path.exists(wav_path):
                reply = QMessageBox.question(self, self.LABELS["overwrite"], 
                                            self.LABELS["overwrite_audio"],
                                            QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    return
            if not PYAUDIO_AVAILABLE:
                QMessageBox.warning(self, "Error", "PyAudio is not available. Cannot record audio.")
                logging.warning("toggle_recording: PyAudio not available, aborting record")
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
    def closeEvent(self, event):
        try:
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
        try:
            wav_paths = self.fs.recordings_in(self.fs.current_folder)
        except FolderAccessError:
            wav_paths = []
        wav_files = [os.path.basename(p) for p in wav_paths]
        if not wav_files:
            QMessageBox.information(self, self.LABELS["no_files"], self.LABELS["no_wavs_found"]) 
            return
        wav_files.sort()
        file_paths = [os.path.join(self.fs.current_folder, f) for f in wav_files]
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
                    QMessageBox.warning(self, self.LABELS["ocenaudio_not_found_title"], "Ocenaudio not found. Please install it to use this feature.")
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
        try:
            wav_paths = self.fs.recordings_in(self.fs.current_folder)
        except FolderAccessError:
            wav_paths = []
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
        metadata_src = os.path.join(self.fs.current_folder, "metadata.txt")
        try:
            shutil.copy2(metadata_src, metadata_dst)
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
        try:
            wav_paths = self.fs.recordings_in(self.fs.current_folder)
        except FolderAccessError:
            wav_paths = []
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
        metadata_path = os.path.join(self.fs.current_folder, "metadata.txt")
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
            QMessageBox.critical(self, self.LABELS["delete_errors_title"], self.LABELS["delete_errors_msg_prefix"] + "\n".join(errors))
        else:
            QMessageBox.information(self, self.LABELS["clear_wavs"], self.LABELS["clear_success_msg_prefix"].format(count=len(wav_files)))
        self.load_video_files()
    # No longer auto-open metadata editor; user can click the button to edit
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
        try:
            wav_paths = self.fs.recordings_in(self.fs.current_folder)
        except FolderAccessError:
            wav_paths = []
        wav_files = [os.path.basename(p) for p in wav_paths]
        errors = []
        for wav in wav_files:
            try:
                os.remove(os.path.join(self.fs.current_folder, wav))
            except Exception as e:
                errors.append(f"Delete {wav}: {e}")
        import_dir = QFileDialog.getExistingDirectory(self, self.LABELS["import_select_folder_dialog"]) 
        if not import_dir:
            return
        import_files = [f for f in os.listdir(import_dir) if f.lower().endswith('.wav') and not f.startswith('.')]
        video_basenames = set(self.fs.video_basename(v) for v in self.video_files)
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
    # No longer auto-open metadata editor; user can click the button to edit
        self.update_video_file_checks()
    def join_all_wavs(self):
        if not self.fs.current_folder:
            QMessageBox.critical(self, self.LABELS["error_title"], self.LABELS["no_folder_selected"]) 
            return
        try:
            wav_paths = self.fs.recordings_in(self.fs.current_folder)
        except FolderAccessError:
            wav_paths = []
        wav_files = [os.path.basename(p) for p in wav_paths]
        if not wav_files:
            QMessageBox.information(self, self.LABELS["no_files"], self.LABELS["no_wavs_found"]) 
            return
        # Verify FFmpeg availability using the resolver which handles Windows .exe/dev/bundled/system
        from vat.utils.resources import resolve_ff_tools
        info = resolve_ff_tools()
        ffmpeg_path = info.get('ffmpeg')
        if not ffmpeg_path or not os.path.exists(ffmpeg_path):
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
        self.join_worker = JoinWavsWorker(None, output_file, fs=self.fs)
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

    # FolderAccessManager signal handlers
    def _on_folder_changed(self, path: str):
        try:
            # Clear selection and stop any active playback before rebuilding the list
            try:
                if self.playing_video:
                    self.stop_video()
            except Exception:
                pass
            self.current_video = None
            self.update_folder_display()
            has_folder = bool(self.fs.current_folder)
            self.export_wavs_button.setEnabled(has_folder)
            self.clear_wavs_button.setEnabled(has_folder)
            self.import_wavs_button.setEnabled(has_folder)
            self.join_wavs_button.setEnabled(has_folder)
            self.open_ocenaudio_button.setEnabled(has_folder)
            self.edit_metadata_button.setEnabled(has_folder)
            if has_folder:
                self.load_video_files()
        except Exception:
            pass

    def _on_videos_updated(self, videos: list):
        try:
            # Rebuild list from shared state
            self.video_listbox.clear()
            self.video_files = list(videos)
            basenames = [os.path.basename(vp) for vp in self.video_files]
            for name in basenames:
                item = QListWidgetItem(name)
                wav_exists = os.path.exists(self.fs.wav_path_for(name))
                item.setIcon(self._check_icon if wav_exists else self._empty_icon)
                self.video_listbox.addItem(item)
            self.update_media_controls()
            self.update_video_file_checks()
        except Exception:
            pass

    def _on_metadata_changed(self, text: str):
        try:
            # Keep editor in sync after external writes
            if getattr(self, 'metadata_text', None):
                self.metadata_text.setPlainText(text)
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
    def _show_folder_access_diagnostics(self):
        try:
            folder = self.fs.current_folder or ""
            if not folder:
                QMessageBox.information(self, "Folder Diagnostics", "No folder selected.")
                return
            info = self.fs.diagnose_access(folder)
            msg = (
                f"Folder: {folder}\n"
                f"Exists: {info.get('exists')}\n"
                f"Is Directory: {info.get('isdir')}\n"
                f"Readable: {info.get('can_read')}\n"
                f"Executable/Traversable: {info.get('can_exec')}\n"
                f"Listable: {info.get('listable')}\n"
            )
            QMessageBox.information(self, "Folder Diagnostics", msg)
        except Exception as e:
            QMessageBox.information(self, "Folder Diagnostics", f"Error: {e}")
    def eventFilter(self, obj, event):
        if obj is self.video_label:
            try:
                if event.type() == QEvent.MouseButtonDblClick and self.current_video and self.fs.current_folder:
                    self._open_fullscreen_video()
                    return True
            except Exception:
                pass
            try:
                self._position_badge()
            except Exception:
                pass
        return super().eventFilter(obj, event)
    def _open_fullscreen_video(self):
        try:
            if not self.current_video or not self.fs.current_folder:
                return
            # Safeguard: if already open, bring to front
            if getattr(self, '_fullscreen_viewer', None) is not None:
                try:
                    if self._fullscreen_viewer.isVisible():
                        self._fullscreen_viewer.raise_()
                        self._fullscreen_viewer.activateWindow()
                        self._fullscreen_viewer.setFocus()
                        return
                except Exception:
                    pass
            video_path = os.path.join(self.fs.current_folder or "", self.current_video)
            # Create as top-level window (no parent) so it truly fullscreen
            viewer = FullscreenVideoViewer(video_path, initial_scale=self.fullscreen_zoom)
            self._fullscreen_viewer = viewer
            viewer.showFullScreen()
            try:
                viewer.raise_()
                viewer.activateWindow()
                viewer.setFocus()
            except Exception:
                pass
            # Track zoom changes and persist on close
            try:
                viewer.scale_changed.connect(self._on_fullscreen_scale_changed)
                viewer.destroyed.connect(self._on_fullscreen_closed)
            except Exception:
                pass
        except Exception as e:
            logging.error(f"Failed to open fullscreen viewer: {e}")
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
        if not self.badge_label.isVisible():
            return
        w = self.video_label.width()
        h = self.video_label.height()
        bw = self.badge_label.width()
        x = max(0, w - bw - 8)
        y = 8
        self.badge_label.move(x, y)
