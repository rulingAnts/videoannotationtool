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
    QFileDialog, QComboBox, QTabWidget, QSplitter, QToolButton, QStyle, QSizePolicy,
    QListView, QStyledItemDelegate, QApplication, QCheckBox, QGraphicsDropShadowEffect,
    QMenu
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QEvent, QSize, QRect, QPoint, QLocale, QMetaObject, QUrl, QMimeData
import time
from PySide6.QtGui import QImage, QPixmap, QIcon, QShortcut, QKeySequence, QImageReader, QPen, QColor, QGuiApplication, QAction, QCursor

from vat.audio import PYAUDIO_AVAILABLE
from vat.audio.playback import AudioPlaybackWorker
from vat.audio.recording import AudioRecordingWorker
from vat.audio.joiner import JoinWavsWorker
from vat.utils.resources import resource_path
from vat.ui.fullscreen import FullscreenVideoViewer, FullscreenImageViewer
from vat.utils.fs_access import (
    FolderAccessManager,
    FolderAccessError,
    FolderPermissionError,
    FolderNotFoundError,
)
from vat.review import ReviewTab

# UI labels for easy translation, with language names in their own language
LABELS_ALL = {
    "English": {
        "language_name": "English",
        "app_title": "Visual Stimulus Kit Tool",
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
        "add_existing_audio": "Add audio…",
        "add_audio_from_file": "From file…",
        "add_audio_paste_clipboard": "Paste from clipboard",
        "import_select_file_dialog": "Select Audio File",
            "images_tab_title": "Images",
            "copy_image": "Copy Image",
            "copy_video": "Copy Video",
        "copied_image": "Image copied to clipboard",
            "copied_video": "Video copied to clipboard",
            "save_image_as": "Save Image as…",
            "save_video_as": "Save Video as…",
            "save_image_as_dialog_title": "Save Image as…",
            "save_video_as_dialog_title": "Save Video as…",
        "paste_audio_failed": "Clipboard does not contain audio or an audio file path.",
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
        
        "review_report_saved_msg": "Laporan disimpan ke:",
        "review_export_report_failed": "Gagal mengekspor laporan:",
        "review_session_complete_title": "Sesi Selesai",
        "review_session_complete_msg": "Sesi ulasan selesai!",
        "review_summary_grade": "Nilai",
        "review_summary_accuracy": "Akurasi",
        "review_summary_avg_time": "Waktu Rata-rata",
        "review_summary_composite": "Skor Komposit",
        "group_export_title": "Ekspor Kelompok",
        "group_export_info": "Ekspor {count} rekaman ke folder grup yang teratur.",
        "group_export_items_per_folder": "Item per folder:",
        "group_export_num_folders": "Jumlah folder:",
        "group_export_preview_none": "Tidak ada item untuk diekspor.",
        "group_export_preview_will_create": "Akan membuat {n} folder:\n",
        "group_export_preview_group_line": "  Grup {i:02d}: {count} item\n",
        "group_export_preview_more": "  ... dan {extra} folder lagi\n",
        "group_export_preview_last_note": "\nCatatan: Folder terakhir memiliki {count} item (sisa).",
        "group_export_copy_mode": "Salin file (default, aman)",
        "group_export_copy_mode_tip": "Hapus centang untuk memindahkan file (gunakan dengan hati-hati)",
        "group_export_export_btn": "Ekspor...",
        "group_export_cancel_btn": "Batal",
        "group_export_select_dir": "Pilih Direktori Ekspor",
        "group_export_no_items_title": "Tidak Ada Item",
        "group_export_no_items_msg": "Tidak ada item untuk diekspor.",
        "group_export_confirm_overwrite_title": "Konfirmasi Timpa",
        "group_export_confirm_overwrite_msg": "Direktori yang dipilih sudah berisi {n} folder Grup.\n\nFile yang ada mungkin ditimpa. Lanjutkan?",
        "group_export_complete_title": "Ekspor Selesai",
        "group_export_complete_msg": "Berhasil mengekspor {items} item ke {groups} folder.",
        "group_export_failed_title": "Ekspor Gagal",
        "group_export_failed_msg": "Gagal mengekspor:",
    },
    "한국어": {
        "language_name": "한국어",
        "app_title": "시각 자극 키트 도구",
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
        "add_existing_audio": "오디오 추가…",
        "add_audio_from_file": "파일에서…",
        "add_audio_paste_clipboard": "클립보드에서 붙여넣기",
        "import_select_file_dialog": "오디오 파일 선택",
        "images_tab_title": "이미지",
        "copy_image": "이미지 복사",
        "copy_video": "비디오 복사",
        "copied_image": "이미지가 클립보드에 복사되었습니다",
        "copied_video": "비디오가 클립보드에 복사되었습니다",
        "save_image_as": "이미지 다른 이름으로 저장…",
        "save_video_as": "비디오 다른 이름으로 저장…",
        "save_image_as_dialog_title": "이미지 다른 이름으로 저장…",
        "save_video_as_dialog_title": "비디오 다른 이름으로 저장…",
        "paste_audio_failed": "클립보드에 오디오 또는 오디오 파일 경로가 없습니다.",
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
        "video_fullscreen_tip": "<b>팁:</b> 비디오를 두 번 클릭하면 전체 화면으로 열립니다. 전체 화면에서 <b>+</b>와 <b>-</b> 키로 확대/축소할 수 있습니다.",
        "image_fullscreen_tip": "<b>팁:</b> 이미지를 두 번 클릭하면 전체 화면으로 열립니다. 전체 화면에서 <b>+</b>와 <b>-</b> 키로 확대/축소할 수 있습니다.",
        "image_show_filenames": "파일 이름 표시",
        "welcome_dialog_title": "시각 자극 키트 도구에 오신 것을 환영합니다",
        "welcome_dialog_body_html": (
            "<p><b>환영합니다!</b> 이 도구는 소수 언어와 충분히 기록되지 않은 언어에서 사람들이 말하고 수어하는 방식을 "
            "명확하고 잘 정리된 예문으로 모을 수 있도록 도와줍니다. "
            "짧은 비디오 클립이나 정지 이미지(자극 자료)를 사용하여 화자와 수어 사용자가 특정 상황이나 의미를 표현하도록 유도하고, "
            "그 결과를 바탕으로 문법과 어휘를 살펴볼 수 있습니다.</p>"
            "<p><b>권장 사용 방법:</b></p>"
            "<ol>"
            "<li><b>사용 중인 자극 자료(킷)의 안내서를 따르십시오.</b> 비디오 클립과 정지 이미지는 안내서에 제시된 순서를 유지하는 것이 좋습니다. "
            "정지 이미지의 파일 이름이나 정확한 순서는 비디오 목록과 완전히 같을 필요는 없지만, 의미와 상황은 의도된 순서대로 제시되어야 합니다.</li>"
            "<li><b>가능하다면 항상 연속적인 백업 녹음을 만드십시오.</b> 이 도구에서 항목마다 짧은 오디오 파일을 하나씩 녹음하는 것과 더불어, "
            "전체 일리스티테이션 세션을 별도의 연속 오디오(및/또는 비디오)로 기록해 두면 큰 도움이 됩니다. "
            "이렇게 하면 개별 파일에 문제가 생겨도 자료를 잃지 않을 가능성이 커집니다.</li>"
            "</ol>"
            "<p>권장 자극 자료와 더 자세한 배경 설명은 프로젝트 웹사이트의 "
            "<a href=\"https://rulingants.github.io/videoannotationtool/#stimulus-kits\">Usage and recommended stimulus kits</a> "
            "섹션에서 확인할 수 있습니다.</p>"
        ),
        "ocenaudio_not_found_body": "Ocenaudio를 찾을 수 없습니다. 이 기능을 사용하려면 먼저 설치해 주세요.",
        
        "review_tab_title": "리뷰",
        "review_tip_html": "<b>팁:</b> 한 번 클릭하면 선택됩니다. 우클릭, Ctrl/Cmd+클릭 또는 Enter로 확인합니다. 두 번 클릭하면 미리보기/전체화면이 열립니다. 스페이스바를 눌러 프롬프트를 다시 재생하세요.",
        "time_label_prefix": "시간: ",
        "review_start": "리뷰 시작",
        "review_pause": "일시 정지",
        "review_resume": "재개",
        "review_stop": "중지",
        "review_replay": "다시 듣기",
        "review_prev_set": "이전 세트",
        "review_next_set": "다음 세트",
        "review_show_settings": "설정 표시",
        "review_hide_settings": "설정 숨기기",
        "review_set_name_placeholder": "세트 이름",
        "review_help_link": "GPA 리뷰 가이드",
        "review_scope_label": "범위:",
        "review_scope_images": "이미지",
        "review_scope_videos": "비디오",
        "review_scope_both": "둘 다",
        "review_play_count_label": "재생 횟수:",
        "review_time_limit_label": "시간 제한(초):",
        "review_time_limit_off": "꺼짐",
        "review_limit_mode_label": "제한 모드:",
        "review_limit_soft": "느슨함",
        "review_limit_hard": "엄격함",
        "review_sfx_label": "효과음",
        "review_sfx_vol_label": "효과음 볼륨:",
        "review_sfx_tone_label": "효과음 톤:",
        "review_sfx_tone_default": "기본",
        "review_sfx_tone_gentle": "부드럽게",
        "review_time_weight_label": "시간 가중치 %:",
        "review_ui_overhead_label": "UI 오버헤드(ms):",
        "review_thumb_size_label": "썸네일 크기:",
        "review_items_per_session_label": "세션당 항목:",
        "review_sessions_label_initial": "세션: --",
        "review_sessions_label_format": "세션: {sessions}  |  항목/세션: {per}  |  마지막: {last_items}",
        "review_set_label_format": "세트 {n}",
        "review_reset": "재설정",
        "review_reset_defaults": "기본값으로 재설정",
        "review_export_results": "결과 내보내기",
        "review_export_sets": "세트 내보내기",
        "review_export_sets_tooltip": "현재 가상 세션 그룹을 저장",
        "review_export_format_label": "형식:",
        "review_export_format_folders": "폴더",
        "review_export_format_zip": "Zip 파일",
        "review_progress_format": "{current}/{total} 프롬프트",
        "review_no_items_title": "항목 없음",
        "review_no_items_scope": "선택한 범위에 해당하는 녹음이 없습니다.",
        "review_no_items_group": "그룹화할 녹음이 없습니다.",
        "review_no_items_export": "내보낼 녹음이 없습니다.",
        "review_no_session_title": "세션 없음",
        "review_no_session_msg": "내보낼 세션 데이터가 없습니다.",
        "review_choose_save_sets": "세트를 저장할 위치 선택",
        "review_export_complete_title": "내보내기 완료",
        "review_export_sets_complete_msg": "{n}개 세트를 내보냈습니다:\n{dir}",
        "review_export_failed_title": "내보내기 실패",
        "review_export_sets_failed": "세트 내보내기 실패:",
        "review_choose_save_report": "보고서 저장 위치 선택",
        "review_report_saved_msg": "보고서가 저장되었습니다:",
        "review_export_report_failed": "보고서 내보내기 실패:",
        "review_session_complete_title": "세션 완료",
        "review_session_complete_msg": "리뷰 세션이 완료되었습니다!",
        "review_summary_grade": "등급",
        "review_summary_accuracy": "정확도",
        "review_summary_avg_time": "평균 시간",
        "review_summary_composite": "종합 점수",
        "group_export_title": "그룹 내보내기",
        "group_export_info": "{count}개의 녹음을 정리된 그룹 폴더로 내보냅니다.",
        "group_export_items_per_folder": "폴더당 항목:",
        "group_export_num_folders": "폴더 수:",
        "group_export_preview_none": "내보낼 항목이 없습니다.",
        "group_export_preview_will_create": "{n}개의 폴더를 생성합니다:\n",
        "group_export_preview_group_line": "  그룹 {i:02d}: {count}개 항목\n",
        "group_export_preview_more": "  ... 그리고 {extra}개 더 많은 폴더\n",
        
        "review_replay": "Repetir",
        "review_prev_set": "Conjunto anterior",
        "review_next_set": "Próximo conjunto",
        "review_show_settings": "Mostrar configurações",
        "review_hide_settings": "Ocultar configurações",
        "review_set_name_placeholder": "Nome do conjunto",
        "review_help_link": "Guia de Revisão GPA",
        "review_scope_label": "Escopo:",
        "review_scope_images": "Imagens",
        "review_scope_videos": "Vídeos",
        "review_scope_both": "Ambos",
        "review_play_count_label": "Reproduções:",
        "review_time_limit_label": "Limite de tempo (s):",
        "review_time_limit_off": "Desligado",
        "review_limit_mode_label": "Modo de limite:",
        "review_limit_soft": "Suave",
        "review_limit_hard": "Rígido",
        "review_sfx_label": "Efeitos sonoros",
        "review_sfx_vol_label": "Vol. SFX:",
        "review_sfx_tone_label": "Tom SFX:",
        "review_sfx_tone_default": "Padrão",
        "review_sfx_tone_gentle": "Suave",
        "review_time_weight_label": "Peso do tempo %:",
        "review_ui_overhead_label": "Sobrecarga da UI (ms):",
        "review_thumb_size_label": "Tamanho das miniaturas:",
        "review_items_per_session_label": "Itens por sessão:",
        "review_sessions_label_initial": "Sessões: --",
        "review_sessions_label_format": "Sessões: {sessions}  |  Itens/sessão: {per}  |  Última: {last_items}",
        "review_set_label_format": "Conjunto {n}",
        "review_reset": "Redefinir",
        "review_reset_defaults": "Redefinir para padrão",
        "review_export_results": "Exportar Resultados",
        "review_export_sets": "Exportar Conjuntos",
        "review_export_sets_tooltip": "Salvar agrupamento da sessão virtual atual",
        "review_export_format_label": "Formato:",
        
        "ffmpeg_not_found_msg": "FFmpeg nie gevind nie. Maak seker FFmpeg is geïnstalleer of saam met die uitvoerbare gebundel.",
        "save_combined_wav_dialog_title": "Stoor saamgevoegde WAV-lêer",
        "video_fullscreen_tip": "<b>Wenk:</b> Dubbelklik op die video om dit op volle skerm oop te maak. Gebruik <b>+</b> en <b>-</b> om in en uit te zoem in die volskerm-aansig.",
        "image_fullscreen_tip": "<b>Wenk:</b> Dubbelklik op 'n prent om dit op volle skerm oop te maak. Gebruik <b>+</b> en <b>-</b> om in en uit te zoem in die volskerm-aansig.",
        "image_show_filenames": "Wys lêername",
        "welcome_dialog_title": "Welkom by die Visuele Stimulus Hulpmiddel",
        "welcome_dialog_body_html": (
            "<p><b>Welkom!</b> Hierdie hulpmiddel help jou om duidelike, goed-geordende voorbeelde te versamel "
            "van hoe mense praat en gebare maak in minderheidstale en ondergedokumenteerde tale. "
            "Jy gebruik kort videoklankies of stilbeelde (stimuli) om sprekers en gebaarders te lei deur spesifieke situasies of betekenisse, "
            "sodat jy hul grammatika en woordeskat kan bestudeer.</p>"
            "<p><b>Aanbevole praktyke:</b></p>"
            "<ol>"
            "<li><b>Volg die instruksies van jou stimulusstel.</b> Hou die volgorde van die videoklankies "
            "en stilbeelde dieselfde as in die stel se handleiding. Die presiese lêername en volgorde van die stilbeelde "
            "hoef nie perfek met die videolys te ooreen te stem nie, maar die betekenisse en situasies moet in die bedoelde volgorde aangebied word.</li>"
            "<li><b>Maak indien moontlik 'n aaneenlopende rugsteunopname.</b> Benewens die een kort oudiolêer per item in hierdie hulpmiddel, "
            "is dit baie nuttig om ook 'n aparte, aaneenlopende oudio- (en/of video-)opname van die hele elisitasiesessie te maak. "
            "Dit beskerm jou as daar iets met individuele lêers verkeerd loop.</li>"
            "</ol>"
            "<p>Vir voorbeelde van aanbevole stimulusstelle en agtergrondinligting, sien die afdeling "
            "<a href=\"https://rulingants.github.io/videoannotationtool/#stimulus-kits\">Usage and recommended stimulus kits</a> "
            "op die projek se webwerf.</p>"
        ),
        "ocenaudio_not_found_body": "Ocenaudio nie gevind nie. Installeer dit om hierdie funksie te gebruik.",
        
        "review_tab_title": "Hersiening",
        "review_tip_html": "<b>Wenk:</b> Een klik kies. Regsklik, Ctrl/Cmd+Klik of Enter bevestig. Dubbelklik open voorskou/volskerm. Druk Spasie om die prompt weer te speel.",
        "time_label_prefix": "Tyd: ",
        "review_start": "Begin Hersiening",
        "review_pause": "Pouse",
        "review_resume": "Hervat",
        "review_stop": "Stop",
        "review_replay": "Speel weer",
        "review_prev_set": "Vorige stel",
        "review_next_set": "Volgende stel",
        "review_show_settings": "Wys instellings",
        "review_hide_settings": "Versteek instellings",
        "review_set_name_placeholder": "Stelnaam",
        "review_help_link": "GPA Hersieningsgids",
        "review_scope_label": "Reikwydte:",
        "review_scope_images": "Prente",
        "review_scope_videos": "Video's",
        "review_scope_both": "Albei",
        "review_play_count_label": "Speelkeer:",
        "review_time_limit_label": "Tydsbeperking (s):",
        "review_time_limit_off": "Af",
        "review_limit_mode_label": "Beperkingsmodus:",
        "review_limit_soft": "Sag",
        "review_limit_hard": "Streng",
        "review_sfx_label": "Klankeffekte",
        "review_sfx_vol_label": "SFX Vol:",
        "review_sfx_tone_label": "SFX Toon:",
        "review_sfx_tone_default": "Standaard",
        "review_sfx_tone_gentle": "Sag",
        "review_time_weight_label": "Tydweging %:",
        "review_ui_overhead_label": "UI-oorskot (ms):",
        "review_thumb_size_label": "Duimnaelgrootte:",
        "review_items_per_session_label": "Items per sessie:",
        "review_sessions_label_initial": "Sessies: --",
        "review_sessions_label_format": "Sessies: {sessions}  |  Items/sessie: {per}  |  Laaste: {last_items}",
        "review_set_label_format": "Stel {n}",
        "review_reset": "Herstel",
        "review_reset_defaults": "Herstel na verstek",
        "review_export_results": "Voer Resultate Uit",
        "review_export_sets": "Voer Stelle Uit",
        "review_export_sets_tooltip": "Stoor die huidige virtuele sessiegroepering",
        "review_export_format_label": "Formaat:",
        "review_export_format_folders": "Gidse",
        "review_export_format_zip": "Zip-lêers",
        "review_progress_format": "{current}/{total} prompts",
        "review_no_items_title": "Geen items",
        "review_no_items_scope": "Geen opnames vir die gekose reikwydte gevind nie.",
        "review_no_items_group": "Geen opnames om te groepeer nie.",
        "review_no_items_export": "Geen opnames om uit te voer nie.",
        "review_no_session_title": "Geen sessie",
        "review_no_session_msg": "Geen sessiedata om uit te voer nie.",
        "review_choose_save_sets": "Kies waar om stelle te stoor",
        "review_export_complete_title": "Uitvoer voltooi",
        "review_export_sets_complete_msg": "{n} stelle uitgevoer na:\n{dir}",
        "review_export_failed_title": "Uitvoer misluk",
        "review_export_sets_failed": "Kon nie stelle uitvoer nie:",
        "review_choose_save_report": "Kies waar om die verslag te stoor",
        "review_report_saved_msg": "Verslag gestoor in:",
        "review_export_report_failed": "Kon nie verslag uitvoer nie:",
        "review_session_complete_title": "Sessie voltooi",
        "review_session_complete_msg": "Hersieningsessie voltooi!",
        "review_summary_grade": "Graad",
        "review_summary_accuracy": "Akkuraatheid",
        "review_summary_avg_time": "Gem. tyd",
        "review_summary_composite": "Samestellingscore",
        "group_export_title": "Gegroepeerde Uitvoer",
        "group_export_info": "Voer {count} opgenomen items uit na georganiseerde groepgidse.",
        "group_export_items_per_folder": "Items per gids:",
        "group_export_num_folders": "Aantal gidse:",
        "group_export_preview_none": "Geen items om uit te voer nie.",
        "group_export_preview_will_create": "Sal {n} gids(e) skep:\n",
        "group_export_preview_group_line": "  Groep {i:02d}: {count} items\n",
        "group_export_preview_more": "  ... en {extra} meer gidse\n",
        "group_export_preview_last_note": "\nLet wel: Laaste gids het {count} items (oorblyfsel).",
        "group_export_copy_mode": "Kopieer lêers (verstek, veilig)",
        "group_export_copy_mode_tip": "Untick om lêers te skuif (gebruik versigtig)",
        "group_export_export_btn": "Voer uit...",
        "group_export_cancel_btn": "Kanselleer",
        "group_export_select_dir": "Kies Uitvoergids",
        "group_export_no_items_title": "Geen items",
        "group_export_no_items_msg": "Geen items om uit te voer nie.",
        "group_export_confirm_overwrite_title": "Bevestig Oorskryf",
        "group_export_confirm_overwrite_msg": "Die geselekteerde gids bevat reeds {n} Groep-gids(e).\n\nBestaande lêers kan oorskryf word. Voortgaan?",
        "group_export_complete_title": "Uitvoer voltooi",
        "group_export_complete_msg": "{items} items suksesvol uitgevoer na {groups} gidse.",
        "group_export_failed_title": "Uitvoer misluk",
        "group_export_failed_msg": "Uitvoer het misluk:",
    },
}

# Prefer labels from external builtin module; replace embedded dict at runtime
try:
    from vat.i18n.builtin_labels import LABELS_ALL as _EXTERNAL_LABELS_ALL
    if isinstance(_EXTERNAL_LABELS_ALL, dict) and _EXTERNAL_LABELS_ALL:
        # Replace any in-file labels with the builtin set to reduce duplication
        globals()['LABELS_ALL'] = dict(_EXTERNAL_LABELS_ALL)
    else:
        raise ValueError("Empty builtin labels")
except Exception:
    # Minimal English fallback to keep UI running if builtin labels fail to load
    globals()['LABELS_ALL'] = {
        "English": {
            "language_name": "English",
            "app_title": "Visual Stimulus Kit Tool",
            "select_folder": "Select Folder",
            "images_tab_title": "Images",
            "videos_tab_title": "Videos",
            "video_fullscreen_tip": "<b>Tip:</b> Double-click the video to open fullscreen. Use <b>+</b> and <b>-</b> to zoom in/out in fullscreen view.",
            "image_fullscreen_tip": "<b>Tip:</b> Double-click an image to open fullscreen. Use <b>+</b> and <b>-</b> to zoom in/out in fullscreen view.",
            "image_show_filenames": "Show filenames",
            "welcome_dialog_title": "Welcome to the Visual Stimulus Kit Tool",
            "welcome_dialog_body_html": (
                "<p><b>Welcome!</b> This tool helps you collect clear, well-organised "
                "examples of how people speak in minority and under-documented languages.</p>"
            ),
            "review_tab_title": "Review",
            "review_tip_html": "<b>Tip:</b> Single-click selects. Right-click, Ctrl/Cmd+Click, or Enter confirms. Double-click opens preview/fullscreen. Press Space to replay prompt.",
            "time_label_prefix": "Time: ",
            "review_start": "Start Review",
            "review_pause": "Pause",
            "review_resume": "Resume",
            "review_stop": "Stop",
            "review_replay": "Replay",
            "review_set_name_placeholder": "Set name",
            "review_show_settings": "Show settings",
            "review_hide_settings": "Hide settings",
            "review_help_link": "GPA Review Guide",
            "review_scope_label": "Scope:",
            "review_scope_images": "Images",
            "review_scope_videos": "Videos",
            "review_scope_both": "Both",
            "review_play_count_label": "Play Count:",
            "review_time_limit_label": "Time Limit (sec):",
            "review_time_limit_off": "Off",
            "review_limit_mode_label": "Limit Mode:",
            "review_limit_soft": "Soft",
            "review_limit_hard": "Hard",
            "review_sfx_label": "Sound Effects",
            "review_sfx_vol_label": "SFX Vol:",
            "review_sfx_tone_label": "SFX Tone:",
            "review_sfx_tone_default": "Default",
            "review_sfx_tone_gentle": "Gentle",
            "review_time_weight_label": "Time Weight %:",
            "review_ui_overhead_label": "UI Overhead (ms):",
            "review_thumb_size_label": "Thumb Size:",
            "review_items_per_session_label": "Items per Session:",
            "review_sessions_label_initial": "Sessions: --",
            "review_sessions_label_format": "Sessions: {sessions}  |  Items/session: {per}  |  Last: {last_items}",
            "review_reset": "Reset",
            "review_reset_defaults": "Reset to Defaults",
            "review_export_results": "Export Results",
            "review_export_sets": "Export Sets",
            "review_export_format_label": "Format:",
            "review_export_format_folders": "Folders",
            "review_export_format_zip": "Zip files",
            "review_progress_format": "{current}/{total} prompts",
            "review_no_items_title": "No Items",
            "review_no_items_scope": "No recorded items found for the selected scope.",
            "review_no_items_group": "No recorded items to group.",
            "review_no_items_export": "No recorded items to export.",
            "review_no_session_title": "No Session",
            "review_no_session_msg": "No session data to export.",
            "group_export_title": "Grouped Export",
            "group_export_info": "Export {count} recorded items into organized group folders.",
            "group_export_items_per_folder": "Items per folder:",
            "group_export_num_folders": "Number of folders:",
            "group_export_copy_mode": "Copy files (default, safe)",
            "group_export_copy_mode_tip": "Uncheck to move files instead (use with caution)",
            "group_export_export_btn": "Export...",
            "group_export_cancel_btn": "Cancel",
            "group_export_preview_none": "No items to export.",
            "group_export_preview_will_create": "Will create {n} folder(s):\n",
            "group_export_preview_group_line": "  Group {i:02d}: {count} items\n",
            "group_export_preview_more": "  ... and {extra} more folders\n",
            "group_export_preview_last_note": "\nNote: Last folder has {count} items (remainder).",
            "group_export_no_items_title": "No Items",
            "group_export_no_items_msg": "No items to export.",
            "group_export_select_dir": "Select Export Directory",
            "group_export_confirm_overwrite_title": "Confirm Overwrite",
            "group_export_confirm_overwrite_msg": "The selected directory already contains {n} Group folder(s).\n\nExisting files may be overwritten. Continue?",
            "group_export_complete_title": "Export Complete",
            "group_export_complete_msg": "Successfully exported {items} items into {groups} folders.",
            "group_export_failed_title": "Export Failed",
            "group_export_failed_msg": "Failed to export:",
        }
    }

# Optional external labels overlay support (YAML or JSON). This lets us
# keep LABELS_ALL out of the main UI file for easier maintenance.
def _deep_merge_labels(base: dict, overlay: dict) -> dict:
    try:
        for lang, labels in overlay.items():
            if lang not in base or not isinstance(base.get(lang), dict):
                base[lang] = labels
                continue
            b = base[lang]
            if isinstance(labels, dict):
                for k, v in labels.items():
                    b[k] = v
    except Exception:
        pass
    return base

def _load_external_labels_overlay() -> None:
    try:
        import os, json
        try:
            import yaml
        except Exception:
            yaml = None
        from vat.utils.resources import resource_path
        # Prefer YAML, then JSON
        yaml_path = resource_path(os.path.join("i18n", "labels.yaml"), check_system=False)
        json_path = resource_path(os.path.join("i18n", "labels.json"), check_system=False)
        loaded = None
        if yaml and os.path.exists(yaml_path):
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    loaded = yaml.safe_load(f)
            except Exception:
                loaded = None
        elif os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
            except Exception:
                loaded = None
        if isinstance(loaded, dict) and loaded:
            # Deep-merge overlay onto built-ins
            globals()['LABELS_ALL'] = _deep_merge_labels(LABELS_ALL, loaded)
    except Exception:
        # Non-fatal if external labels cannot be loaded
        pass

# Attempt to load external overlay at import-time
_load_external_labels_overlay()

class VideoAnnotationApp(QMainWindow):
    ui_info = Signal(str, str)
    ui_warning = Signal(str, str)
    ui_error = Signal(str, str)
    def __init__(self):
        super().__init__()
        # Default language; may be overridden by settings or system locale
        self.language = "English"
        self.LABELS = LABELS_ALL[self.language]
        # Unified file-system access
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
        # Persistent audio thread used for all playback
        self.audio_thread = QThread(self)
        self.audio_worker = None
        # Unified audio playback state + debounce
        self.is_playing_audio = False
        self._last_play_request_ts = 0.0
        self.is_recording = False
        self.recording_thread = None
        self.recording_worker = None
        self.join_thread = None
        self.join_worker = None
        self._suppress_item_changed = False
        # Cache for full-resolution image pixmaps (used by thumbnails and fullscreen)
        self._image_pixmap_cache = {}
        # Fullscreen viewer state
        self._fullscreen_viewer = None
        self.fullscreen_zoom = None
        self._ui_ready = False
        # Connect FS manager signals
        try:
            self.fs.folderChanged.connect(self._on_folder_changed)
            self.fs.videosUpdated.connect(self._on_videos_updated)
            self.fs.imagesUpdated.connect(self._on_images_updated)
        except Exception:
            pass
        self.load_settings()
        self.init_ui()
        self.setWindowTitle(self.LABELS["app_title"])
        # More compact default window size; adapt to screen width
        try:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            avail = screen.availableGeometry() if screen else None
            if avail:
                # Aim for ~70% of screen width with a hard upper cap
                target_w = max(720, min(int(avail.width() * 0.70), 1200))
                target_h = min(680, avail.height())
                self.resize(target_w, target_h)
                # Prevent initial over-expansion beyond target width
                try:
                    self.setMaximumWidth(target_w)
                    self.setFixedWidth(target_w)
                except Exception:
                    pass
                # Adjust splitter sizes proportionally to target width
                try:
                    if hasattr(self, 'main_splitter'):
                        sizes = self.main_splitter.sizes()
                        # Respect collapsed default: only adjust if left is visible
                        if sizes and sizes[0] > 0:
                            left = max(160, int(target_w * 0.26))
                            right = max(1, target_w - left)
                            self.main_splitter.setSizes([left, right])
                            self._splitter_prev_sizes = [left, right]
                except Exception:
                    pass
                try:
                    logging.info(f"UI.window: screen_w={avail.width()}, target_w={target_w}, final_w={self.size().width()}, splitter_sizes={getattr(self, 'main_splitter').sizes() if hasattr(self, 'main_splitter') else 'n/a'}")
                except Exception:
                    pass
                # Enforce width cap again after initial layout to avoid expansion
                try:
                    QTimer.singleShot(0, self._enforce_window_width_cap)
                except Exception:
                    pass
            else:
                # Fallback if screen info unavailable
                self.resize(840, 680)
                try:
                    logging.info(f"UI.window: no screen info; final_w={self.size().width()}")
                except Exception:
                    pass
        except Exception:
            self.resize(840, 680)
            try:
                logging.info(f"UI.window: sizing exception; final_w={self.size().width()}")
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
            # Drawer toggle shortcut: Ctrl+D and Cmd+D (Meta+D on macOS)
            self._shortcut_drawer_ctrl = QShortcut(QKeySequence("Ctrl+D"), self)
            self._shortcut_drawer_ctrl.activated.connect(self._toggle_drawer)
            self._shortcut_drawer_meta = QShortcut(QKeySequence("Meta+D"), self)
            self._shortcut_drawer_meta.activated.connect(self._toggle_drawer)
        except Exception:
            pass

    def _is_dark_mode(self) -> bool:
        """Detect whether the OS/app is currently using a dark color scheme."""
        try:
            from PySide6.QtGui import QGuiApplication, QPalette
            hints = QGuiApplication.styleHints()
            # Qt 6+ provides a color scheme hint
            if hasattr(hints, 'colorScheme'):
                return hints.colorScheme() == Qt.ColorScheme.Dark
            # Fallback: infer from window color lightness
            pal = QGuiApplication.palette()
            base = pal.color(QPalette.Window)
            return base.lightness() < 128
        except Exception:
            return False

    def _apply_theme_styles(self) -> None:
        """Apply theme-aware styles to overlay drawer and scrim."""
        try:
            dark = self._is_dark_mode()
            # Drawer background and border adapt to theme
            if getattr(self, 'drawer_layer', None) is not None:
                bg = 'rgba(32,32,32,0.92)' if dark else 'rgba(248,248,248,0.95)'
                border = '#555' if dark else '#ccc'
                self.drawer_layer.setStyleSheet(f"#drawer_layer {{ background-color: {bg}; border-right: 1px solid {border}; }}")
            # Scrim: slightly stronger in dark mode
            if getattr(self, 'drawer_scrim', None) is not None:
                alpha = 0.25 if dark else 0.15
                self.drawer_scrim.setStyleSheet(f"background-color: rgba(0,0,0,{alpha});")
            # Icons should adapt to theme as well
            self._apply_theme_icons()
        except Exception:
            pass

    def changeEvent(self, event):
        """React to palette/theme changes (e.g., macOS auto dark mode)."""
        try:
            if event.type() in (QEvent.PaletteChange, QEvent.ApplicationPaletteChange, QEvent.StyleChange):
                self._apply_theme_styles()
        except Exception:
            pass
        return super().changeEvent(event)

    def _apply_theme_icons(self) -> None:
        """Update button icons to ensure sufficient contrast in current theme."""
        try:
            # Drawer: regenerate hamburger icon with palette-derived color
            if getattr(self, 'drawer_toggle_btn', None) is not None:
                self.drawer_toggle_btn.setIcon(self._hamburger_icon())
            # Prev/Next: re-fetch standard icons so the style supplies theme-appropriate glyphs
            if getattr(self, 'prev_button', None) is not None:
                try:
                    self.prev_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
                except Exception:
                    pass
            if getattr(self, 'next_button', None) is not None:
                try:
                    self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
                except Exception:
                    pass
        except Exception:
            pass
        # Start persistent audio thread
        try:
            if self.audio_thread and not self.audio_thread.isRunning():
                self.audio_thread.start()
                logging.info("UI.audio: persistent audio thread started")
        except Exception:
            pass

        def _enforce_window_width_cap(self):
            """Enforce a hard maximum width after layouts settle.

            Prevents child widgets with Expanding policies from widening the
            main window beyond our desired cap.
            """
            try:
                from PySide6.QtGui import QGuiApplication
                screen = QGuiApplication.primaryScreen()
                avail = screen.availableGeometry() if screen else None
                if avail:
                    # Cap aligned with target: ~70% of screen, max 1200px
                    cap_w = max(720, min(int(avail.width() * 0.70), 1200))
                else:
                    cap_w = 840
                # Apply cap
                try:
                    self.setMaximumWidth(cap_w)
                    # Also set a fixed width to prevent Expanding children widening the window
                    self.setFixedWidth(cap_w)
                except Exception:
                    pass
                if self.width() > cap_w:
                    self.resize(cap_w, self.height())
                # Keep splitter aligned only if left panel is visible
                try:
                    if hasattr(self, 'main_splitter'):
                        sizes = self.main_splitter.sizes()
                        if sizes and sizes[0] > 0:
                            left = max(180, int(cap_w * 0.26))
                            right = max(1, cap_w - left)
                            self.main_splitter.setSizes([left, right])
                except Exception:
                    pass
                try:
                    logging.info(f"UI.window.cap: applied cap_w={cap_w}, final_w={self.size().width()}")
                except Exception:
                    pass
            except Exception:
                # Best effort only; avoid crashing UI
                pass

        def showEvent(self, event):
            try:
                super().showEvent(event)
            except Exception:
                pass
            # Enforce width immediately on show
            try:
                self._enforce_window_width_cap()
            except Exception:
                pass
            # Ensure drawer starts collapsed
            try:
                if hasattr(self, 'main_splitter'):
                    sizes = self.main_splitter.sizes()
                    total = sum(sizes) if sizes else self.width()
                    self.main_splitter.setSizes([0, max(1, total)])
                    self.drawer_toggle_btn.setToolTip(self.LABELS.get("drawer_show", "Show drawer"))
            except Exception:
                pass

        def resizeEvent(self, event):
            try:
                super().resizeEvent(event)
            except Exception:
                pass
            # Clamp width on any resize to avoid expansion (e.g., due to content policies)
            try:
                self._enforce_window_width_cap()
            except Exception:
                pass
            # Keep drawer and scrim geometry in sync on resize
            try:
                if getattr(self, 'drawer_layer', None) is not None and self.drawer_layer.isVisible():
                    self._position_drawer()
            except Exception:
                pass
        self.ui_info.connect(self._show_info)
        self.ui_warning.connect(self._show_warning)
        self.ui_error.connect(self._show_error)
        if self.fs.current_folder:
            self.update_folder_display()
            self.export_wavs_button.setEnabled(True)
            self.clear_wavs_button.setEnabled(True)
            self.import_wavs_button.setEnabled(True)
            self.join_wavs_button.setEnabled(True)
            self.open_ocenaudio_button.setEnabled(True)
            if getattr(self, 'edit_metadata_btn', None):
                self.edit_metadata_btn.setEnabled(True)
            # Populate via signal with current FS folder
            try:
                self._on_folder_changed(self.fs.current_folder)
                self._on_videos_updated(self.fs.list_videos())
            except Exception:
                self.load_video_files()
            # Do not auto-open metadata; use the button
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
    def _on_folder_changed(self, path: str):
        try:
            if getattr(self, '_ui_ready', False):
                logging.info(f"UI._on_folder_changed: path={path}")
                self.update_folder_display()
                # Populate images directly from the active FS folder to ensure sync
                try:
                    active = self.fs.current_folder or ""
                    imgs = self.fs.list_images(active)
                    logging.info(f"UI._on_folder_changed: active={active}; images_count={len(imgs)}; sample={[os.path.basename(f) for f in imgs[:3]]}")
                    self._populate_images_list(imgs)
                except Exception as e:
                    logging.warning(f"UI._on_folder_changed: failed to list/populate images: {e}")
        except Exception:
            pass
    def _on_videos_updated(self, files: list):
        # Populate listbox and internal state from FS manager update
        try:
            self.video_files = list(files)
            if not getattr(self, '_ui_ready', False) or getattr(self, 'video_listbox', None) is None:
                return
            self.video_listbox.clear()
            basenames = [os.path.basename(vp) for vp in self.video_files]
            for name in basenames:
                item = QListWidgetItem(name)
                wav_exists = os.path.exists(self.fs.wav_path_for(name))
                item.setIcon(self._check_icon if wav_exists else self._empty_icon)
                self.video_listbox.addItem(item)
            if self.last_video_name and self.last_video_name in basenames:
                idx = basenames.index(self.last_video_name)
                self.video_listbox.setCurrentRow(idx)
            elif basenames:
                # Auto-select the first video on folder change
                self.video_listbox.setCurrentRow(0)
            if not self.video_files:
                QMessageBox.information(self, self.LABELS["no_videos_found"], f"{self.LABELS['no_videos_found']} {self.fs.current_folder}")
        except Exception as e:
            logging.warning(f"Failed to refresh videos from FS manager: {e}")
        self.update_media_controls()
        self.update_video_file_checks()
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        # Keep layout tight but ensure a small top margin
        try:
            main_layout.setSpacing(0)
            # Increase top margin to prevent overlap under titlebar
            main_layout.setContentsMargins(8, 14, 8, 6)
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
        # Remove extra margins/padding in the header controls
        try:
            self.language_dropdown.setStyleSheet("margin:0px; padding:0px;")
            self.language_dropdown.setFixedHeight(28)
            # Ensure the dropdown popup list has an opaque background so
            # language names are readable even if parent widgets use
            # transparent backgrounds or custom stylesheets.
            try:
                view = self.language_dropdown.view()
                view.setStyleSheet("background-color: palette(base); color: palette(text);")
            except Exception:
                # If anything goes wrong here, we still want the app to start.
                pass
        except Exception:
            pass
        # Language dropdown will be placed in the header row next to the folder label
        # Folder label + drawer toggle row
        self.folder_display_label = QLabel(self.LABELS["no_folder_selected"])
        self.folder_display_label.setAlignment(Qt.AlignLeft)
        self.folder_display_label.setToolTip("")
        try:
            self.folder_display_label.setMargin(0)
            self.folder_display_label.setStyleSheet("margin:0px; padding:0px;")
            self.folder_display_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        except Exception:
            pass
        header_row = QHBoxLayout()
        # Drawer toggle button (top-left)
        self.drawer_toggle_btn = QToolButton()
        try:
            self.drawer_toggle_btn.setToolTip(self.LABELS.get("drawer_show", "Show drawer"))
            # Use a custom hamburger icon (three horizontal lines)
            try:
                self.drawer_toggle_btn.setIcon(self._hamburger_icon())
            except Exception:
                self.drawer_toggle_btn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMenuButton))
            self.drawer_toggle_btn.setFixedSize(28, 28)
            self.drawer_toggle_btn.setAutoRaise(True)
            self.drawer_toggle_btn.clicked.connect(self._toggle_drawer)
        except Exception:
            pass
        header_row.addWidget(self.drawer_toggle_btn)
        # Small spacing between hamburger and folder name
        try:
            header_row.addSpacing(8)
        except Exception:
            pass
        # Folder label follows the drawer button on the left
        header_row.addWidget(self.folder_display_label)

        # Push the language dropdown to the right edge on the same line
        try:
            header_row.addStretch(1)
        except Exception:
            pass
        header_row.addWidget(self.language_dropdown)
        main_layout.addLayout(header_row)
        splitter = QSplitter(Qt.Horizontal)
        try:
            splitter.setContentsMargins(0, 0, 0, 0)
        except Exception:
            pass
        self.main_splitter = splitter
        self._splitter_prev_sizes = [240, 600]
        main_layout.addWidget(splitter)
        # Build left panel content (will live inside an overlay drawer)
        left_panel = QWidget()
        self.left_panel = left_panel
        left_layout = QVBoxLayout(left_panel)
        try:
            left_layout.setContentsMargins(8, 8, 8, 8)
            left_layout.setSpacing(8)
        except Exception:
            pass
        self.select_button = QPushButton(self.LABELS["select_folder"])
        self.select_button.clicked.connect(self.select_folder)
        try:
            self.select_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.select_button.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.select_button)
        self.open_ocenaudio_button = QPushButton(self.LABELS["open_ocenaudio"])
        self.open_ocenaudio_button.clicked.connect(self.open_in_ocenaudio)
        self.open_ocenaudio_button.setEnabled(False)
        try:
            self.open_ocenaudio_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.open_ocenaudio_button.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.open_ocenaudio_button)
        self.export_wavs_button = QPushButton(self.LABELS["export_wavs"])
        self.export_wavs_button.clicked.connect(self.export_wavs)
        self.export_wavs_button.setEnabled(False)
        try:
            self.export_wavs_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.export_wavs_button.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.export_wavs_button)
        self.clear_wavs_button = QPushButton(self.LABELS["clear_wavs"])
        self.clear_wavs_button.clicked.connect(self.clear_wavs)
        self.clear_wavs_button.setEnabled(False)
        try:
            self.clear_wavs_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.clear_wavs_button.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.clear_wavs_button)
        self.import_wavs_button = QPushButton(self.LABELS["import_wavs"])
        self.import_wavs_button.clicked.connect(self.import_wavs)
        self.import_wavs_button.setEnabled(False)
        try:
            self.import_wavs_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.import_wavs_button.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.import_wavs_button)
        self.join_wavs_button = QPushButton(self.LABELS["join_wavs"])
        self.join_wavs_button.clicked.connect(self.join_all_wavs)
        self.join_wavs_button.setEnabled(False)
        try:
            self.join_wavs_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.join_wavs_button.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.join_wavs_button)
        self.video_listbox = QListWidget()
        try:
            self.video_listbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        except Exception:
            pass
        # Videos context menu and Ctrl+C to copy video file URL
        try:
            self.video_listbox.setContextMenuPolicy(Qt.CustomContextMenu)
            self.video_listbox.customContextMenuRequested.connect(self._on_videos_context_menu)
            self.copy_video_shortcut = QShortcut(QKeySequence.Copy, self.video_listbox)
            self.copy_video_shortcut.activated.connect(self._copy_current_video_to_clipboard)
        except Exception:
            pass
        self.video_listbox.currentRowChanged.connect(self.on_video_select)
        left_layout.addWidget(self.video_listbox)
        # Replace inline metadata editor with a single button
        self.edit_metadata_btn = QPushButton(self.LABELS["edit_metadata"])
        self.edit_metadata_btn.clicked.connect(self.open_metadata_dialog)
        self.edit_metadata_btn.setEnabled(False)
        try:
            self.edit_metadata_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.edit_metadata_btn.setMinimumHeight(30)
        except Exception:
            pass
        left_layout.addWidget(self.edit_metadata_btn)
        # Drawer overlay (appears over UI instead of resizing splitter)
        try:
            self.drawer_layer = QWidget(central_widget)
            self.drawer_layer.setVisible(False)
            self.drawer_layer.setAttribute(Qt.WA_StyledBackground, True)
            # Targeted style on the drawer container only to avoid affecting child controls
            self.drawer_layer.setObjectName("drawer_layer")
            # Initial style; will be updated by _apply_theme_styles()
            self._apply_theme_styles()
            dl = QVBoxLayout(self.drawer_layer)
            dl.setContentsMargins(8, 8, 8, 8)
            dl.setSpacing(6)
            dl.addWidget(left_panel)
            # Ensure child buttons use native style (clear any inherited QSS side-effects)
            try:
                for btn in (
                    self.select_button,
                    self.open_ocenaudio_button,
                    self.export_wavs_button,
                    self.clear_wavs_button,
                    self.import_wavs_button,
                    self.join_wavs_button,
                    self.edit_metadata_btn,
                ):
                    btn.setStyleSheet("")
                    btn.setAutoDefault(False)
            except Exception:
                pass
            # Subtle shadow for visual depth
            try:
                shadow = QGraphicsDropShadowEffect(self.drawer_layer)
                shadow.setBlurRadius(16)
                shadow.setOffset(0, 0)
                shadow.setColor(QColor(0, 0, 0, 80))
                self.drawer_layer.setGraphicsEffect(shadow)
            except Exception:
                pass
            # Background scrim to dim UI and capture clicks to close
            self.drawer_scrim = QWidget(central_widget)
            self.drawer_scrim.setVisible(False)
            self.drawer_scrim.setAttribute(Qt.WA_StyledBackground, True)
            # Initial style; will be updated by _apply_theme_styles()
            self._apply_theme_styles()
            self.drawer_scrim.installEventFilter(self)
        except Exception:
            self.drawer_layer = None
            self.drawer_scrim = None
        # Placeholder on the splitter's left, to keep API stable
        self._drawer_placeholder = QWidget()
        try:
            self._drawer_placeholder.setMinimumWidth(0)
        except Exception:
            pass
        splitter.addWidget(self._drawer_placeholder)
        right_panel = QTabWidget()
        self.right_panel = right_panel
        videos_tab = QWidget()
        videos_layout = QVBoxLayout(videos_tab)
        # Tip for fullscreen video
        self.video_fullscreen_tip = QLabel(
            self.LABELS.get(
                "video_fullscreen_tip",
                LABELS_ALL["English"]["video_fullscreen_tip"],
            )
        )
        self.video_fullscreen_tip.setStyleSheet("color: black; font-size: 13px; margin-bottom: 4px;")
        self.video_fullscreen_tip.setWordWrap(True)
        videos_layout.addWidget(self.video_fullscreen_tip)
        self.video_label = QLabel(self.LABELS["video_listbox_no_video"])
        self.video_label.setAlignment(Qt.AlignCenter)
        # More compact default size for smaller screens; allow expanding
        self.video_label.setMinimumSize(480, 360)
        # Avoid cropping: do not auto-stretch, we will scale pixmaps ourselves
        try:
            self.video_label.setScaledContents(False)
        except Exception:
            pass
        try:
            self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
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
        self.prev_button = QToolButton()
        try:
            self.prev_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        except Exception:
            self.prev_button.setText("◀")
        self.prev_button.setToolTip(self.LABELS.get("prev_video_tip", "Previous video"))
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
        self.next_button.setToolTip(self.LABELS.get("next_video_tip", "Next video"))
        self.next_button.clicked.connect(self.go_next)
        video_controls_layout.addWidget(self.next_button)
        videos_layout.addLayout(video_controls_layout)
        audio_controls_layout = QHBoxLayout()
        try:
            audio_controls_layout.setSpacing(8)
        except Exception:
            pass
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
        # Add audio dropdown (From file / Paste from clipboard)
        self.add_audio_button = QToolButton()
        self.add_audio_button.setText(self.LABELS.get("add_existing_audio", "Add audio…"))
        try:
            self.add_audio_button.setPopupMode(QToolButton.InstantPopup)
        except Exception:
            pass
        self.add_audio_button.setEnabled(False)
        add_menu = QMenu(self)
        act_file = QAction(self.LABELS.get("add_audio_from_file", "From file…"), self)
        act_file.triggered.connect(self._handle_add_existing_audio_video)
        add_menu.addAction(act_file)
        act_clip = QAction(self.LABELS.get("add_audio_paste_clipboard", "Paste from clipboard"), self)
        act_clip.triggered.connect(self._handle_paste_audio_video)
        add_menu.addAction(act_clip)
        self.add_audio_button.setMenu(add_menu)
        audio_controls_layout.addWidget(self.add_audio_button)
        self.recording_status_label = QLabel("")
        self.recording_status_label.setStyleSheet("color: red; font-weight: bold;")
        audio_controls_layout.addWidget(self.recording_status_label)
        audio_controls_layout.addStretch(1)
        videos_layout.addLayout(audio_controls_layout)
        videos_layout.addStretch()
        right_panel.addTab(videos_tab, self.LABELS["videos_tab_title"])
        # Images tab
        images_tab = QWidget()
        images_layout = QVBoxLayout(images_tab)
        try:
            images_layout.setContentsMargins(0, 0, 0, 0)
            images_layout.setSpacing(6)
        except Exception:
            pass
        try:
            logging.info("UI.init_ui: creating Images tab")
        except Exception:
            pass
        # Banner: two columns, left = preview, right = controls+tip
        image_banner = QHBoxLayout()
        try:
            image_banner.setSpacing(8)
            image_banner.setContentsMargins(0, 0, 0, 0)
        except Exception:
            pass
        self.image_thumb = QLabel()
        try:
            self.image_thumb.setFixedSize(96, 72)
            self.image_thumb.setStyleSheet("background-color: black; color: white; border: 1px solid #333;")
        except Exception:
            pass
        image_banner.addWidget(self.image_thumb)
        # Right cell: controls and tip stacked vertically
        # (QVBoxLayout, QHBoxLayout, QCheckBox are already imported at the top)
        controls_and_tip = QVBoxLayout()
        controls_row = QHBoxLayout()
        # Always show Show filenames toggle above controls
        self.show_image_labels = False
        self.image_labels_toggle = QCheckBox(
            self.LABELS.get(
                "image_show_filenames",
                LABELS_ALL["English"]["image_show_filenames"],
            )
        )
        self.image_labels_toggle.setChecked(self.show_image_labels)
        self.image_labels_toggle.toggled.connect(self._toggle_image_labels)
        controls_and_tip.addWidget(self.image_labels_toggle)
        # Controls row (audio/record buttons)
        self.play_image_audio_button = QPushButton(self.LABELS.get("play_audio", "Play Audio"))
        self.play_image_audio_button.clicked.connect(self._handle_play_image_audio)
        self.play_image_audio_button.setEnabled(False)
        controls_row.addWidget(self.play_image_audio_button)
        self.stop_image_audio_button = QPushButton(self.LABELS.get("stop_audio", "Stop Audio"))
        self.stop_image_audio_button.clicked.connect(self._handle_stop_image_audio)
        self.stop_image_audio_button.setEnabled(False)
        controls_row.addWidget(self.stop_image_audio_button)
        self.record_image_button = QPushButton(self.LABELS.get("record_audio", "Record Audio"))
        self.record_image_button.clicked.connect(self._handle_record_image)
        self.record_image_button.setEnabled(False)
        controls_row.addWidget(self.record_image_button)
        # Add audio dropdown (From file / Paste from clipboard)
        self.add_image_audio_button = QToolButton()
        self.add_image_audio_button.setText(self.LABELS.get("add_existing_audio", "Add audio…"))
        try:
            self.add_image_audio_button.setPopupMode(QToolButton.InstantPopup)
        except Exception:
            pass
        self.add_image_audio_button.setEnabled(False)
        add_img_menu = QMenu(self)
        act_img_file = QAction(self.LABELS.get("add_audio_from_file", "From file…"), self)
        act_img_file.triggered.connect(self._handle_add_existing_audio_image)
        add_img_menu.addAction(act_img_file)
        act_img_clip = QAction(self.LABELS.get("add_audio_paste_clipboard", "Paste from clipboard"), self)
        act_img_clip.triggered.connect(self._handle_paste_audio_image)
        add_img_menu.addAction(act_img_clip)
        self.add_image_audio_button.setMenu(add_img_menu)
        controls_row.addWidget(self.add_image_audio_button)
        self.stop_image_record_button = QPushButton(self.LABELS.get("stop_recording", "Stop Recording"))
        self.stop_image_record_button.clicked.connect(self._handle_stop_image_record)
        self.stop_image_record_button.setEnabled(False)
        controls_row.addWidget(self.stop_image_record_button)
        controls_row.addStretch(1)
        controls_and_tip.addLayout(controls_row)
        # Tip below controls
        self.image_fullscreen_tip = QLabel(
            self.LABELS.get(
                "image_fullscreen_tip",
                LABELS_ALL["English"]["image_fullscreen_tip"],
            )
        )
        self.image_fullscreen_tip.setStyleSheet("color: black; font-size: 13px; margin: 4px 0 8px 0;")
        self.image_fullscreen_tip.setWordWrap(True)
        controls_and_tip.addWidget(self.image_fullscreen_tip)
        image_banner.addLayout(controls_and_tip)
        images_layout.addLayout(image_banner)
        # Thumbnail size slider
        try:
            thumb_row = QHBoxLayout()
            thumb_row.addWidget(QLabel("Thumb Size:"))
            self.images_thumb_slider = QSlider(Qt.Horizontal)
            self.images_thumb_slider.setRange(60, 180)  # percent
            self.images_thumb_slider.setValue(100)
            self.images_thumb_slider.setMaximumWidth(140)
            thumb_row.addWidget(self.images_thumb_slider)
            thumb_row.addStretch(1)
            images_layout.addLayout(thumb_row)
            self.images_thumb_scale = 1.0
            self.images_thumb_slider.valueChanged.connect(self._on_images_thumb_scale_changed)
        except Exception:
            self.images_thumb_scale = 1.0
        # Grid of thumbnails
        self.images_list = QListWidget()
        try:
            self.images_list.setViewMode(QListView.IconMode)
            # Ensure Adjust mode is set from QListView enum
            self.images_list.setResizeMode(QListView.Adjust)
            # Fill rows left-to-right to avoid a single tall column
            self.images_list.setFlow(QListView.LeftToRight)
            # Initial placeholder sizes; smaller defaults for compact UI (recomputed adaptively)
            self.images_list.setIconSize(QSize(240, 180))
            self.images_list.setGridSize(QSize(260, 190))
            self.images_list.setSpacing(6)
            self.images_list.setMovement(QListView.Static)
            self.images_list.setWrapping(True)
            # Let items compute size per grid cell for better wrapping
            self.images_list.setUniformItemSizes(False)
            self.images_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.images_list.setSelectionMode(QListWidget.SingleSelection)
            self.images_list.setSelectionBehavior(QListWidget.SelectItems)
            logging.info("UI.init_ui: images_list ready (IconMode)")
        except Exception:
            pass
        # Context menu and Ctrl+C to copy image to clipboard
        try:
            self.images_list.setContextMenuPolicy(Qt.CustomContextMenu)
            self.images_list.customContextMenuRequested.connect(self._on_images_context_menu)
            self.copy_image_shortcut = QShortcut(QKeySequence.Copy, self.images_list)
            self.copy_image_shortcut.activated.connect(self._copy_current_image_to_clipboard)
        except Exception:
            pass
        # Install custom delegate to draw green border and check overlay for recorded images
        try:
            self.images_list.setItemDelegate(ImageGridDelegate(self.fs))
        except Exception:
            pass
        # Selection syncing: rely on current-item changes to avoid duplicate triggers
        try:
            self.images_list.currentItemChanged.connect(lambda *args: self._handle_image_selection())
        except Exception:
            pass
        self.images_list.itemDoubleClicked.connect(self._handle_open_fullscreen_image)
        # Warm the image cache for items that become visible as the user
        # scrolls the grid, so fullscreen opens don't pay a cold-start
        # decoding cost.
        try:
            vsb = self.images_list.verticalScrollBar()
            if vsb is not None:
                vsb.valueChanged.connect(lambda *_: self._preload_visible_images())
        except Exception:
            pass
        images_layout.addWidget(self.images_list)
        right_panel.addTab(images_tab, self.LABELS.get("images_tab_title", "Images"))
        
        # Review tab
        try:
            from vat import VERSION
            app_version = VERSION
        except Exception:
            app_version = "2.0.3"
        
        self.review_tab = ReviewTab(self.fs, app_version, self, labels=self.LABELS)
        right_panel.addTab(self.review_tab, self.LABELS.get("review_tab_title", "Review"))
        
        splitter.addWidget(right_panel)
        # Start with drawer collapsed; remember previous sizes for temporary expand
        splitter.setSizes([0, 600])
        self._splitter_prev_sizes = [240, 600]
        # Connect tab change to enable/disable video_listbox
        def _on_tab_changed(idx):
            # 0 = Videos, 1 = Images, 2 = Review (assume order)
            try:
                self.video_listbox.setEnabled(idx == 0)
            except Exception:
                pass
            # Keep drawer overlay position in sync
            try:
                self._position_drawer()
            except Exception:
                pass
        self.right_panel.currentChanged.connect(_on_tab_changed)
        # Set initial state
        _on_tab_changed(self.right_panel.currentIndex())
        # Keep images grid sizing in sync and defer initial compute
        try:
            self.images_list.installEventFilter(self)
            QTimer.singleShot(0, self._recompute_image_grid_sizes)
        except Exception:
            pass
        # Compute adaptive two-column sizing after layout
        try:
            self._recompute_image_grid_sizes()
        except Exception:
            pass
        # Mark UI as ready for FS signal handlers
        self._ui_ready = True
        # Populate images initially if a folder is already set
        if self.fs.current_folder:
            try:
                imgs = self.fs.list_images()
                self._on_images_updated(self.fs.current_folder, imgs)
            except Exception:
                pass
            # Also populate the videos list to avoid empty state on startup
            try:
                vids = self.fs.list_videos()
                self._on_videos_updated(vids)
            except Exception:
                try:
                    self.load_video_files()
                except Exception:
                    pass
        # Show a short welcome/best-practices message once on startup
        try:
            QTimer.singleShot(0, self._show_welcome_dialog)
        except Exception:
            pass
        # After the first population/layout pass, warm the cache for the
        # thumbnails that are actually visible.
        try:
            QTimer.singleShot(0, self._preload_visible_images)
        except Exception:
            pass

        # Collapse drawer on outside click
        try:
            central_widget.installEventFilter(self)
            self._central_widget = central_widget
        except Exception:
            pass
    def change_language(self, selected_name):
        for key, labels in LABELS_ALL.items():
            if labels["language_name"] == selected_name:
                self.language = key
                self.LABELS = LABELS_ALL[self.language]
                break
        self.setWindowTitle(self.LABELS["app_title"])
        # Update tab titles
        try:
            if getattr(self, 'right_panel', None) is not None:
                self.right_panel.setTabText(0, self.LABELS.get("videos_tab_title", "Videos"))
                self.right_panel.setTabText(1, self.LABELS.get("images_tab_title", "Images"))
                self.right_panel.setTabText(2, self.LABELS.get("review_tab_title", "Review"))
        except Exception:
            pass
        # Retranslate Review tab
        try:
            if getattr(self, 'review_tab', None) is not None:
                self.review_tab.retranslate(self.LABELS)
        except Exception:
            pass
        # Refresh other UI texts
        self.refresh_ui_texts()
        # Update dropdown/menu labels where created earlier
        try:
            if getattr(self, 'add_audio_button', None) is not None and self.add_audio_button.menu():
                self.add_audio_button.setText(self.LABELS.get("add_existing_audio", "Add audio…"))
                acts = self.add_audio_button.menu().actions()
                if len(acts) >= 2:
                    acts[0].setText(self.LABELS.get("add_audio_from_file", "From file…"))
                    acts[1].setText(self.LABELS.get("add_audio_paste_clipboard", "Paste from clipboard"))
        except Exception:
            pass
        self.save_settings()

    def _toggle_drawer(self):
        """Toggle the left drawer overlay visibility."""
        try:
            if getattr(self, 'drawer_layer', None) is None:
                return
            vis = self.drawer_layer.isVisible()
            if vis:
                self.drawer_layer.hide()
                try:
                    if getattr(self, 'drawer_scrim', None) is not None:
                        self.drawer_scrim.hide()
                except Exception:
                    pass
                try:
                    self.drawer_toggle_btn.setToolTip("Show drawer")
                except Exception:
                    pass
            else:
                self._position_drawer()
                # Show scrim behind drawer
                try:
                    if getattr(self, 'drawer_scrim', None) is not None:
                        self.drawer_scrim.show()
                        self.drawer_scrim.raise_()
                except Exception:
                    pass
                self.drawer_layer.show()
                self.drawer_layer.raise_()
                try:
                    self.drawer_toggle_btn.setToolTip("Hide drawer")
                except Exception:
                    pass
        except Exception:
            pass

    def _hamburger_icon(self):
        """Create a simple hamburger icon (three stacked lines)."""
        try:
            size = 24
            pm = QPixmap(size, size)
            pm.fill(Qt.transparent)
            from PySide6.QtGui import QPainter
            painter = QPainter(pm)
            try:
                painter.setRenderHint(QPainter.Antialiasing, True)
                # Derive stroke color from current palette for good contrast
                from PySide6.QtGui import QGuiApplication, QPalette
                pal = QGuiApplication.palette()
                stroke = pal.color(QPalette.ButtonText)
                pen = QPen(stroke)
                pen.setWidth(2)
                painter.setPen(pen)
                # Draw three lines
                y_positions = [6, 12, 18]
                for y in y_positions:
                    painter.drawLine(5, y, size - 5, y)
            finally:
                painter.end()
            return QIcon(pm)
        except Exception:
            return QIcon()

    def _position_drawer(self):
        """Position the drawer overlay anchored to the left inside the central widget."""
        try:
            if getattr(self, 'drawer_layer', None) is None:
                return
            cw = getattr(self, '_central_widget', None)
            if cw is None:
                return
            # Default drawer width: proportional to window, with sensible bounds
            dw = min(max(400, int(cw.width() * 0.40)), 600)
            # Compute top offset based on header row metrics
            try:
                # Use the lower edge of the highest header element
                lbl = getattr(self, 'folder_display_label', None)
                dd = getattr(self, 'language_dropdown', None)
                btn = getattr(self, 'drawer_toggle_btn', None)
                candidates = []
                for w in (lbl, dd, btn):
                    if w is not None:
                        p = w.mapTo(cw, QPoint(0, 0))
                        candidates.append(p.y() + w.height())
                header_bottom = max(candidates) if candidates else 50
                top_margin = header_bottom + 6
            except Exception:
                top_margin = 50
            h = cw.height() - top_margin
            h = max(200, h)
            self.drawer_layer.setGeometry(8, top_margin, dw, h)
            # Keep scrim covering the central widget
            try:
                if getattr(self, 'drawer_scrim', None) is not None:
                    # Leave header/hamburger clickable: scrim starts below header
                    self.drawer_scrim.setGeometry(0, top_margin, cw.width(), cw.height() - top_margin)
            except Exception:
                pass
        except Exception:
            pass

    def _on_images_thumb_scale_changed(self, value: int):
        try:
            self.images_thumb_scale = max(0.5, min(1.8, value / 100.0))
            self._recompute_image_grid_sizes()
            self.save_settings()
        except Exception:
            pass

    def eventFilter(self, obj, event):
        # Collapse drawer when clicking outside the drawer overlay
        try:
            target_central = getattr(self, '_central_widget', None)
            target_scrim = getattr(self, 'drawer_scrim', None)
            if obj is target_central or obj is target_scrim:
                if event.type() == QEvent.MouseButtonPress:
                    dl = getattr(self, 'drawer_layer', None)
                    if dl is not None and dl.isVisible():
                        # Map drawer geometry to the coordinate space of the clicked widget
                        top_left_in_obj = dl.mapTo(obj, QPoint(0, 0))
                        rect = QRect(top_left_in_obj, dl.size())
                        pos = event.position() if hasattr(event, 'position') else event.pos()
                        p = QPoint(int(pos.x()), int(pos.y()))
                        if not rect.contains(p):
                            dl.hide()
                            try:
                                if target_scrim is not None:
                                    target_scrim.hide()
                            except Exception:
                                pass
                            try:
                                self.drawer_toggle_btn.setToolTip("Show drawer")
                            except Exception:
                                pass
                            return True
        except Exception:
            pass
        try:
            return super().eventFilter(obj, event)
        except Exception:
            return False
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
        if getattr(self, 'edit_metadata_btn', None):
            self.edit_metadata_btn.setText(self.LABELS["edit_metadata"])
        if not self.current_video:
            self.video_label.setText(self.LABELS["video_listbox_no_video"])
        # Localized tips and checkbox labels
        try:
            if getattr(self, "video_fullscreen_tip", None) is not None:
                self.video_fullscreen_tip.setText(
                    self.LABELS.get(
                        "video_fullscreen_tip",
                        LABELS_ALL["English"]["video_fullscreen_tip"],
                    )
                )
        except Exception:
            pass
        try:
            if getattr(self, "image_fullscreen_tip", None) is not None:
                self.image_fullscreen_tip.setText(
                    self.LABELS.get(
                        "image_fullscreen_tip",
                        LABELS_ALL["English"]["image_fullscreen_tip"],
                    )
                )
        except Exception:
            pass
        try:
            if getattr(self, "image_labels_toggle", None) is not None:
                self.image_labels_toggle.setText(
                    self.LABELS.get(
                        "image_show_filenames",
                        LABELS_ALL["English"]["image_show_filenames"],
                    )
                )
        except Exception:
            pass
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
            settings = None
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
            if isinstance(settings, dict):
                self.ocenaudio_path = settings.get('ocenaudio_path')
                saved_lang = settings.get('language')
                if saved_lang and saved_lang in LABELS_ALL:
                    # Respect explicit user choice
                    self.language = saved_lang
                    self.LABELS = LABELS_ALL[self.language]
                last_folder = settings.get('last_folder')
                if last_folder and os.path.isdir(last_folder):
                    try:
                        self.fs.set_folder(last_folder)
                    except Exception:
                        pass
                last_video = settings.get('last_video')
                if last_video:
                    self.last_video_name = last_video
                # Persistent fullscreen zoom
                zoom = settings.get('fullscreen_zoom')
                if isinstance(zoom, (int, float)) and zoom > 0:
                    self.fullscreen_zoom = float(zoom)
                
                # Load review settings if review tab exists
                if hasattr(self, 'review_tab') and settings:
                    try:
                        self.review_tab.state.load_from_json(settings)
                        self.review_tab._sync_ui_from_state()
                    except Exception:
                        pass
                # Images thumbnail scale (persisted)
                try:
                    img_scale = settings.get('images_thumb_scale')
                    if isinstance(img_scale, (int, float)):
                        self.images_thumb_scale = max(0.5, min(1.8, float(img_scale)))
                        if hasattr(self, 'images_thumb_slider'):
                            self.images_thumb_slider.setValue(int(self.images_thumb_scale * 100))
                        self._recompute_image_grid_sizes()
                except Exception:
                    pass
            else:
                # No saved language preference: try to match system UI language
                try:
                    locale = QLocale.system()
                    # Prefer explicit language codes; fall back to language name
                    lang_name = locale.languageToString(locale.language())
                    lang_name = (lang_name or "").strip()
                    candidates = []
                    if lang_name:
                        candidates.append(lang_name)
                    ui_name = locale.name()  # e.g. "en_US"
                    if ui_name:
                        candidates.append(ui_name)
                    # Map common Qt language names / codes to our LABELS_ALL keys
                    def _match_language():
                        # Direct match on language_name
                        for key, labels in LABELS_ALL.items():
                            if labels.get("language_name") in candidates:
                                return key
                        # Simple heuristics for common locales
                        for c in candidates:
                            c_lower = c.lower()
                            if c_lower.startswith("en"):
                                return "English"
                            if c_lower.startswith("id") or "bahasa" in c_lower:
                                return "Bahasa Indonesia"
                            if c_lower.startswith("ko"):
                                return "한국어"
                            if c_lower.startswith("nl"):
                                return "Nederlands"
                            if c_lower.startswith("pt"):
                                return "Português (Brasil)"
                            if c_lower.startswith("es"):
                                return "Español (Latinoamérica)"
                            if c_lower.startswith("af"):
                                return "Afrikaans"
                        return None
                    matched = _match_language()
                    if matched and matched in LABELS_ALL:
                        self.language = matched
                        self.LABELS = LABELS_ALL[self.language]
                except Exception:
                    # On any failure, keep English defaults
                    pass
        except Exception as e:
            logging.warning(f"Failed to load settings: {e}")
    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            settings = {
                'ocenaudio_path': self.ocenaudio_path,
                'language': self.language,
                'last_folder': self.fs.current_folder,
                'last_video': self.current_video,
                # Persist the last used fullscreen zoom if set
                'fullscreen_zoom': self.fullscreen_zoom if isinstance(self.fullscreen_zoom, (int, float)) else None,
                'images_thumb_scale': getattr(self, 'images_thumb_scale', 1.0),
            }
            
            # Save review settings if review tab exists
            if hasattr(self, 'review_tab'):
                try:
                    self.review_tab._sync_state_from_ui()
                    settings = self.review_tab.state.save_to_json(settings)
                except Exception:
                    pass
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2, sort_keys=True)
        except Exception as e:
            logging.warning(f"Failed to save settings: {e}")
    def select_folder(self):
        initial_dir = self.fs.current_folder or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, self.LABELS["select_folder_dialog"], initial_dir)
        if folder:
            # Set via FS manager for unified state and signal refresh
            if not self.fs.set_folder(folder):
                QMessageBox.critical(self, self.LABELS["error_title"], self.LABELS["permission_denied_title"])
                return
            try:
                errors = self.fs.cleanup_hidden_files()
                if errors:
                    QMessageBox.warning(self, self.LABELS["cleanup_errors_title"], "Some hidden files could not be deleted:\n" + "\n".join(errors))
            except Exception:
                pass
            self.export_wavs_button.setEnabled(True)
            self.clear_wavs_button.setEnabled(True)
            self.import_wavs_button.setEnabled(True)
            self.join_wavs_button.setEnabled(True)
            self.open_ocenaudio_button.setEnabled(True)
            if getattr(self, 'edit_metadata_btn', None):
                self.edit_metadata_btn.setEnabled(True)
            self.save_settings()
            # Rely on FS signals (_on_folder_changed -> list_images -> imagesUpdated)
            try:
                logging.info(f"UI.select_folder: path={folder}")
            except Exception:
                pass
            # Populate immediately to prevent transient empty state
            try:
                self._on_folder_changed(folder)
            except Exception:
                pass
    def load_video_files(self):
        # Manual refresh using FS manager (in case signals are not available)
        self.video_listbox.clear()
        self.video_files = []
        if not self.fs.current_folder:
            QMessageBox.information(self, self.LABELS["no_folder_selected"], self.LABELS["no_folder_selected"])
            return
        try:
            self.video_files = self.fs.list_videos()
            self.video_files.sort()
            basenames = [os.path.basename(vp) for vp in self.video_files]
            for name in basenames:
                item = QListWidgetItem(name)
                wav_exists = os.path.exists(self.fs.wav_path_for(name))
                item.setIcon(self._check_icon if wav_exists else self._empty_icon)
                self.video_listbox.addItem(item)
            if self.last_video_name and self.last_video_name in basenames:
                idx = basenames.index(self.last_video_name)
                self.video_listbox.setCurrentRow(idx)
            elif basenames:
                # Auto-select first video to ensure player loads
                self.video_listbox.setCurrentRow(0)
            if not self.video_files:
                QMessageBox.information(self, self.LABELS["no_videos_found"], f"{self.LABELS['no_videos_found']} {self.fs.current_folder}")
        except FolderPermissionError:
            QMessageBox.critical(self, self.LABELS["permission_denied_title"], f"You do not have permission to access the folder: {self.fs.current_folder}")
        except FolderNotFoundError:
            QMessageBox.critical(self, self.LABELS["folder_not_found_title"], f"The selected folder no longer exists: {self.fs.current_folder}")
        except FolderAccessError as e:
            QMessageBox.critical(self, self.LABELS["unexpected_error_title"], f"An unexpected error occurred: {e}")
        except Exception as e:
            QMessageBox.critical(self, self.LABELS["unexpected_error_title"], f"An unexpected error occurred: {e}")
        if not self.video_files:
            self.current_video = None
        self.update_media_controls()
        self.update_video_file_checks()
    def open_metadata_dialog(self):
        if not self.fs.current_folder:
            return
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
        except Exception:
            QMessageBox.critical(self, self.LABELS["error_title"], "Unable to open metadata editor.")
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
        except FolderAccessError as e:
            QMessageBox.critical(self, self.LABELS["error_title"], f"Failed to load metadata: {e}")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(self.LABELS["edit_metadata"])
        layout = QVBoxLayout(dlg)
        editor = QTextEdit(dlg)
        editor.setPlainText(content)
        layout.addWidget(editor)
        btns = QHBoxLayout()
        save_btn = QPushButton(self.LABELS["save_metadata"], dlg)
        cancel_btn = QPushButton("Cancel", dlg)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        def _save_and_close():
            try:
                self.fs.write_metadata(editor.toPlainText())
                QMessageBox.information(dlg, self.LABELS["saved"], self.LABELS["metadata_saved"])
                dlg.accept()
            except Exception as e:
                QMessageBox.critical(dlg, self.LABELS["error_title"], f"Failed to save metadata: {e}")
        save_btn.clicked.connect(_save_and_close)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.resize(600, 400)
        dlg.exec()
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
    def _resolve_current_video_path(self) -> str:
        """Return full path for `self.current_video` by matching against `self.video_files`.
        Fallback to FS join if not found.
        """
        try:
            if self.current_video:
                for vp in self.video_files:
                    if os.path.basename(vp) == self.current_video:
                        return vp
                if self.fs.current_folder:
                    return os.path.join(self.fs.current_folder, self.current_video)
        except Exception:
            pass
        return ""
    def show_first_frame(self):
        if not self.current_video:
            self.video_label.setText(self.LABELS["video_listbox_no_video"])
            return
        video_path = self._resolve_current_video_path()
        if not (video_path and os.path.exists(video_path)):
            logging.warning(f"Cannot open video (path missing or inaccessible): {video_path}")
            self.video_label.setText("Loading preview…")
            return
        cap = None
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logging.warning(f"Cannot open video (cv2 open failed): {video_path}")
                self.video_label.setText("Loading preview…")
                return
            ret, frame = cap.read()
            if not ret:
                logging.warning(f"Cannot open video (first frame read failed): {video_path}")
                self.video_label.setText("Loading preview…")
                return
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(qt_image)
            # Scale pixmap to fit the label while preserving aspect ratio
            try:
                target = self.video_label.contentsRect().size()
                if target.width() > 0 and target.height() > 0:
                    pixmap = pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            except Exception:
                pass
            self.video_label.setPixmap(pixmap)
        except Exception as e:
            logging.error(f"Failed to load first frame for {video_path}: {e}")
            # Silent UI update; avoid popup on auto-selection
            self.video_label.setText("Loading preview…")
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
            # Enable import button when a video is selected and not recording
            if getattr(self, 'add_audio_button', None):
                self.add_audio_button.setEnabled(not self.is_recording)
            wav_path = self.fs.wav_path_for(self.current_video)
            if os.path.exists(wav_path):
                # Disable Play while audio is actively playing
                self.play_audio_button.setEnabled(not self.is_playing_audio)
                self.stop_audio_button.setEnabled(True)
                self.video_label.setStyleSheet("background-color: black; color: white; border: 3px solid #2ecc71;")
                if getattr(self, 'badge_label', None):
                    self.badge_label.setVisible(True)
            else:
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
            if getattr(self, 'add_audio_button', None):
                self.add_audio_button.setEnabled(False)
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
        video_path = self._resolve_current_video_path()
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
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
                # Scale pixmap to fit the label while preserving aspect ratio
                try:
                    target = self.video_label.contentsRect().size()
                    if target.width() > 0 and target.height() > 0:
                        pixmap = pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                except Exception:
                    pass
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
        # Debounce rapid clicks
        now = time.time()
        if (now - self._last_play_request_ts) < 0.2:
            return
        self._last_play_request_ts = now
        # Re-entrancy guard: ignore if already playing
        if self.is_playing_audio:
            return
        wav_path = self.fs.wav_path_for(self.current_video)
        if not os.path.exists(wav_path):
            return
        if not PYAUDIO_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyAudio is not available. Cannot play audio.")
            return
        # Mark playing and update UI (busy indicator)
        try:
            self.is_playing_audio = True
            self.play_audio_button.setText("Playing…")
            self.play_audio_button.setEnabled(False)
            logging.info(f"UI.audio: start video audio path={os.path.basename(wav_path)}")
        except Exception:
            pass
        # Use persistent audio thread
        try:
            self.audio_worker = AudioPlaybackWorker(wav_path)
            self.audio_worker.moveToThread(self.audio_thread)
            QMetaObject.invokeMethod(self.audio_worker, "run", Qt.QueuedConnection)
            # Re-enable controls when playback finishes
            self.audio_worker.finished.connect(self._on_any_audio_finished)
            self.audio_worker.error.connect(self._show_worker_error)
        except Exception:
            # Fallback: start thread if not running
            try:
                if self.audio_thread and not self.audio_thread.isRunning():
                    self.audio_thread.start()
                self.audio_thread.started.connect(self.audio_worker.run)
            except Exception:
                pass
    def stop_audio(self):
        logging.info("UI.audio: stop requested")
        if self.audio_worker:
            try:
                self.audio_worker.stop()
            except RuntimeError:
                pass
        # Do not quit persistent thread here; just clear UI state
        self.is_playing_audio = False
        try:
            # Restore button text
            self.play_audio_button.setText(self.LABELS.get("play_audio", "Play Audio"))
        except Exception:
            pass
        try:
            self.update_media_controls()
        except Exception:
            pass
        try:
            self._update_image_record_controls()
        except Exception:
            pass
        # Clear playing state and re-enable Play buttons
        self.is_playing_audio = False
        try:
            self.update_media_controls()
        except Exception:
            pass
        try:
            self._update_image_record_controls()
        except Exception:
            pass
    def _on_audio_thread_finished(self):
        self.audio_thread = None
        self.audio_worker = None
        # Ensure UI reflects that playback has ended
        self.is_playing_audio = False
        try:
            self.update_media_controls()
        except Exception:
            pass
        try:
            self._update_image_record_controls()
        except Exception:
            pass
    def _handle_play_image_audio(self):
        try:
            return self.play_image_audio()
        except Exception:
            pass
    def _handle_stop_image_audio(self):
        try:
            return self.stop_image_audio()
        except Exception:
            pass
    def _on_images_context_menu(self, pos: QPoint):
        try:
            # Select the item under the cursor if present
            item = self.images_list.itemAt(pos)
            if item is not None:
                self.images_list.setCurrentItem(item)
            menu = QMenu(self)
            copy_act = QAction(self.LABELS.get("copy_image", "Copy Image"), self)
            copy_act.triggered.connect(self._copy_current_image_to_clipboard)
            menu.addAction(copy_act)
            save_act = QAction(self.LABELS.get("save_image_as", "Save Image as…"), self)
            save_act.triggered.connect(self._save_current_image_as)
            menu.addAction(save_act)
            try:
                global_pos = self.images_list.mapToGlobal(pos)
            except Exception:
                global_pos = None
            if global_pos:
                menu.exec(global_pos)
            else:
                menu.exec(QCursor.pos())
        except Exception:
            pass
    def _copy_current_image_to_clipboard(self):
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            if not path or not os.path.exists(path):
                return
            reader = QImageReader(path)
            img = reader.read()
            if img.isNull():
                # Fallback: try via QPixmap
                try:
                    pix = QPixmap(path)
                    if not pix.isNull():
                        QGuiApplication.clipboard().setPixmap(pix)
                        return
                except Exception:
                    pass
                return
            QGuiApplication.clipboard().setImage(img)
            try:
                self.statusBar().showMessage(self.LABELS.get("copied_image", "Image copied to clipboard"), 2000)
            except Exception:
                pass
        except Exception:
            pass
    def _on_videos_context_menu(self, pos: QPoint):
        try:
            item = self.video_listbox.itemAt(pos)
            if item is not None:
                self.video_listbox.setCurrentItem(item)
            menu = QMenu(self)
            copy_act = QAction(self.LABELS.get("copy_video", "Copy Video"), self)
            copy_act.triggered.connect(self._copy_current_video_to_clipboard)
            menu.addAction(copy_act)
            save_act = QAction(self.LABELS.get("save_video_as", "Save Video as…"), self)
            save_act.triggered.connect(self._save_current_video_as)
            menu.addAction(save_act)
            try:
                global_pos = self.video_listbox.mapToGlobal(pos)
            except Exception:
                global_pos = None
            if global_pos:
                menu.exec(global_pos)
            else:
                menu.exec(QCursor.pos())
        except Exception:
            pass
    def _copy_current_video_to_clipboard(self):
        try:
            if not self.current_video:
                return
            video_path = self._resolve_current_video_path()
            if not (video_path and os.path.exists(video_path)):
                return
            mime = QMimeData()
            try:
                mime.setUrls([QUrl.fromLocalFile(video_path)])
            except Exception:
                pass
            try:
                mime.setText(video_path)
            except Exception:
                pass
            QGuiApplication.clipboard().setMimeData(mime)
            try:
                self.statusBar().showMessage(self.LABELS.get("copied_video", "Video copied to clipboard"), 2000)
            except Exception:
                pass
        except Exception:
            pass
    def _save_current_video_as(self):
        try:
            if not self.current_video:
                return
            src = self._resolve_current_video_path()
            if not (src and os.path.exists(src)):
                return
            name = os.path.basename(src)
            dst, _ = QFileDialog.getSaveFileName(
                self,
                self.LABELS.get("save_video_as_dialog_title", "Save Video as…"),
                name,
                "Video files (*.mpg *.mpeg *.mp4 *.avi *.mkv *.mov);;All files (*)",
            )
            if not dst:
                return
            try:
                shutil.copyfile(src, dst)
            except Exception as e:
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), f"Failed to save video: {e}")
                return
        except Exception:
            pass
    def _save_current_image_as(self):
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            if not path or not os.path.exists(path):
                return
            name = os.path.basename(path)
            dst, _ = QFileDialog.getSaveFileName(
                self,
                self.LABELS.get("save_image_as_dialog_title", "Save Image as…"),
                name,
                "Image files (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.gif);;All files (*)",
            )
            if not dst:
                return
            try:
                shutil.copyfile(path, dst)
            except Exception as e:
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), f"Failed to save image: {e}")
                return
        except Exception:
            pass
    def _handle_add_existing_audio_video(self):
        """Import an existing audio file for the currently selected video and convert to 16-bit WAV."""
        try:
            if not self.current_video or not self.fs.current_folder:
                return
            target_wav = self.fs.wav_path_for(self.current_video)
            if os.path.exists(target_wav):
                reply = QMessageBox.question(
                    self,
                    self.LABELS.get("overwrite", "Overwrite?"),
                    self.LABELS.get("overwrite_audio", "Audio file already exists. Overwrite?"),
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return
            # Choose source audio file
            src_path, _ = QFileDialog.getOpenFileName(
                self,
                self.LABELS.get("import_select_file_dialog", "Select Audio File"),
                self.fs.current_folder or "",
                "Audio files (*.wav *.mp3 *.ogg *.m4a *.aac *.flac *.opus *.aif *.aiff);;All files (*)",
            )
            if not src_path:
                return
            try:
                seg = AudioSegment.from_file(src_path)
                seg = seg.set_channels(1).set_frame_rate(44100).set_sample_width(2)
                seg.export(target_wav, format="wav")
            except Exception as e:
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), f"Failed to import audio: {e}")
                return
            try:
                self.statusBar().showMessage(self.LABELS.get("metadata_saved", "Metadata saved!"))
            except Exception:
                pass
            # Refresh controls and badges
            self.update_media_controls()
        except Exception:
            pass
    def _convert_audio_to_wav(self, src_path: str, target_wav: str) -> None:
        seg = AudioSegment.from_file(src_path)
        seg = seg.set_channels(1).set_frame_rate(44100).set_sample_width(2)
        seg.export(target_wav, format="wav")
    def _clipboard_audio_to_tempfile(self, mime) -> str | None:
        try:
            # Prefer file URLs on the clipboard
            if mime.hasUrls():
                for url in mime.urls():
                    try:
                        if isinstance(url, QUrl) and url.isLocalFile():
                            p = url.toLocalFile()
                            if p and os.path.exists(p):
                                return p
                    except Exception:
                        continue
            # Next, check for plain-text paths or file:// URLs
            if mime.hasText():
                txt = (mime.text() or "").strip()
                if txt:
                    if os.path.exists(txt):
                        return txt
                    try:
                        u = QUrl(txt)
                        if u.isLocalFile():
                            p = u.toLocalFile()
                            if p and os.path.exists(p):
                                return p
                    except Exception:
                        pass
            # Finally, handle raw audio bytes for known MIME types
            format_map = {
                "audio/wav": ".wav",
                "audio/x-wav": ".wav",
                "audio/mpeg": ".mp3",
                "audio/mp3": ".mp3",
                "audio/ogg": ".ogg",
                "application/ogg": ".ogg",
                "audio/aac": ".aac",
                "audio/flac": ".flac",
                "audio/opus": ".opus",
                "audio/webm": ".webm",
                "audio/aiff": ".aiff",
                "audio/x-aiff": ".aif",
            }
            for fmt, ext in format_map.items():
                try:
                    if fmt in mime.formats():
                        data = mime.data(fmt)
                        if data and len(data) > 0:
                            import tempfile
                            fd, tmp = tempfile.mkstemp(suffix=ext)
                            os.write(fd, bytes(data))
                            os.close(fd)
                            return tmp
                except Exception:
                    continue
        except Exception:
            pass
        return None
    def _handle_paste_audio_video(self):
        try:
            if not self.current_video or not self.fs.current_folder:
                return
            target_wav = self.fs.wav_path_for(self.current_video)
            if os.path.exists(target_wav):
                reply = QMessageBox.question(
                    self,
                    self.LABELS.get("overwrite", "Overwrite?"),
                    self.LABELS.get("overwrite_audio", "Audio file already exists. Overwrite?"),
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return
            cb = QGuiApplication.clipboard()
            mime = cb.mimeData()
            src = self._clipboard_audio_to_tempfile(mime)
            if not src:
                QMessageBox.warning(self, self.LABELS.get("error_title", "Error"), self.LABELS.get("paste_audio_failed", "Clipboard does not contain audio or an audio file path."))
                return
            try:
                self._convert_audio_to_wav(src, target_wav)
            finally:
                # Clean temp file if we created one
                try:
                    if src and os.path.basename(src).startswith("tmp") and not os.path.isdir(src):
                        pass
                except Exception:
                    pass
            self.update_media_controls()
        except Exception:
            pass
    def _handle_paste_audio_image(self):
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            if not path:
                return
            existing = self.fs.find_existing_image_audio(path)
            target_wav = self.fs.wav_path_for_image(path)
            if existing and os.path.exists(existing):
                reply = QMessageBox.question(
                    self,
                    self.LABELS.get("overwrite", "Overwrite?"),
                    self.LABELS.get("overwrite_audio", "Audio file already exists. Overwrite?"),
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return
            cb = QGuiApplication.clipboard()
            mime = cb.mimeData()
            src = self._clipboard_audio_to_tempfile(mime)
            if not src:
                QMessageBox.warning(self, self.LABELS.get("error_title", "Error"), self.LABELS.get("paste_audio_failed", "Clipboard does not contain audio or an audio file path."))
                return
            try:
                self._convert_audio_to_wav(src, target_wav)
            finally:
                try:
                    if src and os.path.basename(src).startswith("tmp") and not os.path.isdir(src):
                        pass
                except Exception:
                    pass
            try:
                self._update_image_record_controls(path)
            except Exception:
                pass
            self.update_video_file_checks()
        except Exception:
            pass
    def _handle_add_existing_audio_image(self):
        """Import an existing audio file for the selected image and convert to 16-bit WAV."""
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            if not path:
                return
            existing = self.fs.find_existing_image_audio(path)
            target_wav = self.fs.wav_path_for_image(path)
            if existing and os.path.exists(existing):
                reply = QMessageBox.question(
                    self,
                    self.LABELS.get("overwrite", "Overwrite?"),
                    self.LABELS.get("overwrite_audio", "Audio file already exists. Overwrite?"),
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return
            # Choose source audio file
            src_path, _ = QFileDialog.getOpenFileName(
                self,
                self.LABELS.get("import_select_file_dialog", "Select Audio File"),
                os.path.dirname(path) or (self.fs.current_folder or ""),
                "Audio files (*.wav *.mp3 *.ogg *.m4a *.aac *.flac *.opus *.aif *.aiff);;All files (*)",
            )
            if not src_path:
                return
            try:
                seg = AudioSegment.from_file(src_path)
                seg = seg.set_channels(1).set_frame_rate(44100).set_sample_width(2)
                seg.export(target_wav, format="wav")
            except Exception as e:
                QMessageBox.critical(self, self.LABELS.get("error_title", "Error"), f"Failed to import audio: {e}")
                return
            try:
                self.statusBar().showMessage(self.LABELS.get("metadata_saved", "Metadata saved!"))
            except Exception:
                pass
            # Refresh controls and visuals
            try:
                self._update_image_record_controls(path)
            except Exception:
                pass
            self.update_video_file_checks()
        except Exception:
            pass
    def _handle_record_image(self):
        try:
            return self.toggle_image_recording()
        except Exception:
            pass
    def _handle_stop_image_record(self):
        try:
            return self.stop_image_recording()
        except Exception:
            pass
    def _handle_image_selection(self):
        try:
            logging.debug("UI._handle_image_selection invoked")
            return self.on_image_select()
        except Exception:
            pass
    def _handle_open_fullscreen_image(self, item):
        try:
            return self._open_fullscreen_image(item)
        except Exception:
            pass
    def toggle_recording(self):
        if not self.current_video:
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
        # Ensure recording state resets on thread finish (videos and images)
        try:
            self.is_recording = False
        except Exception:
            pass
        # Update UI controls accordingly
        try:
            self.update_media_controls()
        except Exception:
            pass
        try:
            self._update_image_record_controls()
        except Exception:
            pass
        try:
            # Ensure grid overlays update when recording stops
            self.images_list.viewport().update()
        except Exception:
            pass
    def closeEvent(self, event):
        try:
            # Ensure Review tab threads stop before main window closes
            try:
                review_tab = getattr(self, 'review_tab', None)
                if review_tab and hasattr(review_tab, 'cleanup'):
                    review_tab.cleanup()
            except Exception:
                pass
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
            # Ensure persistent audio thread stops on app close
            try:
                if self.audio_thread and self.audio_thread.isRunning():
                    self.audio_thread.quit()
                    self.audio_thread.wait()
                    logging.info("UI.audio: persistent audio thread stopped on close")
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
        # Tab-aware: open recordings for the active tab
        try:
            active_index = self.right_panel.currentIndex() if getattr(self, 'right_panel', None) else 0
        except Exception:
            active_index = 0
        
        # Determine which recordings to open based on active tab
        if active_index == 1:  # Images tab
            file_paths = self.fs.image_recordings_in()
        elif active_index == 2:  # Review tab
            # Get recordings from Review tab's filtered scope
            try:
                review_tab = getattr(self, 'review_tab', None)
                if review_tab:
                    items = review_tab._get_recorded_items()
                    file_paths = [wav_path for _, _, wav_path in items]
                else:
                    file_paths = self.fs.recordings_in()
            except Exception:
                file_paths = self.fs.recordings_in()
        else:  # Videos tab (default)
            file_paths = self.fs.video_recordings_in()
        
        if not file_paths:
            QMessageBox.information(self, self.LABELS["no_files"], self.LABELS["no_wavs_found"]) 
            return
        file_paths.sort()
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
                    QMessageBox.warning(
                        self,
                        self.LABELS["ocenaudio_not_found_title"],
                        self.LABELS.get(
                            "ocenaudio_not_found_body",
                            LABELS_ALL["English"]["ocenaudio_not_found_body"],
                        ),
                    )
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
        wav_paths = self.fs.recordings_in()
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
        try:
            content = self.fs.ensure_and_read_metadata(self.fs.current_folder, "")
            with open(metadata_dst, "w") as f:
                f.write(content if isinstance(content, str) else "")
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
        wav_paths = self.fs.recordings_in()
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
        default_content = (
            "name: \n"
            "date: \n"
            "location: \n"
            "researcher: \n"
            "speaker: \n"
            "permissions for use given by speaker: \n"
        )
        try:
            self.fs.write_metadata(default_content)
        except Exception as e:
            errors.append(f"metadata.txt reset: {e}")
        if errors:
            QMessageBox.critical(self, self.LABELS["delete_errors_title"], self.LABELS["delete_errors_msg_prefix"] + "\n".join(errors))
        else:
            QMessageBox.information(self, self.LABELS["clear_wavs"], self.LABELS["clear_success_msg_prefix"].format(count=len(wav_files)))
        self.load_video_files()
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
        wav_paths_existing = self.fs.recordings_in()
        wav_files = [os.path.basename(p) for p in wav_paths_existing]
        errors = []
        for wav in wav_files:
            try:
                os.remove(os.path.join(self.fs.current_folder, wav))
            except Exception as e:
                errors.append(f"Delete {wav}: {e}")
        import_dir = QFileDialog.getExistingDirectory(self, self.LABELS["import_select_folder_dialog"]) 
        if not import_dir:
            return
        try:
            import_paths = self.fs.recordings_in(import_dir)
            import_files = [os.path.basename(p) for p in import_paths]
        except Exception:
            import_files = [f for f in os.listdir(import_dir) if f.lower().endswith('.wav') and not f.startswith('.')]
        video_basenames = set(os.path.splitext(os.path.basename(f))[0] for f in self.video_files)
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
        self.update_video_file_checks()
    def join_all_wavs(self):
        if not self.fs.current_folder:
            QMessageBox.critical(self, self.LABELS["error_title"], self.LABELS["no_folder_selected"]) 
            return
        # Tab-aware: join recordings for the active tab
        try:
            active_index = self.right_panel.currentIndex() if getattr(self, 'right_panel', None) else 0
        except Exception:
            active_index = 0
        
        # Determine which recordings to join based on active tab
        if active_index == 1:  # Images tab
            wav_paths = self.fs.image_recordings_in()
        elif active_index == 2:  # Review tab
            # Get recordings from Review tab's filtered scope
            try:
                review_tab = getattr(self, 'review_tab', None)
                if review_tab:
                    items = review_tab._get_recorded_items()
                    wav_paths = [wav_path for _, _, wav_path in items]
                else:
                    wav_paths = self.fs.recordings_in()
            except Exception:
                wav_paths = self.fs.recordings_in()
        else:  # Videos tab (default)
            wav_paths = self.fs.video_recordings_in()
        if not wav_paths:
            QMessageBox.information(self, self.LABELS["no_files"], self.LABELS["no_wavs_found"]) 
            return
        ffmpeg_path = resource_path(os.path.join("ffmpeg", "bin", "ffmpeg"))
        if not os.path.exists(ffmpeg_path):
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
        self.join_worker = JoinWavsWorker(output_file=output_file, fs=self.fs, file_paths=wav_paths)
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
        # Update image badges
        try:
            # Just trigger repaint; delegate will render overlays based on wav existence
            if getattr(self, 'images_list', None):
                self.images_list.viewport().update()
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
    def resizeEvent(self, event):
        try:
            # Reduce listbox vertical size to ~75% of the left panel
            if getattr(self, 'left_panel', None) is not None and getattr(self, 'video_listbox', None) is not None:
                left_h = max(0, self.left_panel.height())
                # Reduce another ~10%: target ~65% of left panel height
                target_h = int(left_h * 0.65)
                min_h = 200
                self.video_listbox.setMaximumHeight(max(min_h, target_h))
        except Exception:
            pass
        # Recompute images grid sizes to maintain true two-column layout
        try:
            self._recompute_image_grid_sizes()
        except Exception:
            pass
        try:
            return super().resizeEvent(event)
        except Exception:
            pass
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
        # Keep images grid sizing in sync with show/resize events
        try:
            if obj is getattr(self, 'images_list', None):
                if event.type() in (QEvent.Show, QEvent.Resize):
                    self._recompute_image_grid_sizes()
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _show_welcome_dialog(self):
        """Display a brief purpose + best-practices message on startup."""
        try:
            title = self.LABELS.get(
                "welcome_dialog_title",
                LABELS_ALL["English"]["welcome_dialog_title"],
            )
            body = self.LABELS.get(
                "welcome_dialog_body_html",
                LABELS_ALL["English"]["welcome_dialog_body_html"],
            )
            try:
                from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
                from PySide6.QtCore import Qt
            except Exception:
                # Fallback if widgets cannot be imported for some reason
                QMessageBox.information(self, title, body)
                return

            dlg = QDialog(self)
            dlg.setWindowTitle(title)
            layout = QVBoxLayout(dlg)
            try:
                layout.setContentsMargins(16, 10, 16, 10)
                layout.setSpacing(8)
            except Exception:
                pass

            label = QLabel(dlg)
            label.setTextFormat(Qt.RichText)
            label.setWordWrap(True)
            try:
                label.setOpenExternalLinks(True)
            except Exception:
                pass
            label.setText(body)
            layout.addWidget(label)

            btn_row = QHBoxLayout()
            btn_row.addStretch(1)
            ok_btn = QPushButton("OK", dlg)
            ok_btn.clicked.connect(dlg.accept)
            btn_row.addWidget(ok_btn)
            layout.addLayout(btn_row)

            # Make the dialog wider but slightly shorter to reduce empty space
            try:
                current_size = dlg.sizeHint()
                # Target ~1.25x typical width, with a reasonable minimum
                new_w = max(720, int(current_size.width() * 1.25))
                # Reduce minimum height to trim top/bottom whitespace
                new_h = max(440, current_size.height())
                dlg.resize(new_w, new_h)
            except Exception:
                dlg.resize(720, 460)

            dlg.exec()
        except Exception:
            pass

    def _open_docs_site(self, _link: str = "internal:docs#default"):
        """Open the bundled documentation site in a pywebview window."""
        try:
            import subprocess, sys
            from vat.utils.resources import resource_path
            # Resolve bundled docs path (PyInstaller-aware)
            index_path = resource_path(os.path.join("docs", "gpa", "index.html"), check_system=False)
            # Support internal anchors like internal:docs#section
            frag = None
            try:
                if isinstance(_link, str) and "#" in _link:
                    frag = _link.split("#", 1)[1]
            except Exception:
                frag = None
            if not os.path.exists(index_path):
                # Fallback: bundled full docs
                index_path = resource_path(os.path.join("docs", "index.html"), check_system=False)
            # Launch a separate process to avoid interfering with the Qt event loop
            if frag:
                cmd = [sys.executable, "-m", "vat.ui.docs_webview", index_path, frag]
            else:
                cmd = [sys.executable, "-m", "vat.ui.docs_webview", index_path]
            subprocess.Popen(cmd)
        except Exception as e:
            try:
                QMessageBox.information(self, "Documentation", f"Unable to open documentation window: {e}")
            except Exception:
                pass

    # --- Images tab helpers (moved back into VideoAnnotationApp) ---
    def _open_fullscreen_video(self):
        try:
            if not self.current_video or not self.fs.current_folder:
                return
            if getattr(self, '_fullscreen_viewer', None) is not None:
                try:
                    if self._fullscreen_viewer.isVisible():
                        self._fullscreen_viewer.raise_()
                        self._fullscreen_viewer.activateWindow()
                        self._fullscreen_viewer.setFocus()
                        return
                except Exception:
                    pass
            video_path = self._resolve_current_video_path()
            viewer = FullscreenVideoViewer(video_path)
            self._fullscreen_viewer = viewer
            viewer.showFullScreen()
            try:
                viewer.raise_()
                viewer.activateWindow()
                viewer.setFocus()
            except Exception:
                pass
            try:
                viewer.scale_changed.connect(self._on_fullscreen_scale_changed)
                viewer.destroyed.connect(self._on_fullscreen_closed)
            except Exception:
                pass
        except Exception as e:
            logging.error(f"Failed to open fullscreen viewer: {e}")

    def _open_fullscreen_image(self, item=None):
        try:
            if getattr(self, 'images_list', None) is None:
                return
            # Reuse existing fullscreen viewer if still visible
            try:
                if getattr(self, '_fullscreen_viewer', None) is not None and self._fullscreen_viewer.isVisible():
                    self._fullscreen_viewer.raise_()
                    self._fullscreen_viewer.activateWindow()
                    self._fullscreen_viewer.setFocus()
                    return
            except Exception:
                pass
            if item is None:
                sel = self.images_list.currentItem()
                if sel is None:
                    return
            else:
                sel = item
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                if not (self.fs.current_folder and name):
                    return
                path = os.path.join(self.fs.current_folder, name)

            # Use any cached pixmap if available so the fullscreen viewer
            # can display immediately on first open.
            cached_pix = None
            try:
                cache = getattr(self, "_image_pixmap_cache", None)
                if cache:
                    cached_pix = cache.get(path)
            except Exception:
                cached_pix = None

            # Always attempt to open the fullscreen viewer; any image-loading
            # issues are handled defensively inside FullscreenImageViewer.
            viewer = FullscreenImageViewer(path, pixmap=cached_pix)
            self._fullscreen_viewer = viewer
            viewer.showFullScreen()
            try:
                viewer.raise_()
                viewer.activateWindow()
                viewer.setFocus()
            except Exception:
                pass
            try:
                viewer.scale_changed.connect(self._on_fullscreen_scale_changed)
                viewer.destroyed.connect(self._on_fullscreen_closed)
            except Exception:
                pass
        except Exception as e:
            logging.error(f"Failed to open fullscreen image viewer: {e}")

    def _toggle_image_labels(self, checked: bool):
        try:
            self.show_image_labels = bool(checked)
            files = []
            for i in range(self.images_list.count()):
                it = self.images_list.item(i)
                fp = it.data(Qt.UserRole)
                if fp:
                    files.append(fp)
            if not files:
                files = self.fs.list_images()
            self._populate_images_list(files)
            try:
                self._recompute_image_grid_sizes()
            except Exception:
                pass
        except Exception:
            pass

    def _load_image_pixmap(self, path: str | None):
        """Load or retrieve a cached full-resolution pixmap for an image.

        Uses QImageReader first for robustness, then falls back to
        QPixmap. Successful loads are stored in self._image_pixmap_cache
        so later fullscreen opens do not pay a first-decode penalty.
        """
        if not path:
            return None
        try:
            cache = getattr(self, "_image_pixmap_cache", None)
            if cache is None:
                self._image_pixmap_cache = {}
                cache = self._image_pixmap_cache
        except Exception:
            return None
        pix = cache.get(path)
        if pix is not None and not pix.isNull():
            return pix
        try:
            pix = QPixmap(path)
            if pix.isNull():
                try:
                    reader = QImageReader(path)
                    img = reader.read()
                    if img and not img.isNull():
                        pix = QPixmap.fromImage(img)
                except Exception:
                    pass
            if pix is None or pix.isNull():
                return None
            cache[path] = pix
            return pix
        except Exception:
            return None

    def _preload_visible_images(self):
        """Warm the pixmap cache for all items currently visible in the grid."""
        try:
            if getattr(self, 'images_list', None) is None:
                return
            viewport = self.images_list.viewport()
            if viewport is None:
                return
            vp_rect = viewport.rect()
            for i in range(self.images_list.count()):
                item = self.images_list.item(i)
                if item is None:
                    continue
                rect = self.images_list.visualItemRect(item)
                if (not rect.isValid()) or (not rect.intersects(vp_rect)):
                    continue
                path = None
                try:
                    path = item.data(Qt.UserRole)
                except Exception:
                    path = None
                if not path:
                    name = item.text()
                    if self.fs.current_folder and name:
                        path = os.path.join(self.fs.current_folder, name)
                if path:
                    self._load_image_pixmap(path)
        except Exception:
            pass

    def _populate_images_list(self, files: list):
        try:
            if getattr(self, 'images_list', None) is None:
                return
            self.images_list.clear()
            try:
                self._recompute_image_grid_sizes()
            except Exception:
                pass
            icon_size = self.images_list.iconSize()
            count = 0
            for full in files:
                name = os.path.basename(full)
                item_text = name if getattr(self, 'show_image_labels', False) else ""
                item = QListWidgetItem(item_text)
                try:
                    item.setData(Qt.UserRole, full)
                except Exception:
                    pass
                try:
                    pix = self._load_image_pixmap(full)
                    if pix is not None and not pix.isNull():
                        thumb = pix.scaled(icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        item.setIcon(QIcon(thumb))
                    else:
                        item.setIcon(self._empty_icon)
                except Exception:
                    item.setIcon(self._empty_icon)
                self.images_list.addItem(item)
                count += 1
            if count > 0:
                self.images_list.setCurrentRow(0)
            # Delegate repaint checks; selection change will trigger banner update
            self.update_video_file_checks()
            try:
                logging.info(f"Images tab populated: count={count}; sample={[os.path.basename(f) for f in files[:3]]}")
            except Exception:
                pass
            # Avoid manual select handlers here; currentItemChanged will fire
        except Exception as e:
            logging.warning(f"Failed to refresh images from FS manager: {e}")
        # Warm the cache for the thumbnails that are currently visible.
        try:
            self._preload_visible_images()
        except Exception:
            pass

    def _recompute_image_grid_sizes(self):
        if getattr(self, 'images_list', None) is None:
            return
        try:
            vp = self.images_list.viewport()
            vpw = vp.width() if vp is not None else self.images_list.width()
            try:
                fw = int(getattr(self.images_list, 'frameWidth', lambda: 0)())
            except Exception:
                fw = 0
            vpw = max(50, vpw - (fw * 2))
            try:
                sbw = int(self.images_list.verticalScrollBar().width())
                if sbw <= 0:
                    sbw = 12
            except Exception:
                sbw = 12
            vpw = max(100, vpw - sbw)
            try:
                spacing = int(self.images_list.spacing())
            except Exception:
                spacing = 8
            # Auto-adjust columns based on available width and user scale
            usable = max(120, vpw - spacing * 3)
            min_col_w = int(160 * max(0.5, min(1.8, getattr(self, 'images_thumb_scale', 1.0))))
            cols = max(1, usable // max(120, min_col_w))
            total_spacing = spacing * (cols + 1)
            usable = max(120, vpw - total_spacing)
            col_w = max(min_col_w, usable // max(1, cols))
            icon_w = int(col_w * 0.90)
            icon_h = int(icon_w * 3 / 4)
            label_h = 18 if getattr(self, 'show_image_labels', False) else 0
            grid_w = max(100, col_w)
            grid_h = icon_h + label_h + 10
            self.images_list.setIconSize(QSize(icon_w, icon_h))
            self.images_list.setGridSize(QSize(grid_w, grid_h))
            try:
                logging.debug(f"UI._recompute_image_grid_sizes: vpw={vpw}, fw={fw}, sbw={sbw}, usable={usable}, col_w={col_w}, icon=({icon_w}x{icon_h}), grid=({grid_w}x{grid_h}), spacing={spacing}")
            except Exception:
                pass
        except Exception:
            pass

    def _on_images_updated(self, *args):
        # Support both legacy (files) and new (folder, files) signal forms
        if len(args) == 2:
            folder, files = args
        elif len(args) == 1:
            folder, files = "", args[0]
        else:
            return
        try:
            active = self.fs.current_folder or ""
            if folder and os.path.normpath(folder) != os.path.normpath(active):
                try:
                    logging.warning(f"UI._on_images_updated: ignoring update for folder={folder}; active={active}")
                except Exception:
                    pass
                return
        except Exception:
            pass
        self._populate_images_list(files)

    def on_image_select(self):
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                try:
                    self.image_thumb.clear()
                except Exception:
                    pass
                self.play_image_audio_button.setEnabled(False)
                self.stop_image_audio_button.setEnabled(False)
                self.record_image_button.setEnabled(False)
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            try:
                logging.debug(f"UI.on_image_select: path={path}")
            except Exception:
                pass
            try:
                pix = self._load_image_pixmap(path)
                if pix is not None and not pix.isNull():
                    self.image_thumb.setPixmap(pix.scaled(self.image_thumb.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    self.image_thumb.clear()
            except Exception:
                pass
            # Update image-related controls (play/stop and record/stop-record)
            try:
                self._update_image_record_controls(path)
            except Exception:
                pass
            try:
                logging.debug(f"UI.on_image_select: selected='{os.path.basename(path)}', wav_exists={exists}")
            except Exception:
                pass
        except Exception:
            pass

    def _update_image_record_controls(self, path: str | None = None):
        try:
            # Resolve current selection path if not provided
            if not path:
                sel = self.images_list.currentItem()
                if sel is not None:
                    try:
                        path = sel.data(Qt.UserRole) or os.path.join(self.fs.current_folder or "", sel.text())
                    except Exception:
                        path = None
            # Resolve existing audio with compatibility (legacy basename.wav, root folder)
            resolved = self.fs.find_existing_image_audio(path or "")
            wav_path = resolved or self.fs.wav_path_for_image(path or "")
            exists = bool(resolved)
            # Play/Stop audio reflect wav existence, but disable Play while actively playing
            self.play_image_audio_button.setEnabled(exists and not self.is_playing_audio)
            self.stop_image_audio_button.setEnabled(exists)
            # Record/Stop-Record reflect recording state
            if self.is_recording:
                self.record_image_button.setEnabled(False)
                self.stop_image_record_button.setEnabled(True)
                if getattr(self, 'add_image_audio_button', None):
                    self.add_image_audio_button.setEnabled(False)
            else:
                self.record_image_button.setEnabled(True)
                self.stop_image_record_button.setEnabled(False)
                if getattr(self, 'add_image_audio_button', None):
                    # Enable import when an image is selected
                    self.add_image_audio_button.setEnabled(bool(path))
            try:
                logging.debug(f"UI._update_image_record_controls: wav_path={wav_path}, exists={exists}, is_recording={self.is_recording}")
            except Exception:
                pass
            # Trigger repaint so delegate overlays reflect current state
            try:
                self.images_list.viewport().update()
            except Exception:
                pass
        except Exception:
            pass

    def play_image_audio(self):
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            # Resolve existing audio; play if found
            wav_path = self.fs.find_existing_image_audio(path) or self.fs.wav_path_for_image(path)
            if not (wav_path and os.path.exists(wav_path)):
                return
            # Re-entrancy guard: ignore if already playing
            if self.is_playing_audio:
                return
            if not PYAUDIO_AVAILABLE:
                QMessageBox.warning(self, "Error", "PyAudio is not available. Cannot play audio.")
                return
            # Mark playing and update UI (disable Play, enable Stop)
            self.is_playing_audio = True
            try:
                self.play_image_audio_button.setEnabled(False)
                self.stop_image_audio_button.setEnabled(True)
            except Exception:
                pass
            try:
                # Also disable videos tab Play if present
                if getattr(self, 'play_audio_button', None):
                    self.play_audio_button.setEnabled(False)
            except Exception:
                pass
            # Use persistent audio thread (created in __init__) for playback
            self.audio_worker = AudioPlaybackWorker(wav_path)
            self.audio_worker.moveToThread(self.audio_thread)
            try:
                from PySide6.QtCore import QMetaObject
                QMetaObject.invokeMethod(self.audio_worker, "run", Qt.QueuedConnection)
            except Exception:
                # Fallback: start thread if not already running and connect
                try:
                    if self.audio_thread and not self.audio_thread.isRunning():
                        self.audio_thread.start()
                    self.audio_thread.started.connect(self.audio_worker.run)
                except Exception:
                    pass
            # Re-enable controls when playback finishes
            self.audio_worker.finished.connect(self._on_any_audio_finished)
            self.audio_worker.error.connect(self._show_worker_error)
        except Exception:
            pass

    def _on_any_audio_finished(self):
        """Shared handler to re-enable Play buttons after audio playback completes."""
        try:
            logging.info("UI.audio: finished")
        except Exception:
            pass
        self.is_playing_audio = False
        # Restore Play button texts
        try:
            if getattr(self, 'play_audio_button', None):
                self.play_audio_button.setText(self.LABELS.get("play_audio", "Play Audio"))
        except Exception:
            pass
        try:
            if getattr(self, 'play_image_audio_button', None):
                self.play_image_audio_button.setText(self.LABELS.get("play_audio", "Play Audio"))
        except Exception:
            pass
        try:
            self.update_media_controls()
        except Exception:
            pass
        try:
            self._update_image_record_controls()
        except Exception:
            pass

    def stop_image_audio(self):
        self.stop_audio()

    def toggle_image_recording(self):
        try:
            sel = self.images_list.currentItem()
            if sel is None:
                return
            path = None
            try:
                path = sel.data(Qt.UserRole)
            except Exception:
                path = None
            if not path:
                name = sel.text()
                path = os.path.join(self.fs.current_folder or "", name)
            # If any existing audio (including legacy paths) exists, confirm overwrite
            existing = self.fs.find_existing_image_audio(path)
            wav_path = self.fs.wav_path_for_image(path)
            if existing and os.path.exists(existing):
                reply = QMessageBox.question(self, self.LABELS["overwrite"], 
                                            self.LABELS["overwrite_audio"],
                                            QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    return
            if not PYAUDIO_AVAILABLE:
                QMessageBox.warning(self, "Error", "PyAudio is not available. Cannot record audio.")
                return
            self.is_recording = True
            try:
                self.statusBar().showMessage(self.LABELS.get("recording_started", "Recording started"), 2000)
            except Exception:
                pass
            # Update controls: disable Record, enable Stop Recording
            try:
                self._update_image_record_controls(path)
            except Exception:
                pass
            self.recording_thread = QThread()
            self.recording_worker = AudioRecordingWorker(wav_path)
            self.recording_worker.moveToThread(self.recording_thread)
            self.recording_thread.started.connect(self.recording_worker.run)
            self.recording_worker.finished.connect(self.recording_thread.quit)
            self.recording_worker.finished.connect(self.recording_worker.deleteLater)
            self.recording_thread.finished.connect(self.recording_thread.deleteLater)
            self.recording_worker.finished.connect(self.update_video_file_checks)
            self.recording_thread.finished.connect(self._on_recording_thread_finished)
            self.recording_worker.error.connect(self._show_worker_error)
            self.recording_thread.start()
        except Exception:
            pass

    def stop_image_recording(self):
        try:
            if not self.is_recording:
                return
            # Request worker stop
            if self.recording_worker:
                try:
                    self.recording_worker.stop()
                except RuntimeError:
                    pass
            # Quit and wait for thread
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
            self.is_recording = False
            # Update controls after stop
            try:
                self._update_image_record_controls()
            except Exception:
                pass
            try:
                self.statusBar().showMessage(self.LABELS.get("recording_stopped", "Recording stopped"), 2000)
            except Exception:
                pass
            self.update_video_file_checks()
            try:
                # Update the images grid visuals
                self.images_list.viewport().update()
            except Exception:
                pass
        except Exception:
            pass

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


class ImageGridDelegate(QStyledItemDelegate):
    def __init__(self, fs_manager: FolderAccessManager, parent=None):
        super().__init__(parent)
        self.fs = fs_manager

    def paint(self, painter, option, index):
        # Default painting first (thumbnail + optional text)
        super().paint(painter, option, index)
        try:
            path = index.data(Qt.UserRole)
            if not path:
                name = index.data(Qt.DisplayRole) or ""
                parent_folder = getattr(getattr(self.parent(), 'fs', None), 'current_folder', None)
                if parent_folder and name:
                    path = os.path.join(parent_folder, name)
            wav_path = self.fs.wav_path_for_image(path or "")
            has_wav = bool(wav_path and os.path.exists(wav_path))
        except Exception:
            has_wav = False
        if not has_wav:
            return
        try:
            painter.save()
            # Green border around icon area
            pen = QPen(QColor("#2ecc71"))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            r = option.rect
            ds = getattr(option, 'decorationSize', QSize(0, 0))
            iw = max(1, ds.width())
            ih = max(1, ds.height())
            x = r.x() + (r.width() - iw) // 2
            y = r.y() + 5
            icon_rect = QRect(x, y, iw, ih)
            painter.drawRect(icon_rect.adjusted(1, 1, -1, -1))
            # Small check overlay in the top-right of the icon
            try:
                chk = QApplication.style().standardIcon(QStyle.SP_DialogApplyButton).pixmap(18, 18)
                ox = icon_rect.right() - 18 - 4
                oy = icon_rect.top() + 4
                painter.drawPixmap(QPoint(ox, oy), chk)
            except Exception:
                pass
        finally:
            try:
                painter.restore()
            except Exception:
                pass
