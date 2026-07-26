# PyInstaller spec for PySide6-based Visual Stimulus Kit Tool
# ONEFILE (single portable .exe) build.
#
# NOTE: pyinstaller-onedir.spec builds the same app as a one-folder bundle.
# The Analysis configuration below is intentionally duplicated there --
# keep the two in sync when changing datas/hiddenimports/excludes.
#
# UPX is disabled: it forces every bundled DLL to be decompressed at load
# (slower startup) and UPX-packed executables are a common antivirus
# false-positive trigger, which matters for users on lab/shared machines.

block_cipher = None

# Artifact name carries the version and "portable" so downloaded files are
# self-identifying (e.g. Visual-Stimulus-Kit-Tool-2.3.3-portable.exe).
# SPECPATH is injected by PyInstaller and points at this file's directory.
import os as _os
try:
    with open(_os.path.join(SPECPATH, 'VERSION'), 'r', encoding='utf-8') as _f:
        _VERSION = _f.read().strip()
except Exception:
    _VERSION = '0.0.0'
APP_NAME = 'Visual-Stimulus-Kit-Tool-%s-portable' % _VERSION

datas = [
    ('assets/icon.ico', 'assets'),
    ('assets/icon.png', 'assets'),
    ('assets/ffmpeg-bin/windows/ffmpeg.exe', 'assets/ffmpeg-bin/windows'),
    ('assets/ffmpeg-bin/windows/ffprobe.exe', 'assets/ffmpeg-bin/windows'),
]
datas += [('vat/i18n/labels.yaml', 'vat/i18n')]
# Deliberately NOT using collect_data_files('PySide6'): that force-collects the
# entire PySide6 package (every Qt DLL, translation and resource, including
# WebEngine/Quick/3D) regardless of what is imported. PyInstaller's official
# PySide6 hook already bundles the Qt libraries and plugins the app actually
# needs, which keeps the build far smaller.

# This app imports only QtCore/QtGui/QtWidgets. Excluding the unused Qt
# frameworks (and other large libs that are never imported) keeps the bundle
# small, which also shortens onefile's per-launch extraction.
excludes = [
    'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
    'PySide6.QtWebChannel', 'PySide6.QtWebSockets', 'PySide6.QtWebView',
    'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuick3D',
    'PySide6.QtQuickWidgets', 'PySide6.QtQuickControls2',
    'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput',
    'PySide6.Qt3DLogic', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
    'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtGraphs',
    'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtSpatialAudio',
    'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtPositioning',
    'PySide6.QtSerialPort', 'PySide6.QtSensors', 'PySide6.QtTextToSpeech',
    'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtDesigner', 'PySide6.QtHelp',
    'PySide6.QtUiTools', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
    # Never imported by this app
    'tkinter', 'matplotlib', 'scipy', 'pandas', 'IPython', 'notebook', 'pytest',
    'PyQt5', 'PyQt6', 'PySide2',
]

a = Analysis([
    'videoannotation.py'
],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=APP_NAME,
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False,
          icon='assets/icon.ico')
