# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PySide6-based Video Annotation Tool (macOS)

# DEPRECATED: macOS bundle spec. macOS builds are not officially supported.

from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['videoannotation.py'],
    pathex=[],
    binaries=[('/opt/homebrew/bin/ffmpeg', 'ffmpeg/bin'), ('/opt/homebrew/bin/ffprobe', 'ffmpeg/bin')],
    datas=collect_data_files('PySide6', include_py_files=False),
    hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VideoAnnotationTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.icns',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VideoAnnotationTool',
)
app = BUNDLE(
    coll,
    name='VideoAnnotationTool.app',
    icon='assets/icon.icns',
    bundle_identifier=None,
    info_plist={
        'NSMicrophoneUsageDescription': 'Video Annotation Tool needs microphone access to record annotations.',
        'NSDesktopFolderUsageDescription': 'Allow access to Desktop to open and save annotated videos and audio.',
        'NSDocumentsFolderUsageDescription': 'Allow access to Documents to manage project folders, metadata, and recordings.',
        'NSDownloadsFolderUsageDescription': 'Allow access to Downloads to open videos for annotation.',
        'NSNetworkVolumesUsageDescription': 'Allow access to files on network volumes for annotation projects.',
        'NSRemovableVolumesUsageDescription': 'Allow access to external drives (USB/SD) to read/write project media.',
    },
)
