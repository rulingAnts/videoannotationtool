# PyInstaller spec for PySide6-based Visual Stimulus Kit Tool
# ONEDIR (one-folder portable bundle) build.
#
# Unlike the onefile build, nothing is extracted at launch: the small
# launcher .exe loads its libraries directly from the _internal folder
# beside it, so startup is dramatically faster (and the OS caches the
# files between runs). Distributed as a ZIP the user extracts once.
#
# NOTE: pyinstaller.spec builds the same app as a single .exe. The Analysis
# configuration below is intentionally duplicated there -- keep the two in
# sync when changing datas/hiddenimports/excludes.

block_cipher = None

datas = [
    ('assets/icon.ico', 'assets'),
    ('assets/icon.png', 'assets'),
    ('assets/ffmpeg-bin/windows/ffmpeg.exe', 'assets/ffmpeg-bin/windows'),
    ('assets/ffmpeg-bin/windows/ffprobe.exe', 'assets/ffmpeg-bin/windows'),
]
datas += [('vat/i18n/labels.yaml', 'vat/i18n')]
# See pyinstaller.spec for why collect_data_files('PySide6') is not used.

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

# exclude_binaries=True keeps the payload out of the .exe; COLLECT places it
# alongside (PyInstaller 6.x puts it in an _internal subfolder).
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Visual Stimulus Kit Tool',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False,
          icon='assets/icon.ico')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='Visual Stimulus Kit Tool')
